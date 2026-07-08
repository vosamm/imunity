# Project Status

이 문서는 새 대화창이나 다른 작업자가 프로젝트를 이어받을 때 가장 먼저 확인하는 현재 상태 기록이다.

마지막 업데이트: 2026-07-09 (자율 세션)

## Current Focus

Phase 0~3 전 단계 게이트 통과. 아침 체크포인트(사람 검토) 대기.

다음 초점은 `data/review_samples.md` 30건 사람 검토와 웹 MVP 로컬 확인이다.

## Active Ownership

| 담당 | 현재 역할 |
|---|---|
| User | 제품 방향 결정, API 키 로컬 관리, 다음 우선순위 승인 |
| Codex | 문서 정리, 보안 기준 반영, 데이터 파이프라인 초기 검증 |
| Future AI/Developer | `README.md`, `docs/INDEX.md`, 이 문서를 읽고 이어서 작업 |

## Done

- GitHub 저장소 clone 완료
- 로컬 `.env` 설정 완료
- `.env`, `.venv/`, Python 캐시 Git ignore 확인
- 중앙부처 복지서비스 API 1건 조회 성공
- 지자체 복지서비스 API 1건 조회 성공
- HTTP 오류 시 API 키가 포함된 요청 URL이 로그에 노출될 수 있는 문제 수정
- 공공데이터포털 키 URL decoding 처리 추가
- `requirements.txt` 추가
- `README.md`, `CLAUDE.md` 기본 정리
- 제품/아키텍처/데이터/보안/AI 협업/로드맵 문서 초안 작성
- docs 변경사항 커밋/푸시 완료 확인
- 중앙부처 Mistral 전처리 1건 검증 성공
  - 서비스 ID: `WLF00000022`
  - 서비스명: 산재근로자 사회심리재활지원
  - 결과: JSON 파싱 성공
- 지자체 Mistral 전처리 1건 검증 성공
  - 서비스 ID: `WLF00006549`
  - 서비스명: 학교 밖 청소년 검정고시 합격 축하금 지원
  - 결과: JSON 파싱 성공
- 네트워크 연결 오류 시 `requests` 기본 traceback이 API 키가 포함된 요청 URL을 노출할 수 있는 문제 수정
- 수집 코드 버그 수정 및 테스트 추가 (2026-07-09, 프로젝트 전체 리뷰 후속)
  - `iter_details` 페이지네이션 버그 수정: total이 page_size 배수가 아니면 중복 수집/누락 발생하던 문제
  - 상세 조회/파싱 실패 레코드 스킵 처리 (전체 배치 중단 방지, CLAUDE.md 2.3 준수)
  - HTTP 200 + `OpenAPI_ServiceResponse` 에러 XML(쿼터 초과, 키 오류) 감지 추가
  - 재시도 정책 통일: 목록/상세 모두 기본 3회, 타임아웃·연결오류·5xx 재시도, 4xx 즉시 실패
  - 전처리 결과 `data/*.json` 저장 추가 (Mistral 비용 보존, `data/`는 gitignore)
  - `tests/` unittest 11건 추가 (네트워크 스텁 기반, API 키 불필요)

- 자율 개발(밤샘) 실행 패키지 구축 (2026-07-09)
  - 미결정 항목 확정: SQLite / Next.js / exclude 기준 수정 (`docs/adr/0001-mvp-storage-stack-classification.md`)
  - 수락 테스트(채점표) 16건 작성: `acceptance_tests/` — Phase 1(스키마+SQLite), Phase 2(분류 골든 케이스)
  - 가드레일: `raw_cache.py` (API 원문 캐시, 쿼터 보호), `MISTRAL_MAX_CALLS` 호출 상한
  - 실행 규칙/Phase 게이트/아침 체크포인트: `docs/AUTONOMOUS_RUN.md`

## 자율 세션 진행 (2026-07-09)

- Phase 0 (초기 수집, 실 API 1회): `collect_raw.py` 작성. 중앙/지자체 각 **99건** 원문 XML을 `data/raw/`에 캐시. 게이트(각 50건 이상) PASS.
- Phase 1 (공통 스키마 + SQLite): `schema.py`(`normalize_national`/`normalize_local`), `storage.py`(`init_db`/`upsert_services`/`count_services`/`get_service`/`all_services`) 구현.
  - `acceptance_tests/test_phase1_schema_storage.py` 11건 통과, 단위 테스트 17건 GREEN 유지.
  - `build_db.py`로 캐시 전체 정규화 → `data/welfare.db` 생성 (총 **198건**).

