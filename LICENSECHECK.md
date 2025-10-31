
---

# 커스터마이징 자유도 기준 권장 버전 (요약)

| 구성요소                         | 목적             |              권장 fork 기준 | 라이선스                             | 왜 이 버전인가                                                                                             |
| ---------------------------- | -------------- | ----------------------: | -------------------------------- | ---------------------------------------------------------------------------------------------------- |
| **Open-WebUI (포털 쉘)**        | 메인 UI          |    **v0.6.5** (또는 그 이전) | **BSD-3-Clause**                 | v0.6.6부터는 **Open WebUI License**(브랜딩·상표 고지 의무 등)로 변경. **v0.6.5 이하**는 BSD-3로 **브랜딩 제거·전면 커스터마이징 가능**. |
| **Perplexica**               | RAG/웹검색 포털     | 최신 안정 태그(예: v0.10.x 계열) | **MIT**                          | MIT는 재라이선싱 제외 모든 커스터마이징 자유. 레포지토리 라이선스 명시.                                                           |
| **Open-Notebook**            | LLM 노트북/리서치 포털 |                최신 안정 태그 | **MIT**                          | 동일. 설정파일로 vLLM·OpenRouter·SOTA API 구성 포함 가능(해당 문서 경로 기준). 라이선스 MIT 확인. ([GitHub][1])                 |
| **Langflow**                 | 노코드 에이전트 빌더    |                최신 안정 태그 | MIT                              | UI 임베드/테마·노드 추가 자유(퍼미시브).                                                                            |
| **Flowise**                  | 노코드 에이전트 빌더    |                최신 안정 태그 | Apache-2.0                       | 상표만 주의하면 브랜딩·기능 커스텀 자유.                                                                              |
| **LiteLLM**                  | LLM 게이트웨이      |                최신 안정 태그 | MIT                              | 라우팅/콜백 커스터마이징 자유. ([GitHub][2])                                                                      |
| **Langfuse**                 | 트레이싱/평가        |               최신 CE 릴리스 | *(공개 라이선스: Apache-2.0 계열/레포 확인)* | 대시보드 임베드, 스키마 확장에 제약 적음.                                                                             |
| **Helicone**                 | 비용/지연 프록시      |                최신 안정 태그 | *(MIT 표기, 레포 확인)*                | 프록시 계층 커스터마이징 자유.                                                                                    |
| **ChromaDB**                 | 벡터 DB          |                최신 안정 태그 | **Apache-2.0**                   | 인덱싱/스키마 메타 확장 자유. ([GitHub][3])                                                                      |
| **PaddleOCR / unstructured** | OCR/파서         |                최신 안정 태그 | Apache-2.0                       | 파이프라인 조합·후처리 자유.                                                                                     |
| **Kong Gateway (OSS)**       | MCP/API 보안     |               3.6.x LTS | Apache-2.0                       | 플러그인·디클레어 구성 커스텀 자유.                                                                                 |

> ⚑ **특히 중요:** Open-WebUI는 **v0.6.6부터** ‘Open WebUI License’로 바뀌어 **브랜딩·표기 의무**가 생깁니다. **v0.6.5 이하(BSD-3)**를 포크하면 **브랜딩 제거/전체 UI 재구성**이 법적으로 깔끔합니다. 공식 문서에 **“v0.6.5 및 이하 = BSD-3, v0.6.6+ = Open WebUI License”**가 명시되어 있습니다.

---

## 라이선스 관점에서의 커스터마이징 가이드 (Step-by-Step)

1. **포털 3 in 1 전략**

   * **Portal A (Chat/Agent)**: **Open-WebUI v0.6.5(BSD-3)** 포크 → 메뉴/브랜딩/레이아웃 전면 교체, 플러그인 구조로 Langflow/Flowise 임베드, MCP 설정·감사 UI 추가.
   * **Portal B (Notebook)**: **Open-Notebook(MIT)** 임베드/리버스프록시. AI 모델 설정 페이지는 해당 문서 스펙 전부 반영(로컬 vLLM, OpenRouter, 외부 SOTA API 키·엔드포인트). ([GitHub][1])
   * **Portal C (Perplexica)**: **MIT**이므로 테마/브랜딩·검색 플러그인 전면 교체 OK.

2. **퍼미시브 우선 원칙**

   * **MIT/Apache/BSD** 조합으로 핵심 UI·게이트웨이·벡터DB를 구성 → **브랜딩 제거/테마 전환/플러그인 주입** 모두 자유.
   * (참고) **AGPL** 컴포넌트는 **수정 후 네트워크 제공 시 소스 공개 의무**가 생기니, 가능한 **퍼미시브 대체**를 기본값으로.

     * 예: 오브젝트 스토리지가 꼭 필요하면 **MinIO(AGPL-3.0)** 대신 **SeaweedFS(Apache-2.0)** 같은 대안을 검토.
     * MinIO를 **수정 없이 서비스로만 사용**하면 의무가 완화되지만, “완전 자유” 관점에선 퍼미시브 대안이 더 안전.

3. **상표/브랜딩**

   * 퍼미시브라도 **상표권은 별개**입니다. 레포의 **TRADEMARK**·**BRANDING** 가이드를 확인하고, **자체 브랜드로 전면 교체**하세요.
   * Open-WebUI는 **v0.6.5 이하** 선택으로 이슈를 차단.

