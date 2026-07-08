# 테스트 계획 (자율 개발 루프 종료 기준)

> 이 문서는 자율 개발 루프의 **종료 조건**이다.
> 아래 모든 항목이 GREEN이 될 때까지 개발→테스트→개선을 반복한다.
> `acceptance_tests/`(사람 확정 채점표)와 별개로, AI가 스스로 설계한 상위 검증 계층이다.
>
> 비용 규칙: 이 루프에서 Mistral 호출 0회, 실 공공 API 호출 0회 (data/raw/ 캐시만 사용).

## 실행 방법 (전체 한 번에)

```bash
bash scripts/run_all_tests.sh
```

## 1. Python 단위 테스트 (`tests/`)

기존 17건 + 아래 확장. 명령:
`DATA_GO_KR_KEY=dummy MISTRAL_API_KEY=dummy .venv/bin/python -m unittest discover -s tests -t .`

| ID | 항목 | 내용 |
|---|---|---|
| PY-01 | classify 경계 | 빈 문자열/None/공백만 → exclude, reason 비어있지 않음 |
| PY-02 | classify 혼합 | high+medium 키워드 공존 시 high 우선 |
| PY-03 | classify 저소득 단독 | 의료 맥락 없는 "저소득/긴급/위기"만 → low (exclude 아님) |
| PY-04 | schema 빈 detail | 모든 값이 빈 문자열이어도 필드 전부 존재, None 처리, links는 [] |
| PY-05 | schema 링크 다건 | " / " 구분 링크 3건 → 리스트 3건 분리 |
| PY-06 | schema 원문 보존 | raw_payload == 입력 detail (동일 객체 수준 보존) |
| PY-07 | schema 카테고리 파생 | 의료비/생계/돌봄 등 support_categories 파생 규칙 |
| PY-08 | storage 특수문자 | 따옴표/이모지/개행 포함 저장·조회 무손실 |
| PY-09 | storage 대량 | 500건 upsert 후 count 정확, 재실행 중복 없음 |
| PY-10 | storage 없는 키 | get_service 미존재 → None |
| PY-11 | build_db 통합 | fixture 캐시 디렉터리 → DB 적재 건수/분류 적용 확인 |
| PY-12 | review_samples 계약 | 30건, 등급 쿼터, 마크다운 테이블 형식 |

## 2. 수락 테스트 (`acceptance_tests/`, 무수정)

16건 전체 GREEN 유지. 명령:
`DATA_GO_KR_KEY=dummy MISTRAL_API_KEY=dummy .venv/bin/python -m unittest discover -s acceptance_tests -t .`

## 3. 웹 유닛/통합 (`web/`, vitest)

명령: `cd web && npm test`

| ID | 항목 | 내용 |
|---|---|---|
| WB-01 | 기본 노출 | 필터 없음 → exclude 제외 전부, high 우선 정렬 |
| WB-02 | 키워드 검색 | q 부분일치 (제목/요약/대상/내용/기준), 대소문자 무시 |
| WB-03 | 시도 필터 | sido 지정 시 해당 시도 + region null(중앙부처) 포함 |
| WB-04 | 시군구 필터 | sigungu 동일 규칙 |
| WB-05 | 관련성 필터 | relevance CSV 지정 등급만 |
| WB-06 | 카테고리 필터 | category 지정 시 해당 카테고리 포함 레코드만 |
| WB-07 | limit/offset | 페이지 크기·전체 건수(total) 계약 |
| WB-08 | 미존재 상세 | getService 미존재 → null |
| WB-09 | listSido | DISTINCT 시도 정렬 목록 |
| WB-10 | listSigungu | 시도 종속 시군구 목록 |
| WB-11 | API 계약 | /api/services 응답 {count,total,results[]} 스키마, 잘못된 limit 방어 |
| WB-12 | API 검색 | ?q=암 → 결과 전부 검색어 포함 필드 보유 |

