"""storage.py 확장 테스트 — TEST_PLAN.md PY-08 ~ PY-10."""
import os
import tempfile
import unittest

os.environ.setdefault("DATA_GO_KR_KEY", "dummy")
os.environ.setdefault("MISTRAL_API_KEY", "dummy")

import schema
import storage


def _make_row(serv_id, title="제도", **overrides):
    row = schema.normalize_national(
        {"servId": serv_id, "servNm": title, "ministry": "부처"},
        {"서비스요약": "요약", "급여내용": "내용"},
    )
    row.update(overrides)
    return row


class TestSpecialCharacters(unittest.TestCase):
    """PY-08: 따옴표/이모지/개행 포함 데이터 무손실 저장·조회."""

    def test_roundtrip_special_chars(self):
        tricky = "'따옴표' \"쌍따옴표\" 😀 이모지\n개행;DROP TABLE welfare_services;--"
        with tempfile.TemporaryDirectory() as tmp:
            db = os.path.join(tmp, "t.db")
            storage.init_db(db)
            storage.upsert_services(db, [_make_row("S1", benefit=tricky)])
            got = storage.get_service(db, "national", "S1")
            self.assertEqual(got["benefit"], tricky)
            # SQL injection 문자열이 데이터로만 저장되고 테이블은 살아있다
            self.assertEqual(storage.count_services(db), 1)


class TestBulk(unittest.TestCase):
    """PY-09: 대량 upsert 정확성 + 재실행 무중복."""

    def test_500_rows_and_rerun(self):
        rows = [_make_row(f"B{i:04d}") for i in range(500)]
        with tempfile.TemporaryDirectory() as tmp:
            db = os.path.join(tmp, "t.db")
            storage.init_db(db)
            storage.upsert_services(db, rows)
            self.assertEqual(storage.count_services(db), 500)
            storage.upsert_services(db, rows)
            self.assertEqual(storage.count_services(db), 500)


class TestMissingKey(unittest.TestCase):
    """PY-10: 미존재 키 조회는 None."""

    def test_get_missing_returns_none(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = os.path.join(tmp, "t.db")
            storage.init_db(db)
            self.assertIsNone(storage.get_service(db, "national", "NOPE"))


if __name__ == "__main__":
    unittest.main()
