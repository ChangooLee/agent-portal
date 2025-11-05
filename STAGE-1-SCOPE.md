# 1단계 구현 범위 (Stage 1 Scope)

## 📋 1단계 목표

**Open-WebUI 커스터마이즈 및 UI 필터링**

Open-WebUI를 포크하여 필요한 기능만 노출하고 나머지 UI는 숨김 처리

## ✅ 1단계에 포함되는 작업

### 1. Open-WebUI 포크 및 기본 설정
- ✅ Open-WebUI v0.6.5 포크 완료 (`webui/` 디렉토리)
- ✅ AGPL 라이선스 커밋 고정
- ✅ 커스텀 브랜치 생성 (`agent-portal-custom`)

### 2. UI 필터링 설정
- ⚠️ `webui/overrides/` 디렉토리 생성 필요
- ⚠️ 사이드바 메뉴 필터링 (필요 기능만 표시)
  - 기본 채팅 메뉴만 노출
  - 프로젝트/파일 관리 메뉴 유지
  - 설정 메뉴 필터링
  - 관리자 메뉴는 `admin` 역할만 접근
- ⚠️ 불필요한 UI 요소 숨김 처리

### 3. Docker 설정
- ⚠️ `webui/Dockerfile` 생성 (기본 이미지 확장)
- ⚠️ `webui/.dockerignore` 설정
- ✅ `docker-compose.yml`에 webui 서비스 추가 완료

### 4. 환경 변수 설정
- ⚠️ `.env` 파일에 Open-WebUI 설정 추가
  - `WEBUI_PORT=3000`
  - `WEBUI_DISABLE_SIGNUP=true`
  - `WEBUI_DEFAULT_USER_ROLE=user`

### 5. 테스트 절차
- ✅ 기본 구동 테스트 (완료)
- ⚠️ UI 요소 확인 (메뉴 필터링 검증)
- ⚠️ 메뉴 접근 권한 확인

## ❌ 1단계에 포함되지 않는 작업

### 2단계 작업 (현재 진행 중)
- ❌ Backend BFF 구현 (FastAPI)
- ❌ Chat 엔드포인트 연동
- ❌ LiteLLM 연동
- ❌ Langfuse/Helicone 연동

### 4단계 작업 (일부 진행 중)
- ❌ Kong Gateway 설정
- ❌ Konga (Kong Admin UI) 통합
- ❌ MCP SSE 엔드포인트
- ❌ Kong을 통한 보안/레이트리밋

### 기타 단계
- ❌ Langflow/Flowise 임베드 (3단계)
- ❌ MariaDB 스키마 설계 (5단계)
- ❌ Document Intelligence (6단계)
- ❌ UI 뷰 모드 전환 (7단계)
- ❌ Open Notebook/Perplexica 통합 (8단계)
- ❌ Guardrails 관리 (9단계)

## 📊 현재 진행 상황

### 완료된 것
- ✅ Open-WebUI 포크 및 실행
- ✅ 기본 Docker Compose 설정
- ✅ 기본 채팅 인터페이스 작동

### 진행 중 (1단계 범위 외)
- ⚠️ Konga 통합 (4단계 범위)
- ⚠️ BFF 백엔드 구현 (2단계 범위)

### 미완료 (1단계 범위)
- ❌ UI 메뉴 필터링 구현
- ❌ Overrides 디렉토리 구조 생성
- ❌ 사이드바 커스터마이즈
- ❌ Dockerfile 생성
- ❌ 환경 변수 설정 완료

## 🎯 1단계 완료 조건

1. ✅ Open-WebUI 포크 완료
2. ⚠️ UI 필터링 구현 완료
   - 사이드바에서 필요한 메뉴만 표시
   - 불필요한 기능 숨김
3. ⚠️ Docker 설정 완료
   - Dockerfile 생성
   - 볼륨 마운트 설정
4. ⚠️ 기본 테스트 통과
   - 접근 가능 확인
   - 필터링된 메뉴 확인
   - 관리자 권한 확인

## 📝 구현 파일 구조

```
webui/
├─ Dockerfile              # ⚠️ 생성 필요
├─ .dockerignore           # ⚠️ 생성 필요
├─ overrides/              # ⚠️ 생성 필요
│  ├─ components/
│  │  └─ Sidebar.svelte    # 사이드바 메뉴 필터링
│  └─ pages/
│     └─ Settings.svelte    # 설정 페이지 커스터마이즈
└─ plugins/                # ✅ 디렉토리 존재
   └─ custom-features/     # 커스텀 기능 플러그인
```

## 🔍 체크리스트

### 1단계 필수 작업
- [ ] `webui/overrides/` 디렉토리 생성
- [ ] 사이드바 메뉴 필터링 파일 작성
- [ ] `webui/Dockerfile` 생성
- [ ] `webui/.dockerignore` 생성
- [ ] 환경 변수 설정 (`.env`)
- [ ] 메뉴 필터링 테스트

### 현재 상태
- [x] Open-WebUI 포크 완료
- [x] Docker Compose 기본 설정
- [x] 기본 실행 확인
- [ ] UI 필터링 미구현
- [ ] Overrides 미구현

## ⚠️ 주의사항

**현재 진행 중인 작업들은 1단계 범위가 아닙니다:**

1. **Konga 통합** → 4단계 (MCP SSE & Kong Gateway)
2. **BFF 백엔드** → 2단계 (Chat Endpoint & Monitoring)
3. **Admin > Gateway 메뉴** → 4단계 범위

1단계는 순수하게 **Open-WebUI의 UI만 필터링**하는 것이 목표입니다.


