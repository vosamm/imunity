# RAG 기반 AI 매칭 검색 설계

> 환자가 본인 정보(폼 + 자유 텍스트)를 입력하면, Mistral 임베딩 + 코사인 유사도로 DB에서 관련 복지 서비스를 검색하는 기능.

## 결정 사항

- **LLM**: Mistral (기존 API 키 재사용)
- **임베딩**: Mistral Embed API
- **벡터 검색**: numpy cosine similarity (sqlite-vss 대신, 198건이라 충분)
- **서버**: Python FastAPI (별도 프로세스)
- **배포**: 로컬 전용
- **UI**: 기존 키워드 검색 탭 유지 + "AI 매칭" 탭 추가

## 아키텍처

```
[사용자] → [Next.js UI (AI 매칭 탭)]
              ↓
         [Next.js API Route /api/rag-search] (프록시)
              ↓
         [Python FastAPI rag_server.py]
              ↓
         1. 폼 + 자유 텍스트 → 쿼리 문장 생성
         2. Mistral Embed API → 쿼리 벡터
         3. SQLite embeddings 테이블에서 전체 벡터 로드
         4. numpy cosine similarity → top-K
         5. 폼 필터 (지역 등) SQL WHERE 추가 적용
         6. 결과 반환
```

## 데이터 파이프라인 변경

### `build_db.py` 확장

기존 빌드 완료 후 임베딩 단계 추가:

1. `welfare_services` 테이블에서 전체 레코드 조회
2. 각 레코드의 `title + summary + target + benefit + criteria`를 하나의 텍스트로 합침
3. Mistral Embed API로 임베딩 생성 (배치 처리)
4. `embeddings` 테이블에 저장

### 새 테이블: `embeddings`

```sql
CREATE TABLE IF NOT EXISTS embeddings (
  source_type TEXT,
  source_service_id TEXT,
  vector BLOB,  -- numpy array를 bytes로 직렬화
  model TEXT,   -- 사용한 임베딩 모델명
  created_at TEXT,
  PRIMARY KEY (source_type, source_service_id),
  FOREIGN KEY (source_type, source_service_id)
    REFERENCES welfare_services(source_type, source_service_id)
);
```

## RAG 검색 서버

### `rag_server.py` (FastAPI)

#### `POST /api/rag-search`

**Request:**
```json
{
  "form": {
    "age": 45,
    "cancer_type": "유방암",
    "region_sido": "서울",
    "region_sigungu": "강남구",
    "income_level": "차상위"
  },
  "free_text": "치료비가 부담되고 간병인이 필요합니다"
}
```

모든 필드 선택사항. `free_text`만 있어도 검색 가능.

**쿼리 문장 생성 로직:**
폼 값 + 자유 텍스트를 자연어 문장으로 합침:
```
"45세 유방암 환자, 서울 강남구 거주, 차상위 소득. 치료비가 부담되고 간병인이 필요합니다"
```

**검색 로직:**
1. 쿼리 문장 → Mistral Embed → 쿼리 벡터
2. SQLite에서 `embeddings` + `welfare_services` JOIN으로 전체 로드
3. numpy cosine similarity 계산
4. 폼 필터 적용:
   - `region_sido` → national(NULL) 항상 포함 + 매칭 local
   - `region_sigungu` → 추가 필터
5. top-K (기본 20건) 반환, 유사도 점수 포함

**Response:**
```json
{
  "total": 15,
  "results": [
    {
      "source_type": "national",
      "source_service_id": "WLF00001",
      "title": "암환자 의료비 지원",
      "summary": "...",
      "similarity": 0.87,
      ...
    }
  ]
}
```

## 프론트엔드 변경

### `web/app/page.tsx`

탭 UI 추가:
- **"키워드 검색" 탭**: 기존 UI 그대로
- **"AI 매칭" 탭**: 새 폼 UI

### AI 매칭 탭 폼 필드

| 필드 | 타입 | 필수 | 비고 |
|---|---|---|---|
| 나이 | 숫자 입력 | X | |
| 암 종류 | 텍스트 입력 | X | 자유 입력 |
| 거주 지역 (시도) | 드롭다운 | X | 기존 regions API 재사용 |
| 거주 지역 (시군구) | 드롭다운 | X | 시도 선택 시 cascade |
| 소득 수준 | 드롭다운 | X | 기초생활/차상위/일반 |
| 추가 상황 | textarea | X | 자유 텍스트 |

- "AI 매칭 검색" 버튼 클릭 시 `POST /api/rag-search`
- 결과는 기존 카드 컴포넌트 재사용 (유사도 점수 배지 추가)

### `web/app/api/rag-search/route.ts`

Next.js API route — Python FastAPI 서버(`localhost:8000`)로 프록시.

## 의존성 추가

### Python (`requirements.txt`)
- `fastapi`
- `uvicorn`
- `numpy`

### Node.js (`web/package.json`)
- 추가 없음 (기존 fetch로 프록시)

## 실행 방법

```bash
# 1. 임베딩 빌드 (최초 1회)
.venv/bin/python build_db.py  # 기존 빌드 + 임베딩 생성

# 2. RAG 서버 시작
.venv/bin/python rag_server.py  # localhost:8000

# 3. Next.js 서버 시작
cd web && npm run dev  # localhost:3100
```

## 범위 밖

- Mistral Chat API로 결과 요약/설명 생성 (A 옵션 — 매칭만)
- 대화형 추가 질문
- 사용자 로그인/프로필 저장
- 벡터 DB 마이그레이션
