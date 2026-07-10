# imunity

암환자가 자신에게 맞는 중앙부처/지자체 공공 복지 정보를 검색·필터링하고, AI 매칭으로 추천받을 수 있는 웹서비스 프로젝트입니다.

저장소 문서가 현재 개발 기준입니다. 외부 기획 링크나 대화 내용은 참고 자료이며, 확정된 내용은 `docs/` 아래 문서로 옮긴 뒤 작업합니다.

## 현재 상태

- 공공데이터포털(중앙부처/지자체 복지서비스 API) 원문 수집 → 정규화 → SQLite 적재 파이프라인 동작
- 암환자 관련성 분류(`classify.py`, 키워드 규칙) 및 목적형 카테고리 파생 포함
- 전체 서비스 임베딩(mistral-embed) 생성·저장, RAG 검색 API 서버(`rag_server.py`) 동작
- Next.js 웹 UI 동작: 키워드 검색 탭(SQLite 직접 조회) + AI 매칭 탭(RAG 서버 연동)
- 수집 데이터(`data/welfare.db`, 원문 캐시) 저장소에 포함 — 별도 수집 없이 바로 실행 가능
- 로그인/회원가입, 배포 설정은 아직 없음

## 구조

```
공공 API ──(collect_raw.py, 1회)──> data/raw/ 원문 XML 캐시
data/raw/ ──(build_db.py)──> data/welfare.db (정규화 + 분류 + 임베딩)
data/welfare.db ──┬── web/ (Next.js :3100) ── 키워드 검색 탭 (SQLite 직접 조회)
                  └── rag_server.py (FastAPI :8001) ── AI 매칭 탭 (임베딩 유사도 검색)
```

## 파일 구성

| 파일 | 설명 |
|---|---|
| `collect_raw.py` | 공공 API 원문 수집 → `data/raw/` 캐시 (초기 1회만 실 API 호출) |
| `national_welfare.py` / `local_welfare.py` | 중앙부처/지자체 복지서비스 API 조회 및 XML 파싱 |
| `schema.py` | 공통 스키마 정규화, 목적형 카테고리 파생 |
| `classify.py` | 암환자 관련성 등급 분류 (키워드 규칙, high/medium/low/exclude) |
| `build_db.py` | 캐시 → 정규화/분류 → SQLite 적재 + 전체 임베딩 생성 |
| `storage.py` | SQLite 저장 계층 (서비스/임베딩 UPSERT) |
| `embed.py` | Mistral Embed API 호출 (배치 분할 포함) |
| `rag_server.py` | RAG 검색 FastAPI 서버 — 쿼리 임베딩 → 코사인 유사도 top-20 + 지역 필터, 표시용 일치율 보정 |
| `national_preprocess.py` / `local_preprocess.py` | 상세 데이터를 Mistral로 구조화 JSON 전처리 |
| `gen_review_samples.py` | 분류 결과 사람 검토용 샘플 출력 |
| `web/` | Next.js(App Router, TS) 웹 UI — 상세는 [web/README.md](./web/README.md) |
| `tests/` | Python 단위 테스트 (네트워크 스텁 기반, 실제 키 불필요) |
| `CLAUDE.md` | 프로젝트 규칙, 보안 기준 문서 |
| `docs/` | 제품, 아키텍처, 데이터, 보안, AI 협업, 로드맵 문서 |

## 문서

작업 전 [docs/INDEX.md](./docs/INDEX.md)를 먼저 확인합니다.

| 문서 | 설명 |
|---|---|
| [docs/PRODUCT_SPEC.md](./docs/PRODUCT_SPEC.md) | 제품 목적, 사용자, MVP 범위 |
| [docs/ARCHITECTURE.md](./docs/ARCHITECTURE.md) | 목표 시스템 구조 |
| [docs/DATA_PIPELINE.md](./docs/DATA_PIPELINE.md) | 데이터 수집/정규화/AI 전처리 기준 |
| [docs/SECURITY_PRIVACY.md](./docs/SECURITY_PRIVACY.md) | 보안과 개인정보 보호 기준 |
| [docs/AI_COLLABORATION.md](./docs/AI_COLLABORATION.md) | AI 협업 작업 규칙 |
| [docs/ROADMAP.md](./docs/ROADMAP.md) | 단계별 구현 계획 |
| [docs/STATUS.md](./docs/STATUS.md) | 현재 진척도, 담당, 다음 작업 |

## 보안 원칙

API 키는 절대 코드, 채팅, 커밋, 로그에 노출하지 않습니다.

로컬에서는 `.env` 파일에만 저장합니다.

```env
DATA_GO_KR_KEY=your_data_go_kr_key
MISTRAL_API_KEY=your_mistral_api_key
```

일반적인 API 키는 따옴표 없이 입력합니다.

`.env`와 `.venv/`는 Git에 커밋하지 않습니다. 웹 클라이언트 번들에는 서버 비밀이 들어가지 않습니다 (SQLite 조회는 서버 API Route에서만).

## 로컬 실행

### 1. Python 환경

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt        # Windows: .venv/Scripts/pip
```

환경변수 설정 여부만 확인합니다. 키 값 자체는 출력하지 않습니다.

```bash
.venv/bin/python -c "from dotenv import load_dotenv; import os; load_dotenv(); print('DATA_GO_KR_KEY set:', bool(os.getenv('DATA_GO_KR_KEY'))); print('MISTRAL_API_KEY set:', bool(os.getenv('MISTRAL_API_KEY')))"
```

### 2. 데이터 (선택)

`data/welfare.db`와 원문 캐시가 저장소에 포함되어 있어 기본적으로 이 단계는 생략합니다. 데이터를 새로 수집/재구축할 때만:

```bash
.venv/bin/python collect_raw.py 100   # 실 API 호출 — 초기 수집 1회만
.venv/bin/python build_db.py          # 정규화/분류 적재 + 전체 임베딩 생성 (Mistral 호출)
```

### 3. RAG 검색 서버 (AI 매칭 탭에 필요)

```bash
.venv/bin/python rag_server.py --port 8001
```

- `POST /api/rag-search` — 폼(나이/지역/소득) + 자유 텍스트를 임베딩해 코사인 유사도 상위 20건 반환
- 응답의 `similarity`는 원시 코사인이 아니라 표시용 보정 점수(전체 후보 평균 대비)입니다. 순위는 원시 코사인 기준입니다.

### 4. 웹 UI

```bash
cd web
npm install
npm run dev     # http://localhost:3100
```

키워드 검색 탭은 `data/welfare.db`만 있으면 동작하고, AI 매칭 탭은 3번의 RAG 서버가 떠 있어야 합니다. 상세 API 명세는 [web/README.md](./web/README.md) 참고.

### 5. 테스트

Python (네트워크/실제 키 불필요):

```bash
DATA_GO_KR_KEY=dummy MISTRAL_API_KEY=dummy .venv/bin/python -m unittest discover -s tests -t .
```

웹:

```bash
cd web && npm test
```

## 다음 작업

1. 검색 품질 개선 (은어/구어 쿼리 대응 — 검색 키워드 임베딩 또는 LLM 재작성 검토)
2. 배포 설정
3. 정기 배치(신규/변경 제도 갱신) 운영 로직

상세 로드맵은 [docs/ROADMAP.md](./docs/ROADMAP.md)를 따릅니다.
