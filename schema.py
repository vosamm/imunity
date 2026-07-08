"""공통 스키마 정규화 계층.

원문 파싱 결과(national_welfare.parse_detail / local_welfare.parse_detail)를
docs/DATA_PIPELINE.md 4장의 공통 스키마로 변환한다.

핵심 원칙(DATA_PIPELINE 6장, 7장):
- 미명시(빈) 필드는 "" 가 아니라 None으로 저장한다 — 사용자 필터에서 '제외 조건'으로 쓰지 않기 위함.
- AI/정규화 결과가 원문을 대체하지 않는다 — raw_payload에 원문 파싱 결과를 그대로 보존한다.
- 분류(cancer_relevance)는 이 계층에서 채우지 않는다 (Phase 2 classify가 채운다).
"""
from datetime import datetime, timezone

# 목적형 지원 카테고리 (환자가 "무엇이 필요한가" 기준으로 찾도록).
# UI 칩 필터와 1:1 대응하므로 이름을 바꾸면 web 쪽도 함께 바꾼다.
SUPPORT_CATEGORIES = [
    "의료비", "생계", "돌봄·간병", "심리지원", "이동·교통", "주거", "현물·물품",
]

_CATEGORY_KEYWORDS = {
    "의료비": ["의료비", "치료비", "진료비", "수술", "항암", "방사선", "본인부담",
             "요양급여", "의료급여", "재활치료", "검진", "예방접종", "약제"],
    "생계": ["생계", "생활비", "생활안정", "수당", "지원금", "장려금", "급여 지급",
           "요금 감면", "감면", "바우처", "긴급복지", "연금"],
    "돌봄·간병": ["간병", "돌봄", "요양보호", "방문요양", "방문 요양", "보호서비스",
              "활동지원", "가사"],
    "심리지원": ["심리", "상담", "정서", "멘토링", "자조모임"],
    "이동·교통": ["교통", "이동지원", "차량", "버스", "택시", "이송"],
    "주거": ["주거", "임대", "주택", "전세", "월세"],
    "현물·물품": ["물품", "용품", "가발", "보장구", "기저귀", "현물"],
}


def derive_support_categories(*texts):
    """제목/요약/급여내용 등 텍스트에서 목적형 카테고리를 파생한다.

    매칭이 없으면 빈 리스트 (억지 분류 금지 — 미확인은 미확인으로 둔다).
    """
    haystack = " ".join(t for t in texts if t)
    result = []
    for category in SUPPORT_CATEGORIES:
        if any(kw in haystack for kw in _CATEGORY_KEYWORDS[category]):
            result.append(category)
    return result


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
    title = _clean(meta.get("servNm")) or _clean(detail.get("서비스명"))
    summary = _clean(detail.get("서비스요약"))
    benefit = _clean(detail.get("급여내용"))
    return {
        "source_type": source_type,
        "source_service_id": _clean(meta.get("servId")),
        "title": title,
        "summary": summary,
        "target": _clean(detail.get("지원대상")),
        "criteria": _clean(detail.get("선정기준")),
        "benefit": benefit,
        "application_method": _clean(detail.get("신청방법")),
        "contact": _clean(detail.get("문의처")) or _clean(detail.get("문의처목록")),
        "links": _split_links(detail.get("관련링크")),
        "ministry": None,
        "region_sido": None,
        "region_sigungu": None,
        "support_categories": derive_support_categories(title, summary, benefit),
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
