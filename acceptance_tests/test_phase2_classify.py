"""Phase 2 수락 테스트 — 암환자 관련성 키워드 분류 (골든 케이스).

⚠️ 이 파일은 채점표다. 자율 개발 세션은 이 파일을 수정할 수 없다.
   구현 대상: classify.py — classify.relevance(text) -> {"level": ..., "reason": ...}

기준: docs/DATA_PIPELINE.md 5장 + ADR-0001 수정 사항.
핵심 결정: 인구집단(아동·청소년·임산부 등)만으로 exclude하지 않는다.
암/질병/의료 맥락이 전혀 없는 경우에만 exclude한다. (소아암 배제 방지)
"""
import os
import unittest

os.environ.setdefault("DATA_GO_KR_KEY", "dummy-key")

VALID_LEVELS = {"high", "medium", "low", "exclude"}


def relevance(text):
    import classify
    return classify.relevance(text)


class TestContract(unittest.TestCase):
    def test_returns_level_and_reason(self):
        result = relevance("암환자 의료비 지원 사업")
        self.assertIn(result["level"], VALID_LEVELS)
        self.assertTrue(result["reason"], "판단 근거(reason)는 비어 있으면 안 된다")


class TestHighRelevance(unittest.TestCase):
    CASES = [
        "암환자 의료비 지원 사업. 소득 기준 충족 시 항암치료비 지원.",
        "재난적 의료비 지원 - 과도한 의료비로 경제적 부담이 큰 가구 지원.",
        "중증질환 산정특례 대상자 본인부담금 경감.",
        "희귀난치성 질환자 의료비 지원.",
        "방사선치료 및 항암제 비용 일부 지원.",
    ]

    def test_direct_cancer_or_treatment_cost_is_high(self):
        for text in self.CASES:
            with self.subTest(text=text[:30]):
                self.assertEqual(relevance(text)["level"], "high")


class TestPediatricCancerNotExcluded(unittest.TestCase):
    """핵심 골든 케이스: 인구집단 단어(아동/청소년/가족)가 있어도
    암·질병 맥락이 있으면 절대 exclude가 아니다."""

    CASES = [
        "소아암 환아 의료비 지원 - 만 18세 미만 소아암 진단 아동의 치료비 지원.",
        "소아·청소년 암환자 가족 심리상담 지원 프로그램.",
        "백혈병 등 소아암 어린이 완치 지원 및 학습 지원.",
    ]

    def test_pediatric_cancer_is_high(self):
        for text in self.CASES:
            with self.subTest(text=text[:30]):
                result = relevance(text)
                self.assertNotEqual(result["level"], "exclude",
                                    "소아암 관련 제도가 exclude로 분류되면 안 된다")
                self.assertEqual(result["level"], "high")


class TestMediumRelevance(unittest.TestCase):
    CASES = [
        "저소득층 긴급 생계비 지원 - 질병 등 위기 사유 발생 가구.",
        "중증 환자 간병 돌봄 서비스 바우처 지원.",
        "입원 환자 무료 간병인 지원 사업.",
    ]

    def test_illness_adjacent_support_is_medium(self):
        for text in self.CASES:
            with self.subTest(text=text[:30]):
                self.assertEqual(relevance(text)["level"], "medium")


class TestExclude(unittest.TestCase):
    """암/질병/의료 맥락이 전혀 없는 경우에만 exclude."""

    CASES = [
        "청년 창업 자금 융자 지원 - 예비 창업자 대상 저금리 대출.",
        "학교 밖 청소년 검정고시 합격 축하금 지원.",
        "농업인 영농 정착 지원금.",
    ]

    def test_no_medical_context_is_exclude(self):
        for text in self.CASES:
            with self.subTest(text=text[:30]):
                self.assertEqual(relevance(text)["level"], "exclude")


if __name__ == "__main__":
    unittest.main()
