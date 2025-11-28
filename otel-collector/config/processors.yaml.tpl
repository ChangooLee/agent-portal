processors:
  resource:
    attributes:
      # For self-hosted deployment, use static project_id from environment
      - key: ProjectId
        action: upsert
        value: "8c59e361-3727-418c-bc68-086b69f7598b"
      - key: {{ SEMCONV.PROJECT_ID }}
        action: upsert
        value: "8c59e361-3727-418c-bc68-086b69f7598b"

  resourcedetection/system:
    detectors: ['system']
    system:
      hostname_sources: ['os']

  transform:
    trace_statements:
      # we are using root-level trace_statements so that the cache is shared across
      # all transforms in the pipeline (as opposed to `- scope: span` which creates
      # a new cache for each transform)

      # cost data gets populated dynamically on container build
      {% for cost in MODEL_COSTS %}
      - set( span.cache["_input_costs"]["{{ cost.model }}"], {{ cost.input }})
      - set(span.cache["_output_costs"]["{{ cost.model }}"], {{ cost.output }})
      {% endfor %}

      # set prompt cost on spans that have prompt tokens an a known model
      - set(span.attributes["{{ SEMCONV.LLM_USAGE_PROMPT_COST }}"],
          Double(span.attributes["{{ SEMCONV.LLM_USAGE_PROMPT_TOKENS }}"]) *
          span.cache["_input_costs"][span.attributes["{{ SEMCONV.LLM_RESPONSE_MODEL }}"]])
          where (
            span.attributes["{{ SEMCONV.LLM_USAGE_PROMPT_TOKENS }}"] != nil and
            span.attributes["{{ SEMCONV.LLM_RESPONSE_MODEL }}"] != nil and
            span.cache["_input_costs"][span.attributes["{{ SEMCONV.LLM_RESPONSE_MODEL }}"]] != nil)

      # set completion cost on spans that have completion tokens an a known model
      - set(span.attributes["{{ SEMCONV.LLM_USAGE_COMPLETION_COST }}"],
          Double(span.attributes["{{ SEMCONV.LLM_USAGE_COMPLETION_TOKENS }}"]) *
          span.cache["_output_costs"][span.attributes["{{ SEMCONV.LLM_RESPONSE_MODEL }}"]])
          where (
            span.attributes["{{ SEMCONV.LLM_USAGE_COMPLETION_TOKENS }}"] != nil and
            span.attributes["{{ SEMCONV.LLM_RESPONSE_MODEL }}"] != nil and
            span.cache["_output_costs"][span.attributes["{{ SEMCONV.LLM_RESPONSE_MODEL }}"]] != nil)
