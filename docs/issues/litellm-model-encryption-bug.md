# LiteLLM GitHub Issue

## 등록 URL
https://github.com/BerriAI/litellm/issues/new

---

## Title
[Bug] `store_model_in_db: true` encrypts `litellm_params.model` field, causing "LLM Provider NOT provided" error

---

## Description

### Summary
When `store_model_in_db: true` is enabled, the `litellm_params.model` field is encrypted in PostgreSQL, which contradicts the official documentation stating that "Model names and aliases" are **NOT encrypted**. This causes `LLM Provider NOT provided` errors during chat completions because LiteLLM cannot properly identify the LLM provider from the encrypted model name.

### Environment
- **LiteLLM Version**: 1.80.0 (`ghcr.io/berriai/litellm:main-stable`)
- **Database**: PostgreSQL 16
- **Configuration**:
  - `store_model_in_db: true` in `general_settings`
  - `LITELLM_SALT_KEY` environment variable set
  - `LITELLM_MASTER_KEY` environment variable set

### Steps to Reproduce

1. Configure LiteLLM with `store_model_in_db: true`:
```yaml
general_settings:
  store_model_in_db: true
  master_key: os.environ/LITELLM_MASTER_KEY
```

2. Register a model via API:
```bash
curl -X POST http://localhost:4000/model/new \
  -H "Authorization: Bearer sk-1234" \
  -H "Content-Type: application/json" \
  -d '{
    "model_name": "qwen-test",
    "litellm_params": {
      "model": "openrouter/qwen/qwen3-235b-a22b-2507",
      "api_key": "os.environ/OPENROUTER_API_KEY"
    }
  }'
```

3. Check the database:
```sql
SELECT model_name, litellm_params FROM "LiteLLM_ProxyModelTable";
```

**Result**: The `litellm_params.model` field is encrypted:
```json
{
  "model": "0-3YYruSezZ_DJKxbfGgw-tHHO88dQeOi6UBPeTo4c78xKS6oinagwTWUwJkfrtJSJyk8Dky9gTvWuNYUEkCmAHeHsv0c762oCzAIQ==",
  "api_key": "I3jTpzgB0hE1y8SNvtXHgk0RdmMI9rVryMC_BwLRg-NaxtZES3wh87UtQJV0Icw9-3T9luqDi28krpBti8Sd-nEK-FC_",
  ...
}
```

4. Attempt chat completion:
```bash
curl -X POST http://localhost:4000/v1/chat/completions \
  -H "Authorization: Bearer sk-1234" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "qwen-test",
    "messages": [{"role": "user", "content": "Hello"}]
  }'
```

**Error Response**:
```json
{
  "error": {
    "message": "litellm.BadRequestError: LLM Provider NOT provided. Pass in the LLM provider you are trying to call. You passed model=qwen-test..."
  }
}
```

### Expected Behavior
According to the [official Security & Encryption FAQ](https://docs.litellm.ai/docs/proxy/security):

> **NOT Encrypted:**
> - Model names and aliases
> - Rate limits / budgets
> - User / team / org metadata

The `litellm_params.model` field should be stored as plaintext (e.g., `"openrouter/qwen/qwen3-235b-a22b-2507"`), while only sensitive fields like `api_key` should be encrypted.

### Actual Behavior
- The `litellm_params.model` field is encrypted along with `api_key`
- When LiteLLM attempts to decrypt and use the model value, it fails to recognize the LLM provider
- This results in `LLM Provider NOT provided` error

### Additional Information
- Tested with `LITELLM_SALT_KEY` both set and unset - same behavior
- Tested with versions: v1.80.0, v1.79.3 - same behavior
- Workaround: Using `store_model_in_db: false` with YAML `model_list` works correctly

### Suggested Fix
The encryption logic should only apply to sensitive credential fields (`api_key`, `api_secret`, etc.) and NOT to the `model` field, as specified in the documentation.

---

## Labels
- bug
- proxy
- database

---

## 등록 방법
1. https://github.com/BerriAI/litellm/issues/new 접속
2. 위 Title을 제목에 입력
3. Description 내용을 본문에 붙여넣기
4. Labels 선택 (가능하면)
5. Submit new issue

