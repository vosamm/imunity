import os
import time
import requests
import xml.etree.ElementTree as ET
from dotenv import load_dotenv

load_dotenv()
SERVICE_KEY = os.environ["DATA_GO_KR_KEY"]
BASE_URL = "https://apis.data.go.kr/B554287/LocalGovernmentWelfareInformations"


def get_welfare_list(page_no=1, num_of_rows=10, search_word=""):
    """지자체복지서비스 목록조회"""
    url = f"{BASE_URL}/LcgvWelfarelist"
    params = {
        "serviceKey": SERVICE_KEY,
        "callTp": "L",
        "pageNo": page_no,
        "numOfRows": num_of_rows,
        "srchKeyCode": "001",  # 001: 제목, 002: 내용, 003: 제목+내용
    }
    if search_word:
        params["searchWrd"] = search_word

    res = requests.get(url, params=params, timeout=30)
    res.raise_for_status()
    return res.text


def get_welfare_detail(serv_id, retries=3):
    """지자체복지서비스 상세조회"""
    url = f"{BASE_URL}/LcgvWelfaredetailed"
    params = {
        "serviceKey": SERVICE_KEY,
        "callTp": "D",
        "servId": serv_id,
    }
    for attempt in range(retries):
        try:
            res = requests.get(url, params=params, timeout=30)
            res.raise_for_status()
            return res.text
        except requests.exceptions.ReadTimeout:
            if attempt < retries - 1:
                time.sleep(3)
            else:
                raise


def iter_details(total=20, page_size=10):
    """목록을 페이지 단위로 순회하며 상세 정보를 순차 yield.

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


def parse_list(xml_text):
    """목록에서 servId, servNm만 간단히 추출"""
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

    result = {
        "서비스명":   root.findtext("servNm", ""),
        "시도":       root.findtext("ctpvNm", ""),
        "시군구":     root.findtext("sggNm", ""),
        "담당부서":   root.findtext("bizChrDeptNm", ""),
        "서비스요약": root.findtext("servDgst", ""),
        "지원대상":   root.findtext("sprtTrgtCn", ""),
        "선정기준":   root.findtext("slctCritCn", ""),
        "급여내용":   root.findtext("alwServCn", ""),
        "신청방법":   root.findtext("aplyMtdCn", ""),
    }

    # 문의처 목록
    contacts = [
        f"{item.findtext('wlfareInfoReldNm', '')} {item.findtext('wlfareInfoReldCn', '')}".strip()
        for item in root.iter("inqplCtadrList")
        if item.findtext("wlfareInfoReldNm", "")
    ]
    result["문의처"] = " / ".join(contacts) if contacts else ""

    # 관련 웹사이트
    links = [
        f"{item.findtext('wlfareInfoReldNm', '')} ({item.findtext('wlfareInfoReldCn', '')})"
        for item in root.iter("inqplHmpgReldList")
        if item.findtext("wlfareInfoReldCn", "")
    ]
    result["관련링크"] = " / ".join(links) if links else ""

    return result


def pretty_print_xml(xml_text):
    root = ET.fromstring(xml_text)
    ET.indent(root)  # Python 3.9+
    print(ET.tostring(root, encoding="unicode"))


if __name__ == "__main__":
    # 1) 목록 조회
    print("=== 복지서비스 목록 (5건) ===")
    list_xml = get_welfare_list(page_no=1, num_of_rows=5)
    services = parse_list(list_xml)
    for s in services:
        print(f"[{s['servId']}] {s['servNm']} ({s['ministry']})")

    # 2) 첫 번째 서비스 상세 조회
    if services:
        first_id = services[0]["servId"]
        print(f"\n=== 상세조회: {first_id} ===")
        detail_xml = get_welfare_detail(first_id)
        pretty_print_xml(detail_xml)
