/** lib/services 유닛 테스트 — TEST_PLAN.md WB-01 ~ WB-10. */
import { describe, it, expect } from "vitest";
import {
  searchServices,
  getService,
  listSido,
  listSigungu,
} from "@/lib/services";

describe("WB-01 기본 노출", () => {
  it("필터 없음 → exclude 제외 전부, high 우선 정렬", () => {
    const { total, results } = searchServices({});
    expect(total).toBe(6); // fixture 8건 중 exclude 2건 제외
    expect(results[0].cancer_relevance).toBe("high");
    const ranks = results.map((r) => r.cancer_relevance);
    const order = { high: 0, medium: 1, low: 2 } as Record<string, number>;
    for (let i = 1; i < ranks.length; i++) {
      expect(order[ranks[i]!]).toBeGreaterThanOrEqual(order[ranks[i - 1]!]);
    }
  });
});

describe("WB-02 키워드 검색", () => {
  it("q 부분일치 (제목/요약/대상/내용)", () => {
    const { results } = searchServices({ q: "간병" });
    expect(results.length).toBe(1);
    expect(results[0].source_service_id).toBe("L-MED-1");
  });

  it("검색 결과 없음 → 빈 배열, total 0", () => {
    const { total, results } = searchServices({ q: "존재하지않는검색어xyz" });
    expect(total).toBe(0);
    expect(results).toEqual([]);
  });
});

describe("WB-03 시도 필터", () => {
  it("서울 선택 → 서울 지자체 + 중앙부처(region null) 포함", () => {
    const { results } = searchServices({ sido: "서울특별시" });
    for (const r of results) {
      expect([null, "서울특별시"]).toContain(r.region_sido);
    }
    // 중앙부처(전국) 제도가 포함되어야 한다
    expect(results.some((r) => r.region_sido === null)).toBe(true);
    // 다른 시도(경기) 지자체 제도는 제외
    expect(results.some((r) => r.region_sido === "경기도")).toBe(false);
  });
});

describe("WB-04 시군구 필터", () => {
  it("강남구 선택 → 강남구 + region null만", () => {
    const { results } = searchServices({
      sido: "서울특별시",
      sigungu: "강남구",
    });
    for (const r of results) {
      expect([null, "강남구"]).toContain(r.region_sigungu);
    }
    // 마포구 제도는 제외
    expect(results.some((r) => r.region_sigungu === "마포구")).toBe(false);
  });
});

describe("WB-05 관련성 필터", () => {
  it("high만 → high 2건", () => {
    const { total, results } = searchServices({ levels: ["high"] });
    expect(total).toBe(2);
    for (const r of results) expect(r.cancer_relevance).toBe("high");
  });

  it("exclude 명시 요청 시에는 노출 (개발/검수 용도)", () => {
    const { total } = searchServices({ levels: ["exclude"] });
    expect(total).toBe(2);
  });
});

describe("WB-06 카테고리 필터", () => {
  it("의료비 → 해당 카테고리 포함 레코드만", () => {
    const { results } = searchServices({ category: "의료비" });
    expect(results.length).toBe(3);
    for (const r of results) {
      expect(r.support_categories).toContain("의료비");
    }
  });

  it("심리지원 → 1건", () => {
    const { results } = searchServices({ category: "심리지원" });
    expect(results.map((r) => r.source_service_id)).toEqual(["L-HIGH-1"]);
  });
});

describe("WB-07 limit/offset", () => {
  it("limit=2 → 2건 반환, total은 전체", () => {
    const { total, results } = searchServices({ limit: 2 });
    expect(results.length).toBe(2);
    expect(total).toBe(6);
  });

  it("offset으로 이어받기 (중복/누락 없음)", () => {
    const page1 = searchServices({ limit: 4 });
    const page2 = searchServices({ limit: 4, offset: 4 });
    const ids = [
      ...page1.results.map((r) => r.source_service_id),
      ...page2.results.map((r) => r.source_service_id),
    ];
    expect(new Set(ids).size).toBe(6);
  });
});

describe("WB-08 미존재 상세", () => {
  it("getService 미존재 → null", () => {
    expect(getService("national", "NOPE")).toBeNull();
  });

  it("존재하면 links/categories가 배열로 디코드", () => {
    const s = getService("local", "L-HIGH-1");
    expect(s).not.toBeNull();
    expect(Array.isArray(s!.links)).toBe(true);
    expect(s!.support_categories).toContain("심리지원");
  });
});

describe("WB-09 listSido", () => {
  it("DISTINCT 시도 정렬 목록", () => {
    const sidos = listSido();
    expect(sidos).toContain("서울특별시");
    expect(sidos).toContain("경기도");
    expect([...sidos].sort((a, b) => a.localeCompare(b))).toEqual(sidos);
  });
});

describe("WB-10 listSigungu", () => {
  it("시도 종속 시군구 목록", () => {
    const sggs = listSigungu("서울특별시");
    expect(sggs).toContain("강남구");
    expect(sggs).toContain("마포구");
    expect(sggs).not.toContain("수원시");
  });

  it("미존재 시도 → 빈 목록", () => {
    expect(listSigungu("없는시도")).toEqual([]);
  });
});
