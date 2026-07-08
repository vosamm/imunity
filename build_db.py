"""캐시된 원문(data/raw/)을 공통 스키마로 정규화해 SQLite(data/welfare.db)에 적재한다.

실 API를 호출하지 않는다 — data/raw/ 캐시만 읽는다 (AUTONOMOUS_RUN 불변 규칙 3).
Phase 2(classify)가 있으면 각 레코드에 관련성 분류를 함께 채운다.
"""
import sys
import os
import glob

sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]

import raw_cache
import national_welfare
import local_welfare
import schema
import storage

DB_PATH = os.path.join("data", "welfare.db")

SOURCES = {
    "national": national_welfare,
    "local": local_welfare,
}
NORMALIZERS = {
    "national": schema.normalize_national,
    "local": schema.normalize_local,
}


def _load_meta_map(source_name, module):
    """캐시된 목록 페이지를 파싱해 servId -> meta 맵을 만든다."""
    meta_map = {}
    list_dir = os.path.join(raw_cache.CACHE_DIR, source_name, "list")
    for path in sorted(glob.glob(os.path.join(list_dir, "*.xml"))):
        with open(path, encoding="utf-8") as f:
            xml = f.read()
        try:
            for meta in module.parse_list(xml):
                if meta.get("servId"):
                    meta_map[meta["servId"]] = meta
        except Exception:
            continue
    return meta_map


def _load_rows(source_name, classifier=None):
    module = SOURCES[source_name]
    normalize = NORMALIZERS[source_name]
    meta_map = _load_meta_map(source_name, module)

    rows = []
    detail_dir = os.path.join(raw_cache.CACHE_DIR, source_name, "detail")
    for path in sorted(glob.glob(os.path.join(detail_dir, "*.xml"))):
        serv_id = os.path.splitext(os.path.basename(path))[0]
        with open(path, encoding="utf-8") as f:
            xml = f.read()
        try:
            detail = module.parse_detail(xml)
        except Exception as exc:
            print(f"  [skip] {source_name}/{serv_id} 파싱 실패: {exc.__class__.__name__}")
            continue
        meta = meta_map.get(serv_id, {"servId": serv_id})
        meta.setdefault("servId", serv_id)
        row = normalize(meta, detail)
        if classifier is not None:
            _apply_classification(row, classifier)
        rows.append(row)
    return rows


def _apply_classification(row, classifier):
    """분류기로 관련성 등급/근거를 채운다. 제목+요약+대상+급여를 근거 텍스트로 사용."""
    text = " ".join(
        v for v in (row.get("title"), row.get("summary"),
                    row.get("target"), row.get("benefit"))
        if v
    )
    result = classifier(text)
    row["cancer_relevance"] = result.get("level")
    row["cancer_relevance_reason"] = result.get("reason")


def build(db_path=DB_PATH, with_classify=True):
    classifier = None
    if with_classify:
        try:
            import classify
            classifier = classify.relevance
        except ImportError:
            print("  classify 모듈 없음 — 분류 없이 적재")

    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    storage.init_db(db_path)

    total = 0
    for source_name in SOURCES:
        rows = _load_rows(source_name, classifier)
        storage.upsert_services(db_path, rows)
        print(f"{source_name}: {len(rows)}건 적재")
        total += len(rows)

    print(f"총 {storage.count_services(db_path)}건 저장됨 → {db_path}")
    return storage.count_services(db_path)


if __name__ == "__main__":
    build()
