"""Manifest-only tests; never access the network or real data."""
import copy
import unittest

from download_corpus import EXPECTED_BYTES, EXPECTED_SHARDS, selected_shards


class CorpusManifestTests(unittest.TestCase):
    def manifest(self):
        rows = []
        for split, count in EXPECTED_SHARDS.items():
            for number in range(count):
                size = EXPECTED_BYTES // 73
                rows.append({"path": f"data/{split}-{number:05}-of-{count:05}-abcdef0123456789.parquet",
                             "size": size, "lfs": {"oid": "a" * 64, "size": size}})
        remainder = EXPECTED_BYTES - sum(r["size"] for r in rows)
        rows[-1]["size"] += remainder
        rows[-1]["lfs"]["size"] += remainder
        return rows

    def test_selects_train_validation_not_test(self):
        rows = self.manifest() + [{"path": "data/test-00000-of-00012-deadbeef.parquet"}]
        self.assertEqual(len(selected_shards(rows)), 73)
        self.assertEqual({r["split"] for r in selected_shards(rows)}, {"train", "validation"})

    def test_missing_or_duplicate_shard_rejected(self):
        rows = self.manifest()
        for broken in (rows[:-1], rows + [copy.deepcopy(rows[0])]):
            with self.assertRaisesRegex(ValueError, "Incomplete or duplicate"):
                selected_shards(broken)

    def test_invalid_hash_rejected(self):
        rows = self.manifest()
        rows[0]["lfs"]["oid"] = "not a SHA-256"
        with self.assertRaises(ValueError):
            selected_shards(rows)

    def test_unexpected_total_rejected(self):
        rows = self.manifest()
        rows[0]["size"] += 1
        rows[0]["lfs"]["size"] += 1
        with self.assertRaisesRegex(ValueError, "total"):
            selected_shards(rows)


if __name__ == "__main__":
    unittest.main()
