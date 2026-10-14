"""Synthetic, offline regression proof for corpus audit checks."""
import hashlib
from pathlib import Path
import tempfile
import threading
import unittest

from audit_corpus import CachedGit, IntegrityError, apply_section, family_identity, label_flags, near_overlap, parse_batch
from verify_corpus_sources import GitSource


class CorpusAuditTests(unittest.TestCase):
    def test_exact_application_with_multiple_hunks(self):
        patch = b'diff --git a/f b/f\n--- a/f\n+++ b/f\n@@ -1,2 +1,2 @@\n one\n-two\n+TWO\n@@ -4 +4,2 @@\n four\n+five\n'
        self.assertEqual(apply_section(patch, b'one\ntwo\nthree\nfour\n'), b'one\nTWO\nthree\nfour\nfive\n')
        with self.assertRaises(IntegrityError):
            apply_section(patch, b'one\nwrong\nthree\nfour\n')

    def test_add_delete_and_missing_final_newline(self):
        add = b'@@ -0,0 +1 @@\n+new\n\\ No newline at end of file\n'
        delete = b'@@ -1 +0,0 @@\n-old\n\\ No newline at end of file\n'
        self.assertEqual(apply_section(add, b''), b'new')
        self.assertEqual(apply_section(delete, b'old'), b'')
        replace = b'@@ -1 +1 @@\n-old\n\\ No newline at end of file\n+new\n'
        self.assertEqual(apply_section(replace, b'old'), b'new\n')

    def test_crlf_and_unicode_are_not_normalized(self):
        patch = '@@ -1 +1 @@\n-hello\r\n+merhaba\u2028world\r\n'.encode()
        self.assertEqual(apply_section(patch, b'hello\r\n'), 'merhaba\u2028world\r\n'.encode())

    def test_missing_changes_and_bad_positions_rejected(self):
        with self.assertRaises(IntegrityError):
            apply_section(b'@@ -1,2 +1 @@\n-a\n+b\n', b'a\nc\n')
        with self.assertRaises(IntegrityError):
            apply_section(b'@@ -1 +2 @@\n-a\n+b\n', b'a\n')
        with self.assertRaises(IntegrityError):
            apply_section(b'only metadata\n', b'a\n')

    def test_batch_checks_object_bytes_type_and_coverage(self):
        value = b'synthetic\n'
        sha = hashlib.sha1(b'blob 10\0' + value).hexdigest()
        data = (sha + ' blob 10\n').encode() + value + b'\n'
        self.assertEqual(parse_batch(data, [sha]), {sha: ('blob', value)})
        for bad in (data[:-1], data.replace(b'synthetic', b'Synthetic'), (sha + ' missing\n').encode()):
            with self.assertRaises(IntegrityError):
                parse_batch(bad, [sha])
        with self.assertRaises(IntegrityError):
            parse_batch(data, ['a' * 40])

    def test_fork_root_requires_evidence(self):
        root = {'id': 42, 'full_name': 'Owner/Root', 'private': False, 'fork': False}
        self.assertEqual(family_identity(root)['family_id'], 42)
        fork = {'id': 43, 'full_name': 'Other/Fork', 'private': False, 'fork': True, 'source': root}
        self.assertEqual(family_identity(fork)['family_id'], 42)
        del fork['source']
        with self.assertRaises(IntegrityError):
            family_identity(fork)
        with self.assertRaises(IntegrityError):
            family_identity(dict(root, private=True))

    def test_quality_rules_do_not_rewrite_subjects(self):
        message = 'Add useful example (thanks Reviewer)'
        self.assertIn('non_diff_attribution_target', label_flags(message, ''))
        self.assertIn('generic_documentation_target', label_flags('docs: Update the README', ''))
        self.assertIn('email_like_input_context', label_flags('Improve the example', '+author@example.test'))
        self.assertEqual(label_flags('Fix missing return value', '+return value;'), set())

    def test_path_independent_similarity_and_trivial_exclusion(self):
        changes = ''.join(f'+call_{i}(value_{i}, argument_{i});\n' for i in range(12))
        rows = [{'commit_id': 'v', 'split': 'validation', 'diff': '+++ b/first\n' + changes},
                {'commit_id': 't', 'split': 'train', 'diff': '+++ b/other\n' + changes}]
        self.assertEqual(near_overlap(rows), [{'train_commit': 't', 'validation_commit': 'v', 'changed_token_jaccard': 1.0}])
        for row in rows:
            row['diff'] = '+return true;\n'
        self.assertEqual(near_overlap(rows), [])

    def test_cached_git_is_read_only_and_patch_ids_are_batched(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            GitSource(root / 'repo', 'owner/repo', root, threading.Event())
            git = CachedGit(root / 'repo', root)
            with self.assertRaisesRegex(IntegrityError, 'read_only_git_command'):
                git.run('fetch', 'origin')
            diff = 'diff --git a/f b/f\n--- a/f\n+++ b/f\n@@ -1 +1 @@\n-a\n+b\n'
            shas = ['a' * 40, 'b' * 40]
            output = git.run('patch-id', '--stable', data=''.join('commit ' + sha + '\n' + diff for sha in shas).encode()).decode().splitlines()
            self.assertEqual([line.split()[1] for line in output], shas)
            self.assertEqual(output[0].split()[0], output[1].split()[0])


if __name__ == '__main__':
    unittest.main()
