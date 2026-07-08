# Documentation Index

이 디렉터리는 imunity 프로젝트의 제품/기술/보안 기준을 정리하는 단일 작업 기준입니다.

외부 기획 링크나 대화 내용은 참고 자료일 수 있지만, 저장소에 반영된 문서가 실제 개발 기준입니다. 외부 artifact의 내용이 필요한 경우 먼저 저장소 문서로 옮긴 뒤 작업합니다.

## 프로젝트 목적

암환자가 자신에게 맞는 공공 복지 정보를 중앙부처와 지자체 범위에서 쉽게 필터링하고 한눈에 확인할 수 있는 웹서비스를 만든다.

## 문서 구성

| 문서 | 목적 |
|---|---|
| [PRODUCT_SPEC.md](./PRODUCT_SPEC.md) | 제품 목표, 사용자, MVP 범위, 비목표 |
| [ARCHITECTURE.md](./ARCHITECTURE.md) | 권장 시스템 구조와 주요 모듈 책임 |
| [DATA_PIPELINE.md](./DATA_PIPELINE.md) | 공공 API 수집, 정규화, AI 전처리, 저장 흐름 |
| [SECURITY_PRIVACY.md](./SECURITY_PRIVACY.md) | API 키, 로그, 개인정보/민감정보 보호 기준 |
| [AI_COLLABORATION.md](./AI_COLLABORATION.md) | AI/개발자가 이어서 작업할 때 지켜야 할 협업 규칙 |
| [GIT_WORKFLOW.md](./GIT_WORKFLOW.md) | 개인 브랜치, main 보호, 커밋/푸시/PR 규칙 |
| [ROADMAP.md](./ROADMAP.md) | 단계별 구현 순서와 완료 기준 |
| [STATUS.md](./STATUS.md) | 현재 진척도, 담당, 다음 작업, handoff prompt |

## 현재 구현 상태

- Python 스크립트 기반 데이터 수집/전처리 프로토타입이다.
- 중앙부처 복지서비스 API 1건 조회를 확인했다.
- 지자체 복지서비스 API 1건 조회를 확인했다.
- Mistral 전처리 코드는 있으며 중앙/지자체 각 1건 실행 검증을 완료했다.
- 웹 프론트엔드, API 서버, DB, 인증, 배포 설정은 아직 없다.

## 문서 변경 원칙

- 기능을 구현하면 관련 문서를 함께 갱신한다.
- 보안/개인정보 관련 판단은 코드보다 문서에 먼저 명시하고 구현한다.
- 문서와 코드가 충돌하면 코드 변경 또는 문서 변경 중 하나를 같은 PR/커밋에서 처리한다.
- 확정되지 않은 내용은 `결정 필요`로 표시하고, 임시 구현이면 이유와 제거 조건을 적는다.
