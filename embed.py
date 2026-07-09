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
