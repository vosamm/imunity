"""build_db.py + gen_review_samples.py 통합 테스트 — TEST_PLAN.md PY-11, PY-12.

fixture 캐시 디렉터리를 만들어 실 API 없이 전체 적재 경로를 검증한다.
"""
import os
import tempfile
import unittest
from unittest import mock

os.environ.setdefault("DATA_GO_KR_KEY", "dummy")
os.environ.setdefault("MISTRAL_API_KEY", "dummy")

import raw_cache
import build_db
import gen_review_samples
import storage

NATIONAL_LIST_XML = """<response><body>
<servList><servId>N001</servId><servNm>암환자 의료비 지원</servNm><jurMnofNm>보건복지부</jurMnofNm></servList>
<servList><servId>N002</servId><servNm>청년 창업 융자</servNm><jurMnofNm>중기부</jurMnofNm></servList>
</body></response>"""

NATIONAL_DETAIL_XML = {
    "N001": """<wantedDtl><servNm>암환자 의료비 지원</servNm><jurMnofNm>보건복지부</jurMnofNm>
<wlfareInfoOutlCn>암환자 치료비 지원</wlfareInfoOutlCn><tgtrDtlCn>암 진단자</tgtrDtlCn>
<slctCritCn>소득 기준</slctCritCn><alwServCn>의료비 지원</alwServCn><rprsCtadr>1234</rprsCtadr></wantedDtl>""",
    "N002": """<wantedDtl><servNm>청년 창업 융자</servNm><jurMnofNm>중기부</jurMnofNm>
<wlfareInfoOutlCn>창업 자금 대출</wlfareInfoOutlCn><tgtrDtlCn>예비 창업자</tgtrDtlCn>
<slctCritCn>연령 기준</slctCritCn><alwServCn>저금리 융자</alwServCn><rprsCtadr>5678</rprsCtadr></wantedDtl>""",
}

LOCAL_LIST_XML = """<response><body>
<servList><servId>L001</servId><servNm>간병비 지원</servNm><jurMnofNm></jurMnofNm></servList>
</body></response>"""

LOCAL_DETAIL_XML = {
    "L001": """<wantedDtl><servNm>간병비 지원</servNm><ctpvNm>서울특별시</ctpvNm><sggNm>강남구</sggNm>
<bizChrDeptNm>복지과</bizChrDeptNm><servDgst>간병 서비스 비용 지원</servDgst>
<sprtTrgtCn>입원 환자</sprtTrgtCn><slctCritCn>소득 기준</slctCritCn>
<alwServCn>간병비 지급</alwServCn><aplyMtdCn>방문 신청</aplyMtdCn></wantedDtl>""",
}


def _write_fixture_cache(cache_dir):
    def w(rel, text):
        path = os.path.join(cache_dir, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)

    w("national/list/p1.xml", NATIONAL_LIST_XML)
    for sid, xml in NATIONAL_DETAIL_XML.items():
        w(f"national/detail/{sid}.xml", xml)
    w("local/list/p1.xml", LOCAL_LIST_XML)
    for sid, xml in LOCAL_DETAIL_XML.items():
        w(f"local/detail/{sid}.xml", xml)


class TestBuildDbIntegration(unittest.TestCase):
    """PY-11: fixture 캐시 → 적재 건수, 분류, 지역, 카테고리."""

    def _build(self, tmp):
        cache = os.path.join(tmp, "raw")
        _write_fixture_cache(cache)
        db = os.path.join(tmp, "welfare.db")
        with mock.patch.object(raw_cache, "CACHE_DIR", cache):
            count = build_db.build(db_path=db)
        return db, count

    def test_counts_and_fields(self):
        with tempfile.TemporaryDirectory() as tmp:
            db, count = self._build(tmp)
            self.assertEqual(count, 3)

            cancer = storage.get_service(db, "national", "N001")
            self.assertEqual(cancer["cancer_relevance"], "high")
            self.assertIn("의료비", cancer["support_categories"])

            startup = storage.get_service(db, "national", "N002")
            self.assertEqual(startup["cancer_relevance"], "exclude")

            care = storage.get_service(db, "local", "L001")
            self.assertEqual(care["region_sido"], "서울특별시")
            self.assertEqual(care["region_sigungu"], "강남구")
            self.assertEqual(care["cancer_relevance"], "medium")
            self.assertIn("돌봄·간병", care["support_categories"])

    def test_rerun_no_duplicates(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache = os.path.join(tmp, "raw")
            _write_fixture_cache(cache)
            db = os.path.join(tmp, "welfare.db")
            with mock.patch.object(raw_cache, "CACHE_DIR", cache):
                build_db.build(db_path=db)
                count = build_db.build(db_path=db)
            self.assertEqual(count, 3)


class TestReviewSamplesContract(unittest.TestCase):
    """PY-12: 샘플 파일 형식 — 마크다운 테이블, 등급·근거 포함."""

    def test_output_format(self):
        with tempfile.TemporaryDirectory() as tmp:
            cache = os.path.join(tmp, "raw")
            _write_fixture_cache(cache)
            db = os.path.join(tmp, "welfare.db")
            out = os.path.join(tmp, "samples.md")
            with mock.patch.object(raw_cache, "CACHE_DIR", cache):
                build_db.build(db_path=db)
            gen_review_samples.main(db_path=db, out_path=out)

            with open(out, encoding="utf-8") as f:
                content = f.read()
            self.assertIn("| # | 등급 | 소스 | 제목 | 근거 |", content)
            self.assertIn("암환자 의료비 지원", content)
            # 데이터 행이 헤더/구분선 외에 존재
            data_rows = [l for l in content.splitlines()
                         if l.startswith("|") and "등급" not in l and "---" not in l]
            self.assertGreaterEqual(len(data_rows), 3)


if __name__ == "__main__":
    unittest.main()
