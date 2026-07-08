"""raw_cache 테스트 — 밤샘 자율 개발 중 공공 API 재호출(쿼터 소진)을 막는 캐시 계층."""
import os
import tempfile
import unittest

os.environ.setdefault("DATA_GO_KR_KEY", "dummy-key")

import raw_cache


class TestCachedCall(unittest.TestCase):
    def test_miss_fetches_once_and_writes_file(self):
        """캐시가 없으면 fetch를 1회 호출하고 결과를 파일로 저장한다."""
        calls = {"n": 0}

        def fetch():
            calls["n"] += 1
            return "<xml>원문</xml>"

        with tempfile.TemporaryDirectory() as tmp:
            result = raw_cache.cached_call("national/detail/WLF00000022", fetch, cache_dir=tmp)
            self.assertEqual(result, "<xml>원문</xml>")
            self.assertEqual(calls["n"], 1)
            path = os.path.join(tmp, "national", "detail", "WLF00000022.xml")
            self.assertTrue(os.path.exists(path))

    def test_hit_does_not_fetch(self):
        """캐시가 있으면 fetch를 호출하지 않고 파일 내용을 반환한다."""
        calls = {"n": 0}

        def fetch():
            calls["n"] += 1
            return "<xml>새 응답</xml>"

        with tempfile.TemporaryDirectory() as tmp:
            raw_cache.cached_call("k1", lambda: "<xml>기존</xml>", cache_dir=tmp)
            result = raw_cache.cached_call("k1", fetch, cache_dir=tmp)
            self.assertEqual(result, "<xml>기존</xml>")
            self.assertEqual(calls["n"], 0)

    def test_fetch_failure_writes_nothing(self):
        """fetch가 실패하면 캐시 파일을 만들지 않는다 (에러 응답 캐싱 방지)."""
        def fetch():
            raise RuntimeError("API request failed: HTTP 500")

        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(RuntimeError):
                raw_cache.cached_call("k2", fetch, cache_dir=tmp)
            self.assertFalse(os.path.exists(os.path.join(tmp, "k2.xml")))

    def test_unsafe_key_rejected(self):
        """경로 탈출이 가능한 키는 거부한다."""
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError):
                raw_cache.cached_call("../escape", lambda: "x", cache_dir=tmp)


if __name__ == "__main__":
    unittest.main()
