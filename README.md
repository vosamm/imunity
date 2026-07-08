# imunity

암환우 AI 복지 매칭 서비스를 위한 데이터 수집/전처리 프로토타입입니다.

현재는 웹앱이 아니라 Python 스크립트 기반입니다. 중앙부처/지자체 복지서비스 API에서 데이터를 가져오고, Mistral API로 주요 항목을 구조화하는 흐름을 목표로 합니다.

## 현재 상태

- 중앙부처 복지서비스 API 1건 조회 성공
- 지자체 복지서비스 API 1건 조회 성공
- Mistral 전처리 코드 구현됨
- 프론트엔드, API 서버, DB, 로그인, 배포 설정은 아직 없음

## 파일 구성

| 파일 | 설명 |
|---|---|
| `national_welfare.py` | 중앙부처 복지서비스 목록/상세 조회 |
| `local_welfare.py` | 지자체 복지서비스 목록/상세 조회 |
| `national_preprocess.py` | 중앙부처 복지서비스 상세 정보 전처리 |
| `local_preprocess.py` | 지자체 복지서비스 상세 정보 전처리 |
| `CLAUDE.md` | 프로젝트 규칙, 보안 기준, 현재 상태 문서 |
| `requirements.txt` | Python 의존성 |

## 보안 원칙

API 키는 절대 코드, 채팅, 커밋, 로그에 노출하지 않습니다.

로컬에서는 `.env` 파일에만 저장합니다.

```env
DATA_GO_KR_KEY=your_data_go_kr_key
MISTRAL_API_KEY=your_mistral_api_key
```

일반적인 API 키는 따옴표 없이 입력합니다.

`.env`와 `.venv/`는 Git에 커밋하지 않습니다.

## 로컬 실행

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

환경변수 설정 여부만 확인합니다. 키 값 자체는 출력하지 않습니다.

```bash
.venv/bin/python -c "from dotenv import load_dotenv; import os; load_dotenv(); print('DATA_GO_KR_KEY set:', bool(os.getenv('DATA_GO_KR_KEY'))); print('MISTRAL_API_KEY set:', bool(os.getenv('MISTRAL_API_KEY')))"
```

중앙부처 API 1건 조회:

```bash
.venv/bin/python -c "import national_welfare; services = national_welfare.parse_list(national_welfare.get_welfare_list(page_no=1, num_of_rows=1)); print('national services:', len(services)); print(services[0]['servNm'] if services else 'no data')"
```

지자체 API 1건 조회:

```bash
.venv/bin/python -c "import local_welfare; services = local_welfare.parse_list(local_welfare.get_welfare_list(page_no=1, num_of_rows=1)); print('local services:', len(services)); print(services[0]['servNm'] if services else 'no data')"
```

## 다음 작업

1. Mistral 전처리 파이프라인을 중앙/지자체 각 1건씩 검증
2. 암환우 관련성 필터링 기준 정의
3. 수집 결과 저장 구조 설계
4. 웹앱 골격 추가
