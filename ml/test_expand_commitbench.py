"""Synthetic expansion tests; no corpus, network, model or optimizer use."""
import copy
import json
from pathlib import Path
import sqlite3
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from expand_commitbench import ATTEMPT_PER_REPO, TARGET, ExpansionGit, audit_result, quality_sample, select_jobs, tree_hashes
from prepare_pilot import Reject, digest
from verify_corpus_sources import GitSource


def row(repo, index):
    return {"repo_id":repo,"commit_id":f"{index:040x}","split":"train","training_approved":False,
            "priority":f"{index:040x}"}


class CommitBenchExpansionTests(unittest.TestCase):
    def test_selection_is_deterministic_bounded_and_skips_prior_holds(self):
        db=sqlite3.connect(':memory:')
        db.execute('CREATE TABLE candidates (commit_id TEXT PRIMARY KEY,repo_id TEXT,priority TEXT,record TEXT)')
        for repo,base in [('org/train',1),('org/held',1000),('org/outside',2000)]:
            for index in range(base,base+220):
                record=row(repo,index)
                db.execute('INSERT INTO candidates VALUES (?,?,?,?)',(record['commit_id'],repo,record['priority'],json.dumps(record)))
        excluded={f'{index:040x}' for index in range(1,11)}
        jobs=select_jobs(db,excluded,{'org/train','org/held'},{'org/held'})
        self.assertEqual([job[0] for job in jobs],['org/train'])
        self.assertEqual(len(jobs[0][1]),ATTEMPT_PER_REPO)
        self.assertFalse(excluded & {value['commit_id'] for value in jobs[0][1]})
        self.assertEqual(jobs,select_jobs(db,excluded,{'org/train','org/held'},{'org/held'}))
        self.assertEqual(db.execute('SELECT COUNT(*) FROM candidates').fetchone()[0],660)
        db.close()

    def test_selection_identity_or_split_drift_is_fatal(self):
        for key,value in [('split','validation'),('training_approved',True),('repo_id','other/repo')]:
            db=sqlite3.connect(':memory:')
            db.execute('CREATE TABLE candidates (commit_id TEXT,repo_id TEXT,priority TEXT,record TEXT)')
            record=row('org/train',1); record[key]=value
            db.execute('INSERT INTO candidates VALUES (?,?,?,?)',(record['commit_id'],'org/train','1',json.dumps(record)))
            with self.assertRaisesRegex(ValueError,'identity/split'):
                select_jobs(db,set(),{'org/train'},set())
            db.close()

    def test_quality_sample_uses_only_predeclared_identity_rank(self):
        rows=[dict(row('org/repo',index),message='Uninspected subject') for index in range(100)]
        expected=sorted(rows,key=lambda record:digest(('commitbench-expansion-quality-42:'+record['commit_id']).encode()))[:40]
        self.assertEqual(quality_sample(rows),expected)
        changed=[dict(record,message='Other target') for record in rows]
        self.assertEqual([r['commit_id'] for r in quality_sample(rows)],[r['commit_id'] for r in quality_sample(changed)])
        self.assertEqual(TARGET,10000)

    def test_audit_gate_holds_entire_repository_on_integrity_error(self):
        result={'repo_id':'org/repo','rows':[row('org/repo',1),row('org/repo',2)],'outcomes':[]}
        audit={'rows':[{'commit_id':result['rows'][0]['commit_id'],'flags':[]}],
               'errors':[{'commit_id':result['rows'][1]['commit_id'],'error':'bad patch'}],'fsck':'pass'}
        with patch('expand_commitbench.audit_repo',return_value=audit):
            audit_result(result,Path('new-output'),Path('workspace'))
        self.assertEqual(result['rows'],[])
        self.assertEqual(len(result['outcomes']),2)
        self.assertTrue(all(value['reason']=='integrity_audit_hold' for value in result['outcomes']))

    def test_audit_flags_do_not_automatically_rewrite_or_approve_labels(self):
        original=dict(row('org/repo',1),message='Original target')
        result={'repo_id':'org/repo','rows':[copy.deepcopy(original)],'outcomes':[]}
        audit={'rows':[{'commit_id':original['commit_id'],'flags':['email_like_input_context']}],'errors':[],'fsck':'pass'}
        with patch('expand_commitbench.audit_repo',return_value=audit):
            audit_result(result,Path('new-output'),Path('workspace'))
        self.assertEqual(result['rows'][0]['message'],original['message'])
        self.assertFalse(result['rows'][0]['training_approved'])
        self.assertEqual(result['rows'][0]['inspection_flags'],['email_like_input_context'])
        self.assertEqual(result['outcomes'],[])

    def test_invalid_fetch_identity_is_rejected_before_batch_or_network(self):
        git=object.__new__(ExpansionGit)
        with patch.object(git,'run') as command:
            with self.assertRaises(Reject): git.fetch(['--option'])
            command.assert_not_called()

    def test_only_missing_blobs_are_fetched_and_order_is_checked(self):
        git=object.__new__(ExpansionGit); git.reused_blob_count=0
        shas=['a'*40,'b'*40]
        raw=f'{shas[0]} blob 12\n{shas[1]} missing\n'.encode()
        with patch.object(git,'run',return_value=raw),patch.object(GitSource,'fetch') as network:
            git.fetch(shas)
            network.assert_called_once_with([shas[1]],commits=False)
        self.assertEqual(git.reused_blob_count,1)
        with patch.object(git,'run',return_value=b'bad shape\n'),patch.object(GitSource,'fetch') as network:
            with self.assertRaises(ValueError): git.fetch(shas)
            network.assert_not_called()

    def test_cached_seed_is_copied_without_modifying_old_repo(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp); seed=root/'seed'; old=GitSource(seed,'unit/repo',root,threading.Event())
            blob=old.run('hash-object','-w','--stdin',data=b'unit fixture\n').decode().strip()
            before=tree_hashes(seed)
            git=ExpansionGit(root/'new','unit/repo',root,threading.Event(),time.monotonic()+60,seed)
            # No commits or network fetch: reuse the known synthetic local blob.
            with patch.object(GitSource,'fetch') as network:
                git.fetch([blob])
                network.assert_called_once_with([],commits=False)
            self.assertEqual(git.blob(blob),b'unit fixture\n')
            self.assertEqual(git.reused_blob_count,1)
            self.assertEqual(tree_hashes(seed),before)
            self.assertNotEqual((root/'new/config').read_bytes(),(seed/'config').read_bytes())
            self.assertEqual(git.env['GIT_NO_LAZY_FETCH'],'1')


if __name__=='__main__': unittest.main()
