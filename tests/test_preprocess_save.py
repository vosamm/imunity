"""전처리 파이프라인 결과 저장 테스트. Mistral 호출과 수집은 스텁으로 대체한다."""
import json
import os
import tempfile
import unittest
from unittest import mock

os.environ.setdefault("DATA_GO_KR_KEY", "dummy-key")
os.environ.setdefault("MISTRAL_API_KEY", "dummy-key")

import national_preprocess
import local_preprocess

CASES = [
    (national_preprocess, "national_welfare"),
    (local_preprocess, "local_welfare"),
]


def fake_iter_details(total=10, page_size=10):
    for i in range(1, 4):
        meta = {"servId": f"WLF{i:05d}", "servNm": f"서비스{i}", "ministry": f"부처{i}"}
        detail = {"서비스명": f"서비스{i}", "지원대상": "암환자"}
        yield meta, detail


class TestRunPipelineSavesResults(unittest.TestCase):
    def test_results_saved_to_json_file(self):
        """run_pipeline은 처리 결과를 JSON 파일로 저장해야 한다."""
        for module, source_attr in CASES:
            with self.subTest(module=module.__name__):
                source = getattr(module, source_attr)
                with tempfile.TemporaryDirectory() as tmp:
                    out = os.path.join(tmp, "out", "result.json")
                    with mock.patch.object(source, "iter_details", fake_iter_details), \
                         mock.patch.object(module, "call_mistral",
                                           return_value='{"서비스명": "요약됨"}'):
                        module.run_pipeline(total=3, output_path=out)
                    with open(out, encoding="utf-8") as f:
                        saved = json.load(f)
                self.assertEqual(len(saved), 3)
                self.assertEqual(saved[0]["meta"]["servId"], "WLF00001")
                self.assertEqual(saved[0]["processed"]["서비스명"], "요약됨")
                self.assertIn("detail", saved[0])

    def test_failed_record_saved_with_null_processed(self):
        """전처리 실패 레코드도 processed=None으로 기록되고 배치는 계속된다."""
        for module, source_attr in CASES:
            with self.subTest(module=module.__name__):
                source = getattr(module, source_attr)
                calls = {"n": 0}

                def flaky_mistral(prompt, retries=3):
                    calls["n"] += 1
                    if calls["n"] == 2:
                        raise RuntimeError("재시도 초과")
                    return '{"서비스명": "요약됨"}'

                calls["n"] = 0
                with tempfile.TemporaryDirectory() as tmp:
                    out = os.path.join(tmp, "result.json")
                    with mock.patch.object(source, "iter_details", fake_iter_details), \
                         mock.patch.object(module, "call_mistral", flaky_mistral):
                        module.run_pipeline(total=3, output_path=out)
                    with open(out, encoding="utf-8") as f:
                        saved = json.load(f)
                self.assertEqual(len(saved), 3)
                self.assertIsNone(saved[1]["processed"])
                self.assertIsNotNone(saved[0]["processed"])
                self.assertIsNotNone(saved[2]["processed"])


if __name__ == "__main__":
    unittest.main()
