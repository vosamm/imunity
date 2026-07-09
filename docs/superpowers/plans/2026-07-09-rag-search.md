# RAG 기반 AI 매칭 검색 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 환자가 폼(나이/암종류/지역/소득) + 자유 텍스트로 본인 정보를 입력하면, Mistral 임베딩 + 코사인 유사도로 DB에서 관련 복지 서비스를 검색하는 RAG 기능 추가.

**Architecture:** Python FastAPI 서버(`rag_server.py`)가 임베딩 검색을 담당. `build_db.py`에서 임베딩 생성 단계 추가. Next.js 프론트엔드에 "AI 매칭" 탭을 추가하고, Next.js API route가 Python 서버로 프록시.

**Tech Stack:** Python (FastAPI, uvicorn, numpy, Mistral Embed API), SQLite (embeddings 테이블), Next.js (기존 UI 확장)

## Global Constraints

- Python 의존성: `requirements.txt`에 추가 (`fastapi`, `uvicorn`, `numpy`)
- Mistral API 키: 기존 `.env`의 `MISTRAL_API_KEY` 재사용
- DB 경로: `data/welfare.db` (기존과 동일)
- 로컬 전용 — 배포 설정 불필요
- 테스트는 네트워크 없이 실행 가능해야 함 (Mistral API 스텁)
- 기존 키워드 검색 UI/API는 변경하지 않음

---

### Task 1: 임베딩 생성 모듈 (`embed.py`)

Mistral Embed API를 호출해 텍스트를 벡터로 변환하는 모듈.

**Files:**
- Create: `embed.py`
- Create: `tests/test_embed.py`

**Interfaces:**
- Consumes: `MISTRAL_API_KEY` 환경변수
- Produces:
  - `get_embeddings(texts: list[str]) -> list[list[float]]` — 텍스트 리스트를 임베딩 벡터 리스트로 변환
  - `get_embedding(text: str) -> list[float]` — 단일 텍스트 임베딩

- [ ] **Step 1: Write the failing test**

```python
# tests/test_embed.py
import unittest
from unittest.mock import patch, MagicMock

class TestEmbed(unittest.TestCase):
    @patch("embed.requests.post")
    def test_get_embeddings_returns_vectors(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "data": [
                {"embedding": [0.1, 0.2, 0.3]},
                {"embedding": [0.4, 0.5, 0.6]},
            ]
        }
        mock_post.return_value = mock_resp

        import embed
        result = embed.get_embeddings(["hello", "world"])
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0], [0.1, 0.2, 0.3])

    @patch("embed.requests.post")
    def test_get_embedding_single(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "data": [{"embedding": [0.1, 0.2, 0.3]}]
        }
        mock_post.return_value = mock_resp

        import embed
        result = embed.get_embedding("hello")
        self.assertEqual(result, [0.1, 0.2, 0.3])

    @patch("embed.requests.post")
    def test_get_embeddings_batches_large_input(self, mock_post):
        """Mistral embed API는 배치 제한이 있으므로 큰 입력은 분할해야 한다."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        # 각 배치마다 호출
        mock_resp.json.return_value = {
            "data": [{"embedding": [0.1]} for _ in range(16)]
        }
        mock_post.return_value = mock_resp

        import embed
        texts = [f"text_{i}" for i in range(32)]
        result = embed.get_embeddings(texts)
        self.assertEqual(len(result), 32)
        # 2번 호출 (배치 크기 16)
        self.assertEqual(mock_post.call_count, 2)

if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `DATA_GO_KR_KEY=dummy MISTRAL_API_KEY=dummy .venv/bin/python -m pytest tests/test_embed.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'embed'`

- [ ] **Step 3: Write minimal implementation**

```python
# embed.py
"""Mistral Embed API를 호출해 텍스트를 벡터로 변환한다."""
import os
import requests
from dotenv import load_dotenv

load_dotenv()

MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY", "")
EMBED_MODEL = "mistral-embed"
EMBED_URL = "https://api.mistral.ai/v1/embeddings"
BATCH_SIZE = 16  # Mistral embed API 배치 제한


