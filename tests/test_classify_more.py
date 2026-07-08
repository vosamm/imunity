"""classify.py 확장 테스트 — TEST_PLAN.md PY-01 ~ PY-03."""
import os
import unittest

os.environ.setdefault("DATA_GO_KR_KEY", "dummy")
os.environ.setdefault("MISTRAL_API_KEY", "dummy")

import classify


class TestEmptyInput(unittest.TestCase):
    """PY-01: 빈/None/공백 입력은 근거가 없으므로 exclude, reason은 항상 존재."""

    def test_empty_string(self):
        result = classify.relevance("")
        self.assertEqual(result["level"], "exclude")
        self.assertTrue(result["reason"])

    def test_none(self):
        result = classify.relevance(None)
        self.assertEqual(result["level"], "exclude")
        self.assertTrue(result["reason"])

    def test_whitespace_only(self):
        result = classify.relevance("   \n\t ")
        self.assertEqual(result["level"], "exclude")


class TestPriority(unittest.TestCase):
    """PY-02: 등급 우선순위 high > medium > low."""

    def test_high_wins_over_medium(self):
        # "질병"(medium) + "항암"(high) 공존 → high
        result = classify.relevance("질병으로 인한 항암치료 지원")
        self.assertEqual(result["level"], "high")

    def test_medium_wins_over_low(self):
        # "저소득"(low) + "간병"(medium) 공존 → medium
        result = classify.relevance("저소득층 간병 서비스")
        self.assertEqual(result["level"], "medium")

    def test_reason_mentions_matched_keyword(self):
        result = classify.relevance("항암치료비 지원")
        self.assertIn("항암", result["reason"])


class TestLowStandalone(unittest.TestCase):
    """PY-03: 의료 맥락 없는 취약계층 지원은 low (exclude가 아님 — 암환자도 볼 수 있는 제도)."""

    CASES = [
        "저소득 가구 난방비 지원",
        "위기 가구 긴급 지원",
        "차상위 계층 문화 바우처",
    ]

    def test_vulnerable_only_is_low(self):
        for text in self.CASES:
            with self.subTest(text=text):
                self.assertEqual(classify.relevance(text)["level"], "low")


if __name__ == "__main__":
    unittest.main()
