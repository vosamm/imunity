# ADR-0001: MVP 저장 구조·웹 스택·암환자 관련성 분류 기준 확정

- 상태: 승인됨
- 결정일: 2026-07-09
- 결정자: User (제품 방향 결정권자)
- 배경: 팀미팅 없이 자율 개발을 진행하기 위해, 블로커였던 미결정 항목 3개를 확정한다.

## 결정 1 — MVP 저장 구조: SQLite

로컬 JSON, Supabase Postgres 직행 대신 **SQLite**를 선택한다.

- 파일 하나로 관리되고 검색/필터 쿼리가 가능하다.
- 이후 Postgres(Supabase) 이전이 쉬운 스키마를 유지한다.
- 무인(밤샘) 개발에 외부 계정/네트워크 의존이 없어 가장 안전하다.

원문 데이터는 `data/raw/`에 파일로, 정규화 데이터는 SQLite에 저장한다
(원문/정규화 분리 원칙 — `docs/ARCHITECTURE.md` 5장).

## 결정 2 — 웹 MVP 스택: Next.js

`docs/ARCHITECTURE.md` 3장의 권장안을 확정한다. Next.js(App Router) + API Route로
검색/필터/상세를 제공하고, Vercel 배포를 전제로 한다. Python 수집 코드는
검증된 수집 모듈로 유지한다.

## 결정 3 — 암환자 관련성 exclude 기준 수정

기존 초안은 "아동, 청소년, 임산부, 농업, 창업 등"을 exclude 예시로 들었다.
이 기준은 **소아암 환자·환아 가족 지원 제도를 배제할 위험**이 있다.

수정된 기준:

> **인구집단(아동·청소년·임산부 등)만으로 exclude하지 않는다.**
> **암/질병/의료 맥락이 전혀 없는 경우에만 exclude한다.**

- "소아암 환아 의료비 지원" → `high` (청소년이어도 암 맥락 존재)
- "학교 밖 청소년 검정고시 축하금" → `exclude` (의료 맥락 없음)

이 기준은 `acceptance_tests/test_phase2_classify.py` 골든 케이스로 고정되어 있다.

## 영향

- `docs/DATA_PIPELINE.md` 5장 분류 기준 갱신
- Phase 1(스키마+SQLite), Phase 3(Next.js)의 기술 선택이 확정되어 자율 개발 가능