def get_embeddings(texts: list[str]) -> list[list[float]]:
    """텍스트 리스트를 임베딩 벡터 리스트로 변환한다. 큰 입력은 배치 분할."""
    all_vectors = []
    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i : i + BATCH_SIZE]
        resp = requests.post(
            EMBED_URL,
            headers={
                "Authorization": f"Bearer {MISTRAL_API_KEY}",
                "Content-Type": "application/json",
            },
            json={"model": EMBED_MODEL, "input": batch},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()["data"]
        all_vectors.extend([item["embedding"] for item in data])
    return all_vectors


def get_embedding(text: str) -> list[float]:
    """단일 텍스트를 임베딩 벡터로 변환한다."""
    return get_embeddings([text])[0]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `DATA_GO_KR_KEY=dummy MISTRAL_API_KEY=dummy .venv/bin/python -m pytest tests/test_embed.py -v`
Expected: 3 tests PASS

- [ ] **Step 5: Commit**

```bash
git add embed.py tests/test_embed.py
git commit -m "feat: add Mistral embed API wrapper (embed.py)"
```

---

### Task 2: 임베딩 저장/로드 (`storage.py` 확장)

SQLite에 `embeddings` 테이블을 추가하고 벡터를 저장/조회하는 함수 추가.

**Files:**
- Modify: `storage.py` — `init_embeddings_table`, `upsert_embedding`, `load_all_embeddings` 추가
- Create: `tests/test_embedding_storage.py`

**Interfaces:**
- Consumes: `storage._connect(db_path)`, `numpy`
- Produces:
  - `init_embeddings_table(db_path: str) -> None`
  - `upsert_embedding(db_path: str, source_type: str, source_service_id: str, vector: list[float], model: str) -> None`
  - `load_all_embeddings(db_path: str) -> list[dict]` — `[{"source_type": str, "source_service_id": str, "vector": np.ndarray}, ...]`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_embedding_storage.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `DATA_GO_KR_KEY=dummy MISTRAL_API_KEY=dummy .venv/bin/python -m pytest tests/test_embedding_storage.py -v`
Expected: FAIL — `AttributeError: module 'storage' has no attribute 'init_embeddings_table'`

- [ ] **Step 3: Write minimal implementation**

`storage.py` 끝에 추가:

```python
# --- 임베딩 저장/조회 ---

import numpy as np

def init_embeddings_table(db_path):
    """임베딩 테이블을 생성한다 (없으면)."""
    con = _connect(db_path)
    try:
        con.execute(
            "CREATE TABLE IF NOT EXISTS embeddings ("
            "source_type TEXT, "
            "source_service_id TEXT, "
            "vector BLOB, "
            "model TEXT, "
            "created_at TEXT, "
            "PRIMARY KEY (source_type, source_service_id))"
        )
        con.commit()
    finally:
        con.close()


def upsert_embedding(db_path, source_type, source_service_id, vector, model):
    """임베딩 벡터를 UPSERT한다. vector는 list[float] 또는 np.ndarray."""
    vec_bytes = np.array(vector, dtype=np.float32).tobytes()
    now = datetime.now(timezone.utc).isoformat()
    con = _connect(db_path)
    try:
        con.execute(
            "INSERT INTO embeddings (source_type, source_service_id, vector, model, created_at) "
            "VALUES (?, ?, ?, ?, ?) "
            "ON CONFLICT(source_type, source_service_id) DO UPDATE SET "
            "vector=excluded.vector, model=excluded.model, created_at=excluded.created_at",
            (source_type, source_service_id, vec_bytes, model, now),
        )
        con.commit()
    finally:
        con.close()


def load_all_embeddings(db_path):
    """전체 임베딩을 로드한다. 각 항목은 {source_type, source_service_id, vector(np.ndarray)}."""
    con = _connect(db_path)
    try:
        cur = con.execute("SELECT source_type, source_service_id, vector FROM embeddings")
        rows = []
        for r in cur.fetchall():
            rows.append({
                "source_type": r["source_type"],
                "source_service_id": r["source_service_id"],
                "vector": np.frombuffer(r["vector"], dtype=np.float32),
            })
        return rows
    finally:
        con.close()
```

Note: `storage.py`에 이미 `from datetime import datetime, timezone`가 없으므로 `schema.py`에서 가져오는지 확인. 실제로는 `storage.py` 상단에 `from datetime import datetime, timezone` import를 추가해야 한다.

- [ ] **Step 4: Run test to verify it passes**

Run: `DATA_GO_KR_KEY=dummy MISTRAL_API_KEY=dummy .venv/bin/python -m pytest tests/test_embedding_storage.py -v`
Expected: 3 tests PASS

- [ ] **Step 5: Commit**

```bash
git add storage.py tests/test_embedding_storage.py
git commit -m "feat: add embeddings table to storage layer"
```

---

### Task 3: `build_db.py`에 임베딩 생성 단계 추가

기존 빌드 완료 후 각 서비스의 텍스트를 임베딩하여 DB에 저장.

**Files:**
- Modify: `build_db.py` — `build_embeddings()` 함수 추가, `__main__`에서 호출
- Modify: `requirements.txt` — `fastapi`, `uvicorn`, `numpy` 추가
- Create: `tests/test_build_embeddings.py`

**Interfaces:**
- Consumes: `storage.all_services`, `storage.init_embeddings_table`, `storage.upsert_embedding`, `embed.get_embeddings`
- Produces: `build_embeddings(db_path: str) -> int` — 임베딩 생성된 레코드 수 반환

- [ ] **Step 1: Update requirements.txt**

```
python-dotenv
requests
fastapi
uvicorn
numpy
```

- [ ] **Step 2: Install dependencies**

Run: `.venv/bin/pip install -r requirements.txt`

- [ ] **Step 3: Write the failing test**

```python
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
```

- [ ] **Step 4: Run test to verify it fails**

Run: `DATA_GO_KR_KEY=dummy MISTRAL_API_KEY=dummy .venv/bin/python -m pytest tests/test_build_embeddings.py -v`
Expected: FAIL — `ImportError: cannot import name 'build_embeddings' from 'build_db'`

- [ ] **Step 5: Write minimal implementation**

`build_db.py`에 추가:

```python
import embed
import storage  # 이미 import 되어 있음


def _service_text(row):
    """임베딩에 사용할 텍스트를 생성한다."""
    parts = [row.get("title"), row.get("summary"), row.get("target"),
             row.get("benefit"), row.get("criteria")]
    return " ".join(v for v in parts if v)


def build_embeddings(db_path=DB_PATH):
    """전체 서비스의 임베딩을 생성해 DB에 저장한다."""
    storage.init_embeddings_table(db_path)
    services = storage.all_services(db_path)
    if not services:
        print("임베딩 대상 레코드 없음")
        return 0

    texts = [_service_text(s) for s in services]
    print(f"임베딩 생성 중... ({len(texts)}건)")
    vectors = embed.get_embeddings(texts)

    for svc, vec in zip(services, vectors):
        storage.upsert_embedding(
            db_path,
            svc["source_type"],
            svc["source_service_id"],
            vec,
            embed.EMBED_MODEL,
        )
    print(f"임베딩 {len(vectors)}건 저장 완료")
    return len(vectors)
```

`build_db.py`의 `__main__` 블록을 수정:

```python
if __name__ == "__main__":
    build()
    build_embeddings()
```

- [ ] **Step 6: Run test to verify it passes**

Run: `DATA_GO_KR_KEY=dummy MISTRAL_API_KEY=dummy .venv/bin/python -m pytest tests/test_build_embeddings.py -v`
Expected: 2 tests PASS

- [ ] **Step 7: Commit**

```bash
git add build_db.py requirements.txt tests/test_build_embeddings.py
git commit -m "feat: add embedding generation step to build_db.py"
```

---

### Task 4: RAG 검색 서버 (`rag_server.py`)

FastAPI 서버. 사용자 입력을 받아 임베딩 검색 후 관련 복지 서비스를 반환.

**Files:**
- Create: `rag_server.py`
- Create: `tests/test_rag_server.py`

**Interfaces:**
- Consumes: `storage.load_all_embeddings`, `storage.all_services`, `embed.get_embedding`, `numpy`
- Produces: `POST /api/rag-search` 엔드포인트
  - Request body: `{"form": {"age": int?, "cancer_type": str?, "region_sido": str?, "region_sigungu": str?, "income_level": str?}, "free_text": str?}`
  - Response: `{"total": int, "results": [Service + {"similarity": float}]}`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_rag_server.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `DATA_GO_KR_KEY=dummy MISTRAL_API_KEY=dummy .venv/bin/python -m pytest tests/test_rag_server.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'rag_server'`

- [ ] **Step 3: Write minimal implementation**

```python
# rag_server.py
"""RAG 기반 복지 서비스 검색 API 서버.

사용자 입력(폼 + 자유 텍스트)을 임베딩하고, DB에 저장된 서비스 임베딩과
코사인 유사도를 계산해 관련 서비스를 반환한다.
"""
import os
from typing import Optional

import numpy as np
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import embed
import storage

DB_PATH = os.path.join("data", "welfare.db")

app = FastAPI(title="RAG 복지 검색")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3100"],
    allow_methods=["POST"],
    allow_headers=["*"],
)


class SearchForm(BaseModel):
    age: Optional[int] = None
    cancer_type: Optional[str] = None
    region_sido: Optional[str] = None
    region_sigungu: Optional[str] = None
    income_level: Optional[str] = None


class SearchRequest(BaseModel):
    form: SearchForm = SearchForm()
    free_text: Optional[str] = None


def _build_query_text(req: SearchRequest) -> str:
    """폼 값 + 자유 텍스트를 하나의 자연어 문장으로 합친다."""
    parts = []
    f = req.form
    if f.age is not None:
        parts.append(f"{f.age}세")
    if f.cancer_type:
        parts.append(f"{f.cancer_type} 환자")
    if f.region_sido:
        region = f.region_sido
        if f.region_sigungu:
            region += f" {f.region_sigungu}"
        parts.append(f"{region} 거주")
    if f.income_level:
        parts.append(f"{f.income_level} 소득")
    if req.free_text and req.free_text.strip():
        parts.append(req.free_text.strip())
    return " ".join(parts) if parts else "복지 서비스"


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    dot = np.dot(a, b)
    norm = np.linalg.norm(a) * np.linalg.norm(b)
    if norm == 0:
        return 0.0
    return float(dot / norm)


@app.post("/api/rag-search")
def rag_search(req: SearchRequest):
    query_text = _build_query_text(req)
    query_vec = np.array(embed.get_embedding(query_text), dtype=np.float32)

    # 전체 임베딩 + 서비스 로드
    emb_rows = storage.load_all_embeddings(DB_PATH)
    all_services = {
        (s["source_type"], s["source_service_id"]): s
        for s in storage.all_services(DB_PATH)
    }

    # 유사도 계산
    scored = []
    for emb in emb_rows:
        key = (emb["source_type"], emb["source_service_id"])
        svc = all_services.get(key)
        if svc is None:
            continue
        sim = _cosine_similarity(query_vec, emb["vector"])
        scored.append((sim, svc))

    # 지역 필터
    sido = (req.form.region_sido or "").strip()
    if sido:
        scored = [
            (sim, svc) for sim, svc in scored
            if svc.get("region_sido") is None or svc.get("region_sido") == sido
        ]
    sigungu = (req.form.region_sigungu or "").strip()
    if sigungu:
        scored = [
            (sim, svc) for sim, svc in scored
            if svc.get("region_sigungu") is None or svc.get("region_sigungu") == sigungu
        ]

    # 유사도 내림차순 정렬
    scored.sort(key=lambda x: x[0], reverse=True)

    # Top-K (기본 20건)
    top_k = 20
    results = []
    for sim, svc in scored[:top_k]:
        result = {
            "source_type": svc.get("source_type"),
            "source_service_id": svc.get("source_service_id"),
            "title": svc.get("title"),
            "summary": svc.get("summary"),
            "target": svc.get("target"),
            "criteria": svc.get("criteria"),
            "benefit": svc.get("benefit"),
            "application_method": svc.get("application_method"),
            "contact": svc.get("contact"),
            "links": svc.get("links") or [],
            "ministry": svc.get("ministry"),
            "region_sido": svc.get("region_sido"),
            "region_sigungu": svc.get("region_sigungu"),
            "support_categories": svc.get("support_categories") or [],
            "cancer_relevance": svc.get("cancer_relevance"),
            "cancer_relevance_reason": svc.get("cancer_relevance_reason"),
            "similarity": round(sim, 4),
        }
        results.append(result)

    return {"total": len(results), "results": results}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `DATA_GO_KR_KEY=dummy MISTRAL_API_KEY=dummy .venv/bin/python -m pytest tests/test_rag_server.py -v`
Expected: 3 tests PASS

- [ ] **Step 5: Commit**

```bash
git add rag_server.py tests/test_rag_server.py
git commit -m "feat: add RAG search FastAPI server (rag_server.py)"
```

---

### Task 5: Next.js API 프록시 + AI 매칭 탭 UI

Next.js에 `/api/rag-search` 프록시 route를 추가하고, 프론트엔드에 "AI 매칭" 탭을 추가.

**Files:**
- Create: `web/app/api/rag-search/route.ts`
- Modify: `web/app/page.tsx` — 탭 UI 추가, AI 매칭 폼 + 결과

**Interfaces:**
- Consumes: Python FastAPI `POST localhost:8000/api/rag-search`
- Produces: Next.js `POST /api/rag-search` (프록시), AI 매칭 탭 UI

- [ ] **Step 1: Create the proxy API route**

```typescript
// web/app/api/rag-search/route.ts
import { NextRequest, NextResponse } from "next/server";

export const dynamic = "force-dynamic";

const RAG_SERVER = process.env.RAG_SERVER_URL || "http://localhost:8000";

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const resp = await fetch(`${RAG_SERVER}/api/rag-search`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!resp.ok) {
      return NextResponse.json(
        { error: "RAG 서버 오류" },
        { status: resp.status }
      );
    }
    const data = await resp.json();
    return NextResponse.json(data);
  } catch {
    return NextResponse.json(
      { error: "RAG 서버에 연결할 수 없습니다. rag_server.py가 실행 중인지 확인하세요." },
      { status: 502 }
    );
  }
}
```

- [ ] **Step 2: Add tab UI and AI matching form to page.tsx**

`web/app/page.tsx`를 수정. 기존 `Home` 컴포넌트를 탭 구조로 리팩터:

기존 `<header>` 아래, `<div className="disclaimer">` 아래에 탭 네비게이션 추가:

```tsx
// page.tsx 상단에 state 추가
const [tab, setTab] = useState<"keyword" | "ai">("keyword");

