import os
import time
import requests
import xml.etree.ElementTree as ET
from dotenv import load_dotenv
from urllib.parse import unquote

load_dotenv()
SERVICE_KEY = unquote(os.environ["DATA_GO_KR_KEY"])
BASE_URL = "https://apis.data.go.kr/B554287/NationalWelfareInformationsV001"


def _get(url, params, retries=1):
    for attempt in range(retries):
        try:
            res = requests.get(url, params=params, timeout=30)
        except requests.exceptions.ReadTimeout:
            if attempt < retries - 1:
                time.sleep(3)
                continue
            raise RuntimeError(f"API request timed out after {retries} attempt(s)") from None
        except requests.exceptions.RequestException as exc:
            raise RuntimeError(
                f"API request failed before response: {exc.__class__.__name__}"
            ) from None

        if not res.ok:
            raise RuntimeError(f"API request failed: HTTP {res.status_code} {res.reason}")
        return res.text

    raise RuntimeError("API request failed: retry loop exhausted")


def get_welfare_list(page_no=1, num_of_rows=10, search_word=""):
    """중앙부처복지서비스 목록조회"""
    url = f"{BASE_URL}/NationalWelfarelistV001"
    params = {
        "serviceKey": SERVICE_KEY,
        "callTp": "L",
        "pageNo": page_no,
        "numOfRows": num_of_rows,
        "srchKeyCode": "001",  # 001: 제목, 002: 내용, 003: 제목+내용
    }
    if search_word:
        params["searchWrd"] = search_word

    return _get(url, params)


def get_welfare_detail(serv_id, retries=3):
    """중앙부처복지서비스 상세조회"""
    url = f"{BASE_URL}/NationalWelfaredetailedV001"
    params = {
        "serviceKey": SERVICE_KEY,
        "callTp": "D",
        "servId": serv_id,
    }
    return _get(url, params, retries=retries)


def parse_list(xml_text):
    """목록에서 servId, servNm, 소관부처명 추출"""
    root = ET.fromstring(xml_text)
    items = []
    for item in root.iter("servList"):
        serv_id = item.findtext("servId", "")
        serv_nm = item.findtext("servNm", "")
        ministry = item.findtext("jurMnofNm", "")
        items.append({"servId": serv_id, "servNm": serv_nm, "ministry": ministry})
    return items


def parse_detail(xml_text):
    """상세조회에서 실용적인 필드 추출"""
    root = ET.fromstring(xml_text)

    # 단일 텍스트 필드
    result = {
        "서비스명": root.findtext("servNm", ""),
        "소관부처": root.findtext("jurMnofNm", ""),
        "서비스요약": root.findtext("wlfareInfoOutlCn", ""),
        "지원대상": root.findtext("tgtrDtlCn", ""),
        "선정기준": root.findtext("slctCritCn", ""),
        "급여내용": root.findtext("alwServCn", ""),
        "문의처":   root.findtext("rprsCtadr", ""),
    }

    # 신청방법 목록
    apply_methods = [
        item.findtext("servSeDetailNm", "")
        for item in root.iter("applmetList")
        if item.findtext("servSeDetailNm", "")
    ]
    result["신청방법"] = " / ".join(apply_methods) if apply_methods else ""

    # 문의처 목록 (기관명 + 연락처)
    contacts = [
        f"{item.findtext('servSeDetailNm', '')} {item.findtext('servSeDetailLink', '')}".strip()
        for item in root.iter("inqplCtadrList")
        if item.findtext("servSeDetailNm", "")
    ]
    result["문의처목록"] = " / ".join(contacts) if contacts else ""

    # 관련 홈페이지
    links = [
        f"{item.findtext('servSeDetailNm', '')} ({item.findtext('servSeDetailLink', '')})"
        for item in root.iter("inqplHmpgReldList")
        if item.findtext("servSeDetailLink", "")
    ]
    result["관련링크"] = " / ".join(links) if links else ""

    return result


def iter_details(total=20, page_size=10):
    """목록을 페이지 단위로 순회하며 상세 정보를 순차 yield.

    Args:
        total: 가져올 최대 서비스 수
        page_size: 한 번에 가져올 목록 수 (최대 500)

    Yields:
        (meta, detail) 튜플
          meta   - {"servId", "servNm", "ministry"}
          detail - parse_detail() 결과 dict
    """
    fetched = 0
    page_no = 1
    while fetched < total:
        rows = min(page_size, total - fetched)
        list_xml = get_welfare_list(page_no=page_no, num_of_rows=rows)
        services = parse_list(list_xml)
        if not services:
            break
        for meta in services:
            detail_xml = get_welfare_detail(meta["servId"])
            yield meta, parse_detail(detail_xml)
            fetched += 1
            if fetched >= total:
                break
        page_no += 1


def pretty_print_xml(xml_text):
    root = ET.fromstring(xml_text)
    ET.indent(root)  # Python 3.9+
    print(ET.tostring(root, encoding="unicode"))


if __name__ == "__main__":
    for meta, detail in iter_details(total=10):
        print(f"\n[{meta['servId']}] {meta['servNm']} ({meta['ministry']})")
        for k, v in detail.items():
            print(f"  {k}: {v}")
