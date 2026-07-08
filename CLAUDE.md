# 암환우 AI 복지 매칭 서비스 — 프로젝트 Rule 문서

> 본 문서는 팀/개발자 간 공유를 위한 기획 기준 문서입니다.
> IPO 명세, 프로세스 흐름, DB 스키마, 메타데이터 규칙, 개인정보 처리 규칙을 통합하여 관리합니다.
> **변경 시 이 문서를 최신 상태로 유지하는 것을 원칙으로 합니다.**
>
> 자세한 제품/기술/보안/협업 기준은 `docs/` 디렉터리 문서를 함께 확인합니다.
> 작업 시작 전 `README.md`, `docs/INDEX.md`, `docs/STATUS.md`를 읽는 것을 기본 규칙으로 합니다.
>
> ⚠️ **본 문서 5장(개인정보 처리 규칙)은 일반적인 개인정보보호법(PIPA) 원칙을 정리한 참고 자료이며, 법률 자문을 대체하지 않습니다.**
> 본 서비스는 건강정보(암 진단 관련 정보)를 다루는 민감한 서비스이므로, 실제 운영 전 반드시 **개인정보보호 전문 변호사 또는 개인정보보호책임자(CPO) 검토**를 받으시기 바랍니다.

---

## 0. 프로젝트 개요

- **서비스명**: 암환우 AI 복지 매칭 서비스
- **현재 구현 상태**: Python 기반 데이터 수집/전처리 프로토타입
- **핵심 기능**:
  1. 공공 API(공공데이터포털)에서 복지 지원 정보를 수집
  2. 암 환자가 받을 수 있는 지원 정보만 AI/키워드 기반으로 필터링
  3. 연령, 성별, 소득수준, 거주지역 등 조건별 필터링 기능 제공
  4. 사용자가 본인에게 맞는 제도를 빠르게 확인 가능하도록 UI 제공

### 0.1 현재 코드 구성

| 파일 | 역할 | 상태 |
|---|---|---|
| `national_welfare.py` | 중앙부처 복지서비스 API 목록/상세 조회 및 XML 파싱 | 1건 조회 검증 완료 |
| `local_welfare.py` | 지자체 복지서비스 API 목록/상세 조회 및 XML 파싱 | 1건 조회 검증 완료 |
| `national_preprocess.py` | 중앙부처 상세 데이터를 Mistral로 구조화 JSON 전처리 후 `data/`에 저장 | 1건 실행 검증 완료 |
| `local_preprocess.py` | 지자체 상세 데이터를 Mistral로 구조화 JSON 전처리 후 `data/`에 저장 | 1건 실행 검증 완료 |
| `tests/` | 수집/전처리 로직 unittest (네트워크 스텁 기반, API 키 불필요) | 11건 통과 |
| `requirements.txt` | Python 실행 의존성 | `requests`, `python-dotenv` |

### 0.2 아직 구현되지 않은 범위

- 웹 프론트엔드
- API 서버 엔드포인트
- 데이터베이스 저장 구조
- 로그인/회원가입
- 사용자 검색/필터 UI
- 배포 설정
- 전체 배치 운영 로직, 캐시, 관리자 알림

---

## 1. Input 규칙

### 1.1 트리거

| 트리거 유형 | 설명 |
|---|---|
| 정기 배치 | 매일 09:00, 스케줄러(cron)가 공공데이터포털 API 자동 호출 |
| 사용자 요청 | 사용자가 필터 조건 설정 후 검색 버튼 클릭 |
| 관리자 수동 트리거 | 신규 API 연동 추가, 강제 갱신 버튼 클릭 |

### 1.2 입력 데이터 소스

- 공공데이터포털 - 지자체복지서비스 API
- 공공데이터포털 - 중앙부처복지서비스 API
- 응답 형식: JSON/XML
- 현재 검증 결과:
  - 중앙부처 복지서비스 API 1건 조회 성공
  - 지자체 복지서비스 API 1건 조회 성공

### 1.3 입력 검증 규칙

- HTTP 응답 코드 200 확인, 아닐 시 재시도(최대 3회) → 실패 시 캐시 데이터 폴백
- 검증 실패 레코드는 스킵 후 오류 로그 적재 (전체 프로세스 중단 금지)
- API 에러 로그에는 `serviceKey`, `DATA_GO_KR_KEY`, `MISTRAL_API_KEY` 등 민감정보가 포함되지 않아야 한다.

---

