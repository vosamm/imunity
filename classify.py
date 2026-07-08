"""암환자 관련성 키워드 분류 (Mistral 없이 동작하는 fallback 규칙).

기준: docs/DATA_PIPELINE.md 5장 + docs/adr/0001-mvp-storage-stack-classification.md 결정 3.

핵심 원칙:
- 인구집단(아동·청소년·임산부 등)만으로 exclude하지 않는다.
- 암/질병/의료 맥락이 전혀 없는 경우에만 exclude한다. (소아암 배제 방지)
- 등급 우선순위: high > medium > low > exclude.

분류 결과는 사용자에게 확정 판정으로 보여주지 않는다. 검색 랭킹/필터에만 쓴다.
"""

# high — 암/중증·희귀질환/치료비와 직접 연결되는 표현.
# "암"은 암환자·소아암·항암·항암치료비 등을 모두 포괄한다.
HIGH_KEYWORDS = [
    "암", "백혈병", "악성신생물", "종양",
    "방사선치료", "항암",
    "중증질환", "산정특례", "희귀난치", "재난적",
]

# medium — 암 직접 표현은 없으나 암환자에게 적용 가능성이 있는 질병/의료 인접 맥락.
MEDIUM_KEYWORDS = [
    "질병", "질환", "환자", "간병", "돌봄", "입원",
    "의료", "장애", "요양", "치료", "재활", "만성",
]

# low — 일반 복지이지만 조건에 따라 암환자도 볼 수 있는 취약계층/생계 지원.
LOW_KEYWORDS = [
    "저소득", "생계", "긴급", "위기", "취약", "기초생활", "차상위",
]


def _matched(text, keywords):
    return [k for k in keywords if k in text]


def relevance(text):
    """text -> {"level": high|medium|low|exclude, "reason": ...}.

    빈 입력은 근거가 없으므로 exclude로 처리한다.
    """
    text = text or ""

    high = _matched(text, HIGH_KEYWORDS)
    if high:
        return {
            "level": "high",
            "reason": f"암·중증/희귀질환 직접 표현 감지: {', '.join(high)}",
        }

    medium = _matched(text, MEDIUM_KEYWORDS)
    if medium:
        return {
            "level": "medium",
            "reason": f"질병/의료 인접 맥락 감지: {', '.join(medium)}",
        }

    low = _matched(text, LOW_KEYWORDS)
    if low:
        return {
            "level": "low",
            "reason": f"일반 복지, 조건부 해당 가능: {', '.join(low)}",
        }

    return {
        "level": "exclude",
        "reason": "암·질병·의료 맥락 없음",
    }
