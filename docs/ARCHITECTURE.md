# Architecture

## 1. 현재 구조

현재 저장소는 Python 스크립트 프로토타입이다.

```text
공공데이터포털 API
  -> national_welfare.py / local_welfare.py
  -> national_preprocess.py / local_preprocess.py
  -> 콘솔 출력
```

## 2. 목표 구조

MVP 웹서비스는 다음 구조를 권장한다.

```text
공공데이터포털 API
  -> 수집 배치
  -> 원문 저장
  -> 정규화/AI 전처리
  -> 검색 DB
  -> API 서버
  -> 웹 프론트엔드
```

## 3. 기술 선택 (확정: ADR-0001)

초기 MVP 기준 — `docs/adr/0001-mvp-storage-stack-classification.md`에서 확정:

- Web: Next.js (App Router + Route Handlers)
- Batch: Python 스크립트 유지 후 점진적으로 작업 큐/cron 연결
- DB: MVP는 **SQLite**, 배포 단계(Phase 4)에서 Supabase Postgres 이전
- Hosting: Vercel
- Secrets: 배포 플랫폼 환경변수 또는 Secret Manager

현재 Python 수집 코드는 버리지 말고, 검증된 수집 모듈로 유지한다.

## 4. 모듈 책임

| 영역 | 책임 |
|---|---|
| Collector | 공공 API 호출, 재시도, 페이지네이션, 원문 응답 보존 |
| Parser | XML/JSON을 내부 표준 형태로 변환 |
| Normalizer | 중앙/지자체 필드명을 공통 스키마로 정리 |
| Classifier | 암환자 관련성, 지원 유형, 대상 조건 태깅 |
| Storage | 원문, 정규화 데이터, 처리 상태 저장 |
| API | 검색/필터/상세 조회 제공 |
| UI | 조건 입력, 결과 목록, 상세 정보 표시 |
| Admin | 수집 실행, 실패 확인, 데이터 갱신 관리 |

## 5. 데이터 저장 원칙

- 원문 데이터와 정규화 데이터를 분리한다.
- AI 결과는 사람이 검증할 수 있게 원문 필드와 연결한다.
- AI 요약은 덮어쓰기보다 버전 관리가 가능한 구조가 좋다.
- 공공 API 호출 실패 시 이전 성공 데이터를 유지한다.

## 6. 장애 처리 원칙

- 수집 실패가 사용자 검색 장애로 이어지지 않게 한다.
- 실패한 레코드는 스킵하고 전체 배치는 계속 진행한다.
- 실패 로그에는 API 키, 사용자 민감정보, 전체 요청 URL을 남기지 않는다.
- 관리자 확인이 필요한 오류는 별도 상태로 기록한다.

## 7. 개발 순서

1. Python 수집 코드 안정화
2. 공통 데이터 스키마 정의
3. 로컬 JSON 또는 SQLite 저장 추가
4. 검색 API 추가
5. 웹 UI 추가
6. DB/배포 연결
7. 배치 자동화와 관리자 기능 추가
