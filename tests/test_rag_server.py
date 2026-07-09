import os
import json
import tempfile
import unittest
from unittest.mock import patch, MagicMock

import numpy as np
import storage
import schema


class TestRagServer(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_path = self.tmp.name
        self.tmp.close()
        storage.init_db(self.db_path)
        storage.init_embeddings_table(self.db_path)

        # 테스트 레코드 + 임베딩
        rows = [
            {f: None for f in schema.SCHEMA_FIELDS}
            | {"source_type": "national", "source_service_id": "SVC001",
               "title": "암환자 의료비 지원", "summary": "암 치료비",
               "cancer_relevance": "high", "region_sido": None},
            {f: None for f in schema.SCHEMA_FIELDS}
            | {"source_type": "local", "source_service_id": "SVC002",
               "title": "창업 지원", "summary": "소상공인 대출",
               "cancer_relevance": "exclude", "region_sido": "서울"},
        ]
        storage.upsert_services(self.db_path, rows)

        # SVC001은 암 관련 → 쿼리와 유사하게, SVC002는 비관련
        storage.upsert_embedding(self.db_path, "national", "SVC001", [0.9, 0.1, 0.0], "mistral-embed")
        storage.upsert_embedding(self.db_path, "local", "SVC002", [0.0, 0.1, 0.9], "mistral-embed")

    def tearDown(self):
        os.unlink(self.db_path)

    @patch("embed.get_embedding")
    def test_rag_search_returns_sorted_by_similarity(self, mock_embed):
        # 쿼리 벡터가 SVC001과 유사
        mock_embed.return_value = [0.9, 0.1, 0.0]

        # rag_server를 import하고 DB 경로 오버라이드
        import rag_server
        rag_server.DB_PATH = self.db_path

        from fastapi.testclient import TestClient
        client = TestClient(rag_server.app)
        resp = client.post("/api/rag-search", json={
            "form": {},
            "free_text": "암 치료비가 부담됩니다"
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertGreater(data["total"], 0)
        # 첫 번째 결과가 SVC001 (더 유사)
        self.assertEqual(data["results"][0]["source_service_id"], "SVC001")
        self.assertIn("similarity", data["results"][0])

    @patch("embed.get_embedding")
    def test_rag_search_filters_by_region(self, mock_embed):
        mock_embed.return_value = [0.5, 0.5, 0.5]

        import rag_server
        rag_server.DB_PATH = self.db_path

        from fastapi.testclient import TestClient
        client = TestClient(rag_server.app)
        resp = client.post("/api/rag-search", json={
            "form": {"region_sido": "부산"},
            "free_text": "도움이 필요합니다"
        })
        data = resp.json()
        # 부산 지역 → 서울 local은 제외, national(region_sido=None)은 포함
        sids = [r["source_service_id"] for r in data["results"]]
        self.assertIn("SVC001", sids)  # national, 항상 포함
        self.assertNotIn("SVC002", sids)  # 서울 local, 부산 필터에 제외

    @patch("embed.get_embedding")
    def test_rag_search_empty_input(self, mock_embed):
        mock_embed.return_value = [0.5, 0.5, 0.5]

        import rag_server
        rag_server.DB_PATH = self.db_path

        from fastapi.testclient import TestClient
        client = TestClient(rag_server.app)
        resp = client.post("/api/rag-search", json={
            "form": {},
            "free_text": ""
        })
        # 빈 입력도 에러 없이 결과 반환 (전체 유사도 기반 정렬)
        self.assertEqual(resp.status_code, 200)


if __name__ == "__main__":
    unittest.main()