// AI 매칭 탭 전용 state
const [aiAge, setAiAge] = useState("");
const [aiCancerType, setAiCancerType] = useState("");
const [aiSido, setAiSido] = useState("");
const [aiSigungu, setAiSigungu] = useState("");
const [aiIncomeLevel, setAiIncomeLevel] = useState("");
const [aiFreeText, setAiFreeText] = useState("");
const [aiResults, setAiResults] = useState<(Service & { similarity?: number })[]>([]);
const [aiTotal, setAiTotal] = useState(0);
const [aiLoading, setAiLoading] = useState(false);
const [aiSigunguOptions, setAiSigunguOptions] = useState<string[]>([]);
```

탭 UI HTML (disclaimer 아래에 삽입):

```tsx
<div className="tabs" role="tablist">
  <button
    role="tab"
    aria-selected={tab === "keyword"}
    className={`tab ${tab === "keyword" ? "active" : ""}`}
    onClick={() => setTab("keyword")}
  >
    키워드 검색
  </button>
  <button
    role="tab"
    aria-selected={tab === "ai"}
    className={`tab ${tab === "ai" ? "active" : ""}`}
    onClick={() => setTab("ai")}
  >
    AI 매칭
  </button>
</div>
```

AI 매칭 탭 내용 (`tab === "ai"` 일 때 렌더링):

```tsx
{tab === "ai" && (
  <>
    <section className="filters" aria-label="AI 매칭 입력">
      <div className="row">
        <div className="field">
          <label htmlFor="ai-age">나이</label>
          <input
            id="ai-age"
            type="number"
            placeholder="예: 45"
            value={aiAge}
            onChange={(e) => setAiAge(e.target.value)}
          />
        </div>
        <div className="field">
          <label htmlFor="ai-cancer">암 종류</label>
          <input
            id="ai-cancer"
            type="text"
            placeholder="예: 유방암, 폐암"
            value={aiCancerType}
            onChange={(e) => setAiCancerType(e.target.value)}
          />
        </div>
        <div className="field">
          <label htmlFor="ai-sido">지역 (시도)</label>
          <select
            id="ai-sido"
            value={aiSido}
            onChange={(e) => setAiSido(e.target.value)}
          >
            <option value="">전체</option>
            {sidoOptions.map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
        </div>
        <div className="field">
          <label htmlFor="ai-sigungu">시군구</label>
          <select
            id="ai-sigungu"
            value={aiSigungu}
            onChange={(e) => setAiSigungu(e.target.value)}
            disabled={!aiSido || aiSigunguOptions.length === 0}
          >
            <option value="">{aiSido ? "전체" : "시도를 먼저 선택"}</option>
            {aiSigunguOptions.map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
        </div>
        <div className="field">
          <label htmlFor="ai-income">소득 수준</label>
          <select
            id="ai-income"
            value={aiIncomeLevel}
            onChange={(e) => setAiIncomeLevel(e.target.value)}
          >
            <option value="">선택 안함</option>
            <option value="기초생활">기초생활</option>
            <option value="차상위">차상위</option>
            <option value="일반">일반</option>
          </select>
        </div>
      </div>
      <div className="field">
        <label htmlFor="ai-text">추가 상황</label>
        <textarea
          id="ai-text"
          placeholder="예: 치료비가 부담되고 간병인이 필요합니다"
          value={aiFreeText}
          onChange={(e) => setAiFreeText(e.target.value)}
          rows={3}
        />
      </div>
      <button
        type="button"
        className="ai-search-btn"
        onClick={handleAiSearch}
        disabled={aiLoading}
      >
        {aiLoading ? "검색 중..." : "AI 매칭 검색"}
      </button>
    </section>

    <p className="result-meta" role="status" aria-live="polite">
      {aiLoading
        ? "AI가 매칭 중…"
        : aiTotal > 0
        ? `AI 매칭 결과 ${aiTotal}건`
        : aiResults.length === 0 && !aiLoading
        ? ""
        : ""}
    </p>

    {aiResults.length > 0 && (
      <div className="list">
        {aiResults.map((s) => {
          const b = badge(s.cancer_relevance);
          return (
            <button
              key={`${s.source_type}:${s.source_service_id}`}
              className="card"
              onClick={(e) => openDetail(s, e.currentTarget)}
            >
              <div className="card-top">
                <h3>{s.title ?? "(제목 없음)"}</h3>
                <span className={`badge ${b.cls}`}>{b.text}</span>
                {s.similarity != null && (
                  <span className="similarity">
                    {Math.round(s.similarity * 100)}% 일치
                  </span>
                )}
              </div>
              {s.summary ? <p className="summary">{s.summary}</p> : null}
              <div className="meta-row">
                <span className="source-tag">
                  {s.source_type === "national" ? "중앙부처" : "지자체"}
                </span>
                <span>{regionText(s)}</span>
                {s.support_categories.slice(0, 3).map((c) => (
                  <span key={c} className="cat-tag">{c}</span>
                ))}
              </div>
            </button>
          );
        })}
      </div>
    )}
  </>
)}
```

AI 검색 핸들러 함수 (`Home` 컴포넌트 내부):

```tsx
async function handleAiSearch() {
  setAiLoading(true);
  try {
    const resp = await fetch("/api/rag-search", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        form: {
          age: aiAge ? parseInt(aiAge, 10) : null,
          cancer_type: aiCancerType || null,
          region_sido: aiSido || null,
          region_sigungu: aiSigungu || null,
          income_level: aiIncomeLevel || null,
        },
        free_text: aiFreeText || null,
      }),
    });
    const data = await resp.json();
    setAiResults(data.results ?? []);
    setAiTotal(data.total ?? 0);
  } catch {
    setAiResults([]);
    setAiTotal(0);
  } finally {
    setAiLoading(false);
  }
}
```

AI 탭 시도 → 시군구 cascade (기존 `useEffect` 패턴 재사용):

```tsx
useEffect(() => {
  setAiSigungu("");
  if (!aiSido) {
    setAiSigunguOptions([]);
    return;
  }
  fetch(`/api/regions?sido=${encodeURIComponent(aiSido)}`)
    .then((r) => r.json())
    .then((d: { sigungu: string[] }) => setAiSigunguOptions(d.sigungu ?? []))
    .catch(() => setAiSigunguOptions([]));
}, [aiSido]);
```

기존 키워드 검색 섹션을 `{tab === "keyword" && (...)}` 로 감싸기.

- [ ] **Step 3: Add tab/AI styles to globals.css**

`web/app/globals.css`에 추가:

```css
.tabs {
  display: flex;
  gap: 0;
  margin-bottom: 1.5rem;
  border-bottom: 2px solid #e5e7eb;
}
.tab {
  padding: 0.75rem 1.5rem;
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  margin-bottom: -2px;
  cursor: pointer;
  font-size: 1rem;
  color: #6b7280;
  font-weight: 500;
}
.tab.active {
  color: #2563eb;
  border-bottom-color: #2563eb;
}
.ai-search-btn {
  margin-top: 0.75rem;
  padding: 0.75rem 2rem;
  background: #2563eb;
  color: white;
  border: none;
  border-radius: 0.5rem;
  font-size: 1rem;
  cursor: pointer;
}
.ai-search-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
textarea {
  width: 100%;
  padding: 0.5rem;
  border: 1px solid #d1d5db;
  border-radius: 0.375rem;
  font-size: 0.95rem;
  resize: vertical;
}
.similarity {
  font-size: 0.8rem;
  color: #2563eb;
  font-weight: 600;
  margin-left: auto;
}
```

- [ ] **Step 4: Test manually**

1. 터미널 1: `.venv/bin/python rag_server.py` (포트 8000)
2. 터미널 2: `cd web && npm run dev` (포트 3100)
3. 브라우저에서 `http://localhost:3100` 접속
4. "AI 매칭" 탭 클릭 → 폼 작성 → "AI 매칭 검색" 클릭 → 결과 확인
5. "키워드 검색" 탭도 기존대로 동작하는지 확인

- [ ] **Step 5: Commit**

```bash
git add web/app/api/rag-search/route.ts web/app/page.tsx web/app/globals.css
git commit -m "feat: add AI matching tab with RAG search proxy"
```

---

### Task 6: 전체 통합 테스트 및 정리

기존 테스트가 깨지지 않았는지 확인하고, 전체 플로우를 검증.

**Files:**
- 수정 없음 — 검증만

- [ ] **Step 1: Run all Python tests**

Run: `DATA_GO_KR_KEY=dummy MISTRAL_API_KEY=dummy .venv/bin/python -m pytest tests/ -v`
Expected: 모든 기존 테스트 + 새 테스트 PASS

- [ ] **Step 2: Run web tests**

Run: `cd web && npm test`
Expected: 기존 vitest 테스트 PASS

- [ ] **Step 3: Commit final state**

```bash
git add -A
git commit -m "chore: verify all tests pass after RAG integration"
```
