# imunity web (MVP)

암환우 관점에서 중앙부처·지자체 공공 복지 정보를 검색·필터링하는 Next.js(App Router, TypeScript) 웹 MVP.

- 데이터 소스: 저장소 루트의 `data/welfare.db` (Phase 1 `build_db.py` 산출물, SQLite).
- 서버(API Route)에서만 SQLite를 읽는다. **API 키를 사용하지 않으며 클라이언트 번들에 서버 비밀이 들어가지 않는다.**

## 사전 준비 (데이터 생성)

`data/`는 gitignore 대상이므로 웹을 띄우기 전에 저장소 루트에서 DB를 만든다.

```bash
# 저장소 루트에서 (.env 필요 — 최초 수집 1회만 실 API 호출)
.venv/bin/python collect_raw.py 100   # data/raw/ 원문 캐시
.venv/bin/python build_db.py          # data/welfare.db 생성 (분류 포함)
```

## 실행

```bash
cd web
npm install
npm run dev     # http://localhost:3100
# 또는
npm run build && npm run start
```

DB 경로는 기본적으로 `../data/welfare.db`를 쓰며, `WELFARE_DB_PATH` 환경변수로 재정의할 수 있다.

## API

`GET /api/services` → `{ count, total, results[] }` (`total` = 필터 적용 후 전체 건수)

| 쿼리 | 설명 |
|---|---|
| `q` | 제목/요약/대상/내용/기준 부분일치 검색 |
| `sido` | 시도 필터. 지역 조건 없는 중앙부처 제도는 항상 포함(전국). |
| `sigungu` | 시군구 필터 (중앙부처 제도는 항상 포함) |
| `category` | 목적형 카테고리 (의료비/생계/돌봄·간병/심리지원/이동·교통/주거/현물·물품) |
| `relevance` | 노출할 관련성 등급 CSV. 기본 `high,medium,low` (exclude 숨김) |
| `limit` | 페이지 크기 (기본 100, 상한 500) |
| `offset` | 페이지 시작 위치 (더보기 페이지네이션용) |

`GET /api/regions` → `{ sido: [...] }`, `GET /api/regions?sido=서울특별시` → `{ sigungu: [...] }`

미입력 필터는 **제외 조건으로 쓰지 않는다** (`docs/DATA_PIPELINE.md` 6장).

## 테스트

```bash
npm test          # vitest 유닛/통합 (fixture SQLite, 실 DB 불필요)
```

저장소 전체 게이트는 루트에서 `bash scripts/run_all_tests.sh` (docs/TEST_PLAN.md 기준).

## 표기 원칙

분류 결과는 확정 판정이 아니다. UI는 "대상일 수 있음 / 확인 필요"만 사용하고
"대상입니다" 같은 확정 표현을 쓰지 않는다 (`docs/PRODUCT_SPEC.md` 7장).

## 분류 근거 노출 (개발/QA 전용)

암환자 관련성 **등급(`cancer_relevance`)과 근거(`cancer_relevance_reason`)는
`/api/services` 응답에 항상 포함**되므로 개발자는 curl/네트워크 탭으로 언제나 확인·테스트할 수 있다.

일반 사용자 화면에는 근거를 노출하지 않는다. 브라우저에서 분류 결과를 눈으로 확인하려면
`?debug=1`을 붙인다 (예: `http://localhost:3100/?debug=1`).

- 목록 카드: `dev:<등급>` 태그 표시
- 상세 드로어: "[개발용] 관련성 등급/분류 근거" 블록 표시

`?debug=1`이 없으면(=실사용자) 위 요소는 렌더되지 않는다.
