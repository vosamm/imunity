"""공공 API 원문 응답 파일 캐시.

무인(밤샘) 개발 루프가 같은 데이터를 반복 요청해 일일 쿼터를 소진하는 것을 막는다.
첫 호출만 실제 API를 타고, 이후에는 data/raw/ 아래 저장된 원문을 재사용한다.

사용 예:
    xml = raw_cache.cached_call(
        f"national/detail/{serv_id}",
        lambda: national_welfare.get_welfare_detail(serv_id),
    )
"""
import os

CACHE_DIR = os.path.join("data", "raw")


def _path_for(cache_key, cache_dir):
    parts = cache_key.split("/")
    if not cache_key or any(p in ("", ".", "..") for p in parts):
        raise ValueError(f"unsafe cache key: {cache_key!r}")
    return os.path.join(cache_dir, *parts) + ".xml"


def cached_call(cache_key, fetch_fn, cache_dir=CACHE_DIR):
    """cache_key에 해당하는 파일이 있으면 그 내용을, 없으면 fetch_fn() 결과를 저장 후 반환.

    fetch_fn이 예외를 던지면 아무것도 저장하지 않는다 (에러 응답 캐싱 방지).
    """
    path = _path_for(cache_key, cache_dir)
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return f.read()

    text = fetch_fn()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return text
