"""분류 결과 사람 검토용 샘플 생성 (아침 체크포인트).

data/welfare.db의 분류 결과에서 등급별로 고르게 30건을 뽑아
data/review_samples.md로 출력한다. 특히 high(암 직접)와 exclude(비의료) 경계를 포함한다.
실 API/Mistral을 호출하지 않는다.
"""
import os
import storage

DB_PATH = os.path.join("data", "welfare.db")
OUT_PATH = os.path.join("data", "review_samples.md")

# 등급별 목표 건수 (합계 30). high/exclude 경계를 반드시 포함.
QUOTA = {"high": 4, "medium": 10, "low": 6, "exclude": 10}


def _pick(rows):
    by_level = {lvl: [] for lvl in QUOTA}
    for r in sorted(rows, key=lambda x: (x["source_type"], x["source_service_id"])):
        lvl = r.get("cancer_relevance")
        if lvl in by_level:
            by_level[lvl].append(r)

    picked = []
    for lvl, n in QUOTA.items():
        picked.extend(by_level[lvl][:n])
    # 부족분은 남은 레코드로 채워 30건을 맞춘다.
    if len(picked) < 30:
        seen = {(r["source_type"], r["source_service_id"]) for r in picked}
        for r in sorted(rows, key=lambda x: (x["source_type"], x["source_service_id"])):
            key = (r["source_type"], r["source_service_id"])
            if key not in seen:
                picked.append(r)
                seen.add(key)
            if len(picked) >= 30:
                break
    return picked[:30]


def main(db_path=DB_PATH, out_path=OUT_PATH):
    rows = storage.all_services(db_path)
    picked = _pick(rows)

    lines = [
        "# 분류 샘플 검토 (아침 체크포인트)",
        "",
        "> 자동 생성 파일. `gen_review_samples.py`로 재생성한다.",
        "> 키워드 분류(`classify.py`) 결과이며 확정 판정이 아니다. 경계 사례를 눈으로 검토한다.",
        "> 특히 소아암 등 인구집단+암 맥락이 exclude로 빠지지 않았는지, 비의료 제도가 medium 이상으로",
        "> 잘못 올라오지 않았는지 확인한다.",
        "",
        f"총 {len(picked)}건 (high {QUOTA['high']} / medium {QUOTA['medium']} / low {QUOTA['low']} / exclude {QUOTA['exclude']} 목표)",
        "",
        "| # | 등급 | 소스 | 제목 | 근거 |",
        "|---|---|---|---|---|",
    ]
    for i, r in enumerate(picked, 1):
        title = (r.get("title") or "").replace("|", "/")
        reason = (r.get("cancer_relevance_reason") or "").replace("|", "/")
        lines.append(
            f"| {i} | {r.get('cancer_relevance')} | {r.get('source_type')} | {title} | {reason} |"
        )
    lines.append("")

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"생성 완료: {out_path} ({len(picked)}건)")
    return out_path


if __name__ == "__main__":
    main()
