# Agent Portal — 현재 상태 (2025-11-19)

> **마지막 업데이트**: 2025-11-19 18:35
> **작성자**: AI Assistant (Claude)

---

## 📊 전체 진행 상황 요약

| 영역 | 상태 | 완료율 | 비고 |
|------|------|--------|------|
| **Stage 1** | ✅ 완료 | 100% | 인프라 및 기본 설정 |
| **Stage 2** | ✅ 완료 | 90% | Chat + Observability (LiteLLM 통합 완료) |
| **Stage 3** | 🚧 진행 중 | 60% | 에이전트 빌더 (UI 임베딩 완료, LangGraph 변환 미완) |
| **Stage 8** | ❌ 미시작 | 0% | Perplexica + Open-Notebook 임베드 |

**전체 진행률**: 약 **45%**  
**최근 주요 작업**: LiteLLM 통합, AgentOps 모니터링 대시보드 구현, Chat UI 개선

---

## ✅ 최근 완료된 작업 (2025-11-18 ~ 2025-11-19)

### 1. LiteLLM 통합 완료 ✨

**목적**: 단일 LLM 게이트웨이로 모든 LLM 요청 통합

**완료 사항**:
- ✅ LiteLLM Dockerfile 생성 (`litellm/Dockerfile`)
- ✅ LiteLLM config.yaml 설정 (OpenRouter 통합)
- ✅ Backend BFF에 LiteLLM 서비스 클라이언트 구현 (`backend/app/services/litellm_service.py`)
- ✅ Chat API LiteLLM 연동 (`backend/app/routes/chat.py`)
- ✅ Open-WebUI 환경 변수 설정 (docker-compose.yml)
- ✅ Langflow/Flowise 환경 변수 설정

**API Keys**:
- OpenRouter: ✅ 설정 완료 (`.env`, gitignored)
- LiteLLM Master Key: ✅ 설정 완료

**테스트 상태**:
- ✅ LiteLLM 서비스 시작 성공
- ✅ Open-WebUI → LiteLLM 스트리밍 채팅 정상 동작
- ⚠️ Langfuse 콜백 비활성화 (Langfuse 미설정)

**문서**:
- `docs/LITELLM_SETUP.md`
- `.cursor/learnings/litellm-integration.md`
- `.cursor/learnings/openwebui-litellm-integration.md`

### 2. Open-WebUI + LiteLLM 스트리밍 수정 🔧

**문제**: JSON 파싱 에러, SSE 스트리밍 실패

**해결**:
- ✅ `data=payload` → `json=payload` 변경 (Line 703)
- ✅ `json.dumps(payload)` 제거 (Line 688)
- ✅ aiohttp 헤더 대소문자 구분 처리 (Line 728-729)

**결과**: 실시간 스트리밍 채팅 정상 동작

**문서**:
- `.cursor/learnings/openwebui-streaming-fix.md`

### 3. AgentOps 모니터링 대시보드 구현 📊

**목적**: AgentOps GitHub 코드를 재활용하여 모니터링 화면 개편

**완료 사항**:
- ✅ AgentOps 서브모듈 추가 (`.gitmodules`)
- ✅ AgentOps MariaDB 스키마 생성 (`scripts/init-agentops-schema.sql`)
- ✅ AgentOps Adapter 구현 (`backend/app/services/agentops_adapter.py`)
- ✅ AgentOps API 엔드포인트 구현 (`backend/app/routes/agentops.py`)
- ✅ AgentOps 대시보드 UI 재구현 (Svelte)
  - Overview 탭: 메트릭 카드 (Total Cost, Events, Latency, Fail Rate)
  - Traces 탭: 트레이스 목록 테이블
  - Analytics 탭: 성능 메트릭 차트
  - Replay 탭: 세션 리플레이어
- ✅ AgentOps 디자인 시스템 적용 (`webui/src/routes/(app)/admin/monitoring/styles.css`)
- ✅ WebSocket 실시간 업데이트

**테스트 상태**:
- ✅ 프론트엔드 빌드 성공
- ✅ Backend API 실행 성공
- ⚠️ 실제 데이터 수집 미완 (AgentOps SDK 미통합)

**문서**:
- `docs/AGENTOPS_GAP_ANALYSIS.md`
- `.cursor/learnings/monitoring-design-complete.md`
- `.cursor/learnings/agentops-integration.md`

### 4. Chat UI 개선 🎨

**완료 사항**:
- ✅ 메시지 입력창 하단 고정
- ✅ 스트리밍 응답 처리 로직 추가
- ✅ 전역 스크롤 복구 (Chat 페이지만 `overflow-hidden`)
- ✅ 입력창 높이 최적화 (`py-4` → `py-2.5`)
- ✅ 입력창 배경 투명 처리
- ✅ 포커스 테두리 색상 개선 (`#0072CE`)

**문서**:
- `.cursor/learnings/chat-layout-fix.md`
- `.cursor/learnings/chat-input-style-fix.md`
- `.cursor/learnings/chat-streaming-ui-fix.md`

### 5. 네비게이션 개선 🚀

