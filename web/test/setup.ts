/**
 * 테스트 fixture DB 생성 + WELFARE_DB_PATH 설정.
 *
 * storage.py의 테이블 정의와 동일한 형태(전 컬럼 TEXT, JSON 필드는 직렬화 문자열)로
 * 예측 가능한 레코드를 넣어 필터/정렬/페이지네이션 로직을 검증한다.
 */
import fs from "node:fs";
import path from "node:path";
import Database from "better-sqlite3";

const TMP_DIR = path.join(__dirname, ".tmp");
// 테스트 파일이 병렬 워커에서 동시에 setup을 실행하므로 워커별로 DB를 분리한다.
const DB_PATH = path.join(TMP_DIR, `fixture-${process.pid}.db`);

const SCHEMA_FIELDS = [
  "source_type", "source_service_id", "title", "summary", "target",
  "criteria", "benefit", "application_method", "contact", "links",
  "ministry", "region_sido", "region_sigungu", "support_categories",
  "cancer_relevance", "cancer_relevance_reason", "raw_payload",
  "fetched_at", "processed_at",
];

type FixtureRow = {
  source_type: string;
  source_service_id: string;
  title: string;
  summary?: string;
  target?: string;
  benefit?: string;
  region_sido?: string | null;
  region_sigungu?: string | null;
  support_categories?: string[];
  cancer_relevance: string;
};

// 시나리오를 커버하는 고정 레코드 8건.
export const FIXTURES: FixtureRow[] = [
  {
    source_type: "national",
    source_service_id: "N-HIGH-1",
    title: "암환자 의료비 지원",
    summary: "암 진단자 치료비 지원",
    target: "암 진단자",
    benefit: "의료비 지원",
    region_sido: null,
    region_sigungu: null,
    support_categories: ["의료비"],
    cancer_relevance: "high",
  },
  {
    source_type: "local",
    source_service_id: "L-HIGH-1",
    title: "서울 소아암 환아 지원",
    summary: "소아암 환아 가족 지원",
    target: "소아암 환아",
    benefit: "치료비 및 심리상담",
    region_sido: "서울특별시",
    region_sigungu: "강남구",
    support_categories: ["의료비", "심리지원"],
    cancer_relevance: "high",
  },
  {
    source_type: "local",
    source_service_id: "L-MED-1",
    title: "경기 간병 바우처",
    summary: "간병 서비스 바우처",
    target: "입원 환자",
    benefit: "간병 지원",
    region_sido: "경기도",
    region_sigungu: "수원시",
    support_categories: ["돌봄·간병"],
    cancer_relevance: "medium",
  },
  {
    source_type: "local",
    source_service_id: "L-MED-2",
    title: "부산 재활 치료 지원",
    summary: "재활 치료비 지원",
    target: "재활 필요 환자",
    benefit: "재활치료 바우처",
    region_sido: "부산광역시",
    region_sigungu: "해운대구",
    support_categories: ["의료비"],
    cancer_relevance: "medium",
  },
  {
    source_type: "national",
    source_service_id: "N-LOW-1",
    title: "저소득 생계 지원",
    summary: "저소득 가구 생계급여",
    target: "저소득 가구",
    benefit: "생계비",
    region_sido: null,
    region_sigungu: null,
    support_categories: ["생계"],
    cancer_relevance: "low",
  },
  {
    source_type: "local",
    source_service_id: "L-LOW-1",
    title: "서울 긴급 주거 지원",
    summary: "위기 가구 주거 지원",
    target: "위기 가구",
    benefit: "임대료 지원",
    region_sido: "서울특별시",
    region_sigungu: "마포구",
    support_categories: ["주거", "생계"],
    cancer_relevance: "low",
  },
  {
    source_type: "national",
    source_service_id: "N-EXC-1",
    title: "청년 창업 융자",
    summary: "예비 창업자 대출",
    target: "예비 창업자",
    benefit: "저금리 융자",
    region_sido: null,
    region_sigungu: null,
    support_categories: [],
    cancer_relevance: "exclude",
  },
  {
    source_type: "local",
    source_service_id: "L-EXC-1",
    title: "서울 영농 정착 지원",
    summary: "영농 정착금",
    target: "농업인",
    benefit: "정착금",
    region_sido: "서울특별시",
    region_sigungu: "강남구",
    support_categories: [],
    cancer_relevance: "exclude",
  },
];

function buildFixtureDb() {
  fs.mkdirSync(TMP_DIR, { recursive: true });
  fs.rmSync(DB_PATH, { force: true });
  const db = new Database(DB_PATH);
  const cols = SCHEMA_FIELDS.map((f) => `"${f}" TEXT`).join(", ");
  db.exec(
    `CREATE TABLE welfare_services (${cols}, PRIMARY KEY ("source_type", "source_service_id"))`
  );
  const placeholders = SCHEMA_FIELDS.map(() => "?").join(", ");
  const insert = db.prepare(
    `INSERT INTO welfare_services (${SCHEMA_FIELDS.map((f) => `"${f}"`).join(", ")}) VALUES (${placeholders})`
  );
  for (const row of FIXTURES) {
    const full: Record<string, unknown> = {
      ...row,
      criteria: null,
      application_method: null,
      contact: null,
      links: JSON.stringify(["기관 (http://example.kr)"]),
      ministry: row.source_type === "national" ? "보건복지부" : null,
      support_categories: JSON.stringify(row.support_categories ?? []),
      cancer_relevance_reason: "테스트 근거",
      raw_payload: JSON.stringify({ 서비스명: row.title }),
      fetched_at: null,
      processed_at: "2026-07-09T00:00:00Z",
    };
    insert.run(SCHEMA_FIELDS.map((f) => (full[f] === undefined ? null : full[f])));
  }
  db.close();
}

buildFixtureDb();
process.env.WELFARE_DB_PATH = DB_PATH;
