"""Phase 0 — 초기 수집 (실 공공 API, 1회만).

중앙부처/지자체 각 N건의 목록+상세 원문 XML을 raw_cache를 통해 data/raw/에 저장한다.

불변 규칙(docs/AUTONOMOUS_RUN.md 1장):
- 실 API 호출은 이 초기 수집에서만 허용한다. 이후 개발/테스트는 data/raw/ 캐시로만 진행한다.
- 쿼터 초과(`API error response`) 발생 시 즉시 중단하고, 확보된 캐시만으로 진행한다.
- 로그에 API 키/전체 요청 URL을 남기지 않는다 (welfare 모듈이 이미 보장).

캐시 키 구조:
    {source}/list/p{page}      목록 원문 XML
    {source}/detail/{servId}   상세 원문 XML
"""
import sys
import os

sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]

import raw_cache
import national_welfare
import local_welfare


class QuotaExceeded(RuntimeError):
    """공공데이터포털 쿼터 초과/키 오류 등 API error response."""


def _is_quota_error(exc):
    return "API error response" in str(exc)


def collect_source(source_name, module, total=100, page_size=50):
    """한 소스(중앙/지자체)의 목록+상세 원문을 캐시에 채운다.

    Returns:
        (detail_count, service_ids) — 성공적으로 상세 원문을 확보한 건수와 servId 목록.
    """
    detail_ids = []
    page_no = 1
    print(f"=== {source_name} 수집 시작 (목표 {total}건) ===")
    while len(detail_ids) < total:
        list_key = f"{source_name}/list/p{page_no}"
        try:
            list_xml = raw_cache.cached_call(
                list_key,
                lambda: module.get_welfare_list(page_no=page_no, num_of_rows=page_size),
            )
            services = module.parse_list(list_xml)
        except Exception as exc:
            if _is_quota_error(exc):
                print(f"  [중단] 목록 p{page_no}에서 쿼터/키 오류: 확보분으로 진행")
                break
            print(f"  [skip] 목록 p{page_no} 실패: {exc.__class__.__name__}")
            break
        if not services:
            print(f"  목록 p{page_no}: 더 이상 서비스 없음")
            break

        for meta in services:
            if len(detail_ids) >= total:
                break
            serv_id = meta.get("servId")
            if not serv_id:
                continue
            detail_key = f"{source_name}/detail/{serv_id}"
            try:
                detail_xml = raw_cache.cached_call(
                    detail_key,
                    lambda: module.get_welfare_detail(serv_id),
                )
                # 파싱 가능한지 검증 (에러 XML/깨진 응답을 캐시로 남기지 않도록)
                module.parse_detail(detail_xml)
            except Exception as exc:
                if _is_quota_error(exc):
                    print(f"  [중단] {serv_id} 상세에서 쿼터/키 오류: 확보분으로 진행")
                    # 에러로 저장됐을 수 있는 캐시 파일 제거
                    _remove_cache(detail_key)
                    return len(detail_ids), detail_ids
                print(f"  [skip] {serv_id} 상세 실패: {exc.__class__.__name__}")
                _remove_cache(detail_key)
                continue
            detail_ids.append(serv_id)
        print(f"  진행: {len(detail_ids)}/{total} (p{page_no}까지)")
        page_no += 1

    print(f"=== {source_name} 수집 완료: 상세 {len(detail_ids)}건 ===\n")
    return len(detail_ids), detail_ids


def _remove_cache(cache_key):
    """파싱 실패/쿼터 에러로 저장된 캐시 파일을 제거해 다음 실행에 재시도되게 한다."""
    try:
        path = raw_cache._path_for(cache_key, raw_cache.CACHE_DIR)
        if os.path.exists(path):
            os.remove(path)
    except Exception:
        pass


def main(total=100):
    n_count, _ = collect_source("national", national_welfare, total=total)
    l_count, _ = collect_source("local", local_welfare, total=total)
    print(f"수집 요약 — national: {n_count}, local: {l_count}")
    gate = n_count >= 50 and l_count >= 50
    print(f"Phase 0 게이트(각 50건 이상): {'PASS' if gate else 'FAIL'}")
    return n_count, l_count


if __name__ == "__main__":
    arg_total = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    main(total=arg_total)
