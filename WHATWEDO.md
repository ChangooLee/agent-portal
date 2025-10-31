무엇을 만들려는가? — “3-in-1 OSS 슈퍼 포털”
1) 한 문장 요약

에이전트 포털(대화·MCP·RAG), 노트북/PKM 포털(Open Notebook), **리서치 포털(Perplexica)**을 하나의 SSO·RBAC 기반 웹 포털로 통합하고, LiteLLM 게이트웨이 + Langfuse/Helicone 관측 + Kong 보안 아래에서 vLLM(사내)·OpenRouter·SOTA API 모델을 자유롭게 라우팅/운영하는 기업용 오픈소스 올인원 AI 플랫폼을 구축합니다.

2) 포털 3종 통합 (기능별 역할)

Portal A — Agent (Open-WebUI 기반 Shell; AGPL 포크)

Claude Desktop 유사 UX(좌측 채팅/우측 아티팩트), 파일/프로젝트, 모델/연결, MCP(stdio+SSE) 설정

Langflow/Flowise 임베드형 에이전트 빌더(설계→Export→LangGraph 실행)

RAG 화면, PDF 번역, 웹캡처/유튜브 리서치 카드, 관리자 대시보드

Portal B — Notebook (Open Notebook; MIT)

노트/지식 관리(PKM) + 모델 도우미(요약·정리·변환)

SOTA 모델 전 범위: vLLM·OpenRouter뿐 아니라 OpenAI/Anthropic/Gemini/Vertex/Ollama/Together/Groq/Mistral/Cohere/DeepSeek/Fireworks/Perplexity 등 문서에 정의된 모든 AI 모델 설정을 사용 가능

Portal C — Perplexica (MIT)

대화형 웹/문서 메타 리서치, 출처·근거 중심 결과, RAG 연동

세 포털은 **단일 상단 네비 + 단일 로그인(SSO/OIDC)**로 묶이고, 조직/팀 단위로 **워크스페이스 격리(RBAC)**가 적용됩니다.

3) 코어 아키텍처 (요소별)

UI Shell: Open-WebUI 포크(AGPL 마지막 커밋 고정) + 플러그인/오버라이드 방식 확장

Agent 실행: LangGraph Server

LLM 라우팅: LiteLLM (단일 OpenAI 호환 엔드포인트)

사내: vLLM (로컬 대규모 모델)

외부: OpenRouter/Anthropic/OpenAI/Google 등 다수 프로바이더

Helicone(옵션): 비용/지연/프롬프트 비교 프록시

관측/추적: Langfuse (체인·툴콜 트레이스), (옵션) OTEL→SigNoz/OpenObserve

문서지능 파이프라인: unstructured + PaddleOCR + (선택) VLM 캡션 → 지능형 청킹(페이지·표/제목 보존·문맥 overlap) → bge-m3 임베딩 → ChromaDB 색인

데이터 커넥터(Data-Cloud): SAP HANA/Oracle/Maria/Postgres/S3/Parquet/Elastic 등

SQLAlchemy/ODBC + 스키마 카탈로그/용어집(업무코드 → 자연어) → 안전 SQL(뷰/권한)

RAG+DB 하이브리드: 규정/ERD 임베딩을 함께 주입해 근거와 제약을 동시 제공

오브젝트/메타: MinIO(파일), MariaDB(코어 메타), Redis(세션/캐시)

MCP: stdio + SSE 모두 지원, Kong Gateway로 Key-Auth/레이트리밋/mTLS/IP 제한/감사 적용

접근제어: SSO(OIDC) + RBAC(admin/power_user/user) + 워크스페이스 격리

가드레일: 입력(PII/독성/정책)·출력(근거 강제/마스킹/차단) + 이벤트 로깅/대시보드

4) 사용자 여정(동작 흐름)

SSO 로그인 → 워크스페이스 권한 부여(RBAC)

모델 연결: 포털에서 LiteLLM Base URL만 등록 → 모델 선택은 카탈로그로 통일

MCP 연결: stdio 도구(로컬 프로세스) + SSE 도구(네트워크) 등록, Kong 키/레이트리밋 부여

에이전트 설계/실행: Langflow/Flowise 템플릿 임베드 → Export→LangGraph → 대화 흐름/툴 호출

문서 업로드/RAG: OCR→청킹→임베딩→색인 → 근거 링크/하이라이트 포함 응답

