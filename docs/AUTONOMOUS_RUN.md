# 자율 개발(밤샘) 실행 계획

> 사람 개입 없이 AI가 Phase 1→2→3을 순서대로 구현하도록 설계된 실행 기준이다.
> 원칙: **채점표(수락 테스트)는 사람이 확정했고, AI는 그것을 통과할 때까지
> 스스로 고치고 재시도한다. 채점표 자체는 수정할 수 없다.**

## 1. 불변 규칙 (자율 세션이 절대 어기면 안 되는 것)

1. `acceptance_tests/` 아래 파일을 **수정·삭제·스킵하지 않는다.**
   테스트가 틀렸다고 판단되면 수정하지 말고 `docs/STATUS.md` Blockers에 기록하고 다음 작업으로 넘어간다.
2. `.env`를 읽거나 출력하지 않는다. 키 값을 어디에도 남기지 않는다.
3. 실제 공공 API 호출은 **초기 수집 1회만** 허용한다 (아래 3장). 이후 모든 개발/테스트는
   `data/raw/` 캐시(`raw_cache.py`)로만 진행한다. 개발 루프에서 실 API를 반복 호출하지 않는다.
4. Mistral 호출은 `MISTRAL_MAX_CALLS`(기본 200) 상한 안에서만 사용한다. 상한을 올리지 않는다.
5. Phase를 건너뛰지 않는다. 이전 Phase 게이트를 통과해야 다음 Phase를 시작한다.
6. Phase 완료마다 커밋한다. 커밋 메시지는 변경 이유(why)를 한 줄로 명시한다.
7. 같은 테스트가 **3회 연속** 같은 방식으로 실패하면 접근을 바꾼다.
   접근을 2번 바꿔도 실패하면 해당 항목을 STATUS Blockers에 기록하고 다음 항목으로 진행한다.
   (밤새 한 문제에 갇히는 것 방지)
8. 기능을 바꾸면 관련 문서를 같은 커밋에서 갱신한다.

## 2. 검증 명령 (모든 Phase 공통)

```bash
# 단위 테스트 — 항상 GREEN 유지
DATA_GO_KR_KEY=dummy MISTRAL_API_KEY=dummy .venv/bin/python -m unittest discover -s tests -t .

# 수락 테스트 — Phase 진행에 따라 GREEN으로 바꿔가는 목표물
DATA_GO_KR_KEY=dummy MISTRAL_API_KEY=dummy .venv/bin/python -m unittest discover -s acceptance_tests -t .
```

## 3. Phase 0 — 초기 수집 (실 API 사용, 1회만)

`.env`가 있는 환경에서 실행한다.

- 중앙부처/지자체 각 **100건**의 목록+상세 원문 XML을 `raw_cache.py`를 통해 `data/raw/`에 저장한다.
- 수집 스크립트는 `collect_raw.py`로 작성한다 (iter_details 재사용, 캐시 경유).
- 쿼터 초과(`API error response`) 발생 시 즉시 중단하고 확보된 캐시만으로 진행한다.
- 게이트: `data/raw/`에 중앙/지자체 각 50건 이상 존재.

## 4. Phase 1 — 공통 스키마 + SQLite 저장

- 구현: `schema.py` (`normalize_national`, `normalize_local`), `storage.py`
  (`init_db`, `upsert_services`, `count_services`, `get_service`).
- 게이트: `acceptance_tests/test_phase1_schema_storage.py` 전체 통과 + 단위 테스트 GREEN.
- 완료 시: 캐시된 원문 전체를 정규화해 `data/welfare.db` 생성, 건수를 STATUS에 기록.

## 5. Phase 2 — 암환자 관련성 분류 (키워드 기반)

- 구현: `classify.py` — `relevance(text) -> {"level", "reason"}`.
  기준은 `docs/DATA_PIPELINE.md` 5장 + ADR-0001 (인구집단만으로 exclude 금지).
- 게이트: `acceptance_tests/test_phase2_classify.py` 전체 통과.
- 완료 시: DB 전 레코드에 분류 적용 후, **사람 검토용 샘플 30건**을
  `data/review_samples.md`로 생성한다 (제목, 등급, 근거 — 아침 체크포인트용).
- Mistral 기반 분류는 이 Phase에서 하지 않는다 (키워드 fallback 먼저, ROADMAP Phase 2 순서).

## 6. Phase 3 — Next.js 웹 MVP

- `web/` 디렉터리에 Next.js 앱 생성 (App Router, TypeScript).
- `/api/services`: SQLite(`data/welfare.db`)를 읽어 지역/키워드/관련성 필터 제공.
  미입력 필터는 제외 조건으로 쓰지 않는다 (DATA_PIPELINE 6장).
- 화면: 검색/필터 + 결과 목록 + 상세. 문구는 "대상일 수 있음/확인 필요"만 사용
  (PRODUCT_SPEC 7장 — 확정 표현 금지).
- 게이트 (코드 채점표가 없으므로 자체 검증 후 증적 남기기):
  - `npm run build` 성공
  - dev 서버 기동 후 `/api/services?q=암` 응답 확인
  - 주요 화면 스크린샷을 `data/screenshots/`에 저장
- 서버 키를 클라이언트 번들에 넣지 않는다.

## 7. 아침 체크포인트 (사람이 할 일, 10~15분)

1. `git log` 와 `docs/STATUS.md` — 어느 Phase까지 갔는지, Blockers 확인
2. 수락 테스트 직접 실행 — 통과 주장 검증
3. `data/review_samples.md` — 분류 샘플 30건 눈으로 검토 (특히 소아암/exclude 경계)
4. Phase 3 도달 시 스크린샷/로컬 실행 확인
5. 피드백을 STATUS Next에 적고 다음 밤 실행

## 8. 실행 방법

`.env`가 있는 원본 디렉터리에서 새 Claude Code 세션(Opus 4.8 이상)을 열고 아래를 붙여넣는다.

```text
/Users/sewoongoh/imunity 프로젝트의 자율 개발 세션이다.
먼저 README.md, docs/INDEX.md, docs/STATUS.md, docs/AUTONOMOUS_RUN.md를 읽어라.
docs/AUTONOMOUS_RUN.md의 불변 규칙을 절대 어기지 말고,
Phase 0부터 순서대로 게이트를 통과할 때까지 스스로 수정·재시도하며 진행해라.
acceptance_tests/는 채점표이므로 수정 금지다.
.env 내용은 읽거나 출력하지 마라.
막히면 멈추지 말고 STATUS Blockers에 기록하고 다음 항목으로 진행해라.
각 Phase 완료마다 커밋하고 docs/STATUS.md를 갱신해라.
```

- 사전 조건: `.env` 존재, `.venv` 설치, (Phase 3용) Node.js 18+ 설치.
- 권한: 파일 수정/테스트 실행은 자동 허용, 외부 API 호출이 잦은 명령은
  세션 권한 설정에 따라 확인이 필요할 수 있다.
