"""Mistral 호출 상한 테스트 — 무인 실행 중 비용 폭주를 막는 가드레일."""
import os
import unittest
from unittest import mock

os.environ.setdefault("DATA_GO_KR_KEY", "dummy-key")
os.environ.setdefault("MISTRAL_API_KEY", "dummy-key")

import national_preprocess
import local_preprocess

MODULES = [national_preprocess, local_preprocess]


class FakeResponse:
    status_code = 200

    @staticmethod
    def raise_for_status():
        pass

    @staticmethod
    def json():
        return {"choices": [{"message": {"content": "{}"}}]}


class TestMistralCallCap(unittest.TestCase):
    def test_raises_when_cap_exceeded(self):
        """상한을 넘는 호출은 API 요청 없이 예외를 던진다."""
        for module in MODULES:
            with self.subTest(module=module.__name__):
                with mock.patch.object(module, "MISTRAL_MAX_CALLS", 2), \
                     mock.patch.object(module, "_mistral_call_count", 0), \
                     mock.patch.object(module.requests, "post", return_value=FakeResponse()) as post:
                    module.call_mistral("p1")
                    module.call_mistral("p2")
                    with self.assertRaises(RuntimeError) as ctx:
                        module.call_mistral("p3")
                self.assertEqual(post.call_count, 2)
                self.assertIn("상한", str(ctx.exception))

    def test_cap_configurable_via_env(self):
        """상한은 MISTRAL_MAX_CALLS 환경변수로 조정 가능해야 한다 (기본값 존재)."""
        for module in MODULES:
            with self.subTest(module=module.__name__):
                self.assertIsInstance(module.MISTRAL_MAX_CALLS, int)
                self.assertGreater(module.MISTRAL_MAX_CALLS, 0)


if __name__ == "__main__":
    unittest.main()
