"""Phase 1 수락 테스트 — 공통 스키마 정규화 + SQLite 저장.

⚠️ 이 파일은 채점표다. 자율 개발 세션은 이 파일을 수정할 수 없다.
   구현 대상: schema.py (normalize_national / normalize_local), storage.py

근거 문서: docs/DATA_PIPELINE.md 4장(공통 스키마), 6장(필터링 규칙),
docs/ARCHITECTURE.md 5장(저장 원칙), docs/adr/0001-mvp-storage-stack-classification.md
"""
import os
import sqlite3
import tempfile
import unittest

os.environ.setdefault("DATA_GO_KR_KEY", "dummy-key")

SCHEMA_FIELDS = [
    "source_type", "source_service_id", "title", "summary", "target",
    "criteria", "benefit", "application_method", "contact", "links",
    "ministry", "region_sido", "region_sigungu", "support_categories",
    "cancer_relevance", "cancer_relevance_reason", "raw_payload",
    "fetched_at", "processed_at",
]

NATIONAL_DETAIL = {
    "서비스명": "산재근로자 사회심리재활지원",
    "소관부처": "고용노동부",
    "서비스요약": "산재근로자의 심리 안정과 사회 복귀를 지원",
    "지원대상": "산재 요양 중이거나 종결한 근로자",
    "선정기준": "산재보험 요양 승인자",
    "급여내용": "심리상담, 재활 프로그램 제공",
    "문의처": "근로복지공단 1588-0075",
    "신청방법": "온라인 / 방문",
    "문의처목록": "근로복지공단 1588-0075",
    "관련링크": "근로복지공단 (https://www.comwel.or.kr)",
}

LOCAL_DETAIL = {
    "서비스명": "학교 밖 청소년 검정고시 합격 축하금 지원",
    "시도": "경기도",
    "시군구": "수원시",
    "담당부서": "청소년과",
    "서비스요약": "학교 밖 청소년의 검정고시 합격을 축하하는 지원금",
    "지원대상": "수원시 거주 학교 밖 청소년",
    "선정기준": "검정고시 합격자",
    "급여내용": "축하금 지급",
    "신청방법": "방문 신청",
    "문의처": "수원시 청소년과 031-000-0000",
    "관련링크": "",
}


class TestNormalizeNational(unittest.TestCase):
    def _normalized(self):
        import schema
        meta = {"servId": "WLF00000022", "servNm": "산재근로자 사회심리재활지원", "ministry": "고용노동부"}
        return schema.normalize_national(meta, NATIONAL_DETAIL)

    def test_all_schema_fields_present(self):
        row = self._normalized()
        for field in SCHEMA_FIELDS:
            self.assertIn(field, row, f"공통 스키마 필드 누락: {field}")

    def test_core_fields_mapped(self):
        row = self._normalized()
        self.assertEqual(row["source_type"], "national")
        self.assertEqual(row["source_service_id"], "WLF00000022")
        self.assertEqual(row["title"], "산재근로자 사회심리재활지원")
        self.assertEqual(row["ministry"], "고용노동부")
        self.assertTrue(row["benefit"])
        self.assertIsInstance(row["links"], list)

    def test_unspecified_condition_is_none_not_empty_string(self):
        """미명시 조건은 빈 문자열이 아니라 None으로 저장한다 (원문에서 확인되지 않음).

        사용자 필터에서 None은 '제외 조건'으로 쓰이면 안 된다 (DATA_PIPELINE 6장).
        """
        row = self._normalized()
        self.assertIsNone(row["region_sido"])
        self.assertIsNone(row["region_sigungu"])

    def test_raw_payload_preserved(self):
        """AI/정규화 결과가 원문을 대체하면 안 된다. 원문 파싱 결과를 보존한다."""
        row = self._normalized()
        self.assertEqual(row["raw_payload"]["서비스명"], NATIONAL_DETAIL["서비스명"])


class TestNormalizeLocal(unittest.TestCase):
    def _normalized(self):
        import schema
        meta = {"servId": "WLF00006549", "servNm": "학교 밖 청소년 검정고시 합격 축하금 지원", "ministry": ""}
        return schema.normalize_local(meta, LOCAL_DETAIL)

    def test_region_mapped(self):
        row = self._normalized()
        self.assertEqual(row["source_type"], "local")
        self.assertEqual(row["region_sido"], "경기도")
        self.assertEqual(row["region_sigungu"], "수원시")

    def test_all_schema_fields_present(self):
        row = self._normalized()
        for field in SCHEMA_FIELDS:
            self.assertIn(field, row, f"공통 스키마 필드 누락: {field}")


class TestSqliteStorage(unittest.TestCase):
    def _rows(self):
        import schema
        n = schema.normalize_national(
            {"servId": "WLF00000022", "servNm": "산재근로자 사회심리재활지원", "ministry": "고용노동부"},
            NATIONAL_DETAIL,
        )
        l = schema.normalize_local(
            {"servId": "WLF00006549", "servNm": "학교 밖 청소년 검정고시 합격 축하금 지원", "ministry": ""},
            LOCAL_DETAIL,
        )
        return [n, l]

    def test_save_and_count(self):
        import storage
        with tempfile.TemporaryDirectory() as tmp:
            db = os.path.join(tmp, "welfare.db")
            storage.init_db(db)
            storage.upsert_services(db, self._rows())
            self.assertEqual(storage.count_services(db), 2)

    def test_rerun_does_not_duplicate(self):
        """같은 데이터를 다시 저장해도 중복이 생기지 않는다 (DATA_PIPELINE 9장 완료 기준)."""
        import storage
        with tempfile.TemporaryDirectory() as tmp:
            db = os.path.join(tmp, "welfare.db")
            storage.init_db(db)
            storage.upsert_services(db, self._rows())
            storage.upsert_services(db, self._rows())
            self.assertEqual(storage.count_services(db), 2)

    def test_upsert_updates_changed_fields(self):
        """동일 (source_type, source_service_id) 재저장 시 내용이 갱신된다."""
        import storage
        with tempfile.TemporaryDirectory() as tmp:
            db = os.path.join(tmp, "welfare.db")
            storage.init_db(db)
            rows = self._rows()
            storage.upsert_services(db, rows)
            rows[0]["benefit"] = "변경된 지원내용"
            storage.upsert_services(db, rows)
            got = storage.get_service(db, "national", "WLF00000022")
            self.assertEqual(got["benefit"], "변경된 지원내용")

    def test_stored_row_roundtrip(self):
        """저장한 레코드를 다시 읽으면 핵심 필드가 보존된다."""
        import storage
        with tempfile.TemporaryDirectory() as tmp:
            db = os.path.join(tmp, "welfare.db")
            storage.init_db(db)
            storage.upsert_services(db, self._rows())
            got = storage.get_service(db, "local", "WLF00006549")
            self.assertEqual(got["region_sido"], "경기도")
            self.assertEqual(got["title"], "학교 밖 청소년 검정고시 합격 축하금 지원")
            self.assertIsInstance(got["links"], list)

    def test_plain_sqlite_file(self):
        """저장소는 표준 SQLite 파일이어야 한다 (도구 독립적 검증 가능)."""
        import storage
        with tempfile.TemporaryDirectory() as tmp:
            db = os.path.join(tmp, "welfare.db")
            storage.init_db(db)
            con = sqlite3.connect(db)
            tables = [r[0] for r in con.execute(
                "SELECT name FROM sqlite_master WHERE type='table'")]
            con.close()
            self.assertTrue(tables, "테이블이 하나 이상 있어야 한다")


if __name__ == "__main__":
    unittest.main()
