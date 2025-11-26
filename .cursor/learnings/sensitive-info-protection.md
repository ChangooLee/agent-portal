# 민감 정보 보호 가이드

## 2025-11-26: API 키 노출 사고 및 예방 조치

### 사고 내용
- `.env.bak`, `.env.bak2` 파일이 git에 커밋됨
- OpenRouter API 키가 노출됨

### 원인
- AI 에이전트가 `.env` 파일 백업을 생성
- `.gitignore`에 백업 패턴 미포함

### 해결 조치
1. `git filter-branch`로 history에서 제거
2. `--force` push로 원격 저장소 정리
3. reflog 정리

### 예방 조치

#### 1. .gitignore 강화
```
.env.bak*
.env.backup*
.env.old*
*.bak
*.backup
*.key
*.pem
*_secret*
*_credentials*
```

#### 2. pre-commit hook 추가
- 민감 파일 패턴 체크
- API 키 패턴 (sk-or-, sk-, sk-ant-) 체크
- 발견 시 커밋 차단

#### 3. AI 에이전트 규칙 (.cursorrules)
민감 정보 관련 작업 시 필수 확인 절차:
1. "이 작업은 민감 정보를 포함합니다. 진행할까요?"
2. 백업 필요 시: "민감 정보 없이 구조만 백업할까요?"
3. 커밋 전: "민감 정보가 없는지 확인했습니다. 커밋할까요?"

### 민감 정보 정의
- API 키 (OpenRouter, OpenAI, Anthropic, etc.)
- 비밀번호, 토큰, 시크릿 키
- 데이터베이스 연결 문자열 (실제 자격 증명 포함)
- 개인 식별 정보 (PII)

### 안전한 대안
- `.env.example` 사용 (플레이스홀더만)
- 환경 변수 참조: `os.environ.get('API_KEY')`
- Docker secrets 또는 Vault 사용

---

**교훈**: AI 에이전트가 자동으로 백업 파일을 생성하지 않도록 명시적 규칙 필요

