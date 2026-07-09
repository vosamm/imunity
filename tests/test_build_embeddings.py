# tests/test_build_embeddings.py
import os
import tempfile
import unittest
from unittest.mock import patch, MagicMock

import storage
import schema

class TestBuildEmbeddings(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_path = self.tmp.name
        self.tmp.close()
        storage.init_db(self.db_path)
        # 테스트용 레코드 2건 삽입
        rows = [
            {f: None for f in schema.SCHEMA_FIELDS}
            | {"source_type": "national", "source_service_id": "SVC001",
               "title": "암환자 의료비", "summary": "치료비 지원", "target": "암환자",
               "benefit": "의료비 지원", "criteria": "소득 기준"},
            {f: None for f in schema.SCHEMA_FIELDS}
            | {"source_type": "local", "source_service_id": "SVC002",
               "title": "생계 지원", "summary": "긴급 생계", "target": "저소득층",
               "benefit": "생활비 지원", "criteria": None},
        ]
        storage.upsert_services(self.db_path, rows)

    def tearDown(self):
        os.unlink(self.db_path)

    @patch("embed.get_embeddings")
    def test_build_embeddings_creates_vectors(self, mock_embed):
        mock_embed.return_value = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]

        from build_db import build_embeddings
        count = build_embeddings(self.db_path)
        self.assertEqual(count, 2)

        rows = storage.load_all_embeddings(self.db_path)
        self.assertEqual(len(rows), 2)

    @patch("embed.get_embeddings")
    def test_build_embeddings_concatenates_text_fields(self, mock_embed):
        mock_embed.return_value = [[0.1]]

        from build_db import build_embeddings
        build_embeddings(self.db_path)

        call_args = mock_embed.call_args[0][0]
        # 첫 번째 레코드: title + summary + target + benefit + criteria
        self.assertIn("암환자 의료비", call_args[0])
        self.assertIn("치료비 지원", call_args[0])

if __name__ == "__main__":
    unittest.main()
