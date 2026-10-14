"""Synthetic tests for the pinned alternate loader; no corpus/network/model loading."""
from collections import Counter
import json
import math
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from prepare_pilot import digest
from test_train_corpus import fixture
from train_corpus import (
    DATA, DATA_VERSIONS, COMMITBENCH_DATA, check_disk_reserve, data_spec,
    epoch_batches, learning_rate, load_commitbench, load_corpus, run,
    select_checkpoint, training_plan,
)


def bench_fixture(commit='a'*40,repo='train/repo'):
    row=fixture('train',commit,repo)
    row.update(review_status='source_checked_pending_quality_review',
        integrity_status='complete_original_diff_applies_to_exact_snapshots',
        usage_status='noncommercial_research_only_pending_quality_and_distribution_clearance',
        source={'license':'MIT'},dataset={'name':'Maxscha/commitbench',
        'revision':'1500792cd6998308da046ba72b688156b2ffa471','license':'CC-BY-NC-4.0','shard':'train.csv',
        'shard_sha256':'23adc5ca32088e9991882ccd252b0579b95d22d07dc9b0bce739f4e920c96f04'})
    return row


class CommitBenchTrainingTests(unittest.TestCase):
    def load_fixture(self, train=None, validation=None, mutation=None, corrupt_evidence=False):
        train=train or [bench_fixture()]
        validation=validation or [fixture('validation','b'*40,'validation/repo')]
        with tempfile.TemporaryDirectory() as temp:
            workspace=Path(temp)
            root=workspace/'data/commitbench-0001/sources-0002'
            held=workspace/'data/corpus-0001/audit-0002/post-review-pending'
            root.mkdir(parents=True); held.mkdir(parents=True)
            spec={}
            for split,rows,path in [('train',train,root/'train-pending.jsonl'),('validation',validation,held/'validation.jsonl')]:
                raw=('\n'.join(json.dumps(row) for row in rows)+'\n').encode()
                path.write_bytes(raw); spec[split]=(len(rows),digest(raw))
            documents={'manifest.json':{'version':'commitbench-source-expansion-0001-pending','license':'CC-BY-NC-4.0',
                'training_approved':False,'research_run_authorized':False,'target_changes':0,
                'train':{'rows':spec['train'][0],'sha256':spec['train'][1]}},
                'verification.json':{'status':'passed','optimizer_updates':0},
                'quality-review.json':{'dataset_targets_changed':0,'training_approved':False},
                'quality-review-verification.json':{'status':'passed'}}
            if mutation:
                name,key,value=mutation; documents[name][key]=value
            evidence={}
            for name,doc in documents.items():
                raw=json.dumps(doc).encode(); (root/name).write_bytes(raw); evidence[name]=digest(raw)
            if corrupt_evidence: (root/'manifest.json').write_bytes(b'changed after freezing')
            before={str(path):path.read_bytes() for directory in (root,held) for path in directory.iterdir()}
            adapter=Mock(); adapter.encode.return_value=SimpleNamespace(ids=[1,7,2])
            with patch('train_corpus.COMMITBENCH_DATA',spec),patch('train_corpus.COMMITBENCH_EVIDENCE',evidence):
                result=load_commitbench(workspace,adapter)
            self.assertEqual(before,{str(path):path.read_bytes() for directory in (root,held) for path in directory.iterdir()})
            return result,adapter

    def test_only_two_named_versions_and_historical_defaults_unchanged(self):
        self.assertEqual(DATA_VERSIONS,('chronicle-frozen','commitbench-source-0002'))
        self.assertIs(data_spec('chronicle-frozen'),DATA)
        self.assertIs(data_spec('commitbench-source-0002'),COMMITBENCH_DATA)
        self.assertEqual(DATA['train'][0],9758)
        self.assertEqual(COMMITBENCH_DATA['train'][0],10000)
        self.assertEqual(COMMITBENCH_DATA['validation'],DATA['validation'])
        for value in ('arbitrary/path','commitbench','latest',None):
            with self.assertRaises(ValueError): data_spec(value)

    def test_commitbench_accepts_only_explicit_fixed_recipes(self):
        with patch('train_corpus.platform.system',return_value='Windows'):
            for epochs in (1,6,0,99,101,True,3.0,100.0):
                with self.assertRaisesRegex(ValueError,'fixed three- or 100-epoch'):
                    run(Path('workspace'),Path('unused'),epochs=epochs,data_version='commitbench-source-0002')

    def test_hundred_epochs_do_not_relax_the_historical_default(self):
        with patch('train_corpus.platform.system',return_value='Windows'):
            with self.assertRaisesRegex(ValueError,'Chronicle supports only'):
                run(Path('workspace'),Path('unused'),epochs=100)
        for epochs in (99,101):
            with self.assertRaises(ValueError): training_plan(10000,epochs)

    def test_explicit_hundred_recipe_reaches_cuda_gate_without_creating_output(self):
        with tempfile.TemporaryDirectory() as temp:
            output=Path(temp)/'new'
            with patch('train_corpus.platform.system',return_value='Windows'), \
                 patch('train_corpus.training_plan',return_value=[[]]) as plan, \
                 patch('torch.cuda.is_available',return_value=False):
                with self.assertRaisesRegex(RuntimeError,'CUDA unavailable'):
                    run(Path(temp),output,epochs=100,data_version='commitbench-source-0002')
                plan.assert_called_once_with(10000,100)
                self.assertFalse(output.exists())

    def test_all_10000_rows_used_a_hundred_times(self):
        plan=training_plan(10000,100)
        self.assertEqual([len(order) for order in plan],[1250]*100)
        self.assertEqual(sum(len(batch) for order in plan for batch in order),1000000)
        self.assertEqual(Counter(index for order in plan for batch in order for index in batch),
                         Counter({index:100 for index in range(10000)}))
        for order in plan:
            self.assertTrue(all(len(batch)==8 for batch in order))
            self.assertEqual(Counter(index for batch in order for index in batch),Counter(range(10000)))
        self.assertEqual(plan[0],epoch_batches(10000,seed=42))
        self.assertEqual(plan[-1],epoch_batches(10000,seed=141))
        self.assertNotEqual(plan[0],plan[-1])

    def test_hundred_schedule_and_final_epoch_selection(self):
        rates=[learning_rate(step,125000,6250) for step in range(125000)]
        self.assertTrue(all(0<rate<=5e-5 for rate in rates))
        self.assertAlmostEqual(rates[6249],5e-5)
        self.assertGreater(rates[1250],rates[1249])  # Warmup spans five full epochs.
        self.assertLess(rates[6250],rates[6249])
        self.assertLess(rates[12500],rates[12499])
        self.assertLess(rates[-1],rates[6250])
        results=[{'epoch':epoch,'loss':{'validation':float(epoch)}} for epoch in range(1,101)]
        self.assertEqual(select_checkpoint(results)['epoch'],100)

    def test_hundred_disk_guard_preserves_reserve_and_legacy_behavior(self):
        with patch('train_corpus.shutil.disk_usage') as usage:
            check_disk_reserve(Path('output'),3)
            usage.assert_not_called()
            usage.return_value=SimpleNamespace(free=23_000_000_000)
            check_disk_reserve(Path('output'),100)
            usage.return_value=SimpleNamespace(free=21_000_000_000)
            with self.assertRaisesRegex(RuntimeError,'Insufficient disk reserve'):
                check_disk_reserve(Path('output'),100)

    def test_all_10000_rows_used_three_times_and_global_schedule(self):
        plan=training_plan(10000,3)
        self.assertEqual([len(order) for order in plan],[1250]*3)
        self.assertEqual(Counter(index for order in plan for batch in order for index in batch),Counter({index:3 for index in range(10000)}))
        self.assertTrue(all(len(batch)==8 for order in plan for batch in order))
        warmup=math.ceil(3750*.05); self.assertEqual(warmup,188)
        rates=[learning_rate(step,3750,warmup) for step in range(3750)]
        self.assertTrue(all(0<value<=5e-5 for value in rates))
        self.assertLess(rates[1250],rates[1249])
        self.assertLess(rates[2500],rates[2499])

    def test_pinned_pending_rows_load_without_mutating_any_flag(self):
        result,adapter=self.load_fixture()
        self.assertEqual(len(result['train']),1)
        self.assertEqual(len(result['validation']),1)
        self.assertEqual(result['train'][0]['target'],'Replace the old value')
        encoder_texts=[call.args[0] for call in adapter.encode.call_args_list if call.args[0].startswith('summarize changes: ')]
        self.assertEqual(len(encoder_texts),2)
        self.assertFalse(any('Maxscha' in text or 'CC-BY' in text or 'Replace the old value' in text for text in encoder_texts))

    def test_evidence_hash_mismatch_stops_before_loading(self):
        with self.assertRaisesRegex(ValueError,'evidence mismatch'): self.load_fixture(corrupt_evidence=True)

    def test_manifest_cannot_be_promoted_or_rewritten_as_authorized(self):
        for name,key,value in [('manifest.json','training_approved',True),
                               ('manifest.json','research_run_authorized',True),
                               ('manifest.json','target_changes',4),
                               ('manifest.json','license','MIT'),
                               ('verification.json','status','failed'),
                               ('verification.json','optimizer_updates',1),
                               ('quality-review.json','training_approved',True)]:
            with self.assertRaisesRegex(ValueError,'pending-version evidence'):
                self.load_fixture(mutation=(name,key,value))

    def test_provenance_integrity_license_drift_rejected(self):
        for key,value in [('integrity_status','unverified'),('usage_status','approved_for_release')]:
            row=bench_fixture(); row[key]=value
            with self.assertRaisesRegex(ValueError,'provenance/integrity/license'):
                self.load_fixture(train=[row])
        for key,value in [('name','other'),('license','MIT'),('shard','test.csv')]:
            row=bench_fixture(); row['dataset'][key]=value
            with self.assertRaisesRegex(ValueError,'provenance/integrity/license'):
                self.load_fixture(train=[row])
        row=bench_fixture(); row['training_approved']=True
        with self.assertRaisesRegex(ValueError,'Unexpected frozen'): self.load_fixture(train=[row])

    def test_cross_split_repository_commit_and_patch_overlap_rejected(self):
        for row in [fixture('validation','b'*40,'TRAIN/REPO'),
                    fixture('validation','a'*40,'other/repo')]:
            with self.assertRaises(ValueError): self.load_fixture(validation=[row])
        row=fixture('validation','b'*40,'other/repo'); row['patch_id']='a'*40
        with self.assertRaisesRegex(ValueError,'Duplicate'): self.load_fixture(validation=[row])

    def test_token_drift_and_legacy_validation_flags_are_rejected(self):
        row=bench_fixture(); row['input_tokens']=4
        with self.assertRaisesRegex(ValueError,'token lengths differ'): self.load_fixture(train=[row])
        row=fixture('validation','b'*40,'other/repo'); row['review_status']='source_checked_pending_quality_review'
        with self.assertRaisesRegex(ValueError,'Unexpected frozen'): self.load_fixture(validation=[row])

    def test_legacy_loader_never_treats_commitbench_tags_as_chronicle(self):
        row=bench_fixture()
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp); raw=(json.dumps(row)+'\n').encode(); (path/'train.jsonl').write_bytes(raw)
            with patch('train_corpus.DATA',{'train':(1,digest(raw))}):
                with self.assertRaisesRegex(ValueError,'Unexpected frozen'):
                    load_corpus(path,Mock())


if __name__=='__main__': unittest.main()