**완료 사항**:
- ✅ 새 채팅 버튼 새로고침 문제 해결
  - `window.location.href` → SvelteKit `goto()` 사용
- ✅ 상단 네비게이션 메뉴 페이지 전체 너비 적용
  - 모든 페이지의 `max-w-*` 제한 제거

**문서**:
- `.cursor/learnings/sveltekit-navigation.md`
- `.cursor/learnings/ui-patterns.md`

---

## 🚧 진행 중인 작업

### Stage 2: Chat 엔드포인트 연동 (90% 완료)

**남은 작업**:
- [ ] Langfuse 서비스 시작 및 API 키 생성
- [ ] Langfuse 트레이싱 테스트
- [ ] 모니터링 대시보드 실제 데이터 확인

### Stage 3: 에이전트 빌더 (60% 완료)

**완료**:
- ✅ Langflow/Flowise/AutoGen Studio iframe 임베딩
- ✅ Langflow UI 재구현 - Phase 1-A (플로우 목록)

**남은 작업**:
- [ ] Langflow UI 재구현 - Phase 1-B (LangGraph 변환 + 실행 + AgentOps)
  - [ ] AgentOps 서비스 레이어 구현
  - [ ] Langflow → LangGraph 변환기 구현
  - [ ] LangGraph 실행 서비스 구현
  - [ ] 변환/실행 API 엔드포인트 추가
  - [ ] 플로우 카드 컴포넌트 (Export/Run 버튼)
  - [ ] 실행 결과 패널 (비용 정보, AgentOps 리플레이 링크)

---

## 🎯 다음 우선순위 작업 (P0 → P1 → P2)

### P0 (Urgent - 즉시 착수)

#### 1. Langfuse 통합 테스트
**목적**: LLM 체인 추적 및 프롬프트 비교 기능 활성화

**작업 내역**:
- [ ] Langfuse PostgreSQL 데이터베이스 설정
- [ ] Langfuse 서비스 시작 및 API 키 생성
- [ ] LiteLLM config.yaml에서 Langfuse 콜백 활성화
- [ ] Backend BFF에서 Langfuse 트레이싱 테스트
- [ ] Monitoring 대시보드에서 Langfuse 데이터 확인

**예상 시간**: 2-3시간  
**우선순위**: Critical (LiteLLM 통합 완료 후 필수)

#### 2. Chat UI End-to-End 테스트
**목적**: 전체 Chat 플로우 검증

**작업 내역**:
- [ ] Chat 입력 → Backend BFF → LiteLLM → OpenRouter → 응답 표시
- [ ] 스트리밍 응답 정상 동작 확인
- [ ] 에러 핸들링 테스트 (타임아웃, 401, 500 등)
- [ ] 다양한 모델 테스트 (qwen-235b, gpt-4, gpt-3.5-turbo)
- [ ] 브라우저 콘솔 에러 확인

**예상 시간**: 1-2시간  
**우선순위**: High (사용자 경험 검증)

### P1 (Important - 금주 내 완료)

#### 3. AgentOps SDK 통합
**목적**: 실제 에이전트 실행 데이터 수집

**작업 내역**:
- [ ] AgentOps SDK 설치 (`pip install agentops`)
- [ ] Langflow/Flowise 실행 시 AgentOps 세션 생성
- [ ] 비용, 토큰, 지연시간 데이터 수집
- [ ] MariaDB에 데이터 저장
- [ ] Monitoring 대시보드에 실제 데이터 표시

**예상 시간**: 4-6시간  
**우선순위**: High (모니터링 대시보드 완성)

#### 4. Langflow → LangGraph 변환기 (MVP)
**목적**: Langflow 플로우를 LangGraph JSON으로 변환

**작업 내역**:
- [ ] Langflow API로 플로우 JSON 가져오기
- [ ] LangGraph JSON 스키마 정의
- [ ] 변환 로직 구현 (노드 매핑)
- [ ] 변환 API 엔드포인트 추가
- [ ] 프론트엔드 Export 버튼 구현

**예상 시간**: 8-12시간  
**우선순위**: High (Stage 3 핵심 기능)

### P2 (Nice to Have - 차주 진행)

#### 5. Today 페이지 뉴스 기능 개선
**목적**: 뉴스 API 실제 연동 및 UI 개선

**작업 내역**:
- [ ] News API 엔드포인트 구현 (Backend BFF)
- [ ] 뉴스 데이터 경로 설정 (`/data/news`)
- [ ] 무한 스크롤 동작 확인
- [ ] 실시간 검색 필터링 테스트
- [ ] 모달 팝업 UX 개선

**예상 시간**: 4-6시간  
**우선순위**: Medium (UI 완성도 향상)

#### 6. 인증/인가 시스템 구현
**목적**: 보안 강화 및 사용자 관리

**작업 내역**:
- [ ] JWT 토큰 기반 인증
- [ ] 역할 기반 접근 제어 (RBAC)
- [ ] 관리자 전용 페이지 보호
- [ ] API 엔드포인트 인증 미들웨어

