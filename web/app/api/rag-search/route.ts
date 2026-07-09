import { NextRequest, NextResponse } from "next/server";

// 항상 서버에서 동적으로 실행 (정적 캐시 방지).
export const dynamic = "force-dynamic";

const RAG_SERVER = process.env.RAG_SERVER_URL || "http://localhost:8000";

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const resp = await fetch(`${RAG_SERVER}/api/rag-search`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!resp.ok) {
      return NextResponse.json(
        { error: "RAG 서버 오류" },
        { status: resp.status }
      );
    }
    const data = await resp.json();
    return NextResponse.json(data);
  } catch {
    return NextResponse.json(
      {
        error:
          "RAG 서버에 연결할 수 없습니다. rag_server.py가 실행 중인지 확인하세요.",
      },
      { status: 502 }
    );
  }
}
