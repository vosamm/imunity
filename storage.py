"""정규화된 복지서비스 레코드의 SQLite 저장 계층.

ADR-0001 결정 1: MVP 저장 구조는 SQLite. 원문은 data/raw/ 파일, 정규화 데이터는 SQLite.
표준 SQLite 파일이므로 도구 독립적으로 검증 가능하다.

키/재실행 규칙(DATA_PIPELINE 9장):
- (source_type, source_service_id)가 논리 키 → 재실행 시 중복이 생기지 않는다 (UPSERT).
- 동일 키 재저장 시 변경된 내용으로 갱신된다.
"""
import json
import sqlite3
from datetime import datetime, timezone

import numpy as np

from schema import SCHEMA_FIELDS

TABLE = "welfare_services"

# 리스트/딕셔너리는 JSON 텍스트로 직렬화해 저장한다.
_JSON_FIELDS = {"links", "support_categories", "raw_payload"}


def _connect(db_path):
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    return con


def init_db(db_path):
    """스키마 필드에 맞춘 테이블을 생성한다 (없으면). (source_type, source_service_id) PK."""
    columns = []
    for field in SCHEMA_FIELDS:
        columns.append(f'"{field}" TEXT')
    cols_sql = ", ".join(columns)
    con = _connect(db_path)
    try:
        con.execute(
            f'CREATE TABLE IF NOT EXISTS {TABLE} ('
            f"{cols_sql}, "
            f'PRIMARY KEY ("source_type", "source_service_id"))'
        )
        con.commit()
    finally:
        con.close()


def _encode(field, value):
    if field in _JSON_FIELDS:
        # None도 JSON으로 저장해 디코드 시 일관되게 처리한다.
        return json.dumps(value, ensure_ascii=False)
    return value


def _decode(field, value):
    if field in _JSON_FIELDS:
        if value is None:
            return None
        return json.loads(value)
    return value


def upsert_services(db_path, rows):
    """레코드 목록을 UPSERT한다. 동일 키는 갱신, 신규는 삽입 (중복 없음)."""
    placeholders = ", ".join("?" for _ in SCHEMA_FIELDS)
    col_list = ", ".join(f'"{f}"' for f in SCHEMA_FIELDS)
    update_cols = [f for f in SCHEMA_FIELDS if f not in ("source_type", "source_service_id")]
    update_sql = ", ".join(f'"{c}"=excluded."{c}"' for c in update_cols)
    sql = (
        f"INSERT INTO {TABLE} ({col_list}) VALUES ({placeholders}) "
        f'ON CONFLICT("source_type", "source_service_id") DO UPDATE SET {update_sql}'
    )
    con = _connect(db_path)
    try:
        for row in rows:
            values = [_encode(f, row.get(f)) for f in SCHEMA_FIELDS]
            con.execute(sql, values)
        con.commit()
    finally:
        con.close()


def count_services(db_path):
    con = _connect(db_path)
    try:
        return con.execute(f"SELECT COUNT(*) FROM {TABLE}").fetchone()[0]
    finally:
        con.close()


def _row_to_dict(row):
    return {f: _decode(f, row[f]) for f in row.keys()}


def get_service(db_path, source_type, source_service_id):
    """단일 레코드를 dict로 반환한다 (JSON 필드는 원래 타입으로 디코드). 없으면 None."""
    con = _connect(db_path)
    try:
        cur = con.execute(
            f"SELECT * FROM {TABLE} WHERE source_type=? AND source_service_id=?",
            (source_type, source_service_id),
        )
        row = cur.fetchone()
        return _row_to_dict(row) if row is not None else None
    finally:
        con.close()


def all_services(db_path):
    """전체 레코드를 dict 리스트로 반환한다 (분류/조회용)."""
    con = _connect(db_path)
    try:
        cur = con.execute(f"SELECT * FROM {TABLE}")
        return [_row_to_dict(r) for r in cur.fetchall()]
    finally:
        con.close()


# --- 임베딩 저장/조회 ---

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