리서치: Perplexica로 수집/요약 → Agent가 후처리해 아티팩트(리포트/표/차트) 생성

노트화/아카이브: Open Notebook에 지식 정리, 재활용 템플릿으로 축적

관측/운영: Langfuse/Helicone/SigNoz 대시보드로 비용·지연·오류·정책 위반 추적

5) 보안/거버넌스

Kong: MCP/API 경로 중앙 게이트웨이(키 회전, 레이트리밋, mTLS, IP 제한, 감사)

DB 보안: 읽기 전용 계정/뷰, 가능하면 행 수준 보안(RLS)

정책 준수: 가드레일 이벤트(마스킹/차단/경고) 로깅 → 관리자 차트

분리 저장: Langfuse/Helicone는 자체 Postgres로 운영(코어 DB와 분리)

6) 운영/관측/트러블슈팅

관측 표준화: Langfuse traceId로 실패 재현, Helicone으로 지연/비용 상위 프롬프트 분석

성능 이슈: LiteLLM 라우팅 정책(시간대/모델 교체) + vLLM 스케일

RAG 품질: 청킹 파라미터/임베딩(bge-m3) 조정, OCR 품질 점검, 근거 누락 시 차단/재질의

업데이트 전략: Open-WebUI는 포크(AGPL 커밋 고정), 오버라이드/플러그인 중심으로 상류 패치 추종

7) 라이선스/포크 기준(이슈 방지)

Open-WebUI(포털 Shell): AGPL-3.0 시점의 마지막 커밋으로 핀 고정 포크

AGPL 의무(소스 공개/저작권 고지) 충족 前提로 브랜딩/풀 커스터마이즈 가능

이후 버전(Open WebUI License)은 브랜딩 보존 등 제한이 있어 채택하지 않음

Open Notebook: MIT (최신 안정 태그 포크)

Perplexica: MIT (최신 릴리스 태그 포크)

Langflow(MIT), Flowise(Apache-2.0), Kong/Chroma/MinIO/Redis/MariaDB/Langfuse/Helicone(각 OSS)
→ 각 LICENSE/NOTICE를 리포지토리에 명시하고, 배포 페이지에 라이선스 표기

8) 모델/프로바이더 범위 (SOTA 전부)

로컬: vLLM, Ollama

게이트웨이: LiteLLM 하나로 OpenAI/Anthropic/Google(Gemini/Vertex)/OpenRouter/Together/Groq/Mistral/Cohere/DeepSeek/Fireworks/Perplexity 등 문서에 정의된 모든 설정을 통합

권장 운영: 모든 키는 Vault/.env 관리 → 세 포털 모두 LiteLLM 단일 엔드포인트 사용으로 UX 일관

9) 산출물/구성 산식

README.md(아키텍처·포트·API·스키마·트러블슈팅·스크린샷 기능 매핑 포함)

DEVELOP.md(라우트/훅/어댑터/테스트 시나리오)

docker-compose.yml + .env 샘플 + config/litellm.yaml + config/kong.yml

webui/plugins|overrides/(Agent/관측/보안 메뉴 플러그인)

document-service/(OCR/VLM/청킹/임베딩 마이크로서비스)

10) 성공 기준(KPI) & 로드맵

KPI(초기):

평균 응답 지연(챗) < 3초(외부 모델), < 1.5초(캐시/로컬)

에이전트 실패율 < 2%, RAG 근거 포함률 > 95%

월간 비용대비 정확도/채택률 개선(Helicone/Langfuse 리포트 기반)

로드맵:

Langflow/Flowise ↔ LangGraph 양방향 동기화(조건/루프/메모리/툴 완전 대응)

Kong Admin 마법사(컨슈머/키/ACL·JWT 자동 발급/회수)

문서지능 고도화(표/수식 OCR, VLM Fallback 자동화)

평가 파이프라인(Golden set·A/B·Drift; Superset/Arize Phoenix 임베드)

비용 거버넌스(모델별 Budget/Alert)

결론

귀하가 만들고자 하는 것은 기업 운영 현실에 맞춘, 100% 오픈소스 기반의 통합 AI 운영 플랫폼입니다.
**대화형 에이전트(Agent) · 지식 노트북(Notebook) · 메타 리서치(Perplexica)**를 하나의 보안/관측 표준 아래 묶고, MCP·RAG·SOTA 모델 라우팅을 안정적으로 제공하여 팀 단위 생산성과 통제력을 동시에 확보하는 것이 목표입니다.