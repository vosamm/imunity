/** /api/services, /api/regions 라우트 핸들러 통합 테스트 — TEST_PLAN.md WB-11, WB-12. */
import { describe, it, expect } from "vitest";
import { NextRequest } from "next/server";
import { GET as servicesGET } from "@/app/api/services/route";
import { GET as regionsGET } from "@/app/api/regions/route";

function req(url: string) {
  return new NextRequest(`http://localhost:3100${url}`);
}

describe("WB-11 /api/services 계약", () => {
  it("응답 스키마 {count,total,results[]}", async () => {
    const res = servicesGET(req("/api/services"));
    expect(res.status).toBe(200);
    const body = await res.json();
    expect(typeof body.count).toBe("number");
    expect(typeof body.total).toBe("number");
    expect(Array.isArray(body.results)).toBe(true);
    expect(body.count).toBe(body.results.length);
  });

  it("잘못된 limit 방어 (문자/음수 → 기본값, 과대 → clamp)", async () => {
    for (const bad of ["abc", "-5", "999999"]) {
      const res = servicesGET(req(`/api/services?limit=${bad}`));
      expect(res.status).toBe(200);
      const body = await res.json();
      expect(body.results.length).toBeLessThanOrEqual(500);
    }
  });

  it("relevance CSV 파싱", async () => {
    const res = servicesGET(req("/api/services?relevance=high"));
    const body = await res.json();
    for (const r of body.results) {
      expect(r.cancer_relevance).toBe("high");
    }
  });

  it("category + sido 조합", async () => {
    const res = servicesGET(
      req("/api/services?category=%EC%9D%98%EB%A3%8C%EB%B9%84&sido=%EC%84%9C%EC%9A%B8%ED%8A%B9%EB%B3%84%EC%8B%9C")
    );
    const body = await res.json();
    for (const r of body.results) {
      expect(r.support_categories).toContain("의료비");
      expect([null, "서울특별시"]).toContain(r.region_sido);
    }
  });
});

describe("WB-12 /api/services 검색", () => {
  it("?q=암 → 결과가 있고 전부 관련 필드에 검색어 포함", async () => {
    const res = servicesGET(req("/api/services?q=%EC%95%94"));
    const body = await res.json();
    expect(body.total).toBeGreaterThan(0);
    for (const r of body.results) {
      const hay = [r.title, r.summary, r.target, r.benefit, r.criteria]
        .filter(Boolean)
        .join(" ");
      expect(hay).toContain("암");
    }
  });
});

describe("/api/regions", () => {
  it("시도 목록", async () => {
    const res = regionsGET(req("/api/regions"));
    const body = await res.json();
    expect(body.sido).toContain("서울특별시");
  });

  it("시군구 목록 (sido 종속)", async () => {
    const res = regionsGET(req("/api/regions?sido=%EC%84%9C%EC%9A%B8%ED%8A%B9%EB%B3%84%EC%8B%9C"));
    const body = await res.json();
    expect(body.sigungu).toContain("강남구");
  });
});