**예상 시간**: 8-12시간  
**우선순위**: Medium (보안 취약점 해결)

---

## 📋 체크리스트

### 개발 환경 상태

- [x] Docker Compose 실행 중
- [x] Open-WebUI (3001 포트) 정상 동작
- [x] Backend BFF (8000 포트) 정상 동작
- [x] LiteLLM (4000 포트) 정상 동작
- [x] MariaDB (3306 포트) 정상 동작
- [ ] Langfuse (3001 포트) 미실행
- [x] Langflow (7861 포트) 정상 동작
- [x] Flowise (3002 포트) 정상 동작
- [ ] AutoGen API (5051 포트) 의존성 오류

### 설정 파일 상태

- [x] `.env` 파일 생성 (gitignored)
- [x] `litellm/config.yaml` 설정 완료
- [x] `backend/app/config.py` 환경 변수 설정
- [x] `docker-compose.yml` LiteLLM 서비스 추가
- [x] `scripts/init-agentops-schema.sql` MariaDB 스키마 생성
- [ ] Langfuse 환경 변수 설정 필요

### 테스트 상태

- [x] Chat 스트리밍 응답 정상
- [x] 새 채팅 버튼 새로고침 없음
- [x] 전체 페이지 너비 적용
- [x] 다크/라이트 모드 전환
- [x] 반응형 디자인 (모바일, 태블릿, 데스크톱)
- [ ] Langfuse 트레이싱 미테스트
- [ ] AgentOps 데이터 수집 미테스트
- [ ] LangGraph 변환 미구현

---

## 🚨 알려진 이슈

### Critical
- ❌ **AutoGen API 의존성 오류**: Python 버전 충돌
- ⚠️ **Langfuse 미설정**: PostgreSQL 데이터베이스 및 API 키 필요
- ⚠️ **AgentOps 실제 데이터 없음**: SDK 통합 미완

### High
- ⚠️ **인증/인가 시스템 없음**: 보안 취약점
- ⚠️ **LangGraph 변환 미구현**: Stage 3 핵심 기능 미완

### Medium
- ⚠️ **News API 미연동**: 샘플 데이터만 표시
- ⚠️ **테스트 코드 없음**: pytest 미작성

---

## 📚 문서 상태

### 최신 문서 (2025-11-19)
- ✅ `.cursor/learnings/litellm-integration.md`
- ✅ `.cursor/learnings/openwebui-litellm-integration.md`
- ✅ `.cursor/learnings/monitoring-design-complete.md`
- ✅ `.cursor/learnings/chat-layout-fix.md`
- ✅ `.cursor/learnings/sveltekit-navigation.md`
- ✅ `docs/LITELLM_SETUP.md`
- ✅ `docs/AGENTOPS_GAP_ANALYSIS.md`

### 업데이트 필요
- ⚠️ `PROGRESS.md` (마지막 업데이트: 2025-11-12)
- ⚠️ `README.md` (LiteLLM 통합 내용 추가 필요)
- ⚠️ `DEVELOP.md` (개발 가이드 업데이트 필요)

---

## 🎯 권장 다음 단계 (우선순위 순)

### 1단계: Langfuse 통합 (2-3시간)
**목적**: LLM 관측성 완성

**절차**:
1. Langfuse PostgreSQL 데이터베이스 설정
2. Langfuse 서비스 시작 (`docker-compose up langfuse`)
3. Langfuse API 키 생성 (웹 UI)
4. `litellm/config.yaml` Langfuse 콜백 활성화
5. Chat API 테스트 및 Langfuse 대시보드 확인

### 2단계: End-to-End 테스트 (1-2시간)
**목적**: 전체 Chat 플로우 검증

**절차**:
1. Chat 입력 → Backend BFF → LiteLLM → OpenRouter
2. 스트리밍 응답 확인
3. Langfuse 트레이스 확인
4. 브라우저 콘솔 에러 확인
5. 다양한 모델 테스트

### 3단계: AgentOps SDK 통합 (4-6시간)
**목적**: 실제 모니터링 데이터 수집

**절차**:
1. `pip install agentops` (Backend BFF)
2. AgentOps 서비스 레이어 구현
3. Langflow 실행 시 세션 생성
4. MariaDB 데이터 저장
5. Monitoring 대시보드 확인

### 4단계: Langflow → LangGraph 변환 (8-12시간)
**목적**: Stage 3 핵심 기능 완성

**절차**:
1. Langflow API 분석
2. LangGraph JSON 스키마 정의
3. 변환 로직 구현
4. API 엔드포인트 추가
5. 프론트엔드 Export 버튼 구현

---

## 📞 문의 사항

다음 작업에 대한 질문이나 우선순위 조정이 필요하면 언제든지 말씀해주세요:

1. **Langfuse 통합 시작?** (P0)
2. **AgentOps SDK 통합 우선?** (P1)
3. **LangGraph 변환 먼저?** (P1)
4. **다른 우선순위?**

---

**마지막 업데이트**: 2025-11-19 18:35  
**다음 리뷰 예정**: 2025-11-20