4. **배포·감사**

   * 포크 저장소의 **LICENSE/NOTICE** 유지(저작권 고지), 변경 내역은 `CHANGES.md`로 정리.
   * 사내 배포 시 OSS 감사(컴포넌트/버전/라이선스 매핑) 생성.

---

## 깃허브 주소(코드 블록로 제공) & 주석

> 아래는 **핵심 4개**만 라이선스 근거를 인용했고(가장 중요), 나머지는 레포 루트의 `LICENSE`를 확인해 퍼미시브군만 채택하세요.

```text
Open-WebUI (BSD-3 for v0.6.5 and below)
- Repo: https://github.com/open-webui/open-webui
- License change note: https://docs.openwebui.com/license/
  * v0.6.5 이하 BSD-3, v0.6.6+ Open WebUI License (브랜딩 의무)  ← 문서에 명시

Perplexica (MIT)
- Repo: https://github.com/ItzCrazyKns/Perplexica
- License: MIT (레포 LICENSE 파일)

Open-Notebook (MIT)
- Repo: https://github.com/lfnovo/open-notebook
- License: MIT (레포 LICENSE 파일)
- AI 모델 설정 문서: /docs/features/ai-models.md (vLLM/OpenRouter/SOTA API)

ChromaDB (Apache-2.0)
- Repo: https://github.com/chroma-core/chroma
- License: Apache-2.0 (레포 LICENSE)
```

문서 근거 인용: Open-WebUI 라이선스 전환 안내(“v0.6.5 이하 BSD-3 / v0.6.6+ 전용 라이선스”)는 공식 문서에 명시되어 있습니다.
Perplexica는 레포에 **MIT**로 표시되어 있습니다.
Open-Notebook도 레포에 **MIT**로 표시되어 있습니다. ([GitHub][1])
ChromaDB는 **Apache-2.0**입니다. ([GitHub][3])

---

## 최종 결론 (한 줄)

* **메인 쉘은 Open-WebUI `v0.6.5`(BSD-3)로 포크** → 전면 리브랜딩/메뉴 개편 가능
* **Perplexica(MIT)** + **Open-Notebook(MIT)** 를 동일 포털에 임베드 → 검색/RAG/노트북 3-in-1
* 나머지 백엔드·관측·DB 계층도 **MIT/Apache/BSD** 계열만 채택하여 **“브랜딩/기능 전면 수정·재배포”가 자유로운 조합**으로 마무리.

[1]: https://github.com/lfnovo/open-notebook "GitHub - lfnovo/open-notebook: An Open Source implementation of Notebook LM with more flexibility and features"
[2]: https://github.com/BerriAI/litellm "GitHub - BerriAI/litellm: Python SDK, Proxy Server (LLM Gateway) to call 100+ LLM APIs in OpenAI format - [Bedrock, Azure, OpenAI, VertexAI, Cohere, Anthropic, Sagemaker, HuggingFace, Replicate, Groq]"
[3]: https://github.com/chroma-core/chroma "GitHub - chroma-core/chroma: Open-source search and retrieval database for AI applications."


Open-WebUI (메인 UI 쉘)
- GitHub: https://github.com/open-webui/open-webui
- 권장 포크 버전: v0.6.5 또는 그 이전 (BSD-3-Clause 라이선스)

Perplexica (RAG/웹검색 포털)
- GitHub: https://github.com/ItzCrazyKns/Perplexica
- 권장 포크 버전: 최신 안정 버전 (MIT 라이선스)

Open-Notebook (LLM 노트북/리서치 포털)
- GitHub: https://github.com/lfnovo/open-notebook
- 권장 포크 버전: 최신 안정 버전 (MIT 라이선스)

Langflow (노코드 에이전트 빌더)
- GitHub: https://github.com/langflow/langflow
- 권장 포크 버전: 최신 안정 버전 (MIT 라이선스)

Flowise (노코드 에이전트 빌더)
- GitHub: https://github.com/FlowiseAI/Flowise
- 권장 포크 버전: 최신 안정 버전 (Apache-2.0 라이선스)

LiteLLM (LLM 게이트웨이)
- GitHub: https://github.com/BerriAI/litellm
- 권장 포크 버전: 최신 안정 버전 (MIT 라이선스)

Langfuse (트레이싱/평가)
- GitHub: https://github.com/langfuse/langfuse
- 권장 포크 버전: 최신 Community Edition 릴리스 (MIT 라이선스)

Helicone (비용/지연 프록시)
- GitHub: https://github.com/Helicone/Helicone
- 권장 포크 버전: 최신 안정 버전 (MIT 라이선스)

ChromaDB (벡터 데이터베이스)
- GitHub: https://github.com/chroma-core/chroma
- 권장 포크 버전: 최신 안정 버전 (Apache-2.0 라이선스)

PaddleOCR / unstructured (OCR/파서)
- GitHub: https://github.com/PaddlePaddle/PaddleOCR
- 권장 포크 버전: 최신 안정 버전 (Apache-2.0 라이선스)

Kong Gateway (MCP/API 보안)
- GitHub: https://github.com/Kong/kong
- 권장 포크 버전: 3.6.x LTS (Apache-2.0 라이선스)

SeaweedFS (오브젝트 스토리지 대체)
- GitHub: https://github.com/chrislusf/seaweedfs
- 권장 포크 버전: 최신 안정 버전 (Apache-2.0 라이선스)
