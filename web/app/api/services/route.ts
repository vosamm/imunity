import { NextRequest, NextResponse } from "next/server";
import { searchServices } from "@/lib/services";

// 항상 서버에서 SQLite를 읽는다 (정적 캐시 방지). 서버 키는 클라이언트로 나가지 않는다.
export const dynamic = "force-dynamic";

export function GET(req: NextRequest) {
  const sp = req.nextUrl.searchParams;

  const levelsParam = sp.get("relevance");
  const levels = levelsParam
    ? levelsParam.split(",").map((s) => s.trim()).filter(Boolean)
    : undefined;

  const limitParam = sp.get("limit");
  const limit = limitParam ? parseInt(limitParam, 10) : undefined;

  try {
    const results = searchServices({
      q: sp.get("q") ?? undefined,
      sido: sp.get("sido") ?? undefined,
      sigungu: sp.get("sigungu") ?? undefined,
      levels,
      limit: Number.isFinite(limit as number) ? limit : undefined,
    });
    return NextResponse.json({ count: results.length, results });
  } catch (err) {
    // 오류 메시지에 경로/키 등 민감정보를 그대로 노출하지 않는다.
    const message =
      err instanceof Error ? err.message : "서비스 조회 중 오류가 발생했습니다.";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