## 2. Process 규칙

### 2.1 처리 단계

1. **Step 1 — 데이터 수집**: API 호출, 인증
2. **Step 2 — 전처리 및 필터링**
3. **Step 3 — AI 매칭**

### 2.3 예외 처리 규칙

- API 타임아웃/서버 오류 → 재시도 3회 → 실패 시 최근 캐시 사용 + 관리자 알림
- 파싱 오류 레코드 → 스킵 + 로그 적재, 전체 배치는 계속 진행
- HTTP 오류 처리 시 전체 요청 URL을 그대로 출력하지 않는다. URL query string에 API 키가 포함될 수 있기 때문이다.
- 공공데이터포털 키가 URL-encoded 형태로 저장될 수 있으므로, 코드에서는 `unquote()` 후 `requests` 파라미터로 전달한다.

---

## 3. Output 규칙

### 3.1 산출물

- 복지 지원 리스트 (서비스명, 지원내용, 신청 기한, 소관기관, 링크)
- (옵션) 신청 마감 임박 알림 데이터

### 3.2 전달 방식

- 화면: 리스트 형태 실시간 렌더링

---

## 4. 필터링 조건 처리 규칙

- 나이/소득/지역 등 조건이 **명시되지 않은 경우** → NULL이 아니라 "전체 허용"으로 명확히 처리 (필터링 로직 오류 방지)

---

## 5. 개인정보 처리 규칙

- 인스타그램 링크 클릭 시 전달되는 리퍼러/UTM/클릭ID는 쿠키·유사기술을 통한 이용자 활동정보 수집에 해당할 수 있으므로, 최초 접속 시 쿠키 사용 고지 및 선택 동의(옵트인/옵트아웃) UI를 제공한다.

---

## 6. 보안 및 환경변수 규칙

- 로컬 API 키는 `.env`에만 저장한다.
- `.env`는 Git에 커밋하지 않는다.
- `.gitignore`는 최소한 다음 항목을 포함해야 한다.
  - `.env`
  - `.venv/`
  - `__pycache__/`
  - `*.pyc`
- API 키 값을 채팅, 이슈, 커밋 메시지, 로그, 스크린샷에 노출하지 않는다.
- `.env` 예시:

```env
DATA_GO_KR_KEY=your_data_go_kr_key
MISTRAL_API_KEY=your_mistral_api_key
```

- 일반적인 API 키 값은 따옴표 없이 입력한다.
- 배포 환경에서는 로컬 `.env`를 복사하지 않고, 배포 플랫폼의 환경변수/시크릿 저장소를 사용한다.

---

## 7. 로컬 실행 기준

### 7.1 환경 준비

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

### 7.2 키 로드 확인

값 자체는 출력하지 않고 설정 여부만 확인한다.

```bash
.venv/bin/python -c "from dotenv import load_dotenv; import os; load_dotenv(); print('DATA_GO_KR_KEY set:', bool(os.getenv('DATA_GO_KR_KEY'))); print('MISTRAL_API_KEY set:', bool(os.getenv('MISTRAL_API_KEY')))"
```

### 7.3 수집 API 스모크 테스트

중앙부처 1건:

```bash
.venv/bin/python -c "import national_welfare; services = national_welfare.parse_list(national_welfare.get_welfare_list(page_no=1, num_of_rows=1)); print('national services:', len(services)); print(services[0]['servNm'] if services else 'no data')"
```

지자체 1건:

```bash
.venv/bin/python -c "import local_welfare; services = local_welfare.parse_list(local_welfare.get_welfare_list(page_no=1, num_of_rows=1)); print('local services:', len(services)); print(services[0]['servNm'] if services else 'no data')"
```

---

### 7.4 단위 테스트 실행

네트워크 호출 없이 수집/전처리 로직을 검증한다. 실제 API 키가 필요 없다.

```bash
DATA_GO_KR_KEY=dummy MISTRAL_API_KEY=dummy .venv/bin/python -m unittest discover -s tests -t .
```

## 8. 다음 작업 우선순위

1. ~~Mistral 전처리 파이프라인을 중앙/지자체 각 1건씩 실행 검증~~ (완료, `docs/DATA_PIPELINE.md` 8장)
2. 전체 배치 전에 소량 배치 기준 수립
3. 암환우 관련성 필터링 기준 확정
4. 저장 구조 설계
5. 웹앱 골격 추가

상세 로드맵은 `docs/ROADMAP.md`를 따른다.
