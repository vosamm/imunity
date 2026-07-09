import os
import tempfile
import unittest
import numpy as np

import storage

class TestEmbeddingStorage(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_path = self.tmp.name
        self.tmp.close()
        storage.init_db(self.db_path)
        storage.init_embeddings_table(self.db_path)

    def tearDown(self):
        os.unlink(self.db_path)

    def test_upsert_and_load(self):
        vec = [0.1, 0.2, 0.3]
        storage.upsert_embedding(self.db_path, "national", "SVC001", vec, "mistral-embed")
        rows = storage.load_all_embeddings(self.db_path)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["source_type"], "national")
        self.assertEqual(rows[0]["source_service_id"], "SVC001")
        np.testing.assert_array_almost_equal(rows[0]["vector"], np.array(vec))

    def test_upsert_overwrites(self):
        storage.upsert_embedding(self.db_path, "national", "SVC001", [0.1, 0.2], "mistral-embed")
        storage.upsert_embedding(self.db_path, "national", "SVC001", [0.9, 0.8], "mistral-embed")
        rows = storage.load_all_embeddings(self.db_path)
        self.assertEqual(len(rows), 1)
        np.testing.assert_array_almost_equal(rows[0]["vector"], np.array([0.9, 0.8]))

    def test_load_empty(self):
        rows = storage.load_all_embeddings(self.db_path)
        self.assertEqual(rows, [])

if __name__ == "__main__":
    unittest.main()
