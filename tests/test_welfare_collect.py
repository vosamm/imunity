"""national_welfare / local_welfare 수집 로직 테스트.

네트워크 호출 없이 스텁으로 검증한다. API 키는 dummy 값으로 대체한다.
"""
import os
import unittest
from unittest import mock

os.environ.setdefault("DATA_GO_KR_KEY", "dummy-key")

import national_welfare
import local_welfare

MODULES = [national_welfare, local_welfare]


def make_list_xml(items):
    """servList 목록 XML 생성. items: [(servId, servNm, ministry), ...]"""
    rows = "".join(
        f"<servList><servId>{sid}</servId><servNm>{nm}</servNm>"
        f"<jurMnofNm>{mn}</jurMnofNm></servList>"
        for sid, nm, mn in items
    )
    return f"<response><srvList>{rows}</srvList></response>"


def make_detail_xml(serv_nm):
    return f"<response><servNm>{serv_nm}</servNm></response>"


API_ERROR_XML = (
    "<OpenAPI_ServiceResponse><cmmMsgHeader>"
    "<errMsg>SERVICE ERROR</errMsg>"
    "<returnAuthMsg>LIMITED_NUMBER_OF_SERVICE_REQUESTS_EXCEEDS_ERROR</returnAuthMsg>"
    "<returnReasonCode>22</returnReasonCode>"
    "</cmmMsgHeader></OpenAPI_ServiceResponse>"
)


def fake_dataset(n):
    return [(f"WLF{i:05d}", f"서비스{i}", f"부처{i}") for i in range(1, n + 1)]


def fake_list_fn(dataset):
    def get_welfare_list(page_no=1, num_of_rows=10, search_word=""):
        start = (page_no - 1) * num_of_rows
        return make_list_xml(dataset[start:start + num_of_rows])
    return get_welfare_list


class TestIterDetailsPagination(unittest.TestCase):
    def test_no_duplicates_or_missing_when_total_not_multiple_of_page_size(self):
        """total=15, page_size=10이면 1~15번이 정확히 한 번씩 나와야 한다."""
        dataset = fake_dataset(30)
        for module in MODULES:
            with self.subTest(module=module.__name__):
                with mock.patch.object(module, "get_welfare_list", fake_list_fn(dataset)), \
                     mock.patch.object(module, "get_welfare_detail",
                                       lambda serv_id, retries=3: make_detail_xml(f"상세-{serv_id}")):
                    got_ids = [meta["servId"] for meta, _ in module.iter_details(total=15, page_size=10)]
                expected = [sid for sid, _, _ in dataset[:15]]
                self.assertEqual(got_ids, expected)

    def test_stops_when_list_runs_out(self):
        """전체 데이터가 total보다 적으면 있는 만큼만 반환하고 종료한다."""
        dataset = fake_dataset(7)
        for module in MODULES:
            with self.subTest(module=module.__name__):
                with mock.patch.object(module, "get_welfare_list", fake_list_fn(dataset)), \
                     mock.patch.object(module, "get_welfare_detail",
                                       lambda serv_id, retries=3: make_detail_xml(f"상세-{serv_id}")):
                    got = list(module.iter_details(total=20, page_size=10))
                self.assertEqual(len(got), 7)


class TestIterDetailsSkipsFailedRecord(unittest.TestCase):
    def test_one_failing_detail_does_not_stop_batch(self):
        """상세 조회가 1건 실패해도 나머지 레코드는 계속 처리된다."""
        dataset = fake_dataset(5)

        def failing_detail(serv_id, retries=3):
            if serv_id == "WLF00003":
                raise RuntimeError("API request failed: HTTP 500 Internal Server Error")
            return make_detail_xml(f"상세-{serv_id}")

        for module in MODULES:
            with self.subTest(module=module.__name__):
                with mock.patch.object(module, "get_welfare_list", fake_list_fn(dataset)), \
                     mock.patch.object(module, "get_welfare_detail", failing_detail):
                    got_ids = [meta["servId"] for meta, _ in module.iter_details(total=5, page_size=10)]
                self.assertEqual(got_ids, ["WLF00001", "WLF00002", "WLF00004", "WLF00005"])


class TestApiErrorXmlDetection(unittest.TestCase):
    def test_parse_list_raises_on_gateway_error_xml(self):
        """HTTP 200 + OpenAPI_ServiceResponse 에러 응답은 빈 목록이 아니라 예외여야 한다."""
        for module in MODULES:
            with self.subTest(module=module.__name__):
                with self.assertRaises(RuntimeError) as ctx:
                    module.parse_list(API_ERROR_XML)
                self.assertIn("LIMITED_NUMBER_OF_SERVICE_REQUESTS_EXCEEDS_ERROR", str(ctx.exception))

    def test_parse_detail_raises_on_gateway_error_xml(self):
        for module in MODULES:
            with self.subTest(module=module.__name__):
                with self.assertRaises(RuntimeError):
                    module.parse_detail(API_ERROR_XML)


class FakeResponse:
    def __init__(self, status_code, text="<response></response>", reason="Err"):
        self.status_code = status_code
        self.text = text
        self.reason = reason
        self.ok = status_code < 400


class TestGetRetryPolicy(unittest.TestCase):
    def test_retries_on_5xx_then_succeeds(self):
        """5xx는 재시도 대상이며, 3회 안에 성공하면 결과를 반환한다."""
        for module in MODULES:
            with self.subTest(module=module.__name__):
                responses = [FakeResponse(500), FakeResponse(503), FakeResponse(200, text="<ok/>")]
                with mock.patch.object(module.requests, "get", side_effect=responses), \
                     mock.patch.object(module.time, "sleep"):
                    result = module._get("https://example.invalid/x", {}, retries=3)
                self.assertEqual(result, "<ok/>")

    def test_retries_on_connection_error(self):
        """연결 오류도 재시도 대상이다."""
        import requests as _requests
        for module in MODULES:
            with self.subTest(module=module.__name__):
                effects = [_requests.exceptions.ConnectionError(), FakeResponse(200, text="<ok/>")]
                with mock.patch.object(module.requests, "get", side_effect=effects), \
                     mock.patch.object(module.time, "sleep"):
                    result = module._get("https://example.invalid/x", {}, retries=3)
                self.assertEqual(result, "<ok/>")

    def test_no_retry_on_4xx_and_no_url_in_message(self):
        """4xx는 즉시 실패하고, 예외 메시지에 URL/키가 없어야 한다."""
        for module in MODULES:
            with self.subTest(module=module.__name__):
                with mock.patch.object(module.requests, "get",
                                       return_value=FakeResponse(403, reason="Forbidden")) as m, \
                     mock.patch.object(module.time, "sleep"):
                    with self.assertRaises(RuntimeError) as ctx:
                        module._get("https://example.invalid/x", {"serviceKey": "SECRET"}, retries=3)
                self.assertEqual(m.call_count, 1)
                self.assertNotIn("SECRET", str(ctx.exception))
                self.assertNotIn("example.invalid", str(ctx.exception))

    def test_list_request_retried_by_default(self):
        """목록 조회도 기본적으로 3회까지 재시도해야 한다 (CLAUDE.md 1.3)."""
        for module in MODULES:
            with self.subTest(module=module.__name__):
                responses = [FakeResponse(500), FakeResponse(500), FakeResponse(200, text="<ok/>")]
                with mock.patch.object(module.requests, "get", side_effect=responses), \
                     mock.patch.object(module.time, "sleep"):
                    result = module.get_welfare_list(page_no=1, num_of_rows=1)
                self.assertEqual(result, "<ok/>")


if __name__ == "__main__":
    unittest.main()
