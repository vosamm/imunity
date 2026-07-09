import { NextRequest, NextResponse } from "next/server";
import { listSido, listSigungu } from "@/lib/services";

// 지역 필터 옵션 (시도 목록, sido 지정 시 해당 시군구 목록).
export const dynamic = "force-dynamic";

export async function GET(req: NextRequest) {
  const sido = req.nextUrl.searchParams.get("sido");
  try {
    if (sido) {
      return NextResponse.json({ sido, sigungu: await listSigungu(sido) });
    }
    return NextResponse.json({ sido: await listSido() });
  } catch (err) {
    const message =
      err instanceof Error ? err.message : "지역 목록 조회 중 오류가 발생했습니다.";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
