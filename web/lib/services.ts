import "server-only";
import path from "node:path";
import fs from "node:fs";
import Database from "better-sqlite3";

// 정규화 데이터는 저장소 루트 data/welfare.db (Phase 1 build_db.py 산출물).
// 환경변수로 재정의 가능. 서버에서만 접근하며 클라이언트 번들에 포함되지 않는다.
const DB_PATH =
  process.env.WELFARE_DB_PATH ||
  path.join(process.cwd(), "..", "data", "welfare.db");

export type Service = {
  source_type: string;
  source_service_id: string;
  title: string | null;
  summary: string | null;
  target: string | null;
  criteria: string | null;
  benefit: string | null;
  application_method: string | null;
  contact: string | null;
  links: string[];
  ministry: string | null;
  region_sido: string | null;
  region_sigungu: string | null;
  support_categories: string[];
  cancer_relevance: string | null;
  cancer_relevance_reason: string | null;
};

export type ServiceQuery = {
  q?: string;
  sido?: string;
  sigungu?: string;
  // 목적형 카테고리 (schema.SUPPORT_CATEGORIES와 1:1).
  category?: string;
  // 노출할 관련성 등급 (기본: exclude 제외).
  levels?: string[];
  limit?: number;
  offset?: number;
};

export type SearchResult = {
  // 필터 적용 후 전체 건수 (페이지네이션 기준).
  total: number;
  results: Service[];
};

let _db: Database.Database | null = null;

function db(): Database.Database {
  if (_db) return _db;
  if (!fs.existsSync(DB_PATH)) {
    throw new Error(
      "welfare.db가 없습니다. 저장소 루트에서 `python build_db.py`로 생성하세요."
    );
  }
  _db = new Database(DB_PATH, { readonly: true, fileMustExist: true });
  return _db;
}

function parseJsonArray(value: unknown): string[] {
  try {
    const parsed = JSON.parse((value as string) ?? "[]");
    return Array.isArray(parsed) ? (parsed as string[]) : [];
  } catch {
    return [];
  }
}

function rowToService(row: Record<string, unknown>): Service {
  const links = parseJsonArray(row.links);
  return {
    source_type: row.source_type as string,
    source_service_id: row.source_service_id as string,
    title: (row.title as string) ?? null,
    summary: (row.summary as string) ?? null,
    target: (row.target as string) ?? null,
    criteria: (row.criteria as string) ?? null,
    benefit: (row.benefit as string) ?? null,
    application_method: (row.application_method as string) ?? null,
    contact: (row.contact as string) ?? null,
    links,
    ministry: (row.ministry as string) ?? null,
    region_sido: (row.region_sido as string) ?? null,
    region_sigungu: (row.region_sigungu as string) ?? null,
    support_categories: parseJsonArray(row.support_categories),
    cancer_relevance: (row.cancer_relevance as string) ?? null,
    cancer_relevance_reason: (row.cancer_relevance_reason as string) ?? null,
  };
}

const RELEVANCE_RANK: Record<string, number> = {
  high: 0,
  medium: 1,
  low: 2,
  exclude: 3,
};

export function searchServices(query: ServiceQuery): SearchResult {
  const rows = db()
    .prepare("SELECT * FROM welfare_services")
    .all() as Record<string, unknown>[];
  let services = rows.map(rowToService);

  const levels = query.levels && query.levels.length
    ? new Set(query.levels)
    : new Set(["high", "medium", "low"]); // 기본은 exclude 숨김
  services = services.filter((s) =>
    levels.has(s.cancer_relevance ?? "exclude")
  );

  const q = (query.q ?? "").trim().toLowerCase();
  if (q) {
    services = services.filter((s) => {
      const hay = [s.title, s.summary, s.target, s.benefit, s.criteria]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();
      return hay.includes(q);
    });
  }

  // 지역 필터: 미입력은 제외 조건으로 쓰지 않는다 (DATA_PIPELINE 6장).
  // 지역 조건이 없는 중앙부처(national, region null) 제도는 모든 지역에서 노출한다.
  const sido = (query.sido ?? "").trim();
  if (sido) {
    services = services.filter(
      (s) => s.region_sido === null || s.region_sido === sido
    );
  }
  const sigungu = (query.sigungu ?? "").trim();
  if (sigungu) {
    services = services.filter(
      (s) => s.region_sigungu === null || s.region_sigungu === sigungu
    );
  }

  // 카테고리 필터: 환자의 목적(치료비/간병 등) 기준 원터치 필터.
  const category = (query.category ?? "").trim();
  if (category) {
    services = services.filter((s) =>
      s.support_categories.includes(category)
    );
  }

  services.sort((a, b) => {
    const ra = RELEVANCE_RANK[a.cancer_relevance ?? "exclude"] ?? 3;
    const rb = RELEVANCE_RANK[b.cancer_relevance ?? "exclude"] ?? 3;
    if (ra !== rb) return ra - rb;
    return (a.title ?? "").localeCompare(b.title ?? "", "ko");
  });

  const total = services.length;
  const offset = query.offset && query.offset > 0 ? query.offset : 0;
  const limit = query.limit && query.limit > 0 ? query.limit : 100;
  return { total, results: services.slice(offset, offset + limit) };
}

export function getService(
  sourceType: string,
  sourceServiceId: string
): Service | null {
  const row = db()
    .prepare(
      "SELECT * FROM welfare_services WHERE source_type=? AND source_service_id=?"
    )
    .get(sourceType, sourceServiceId) as Record<string, unknown> | undefined;
  return row ? rowToService(row) : null;
}

export function listSido(): string[] {
  const rows = db()
    .prepare(
      "SELECT DISTINCT region_sido FROM welfare_services WHERE region_sido IS NOT NULL ORDER BY region_sido"
    )
    .all() as { region_sido: string }[];
  return rows.map((r) => r.region_sido);
}

export function listSigungu(sido: string): string[] {
  const rows = db()
    .prepare(
      "SELECT DISTINCT region_sigungu FROM welfare_services WHERE region_sido = ? AND region_sigungu IS NOT NULL ORDER BY region_sigungu"
    )
    .all(sido) as { region_sigungu: string }[];
  return rows.map((r) => r.region_sigungu);
}
