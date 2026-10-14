"""Synthetic train-only/schema/selection tests; no dataset/network/model access."""
from collections import Counter
import copy
import json
import sqlite3
from types import SimpleNamespace
import unittest

from prepare_commitbench import choose_pilot, flush, inspect_record, project_identity
from prepare_pilot import PREFIX, Reject


def example():
    return {"project":"Example-Org_repo_with_underscores","hash":"a"*40,"split":"train",
            "message":"Replace the old assignment\n\nFull message retained in the CSV.",
            "diff_languages":"{'Python': 1}",
            "diff":"diff --git a/x.py b/x.py\n--- a/x.py\n+++ b/x.py\n@@ -1 +1 @@\n-a = 1\n+b = 2\n"}


def inspect(row):
    return inspect_record(row,7,{'example-org/repo_with_underscores'},set(),set())


def database():
    connection=sqlite3.connect(':memory:')
    connection.execute('CREATE TABLE candidates (commit_id TEXT PRIMARY KEY,repo_id TEXT NOT NULL,diff_sha TEXT UNIQUE NOT NULL,priority TEXT NOT NULL,record TEXT NOT NULL)')
    return connection


class Tokenizer:
    all_special_ids=[0,1,2]
    def __init__(self, target_size=3, input_size=3, marker=False):
        self.target_size,self.input_size,self.marker=target_size,input_size,marker
        self.calls=[]
    def ids(self,text):
        size=self.input_size if text.startswith(PREFIX) else self.target_size
        return [1]+([0] if self.marker else [3]*(size-2))+[2]
    def __call__(self,texts,**kwargs):
        self.calls.append(kwargs)
        return {'input_ids':[self.ids(text) for text in texts]}


class Adapter:
    def __init__(self,**kwargs): self.tokenizer=Tokenizer(**kwargs)
    def encode(self,text): return SimpleNamespace(ids=self.tokenizer.ids(text))


class CommitBenchPreparationTests(unittest.TestCase):
    def test_owner_separator_preserves_repository_underscores(self):
        self.assertEqual(project_identity('Example-Org_repo_with_underscores'),'example-org/repo_with_underscores')
        for name in ('invalid','_repo','owner_','../x_r','owner_../evil','https://github.com/a_b'):
            with self.assertRaises(Reject): project_identity(name)

    def test_nontrain_row_is_fatal_not_silently_skipped(self):
        for split in ('test','val','validation',None):
            row=example(); row['split']=split
            with self.assertRaisesRegex(ValueError,'Non-training'): inspect(row)

    def test_current_validation_and_outside_training_repositories_excluded(self):
        row=example(); repo=project_identity(row['project'])
        for train,held in ((set(),set()),({repo},{repo})):
            with self.assertRaisesRegex(Reject,'outside_reserved'):
                inspect_record(row,0,train,held,set())

    def test_earlier_identities_and_holds_cannot_be_resurrected(self):
        row=example()
        with self.assertRaisesRegex(Reject,'legacy_identity'):
            inspect_record(row,0,{project_identity(row['project'])},set(),{row['hash']})

    def test_candidate_preserves_original_pair_and_coordinate(self):
        row=example(); before=copy.deepcopy(row); result=inspect(row)
        self.assertEqual(row,before)
        self.assertEqual(result['row_index'],7)
        self.assertEqual(result['published_diff'],row['diff'])
        self.assertEqual(result['subject'],row['message'].splitlines()[0])
        self.assertEqual(result['published_diff_languages'],row['diff_languages'])

    def test_paths_controls_and_token_markers(self):
        for value,reason in (('diff --git a/../x b/../x\n','published_path'),
                             ('diff --git a/x b/y\n','published_path'),
                             ('diff --git a/Cargo.lock b/Cargo.lock\n','published_generated'),
                             ('diff --git a/x b/x\n+bad\x00text','published_secret')):
            row=example(); row['diff']=value
            with self.assertRaisesRegex(Reject,reason): inspect(row)
        con=database(); counts=Counter(); rows=[inspect(example())]
        self.assertEqual(flush(con,rows,Adapter(marker=True),counts),0)
        self.assertEqual(counts['reserved_or_unknown_token'],1)
        con.close()

    def test_limits_without_truncation_and_no_approval(self):
        for kwargs in ({'target_size':65},{'input_size':513}):
            con=database(); counts=Counter(); rows=[inspect(example())]; adapter=Adapter(**kwargs)
            self.assertEqual(flush(con,rows,adapter,counts),0)
            self.assertEqual(counts['published_token_budget'],1)
            self.assertFalse(adapter.tokenizer.calls[0]['truncation'])
            con.close()
        con=database(); counts=Counter(); rows=[inspect(example())]
        self.assertEqual(flush(con,rows,Adapter(),counts),1)
        stored=json.loads(con.execute('SELECT record FROM candidates').fetchone()[0])
        self.assertFalse(stored['training_approved'])
        self.assertEqual(stored['review_status'],'unverified_commitbench_candidate')
        con.close()

    def test_duplicate_accounting_and_pilot_caps(self):
        con=database(); counts=Counter(); row=inspect(example())
        self.assertEqual(flush(con,[copy.deepcopy(row),copy.deepcopy(row)],Adapter(),counts),1)
        self.assertEqual(counts['duplicate_commit_or_published_diff'],1)
        con.execute('DELETE FROM candidates')
        for i in range(25):
            for j in range(12):
                key=f'{i:02}-{j:02}'
                record={'repo_id':f'org/r{i}','commit_id':key}
                con.execute('INSERT INTO candidates VALUES (?,?,?,?,?)',(key,record['repo_id'],key,key,json.dumps(record)))
        selected=choose_pilot(con,{'org/r0'})
        self.assertEqual(len(selected),200)
        self.assertEqual(len({r['repo_id'] for r in selected}),20)
        self.assertNotIn('org/r0',{r['repo_id'] for r in selected})
        self.assertTrue(all(count==10 for count in Counter(r['repo_id'] for r in selected).values()))
        self.assertEqual(selected,choose_pilot(con,{'org/r0'}))
        con.close()


if __name__=='__main__': unittest.main()
