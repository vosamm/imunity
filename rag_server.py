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



DISPLAY_SCALE = 0.10


def _display_scores(sims) -> list[float]:

    sims = np.asarray(sims, dtype=np.float64)
    if sims.size == 0:
        return []
    scaled = np.clip((sims - sims.mean()) / DISPLAY_SCALE, 0.0, 1.0)
    return scaled.tolist()


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


    displays = _display_scores([sim for sim, _ in scored])

    # Top-K (기본 20건)
    top_k = 20
    results = []
    for (sim, svc), display in zip(scored[:top_k], displays[:top_k]):
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
            "similarity": round(display, 4),
        }
        results.append(result)

    return {"total": len(results), "results": results}


if __name__ == "__main__":
    import uvicorn
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8001)
    args = parser.parse_args()
    uvicorn.run(app, host="0.0.0.0", port=args.port)
