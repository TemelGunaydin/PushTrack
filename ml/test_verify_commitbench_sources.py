"""Synthetic provenance and overlap guards for the separate CommitBench adapter."""
import copy
import unittest

from prepare_commitbench import DATASET, REVISION, CSV_SHA
from prepare_pilot import digest
from audit_corpus import changed_text
from verify_commitbench_sources import file_pairs, overlap_reason, source_record
from verify_corpus_sources import ZERO


def example():
    row={'repo_id':'owner/repo','commit_id':'a'*40,'parent_id':'b'*40,'patch_id':'c'*40,
         'message':'Replace the old assignment','diff':'@@ -1 +1 @@\n-a = 1\n+b = 2\n',
         'files':['x.py'],'source':{'license':'MIT'},'training_approved':False,
         'dataset':{'name':'JetBrains-Research/commit-chronicle'},
         'source_file_screening':[{'revision':'b'*40,'path':'x.py','blob_sha':'d'*40},
                                  {'revision':'a'*40,'path':'x.py','blob_sha':'e'*40}]}
    candidate={'repo_id':'owner/repo','commit_id':'a'*40,'subject':row['message'],'row_index':17,
               'published_diff_sha256':'f'*64,'published_message_sha256':'1'*64,
               'published_diff_languages':"{'Python': 1}"}
    return row,candidate


class CommitBenchSourceTests(unittest.TestCase):
    def test_compiled_data_license_is_not_replaced_by_git_source_license(self):
        row,candidate=example(); original=copy.deepcopy(row)
        result=source_record(row,candidate)
        self.assertEqual(row,original)
        self.assertEqual(result['dataset']['name'],DATASET)
        self.assertEqual(result['dataset']['revision'],REVISION)
        self.assertEqual(result['dataset']['shard_sha256'],CSV_SHA)
        self.assertEqual(result['dataset']['license'],'CC-BY-NC-4.0')
        self.assertEqual(result['source']['license'],'MIT')
        self.assertFalse(result['training_approved'])
        self.assertIn('noncommercial',result['usage_status'])
        self.assertEqual(result['diff'],original['diff'])
        self.assertEqual(result['dataset']['row_index'],17)

    def test_mismatched_source_identity_or_subject_stops(self):
        for key in ('commit_id','repo_id','message'):
            row,candidate=example(); row[key]='different'
            with self.assertRaisesRegex(ValueError,'identity/subject'):
                source_record(row,candidate)

    def test_overlap_checks_old_holds_patches_parents_text_and_file_pairs(self):
        row,_=example()
        self.assertIsNone(overlap_reason(row,set(),set(),set(),set(),set()))
        self.assertEqual(overlap_reason(row,{row['commit_id']},set(),set(),set(),set()),'legacy_or_duplicate_commit')
        self.assertEqual(overlap_reason(row,set(),set(),set(),set(),{row['parent_id']}),'validation_commit_or_parent_overlap')
        self.assertEqual(overlap_reason(row,set(),{row['patch_id']},set(),set(),set()),'legacy_or_duplicate_stable_patch')
        self.assertEqual(overlap_reason(row,set(),set(),{digest(changed_text(row['diff']).encode())},set(),set()),'legacy_or_duplicate_changed_text')
        self.assertEqual(overlap_reason(row,set(),set(),set(),file_pairs(row),set()),'legacy_or_duplicate_file_change')

    def test_additions_and_deletions_use_explicit_zero_side(self):
        row,_=example()
        self.assertEqual(file_pairs(row),{('d'*40,'e'*40)})
        row['source_file_screening']=row['source_file_screening'][1:]
        self.assertEqual(file_pairs(row),{(ZERO,'e'*40)})
        row['source_file_screening']=[{'revision':row['parent_id'],'path':'x.py','blob_sha':'d'*40}]
        self.assertEqual(file_pairs(row),{('d'*40,ZERO)})


if __name__=='__main__': unittest.main()
