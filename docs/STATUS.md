# Project Status

이 문서는 새 대화창이나 다른 작업자가 프로젝트를 이어받을 때 가장 먼저 확인하는 현재 상태 기록이다.

마지막 업데이트: 2026-07-08

## Current Focus

Phase 0 마무리와 Phase 1 진입 준비.

현재 초점은 문서 기반을 원격에 공유하고, Mistral 전처리 파이프라인을 중앙/지자체 각 1건씩 검증하는 것이다.

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

## In Progress

- docs 문서 세트 정리 및 커밋/푸시 준비
- Mistral 전처리 1건 검증 준비

## Next

1. docs 변경사항 커밋/푸시
2. 중앙부처 Mistral 전처리 1건 검증
3. 지자체 Mistral 전처리 1건 검증
4. 검증 결과를 `docs/DATA_PIPELINE.md`와 이 문서에 반영
5. 공통 데이터 스키마 구현
6. 로컬 저장 구조 추가

## Blockers

- 현재 알려진 blocker 없음

## Risks

- Mistral 전처리 실행은 비용이 발생할 수 있으므로 1건부터 검증해야 한다.
- AI 요약/분류는 원문을 대체하면 안 된다.
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
