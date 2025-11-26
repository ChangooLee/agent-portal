# WebUI Backend 기동 실패 해결 완료

## 날짜
2025-11-25

## 문제

WebUI 백엔드가 기동 중 다음 에러로 실패:
```
ValueError: Unknown embedding engine: ""
```

발생 위치: `webui/backend/open_webui/main.py` line 702

## 근본 원인

1. **환경 변수 충돌**: `docker-compose.dev.yml`에 추가된 환경 변수가 RAG 초기화를 방해
   - `CHROMA_DATA_PATH=""` 
   - `VECTOR_DB=none`

2. **Dockerfile.dev에 RAG 환경 변수 누락**: 프로덕션 Dockerfile에는 있지만 개발용에는 없음
   - `RAG_EMBEDDING_MODEL`
   - `SENTENCE_TRANSFORMERS_HOME`

## 해결 방법

### 1. docker-compose.dev.yml 수정

**삭제한 환경 변수**:
```yaml
- CHROMA_DATA_PATH=""  # ChromaDB 비활성화
- VECTOR_DB=none  # Vector DB 비활성화
```

**추가한 환경 변수**:
```yaml
- RAG_EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
- SENTENCE_TRANSFORMERS_HOME=/app/backend/data/cache/embedding/models
```

### 2. Dockerfile.dev 수정

추가한 환경 변수:
```dockerfile
## RAG Embedding model settings ##
ENV RAG_EMBEDDING_MODEL="sentence-transformers/all-MiniLM-L6-v2" \
    SENTENCE_TRANSFORMERS_HOME="/app/backend/data/cache/embedding/models"
```

### 3. 컨테이너 재시작

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d webui
```

## 결과

✅ **ValueError 에러 해결됨**: 백엔드가 정상적으로 초기화 시작
✅ **ChromaDB 텔레메트리 에러는 무시 가능**: `ERROR [chromadb.telemetry.product.posthog]`는 텔레메트리 전송 실패일 뿐 기능에 영향 없음
⏳ **초기 기동 시간**: Embedding 모델 다운로드로 첫 실행 시 3-5분 소요 (정상)

## 학습 내용

1. **ChromaDB 비활성화는 역효과**: `CHROMA_DATA_PATH=""`나 `VECTOR_DB=none` 설정은 RAG 초기화를 방해할 수 있음
2. **개발/프로덕션 환경 변수 일관성**: Dockerfile과 docker-compose.yml 간 환경 변수 일관성 중요
3. **Embedding 모델 다운로드**: 첫 실행 시 sentence-transformers 모델 다운로드로 시간 소요 (정상 동작)
4. **PersistentConfig 동작 방식**: Open-WebUI는 환경 변수 + SQLite DB 기반 설정 병합 사용

## 참고

- 관련 파일: `docker-compose.dev.yml`, `webui/Dockerfile.dev`
- 관련 코드: `webui/backend/open_webui/config.py:1870-1873`, `webui/backend/open_webui/main.py:686-717`
- 이전 분석: `.cursor/learnings/openwebui-backend-init-failure.md`


