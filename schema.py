"""공통 스키마 정규화 계층.

원문 파싱 결과(national_welfare.parse_detail / local_welfare.parse_detail)를
docs/DATA_PIPELINE.md 4장의 공통 스키마로 변환한다.

핵심 원칙(DATA_PIPELINE 6장, 7장):
- 미명시(빈) 필드는 "" 가 아니라 None으로 저장한다 — 사용자 필터에서 '제외 조건'으로 쓰지 않기 위함.
- AI/정규화 결과가 원문을 대체하지 않는다 — raw_payload에 원문 파싱 결과를 그대로 보존한다.
- 분류(cancer_relevance)는 이 계층에서 채우지 않는다 (Phase 2 classify가 채운다).
"""
from datetime import datetime, timezone

# docs/DATA_PIPELINE.md 4장 공통 스키마 필드 순서
SCHEMA_FIELDS = [
    "source_type", "source_service_id", "title", "summary", "target",
    "criteria", "benefit", "application_method", "contact", "links",
    "ministry", "region_sido", "region_sigungu", "support_categories",
    "cancer_relevance", "cancer_relevance_reason", "raw_payload",
    "fetched_at", "processed_at",
]


def _clean(value):
    """빈 문자열/공백/None을 None으로 정규화한다 (미명시 = 확인되지 않음)."""
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _split_links(value):
    """parse_detail이 ' / '로 이어붙인 관련링크 문자열을 리스트로 분리한다.

    확인되지 않으면 빈 리스트를 반환한다 (필드는 항상 list 타입 유지).
    """
    cleaned = _clean(value)
    if not cleaned:
        return []
    return [part.strip() for part in cleaned.split(" / ") if part.strip()]


def _now():
    return datetime.now(timezone.utc).isoformat()


def _base_row(source_type, meta, detail, fetched_at):
    """공통 필드를 채운 스키마 dict를 만든다. 소스별 함수가 지역 등을 덧붙인다."""
    return {
        "source_type": source_type,
        "source_service_id": _clean(meta.get("servId")),
        "title": _clean(meta.get("servNm")) or _clean(detail.get("서비스명")),
        "summary": _clean(detail.get("서비스요약")),
        "target": _clean(detail.get("지원대상")),
        "criteria": _clean(detail.get("선정기준")),
        "benefit": _clean(detail.get("급여내용")),
        "application_method": _clean(detail.get("신청방법")),
        "contact": _clean(detail.get("문의처")) or _clean(detail.get("문의처목록")),
        "links": _split_links(detail.get("관련링크")),
        "ministry": None,
        "region_sido": None,
        "region_sigungu": None,
        "support_categories": [],
        # 분류는 Phase 2에서 채운다.
        "cancer_relevance": None,
        "cancer_relevance_reason": None,
        # AI/정규화가 원문을 대체하지 않도록 원문 파싱 결과를 보존한다.
        "raw_payload": detail,
        "fetched_at": fetched_at,
        "processed_at": _now(),
    }


def normalize_national(meta, detail, fetched_at=None):
    """중앙부처 복지서비스 원문 → 공통 스키마.

    중앙부처는 지역 조건이 없다 → region_* 는 None (전체 지역 노출 가능).
    """
    row = _base_row("national", meta, detail, fetched_at)
    row["ministry"] = _clean(meta.get("ministry")) or _clean(detail.get("소관부처"))
    # 중앙부처는 지역 미지정 → None 유지 (DATA_PIPELINE 6장).
    row["region_sido"] = None
    row["region_sigungu"] = None
    return row


def normalize_local(meta, detail, fetched_at=None):
    """지자체 복지서비스 원문 → 공통 스키마."""
    row = _base_row("local", meta, detail, fetched_at)
    row["ministry"] = _clean(meta.get("ministry")) or _clean(detail.get("담당부서"))
    row["region_sido"] = _clean(detail.get("시도"))
    row["region_sigungu"] = _clean(detail.get("시군구"))
    return row
