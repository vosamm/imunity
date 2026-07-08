"""schema.py 확장 테스트 — TEST_PLAN.md PY-04 ~ PY-07."""
import os
import unittest

os.environ.setdefault("DATA_GO_KR_KEY", "dummy")
os.environ.setdefault("MISTRAL_API_KEY", "dummy")

import schema


class TestEmptyDetail(unittest.TestCase):
    """PY-04: 모든 값이 빈 문자열이어도 필드 전부 존재 + None 처리."""

    def test_empty_national_detail(self):
        row = schema.normalize_national({"servId": "X1", "servNm": "", "ministry": ""}, {})
        for field in schema.SCHEMA_FIELDS:
            self.assertIn(field, row)
        self.assertIsNone(row["summary"])
        self.assertIsNone(row["benefit"])
        self.assertIsNone(row["contact"])
        self.assertEqual(row["links"], [])
        self.assertEqual(row["support_categories"], [])

    def test_whitespace_only_is_none(self):
        row = schema.normalize_national(
            {"servId": "X2", "servNm": "  ", "ministry": " "},
            {"서비스요약": "   ", "급여내용": "\n\t"},
        )
        self.assertIsNone(row["summary"])
        self.assertIsNone(row["benefit"])
        self.assertIsNone(row["ministry"])


class TestLinkSplitting(unittest.TestCase):
    """PY-05: ' / ' 구분 링크 다건 분리."""

    def test_three_links(self):
        detail = {"관련링크": "기관A (http://a.kr) / 기관B (http://b.kr) / 기관C (http://c.kr)"}
        row = schema.normalize_local({"servId": "X3", "servNm": "t", "ministry": ""}, detail)
        self.assertEqual(len(row["links"]), 3)
        self.assertIn("기관B (http://b.kr)", row["links"])

    def test_single_link(self):
        detail = {"관련링크": "기관A (http://a.kr)"}
        row = schema.normalize_local({"servId": "X4", "servNm": "t", "ministry": ""}, detail)
        self.assertEqual(row["links"], ["기관A (http://a.kr)"])


class TestRawPayloadPreserved(unittest.TestCase):
    """PY-06: raw_payload가 입력 detail을 그대로 보존."""

    def test_payload_identity(self):
        detail = {"서비스명": "테스트", "지원대상": "암환자", "임의필드": "값"}
        row = schema.normalize_national({"servId": "X5", "servNm": "테스트", "ministry": "부처"}, detail)
        self.assertEqual(row["raw_payload"], detail)


class TestSupportCategories(unittest.TestCase):
    """PY-07: 목적형 카테고리 파생 (환자 UX용 칩 필터의 데이터 기반)."""

    def _row(self, **detail):
        base = {"서비스명": detail.pop("title", "제도")}
        base.update(detail)
        return schema.normalize_national(
            {"servId": "C1", "servNm": base["서비스명"], "ministry": ""}, base
        )

    def test_medical_cost(self):
        row = self._row(title="암환자 의료비 지원", 급여내용="치료비 일부 지원")
        self.assertIn("의료비", row["support_categories"])

    def test_livelihood(self):
        row = self._row(title="긴급 생계비 지원", 급여내용="생계급여 지급")
        self.assertIn("생계", row["support_categories"])

    def test_care(self):
        row = self._row(title="간병 돌봄 바우처", 급여내용="간병인 지원")
        self.assertIn("돌봄·간병", row["support_categories"])

    def test_psychological(self):
        row = self._row(title="환자 가족 심리상담", 급여내용="심리상담 제공")
        self.assertIn("심리지원", row["support_categories"])

    def test_multiple_categories(self):
        row = self._row(title="의료비 및 간병비 지원", 급여내용="치료비와 간병 서비스")
        self.assertIn("의료비", row["support_categories"])
        self.assertIn("돌봄·간병", row["support_categories"])

    def test_no_category_is_empty_list(self):
        row = self._row(title="검정고시 축하금", 급여내용="축하금 지급")
        self.assertEqual(row["support_categories"], [])

    def test_categories_are_from_known_set(self):
        row = self._row(title="의료비 주거 교통 심리 돌봄 생계 지원", 급여내용="종합 지원")
        for cat in row["support_categories"]:
            self.assertIn(cat, schema.SUPPORT_CATEGORIES)


if __name__ == "__main__":
    unittest.main()