## 4. 빌드/보안 게이트

| ID | 항목 | 내용 |
|---|---|---|
| SEC-01 | `npm run build` 성공 | 타입 에러 0 |
| SEC-02 | 클라이언트 번들 비밀 스캔 | MISTRAL/DATA_GO_KR/serviceKey/Bearer 패턴 0건 |
| SEC-03 | git 추적 파일 점검 | .env, data/, node_modules, *.db 미추적 |
| SEC-04 | npm audit | critical/high 0건 (moderate 전개성은 기록 후 허용) |

## 5. E2E 브라우저 시나리오 (Playwright, dev 서버)

증적: `data/screenshots/e2e-*.png`, 콘솔 에러 0건.

| ID | 시나리오 | 기대 |
|---|---|---|
| E2E-01 | 첫 화면 | 고지문, 검색/필터, 결과 목록, 관련성 높은 순 |
| E2E-02 | "암" 검색 | 암 관련 제도만, 0건 아님 |
| E2E-03 | 시도 선택 | 지자체(해당 시도)+중앙부처 혼합 노출 |
| E2E-04 | 카테고리 칩 | 선택 시 해당 목적 제도만 |
| E2E-05 | 상세 열기/닫기 | 클릭→드로어, ESC/배경클릭/버튼으로 닫힘, 포커스 복귀 |
| E2E-06 | 확정 표현 금지 | "대상입니다" 등 확정 문구 부재, "대상일 수 있음/확인 필요"만 |
| E2E-07 | debug 게이트 | 기본: 분류 근거 미노출 / ?debug=1: dev 태그+근거 노출 |
| E2E-08 | 빈 결과 | 무의미 검색어 → 안내 문구 + 필터 초기화 버튼 |
| E2E-09 | 모바일(375px) | 가로 스크롤 없음, 카드/드로어 사용 가능 |
| E2E-10 | 더보기 | 결과 100건 초과 시 total 표기·더보기 동작 |

## 6. UX 결정 기록 (환자 유저 기준, AI 결정)

- **필터 방식 유지 (챗봇 대신)**: 투병 중 사용자는 인지 부담이 낮은 "보이는 선택지"가 낫다. 자유 입력 챗봇은 무엇을 물어야 할지 모르는 사용자에게 부담. → 칩/드롭다운 필터 + 키워드 검색.
- **카테고리 칩**: 환자의 실제 질문은 "치료비 도움", "간병 도움"처럼 목적형 → support_categories 파생 후 목적별 원터치 필터.
- **시군구 필터**: 지자체 제도는 거주지가 결정적 → 시도 선택 시 시군구 선택지 노출.
- **접근성**: 고령 사용자 비중 고려 — 키보드 조작(ESC), 포커스 복귀, aria-live, 충분한 대비/글자 크기.
- **빈 결과**: 막다른 골목 금지 — 초기화 버튼과 다음 행동 안내 제공.

## 7. 결과 기록

루프 완료 시 아래를 갱신한다.

기록일: 2026-07-09 (자율 루프 1회차 완료)

- [x] 1장 Python 단위: **42건 GREEN** (기존 17 + 확장 25)
- [x] 2장 수락: **16건 GREEN** (무수정 유지)
- [x] 3장 웹 vitest: **23건 GREEN**
- [x] 4장 빌드/보안: SEC-01~04 전부 PASS (npm audit critical/high 0건; moderate 2건은 Next 내부 postcss 전개성 — 강제 수정 시 Next 9로 다운그레이드되므로 기록 후 허용)
- [x] 5장 E2E: E2E-01~10 전부 PASS, 스크린샷 9장(`data/screenshots/e2e-*.png`), 콘솔 에러/경고 0건
  - E2E-06 참고: 본문 "확정" 검출 2건은 모두 고지문의 부정 표현("확정 판정이 아니라/아닙니다")으로 의도된 문구. 확정형 표현("대상입니다" 등)은 0건.
