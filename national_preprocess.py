import sys
import os
import json
import time
import requests
from dotenv import load_dotenv

sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[union-attr]

import national_welfare

load_dotenv()
MISTRAL_API_KEY = os.environ["MISTRAL_API_KEY"]
MISTRAL_URL = "https://api.mistral.ai/v1/chat/completions"

# 무인 실행 중 비용 폭주 방지: 프로세스당 Mistral 호출 상한
MISTRAL_MAX_CALLS = int(os.getenv("MISTRAL_MAX_CALLS", "200"))
_mistral_call_count = 0

PROMPT_TEMPLATE = """
아래는 한국 중앙부처 복지서비스의 상세 정보야.
다음 항목을 JSON으로 추출해줘. 없으면 null로 표기해.

- 서비스명
- 지원대상 (간결하게 요약)
- 지원내용 (금액/현물/서비스 형태로 핵심만)
- 신청방법 (온라인/방문/우편 등 방식과 절차 요약)
- 문의처

복지서비스 정보:
{detail_text}

JSON만 출력해. 다른 설명 없이.
"""


def build_detail_text(info: dict) -> str:
    return "\n".join(f"{k}: {v}" for k, v in info.items() if v)


def call_mistral(prompt: str, retries: int = 3) -> str:
    global _mistral_call_count
    if _mistral_call_count >= MISTRAL_MAX_CALLS:
        raise RuntimeError(
            f"Mistral 호출 상한 도달 ({MISTRAL_MAX_CALLS}회). "
            "필요하면 MISTRAL_MAX_CALLS 환경변수로 조정한다."
        )
    _mistral_call_count += 1
    headers = {
        "Authorization": f"Bearer {MISTRAL_API_KEY}",
        "Content-Type": "application/json",
    }
    body = {
        "model": "mistral-large-latest",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
    }
    for attempt in range(retries):
        res = requests.post(MISTRAL_URL, headers=headers, json=body, timeout=30)
        if res.status_code == 429:
            print("  Rate limit, 30초 대기 후 재시도...")
            time.sleep(30)
            continue
        res.raise_for_status()
        return res.json()["choices"][0]["message"]["content"]
    raise RuntimeError("재시도 초과")


def preprocess(detail: dict) -> dict:
    """상세 dict → Mistral 전처리 → 정제된 dict"""
    prompt = PROMPT_TEMPLATE.format(detail_text=build_detail_text(detail))
    text = call_mistral(prompt).strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    return json.loads(text)


def run_pipeline(total=10, output_path="data/national_preprocessed.json"):
    """national_welfare에서 total건 연속 조회 → Mistral 전처리 → JSON 파일 저장.

    전처리 실패 레코드는 processed=None으로 기록하고 배치는 계속 진행한다.
    Mistral 호출은 비용이 발생하므로 결과를 항상 파일로 보존한다.
    """
    print(f"=== 중앙부처 복지서비스 전처리 파이프라인 ({total}건) ===\n")
    results = []
    for meta, detail in national_welfare.iter_details(total=total):
        print(f"[{meta['servId']}] {meta['servNm']}")
        processed = None
        try:
            processed = preprocess(detail)
            print(json.dumps(processed, ensure_ascii=False, indent=2))
        except Exception as e:
            print(f"  전처리 실패: {e}")
        results.append({"meta": meta, "detail": detail, "processed": processed})
        print()

    out_dir = os.path.dirname(output_path)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"저장 완료: {output_path} ({len(results)}건)")
    return results


if __name__ == "__main__":
    run_pipeline(total=10)