- Phase 2 (암환자 관련성 키워드 분류): `classify.py`(`relevance(text)`) 구현.
  - `acceptance_tests/test_phase2_classify.py` 5건 통과 (소아암 non-exclude 골든 케이스 포함).
  - DB 전 레코드에 분류 적용 (high 4 / medium 86 / low 29 / exclude 79).
  - `gen_review_samples.py`로 `data/review_samples.md` 30건 생성 (아침 검토용, high/exclude 경계 포함).
- 수락 테스트 16건 + 단위 테스트 17건 전부 GREEN.
- Phase 3 (Next.js 웹 MVP): `web/` (App Router, TypeScript, Next 15.5.20).
  - `web/lib/services.ts`: `data/welfare.db`를 서버에서만 읽는 조회 계층 (better-sqlite3, readonly).
  - `web/app/api/services/route.ts`: 지역/키워드/관련성 필터 API. 미입력 필터는 제외 조건 아님. 중앙부처(전국) 항상 포함.
  - `web/app/page.tsx`: 검색/필터 + 결과 목록 + 상세 드로어. 문구는 "대상일 수 있음/확인 필요"만 사용 (확정 표현 금지).
  - 게이트: `npm run build` 성공, dev 서버 `/api/services?q=암` 응답(2건, 모두 암환자 제도) 확인, 스크린샷 3장 `data/screenshots/` 저장.
  - 보안: 서버 키 클라이언트 번들 미유입 확인(웹은 API 키 미사용, SQLite readonly). Next.js critical CVE 회피 위해 15.1.6 → 15.5.20 업그레이드.

## In Progress

- 없음 (Phase 0~3 완료). 아침 체크포인트 대기.

## Next (아침 체크포인트 이후)

1. `data/review_samples.md` 30건 사람 검토 — 특히 high/exclude 경계 (예: "에너지바우처"가 중증질환/산정특례 대상 문구로 high 판정된 것이 타당한지). 필요하면 `classify.py` 키워드 조정.
2. 웹 MVP 로컬 확인: 저장소 루트에서 `python collect_raw.py 100 && python build_db.py` → `cd web && npm install && npm run dev` → http://localhost:3100
3. 분류 근거를 사용자에게 노출할지 결정 (현재 상세 드로어 note에 분류 근거 표시 중 — 확정 판정 아님 문구와 함께).
4. Mistral 기반 분류(ROADMAP Phase 2 후반)로 키워드 fallback 보완 검토.
5. 시군구 단위 필터 UI 및 지역 자동완성, 페이지네이션 추가.
6. Supabase(Postgres) 이전 및 Vercel 배포 준비 (ADR-0001).

## Blockers

- 현재 알려진 blocker 없음

## Risks

- Mistral 전처리 실행은 비용이 발생할 수 있으므로 1건부터 검증해야 한다.
- AI 요약/분류는 원문을 대체하면 안 된다.
- 현재 Mistral 출력은 공통 스키마와 직접 일치하지 않으므로, AI 출력에 저장 구조를 종속시키면 안 된다.
- 암환자 관련성 분류 기준은 샘플 검토 후 조정이 필요하다.
- 개인정보/민감정보 관련 운영 전 법률 또는 개인정보보호 전문가 검토가 필요하다.

## Important Rules

- `.env` 내용을 읽거나 출력하지 않는다.
- `.env`를 커밋하지 않는다.
- API 키를 채팅, 문서, 로그, 커밋 메시지에 남기지 않는다.
- 전체 요청 URL을 로그에 남기지 않는다.
- 외부 API와 AI 호출은 1건부터 시작한다.
- 사용자의 진단명, 병력, 주민등록번호, 연락처 등 민감정보를 MVP에서 수집하지 않는다.
- 새 작업은 `README.md`, `docs/INDEX.md`, 이 문서를 먼저 읽고 시작한다.

## Handoff Prompt

새 대화창에서 이어서 작업할 때 아래 문장을 사용한다.

```text
/Users/sewoongoh/imunity 프로젝트 이어서 작업해줘.
먼저 README.md, docs/INDEX.md, docs/STATUS.md를 읽고 현재 상태를 파악해.
보안과 개인정보 최소 수집이 최우선이고, .env 내용은 읽거나 출력하지 마.
다음 작업은 docs/STATUS.md의 Next 항목을 기준으로 진행해.
```
