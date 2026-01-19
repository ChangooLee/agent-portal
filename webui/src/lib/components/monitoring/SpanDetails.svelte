<script lang="ts">
	import type { Span } from '$lib/monitoring/types';

	export let span: Span;

	function formatDuration(ms: number): string {
		if (ms < 1000) return `${ms.toFixed(0)}ms`;
		return `${(ms / 1000).toFixed(2)}s`;
	}

	function formatTimestamp(timestamp: string): string {
		return new Date(timestamp).toLocaleString();
	}

	function isLLMCall(span: Span): boolean {
		return (
			span.span_attributes?.model !== undefined ||
			span.span_attributes?.prompt_tokens !== undefined ||
			span.span_attributes?.['llm.model'] !== undefined ||
			span.span_attributes?.['llm.request.messages'] !== undefined
		);
	}

	function isToolUse(span: Span): boolean {
		return span.span_attributes?.tool_name !== undefined;
	}

	/**
	 * Span attributes에서 비용 정보 추출 (GenAI 표준 + 기존 호환)
	 * 우선순위:
	 * 1. gen_ai.usage.total_cost (GenAI 표준)
	 * 2. llm.openrouter.usage에서 cost 추출
	 * 3. metadata.usage_object에서 cost 추출
	 * 4. cost (기존 호환)
	 */
	function extractCost(attrs: any): number {
		if (!attrs) return 0;
		
		// 1. GenAI 표준: gen_ai.usage.total_cost
		if (attrs['gen_ai.usage.total_cost'] !== undefined) {
			const cost = parseFloat(attrs['gen_ai.usage.total_cost']);
			if (!isNaN(cost)) return cost;
		}
		
		// 2. llm.openrouter.usage에서 cost 추출
		if (attrs['llm.openrouter.usage']) {
			try {
				const usage = typeof attrs['llm.openrouter.usage'] === 'string' 
					? JSON.parse(attrs['llm.openrouter.usage']) 
					: attrs['llm.openrouter.usage'];
				if (usage?.cost !== undefined) {
					const cost = parseFloat(usage.cost);
					if (!isNaN(cost)) return cost;
				}
			} catch (e) {
				// Python 딕셔너리 문자열 형식 처리: {'cost': 0.000159295, ...} 또는 {'cost': 9.2294e-05, ...}
				try {
					const usageStr = String(attrs['llm.openrouter.usage']);
					// 과학적 표기법 포함 매칭: 'cost': 0.000159295 또는 'cost': 9.2294e-05
					const match = usageStr.match(/'cost':\s*([0-9.eE+-]+)/);
					if (match && match[1]) {
						const cost = parseFloat(match[1]);
						if (!isNaN(cost)) return cost;
					}
				} catch (e2) {
					// Ignore
				}
			}
		}
		
		// 3. metadata.usage_object에서 cost 추출
		if (attrs['metadata.usage_object']) {
			try {
				const usage = typeof attrs['metadata.usage_object'] === 'string'
					? JSON.parse(attrs['metadata.usage_object'])
					: attrs['metadata.usage_object'];
				if (usage?.cost !== undefined) {
					const cost = parseFloat(usage.cost);
					if (!isNaN(cost)) return cost;
				}
			} catch (e) {
				// Python 딕셔너리 문자열 형식 처리: {'cost': 0.000158, ...} 또는 {'cost': 7.84e-05, ...}
				try {
					const usageStr = String(attrs['metadata.usage_object']);
					// 과학적 표기법 포함 매칭: 'cost': 0.000158 또는 'cost': 7.84e-05
					const match = usageStr.match(/'cost':\s*([0-9.eE+-]+)/);
					if (match && match[1]) {
						const cost = parseFloat(match[1]);
						if (!isNaN(cost)) return cost;
					}
				} catch (e2) {
					// Ignore
				}
			}
		}
		
		// 4. 기존 호환: cost
		if (attrs.cost !== undefined) {
			const cost = parseFloat(attrs.cost);
			if (!isNaN(cost)) return cost;
		}
		
		return 0;
	}

	function formatJSON(obj: any): string {
		return JSON.stringify(obj, null, 2);
	}

	/**
	 * 값을 beautify하여 표시.
	 * - JSON 문자열이면 파싱 후 들여쓰기
	 * - escape 문자 (\\n, \\t) 처리
	 * - 배열/객체면 JSON으로 포맷팅
	 */
	function beautifyValue(value: any): { formatted: string; isStructured: boolean } {
		if (value === null || value === undefined) {
			return { formatted: String(value), isStructured: false };
		}

		// 이미 객체/배열인 경우
		if (typeof value === 'object') {
			return { formatted: JSON.stringify(value, null, 2), isStructured: true };
		}

		// 문자열인 경우
		if (typeof value === 'string') {
			// escape 문자 복원
			let cleaned = value
				.replace(/\\n/g, '\n')
				.replace(/\\t/g, '\t')
				.replace(/\\r/g, '\r')
				.replace(/\\"/g, '"');

			// JSON 문자열인지 확인 ([ 또는 {로 시작)
			const trimmed = cleaned.trim();
			if ((trimmed.startsWith('[') || trimmed.startsWith('{')) && (trimmed.endsWith(']') || trimmed.endsWith('}'))) {
				try {
					const parsed = JSON.parse(trimmed);
					return { formatted: JSON.stringify(parsed, null, 2), isStructured: true };
				} catch {
					// 파싱 실패하면 그냥 cleaned 반환
				}
			}

			// 긴 문자열 (줄바꿈 포함)
			if (cleaned.includes('\n') || cleaned.length > 100) {
				return { formatted: cleaned, isStructured: true };
			}

			return { formatted: cleaned, isStructured: false };
		}

		return { formatted: String(value), isStructured: false };
	}

	/**
	 * LLM 관련 필드인지 확인
	 */
	function isLLMAttribute(key: string): boolean {
		const llmKeys = [
			'llm.model', 'llm.node', 'llm.temperature',
			'llm.request.messages', 'llm.response.content', 'llm.response.model',
			'llm.response.finish_reason',
			'llm.usage.prompt_tokens', 'llm.usage.completion_tokens', 'llm.usage.total_tokens',
			'llm.latency_ms'
		];
		return llmKeys.includes(key);
	}

	/**
	 * 숨길 기본 속성 (이미 UI에 별도 표시됨)
	 */
	function shouldHideAttribute(key: string): boolean {
		const hiddenKeys = [
			'prompt', 'response', 'input', 'output', 'model', 'tool_name',
			'prompt_tokens', 'completion_tokens', 'total_tokens', 'cost',
			'service.name', 'component' // 기본 메타데이터
		];
		return hiddenKeys.includes(key);
	}

	// LLM 속성 추출
	$: llmAttributes = span.span_attributes ? Object.entries(span.span_attributes)
		.filter(([key]) => isLLMAttribute(key))
		.reduce((acc, [k, v]) => ({ ...acc, [k]: v }), {} as Record<string, any>) : {};

	$: hasLLMAttributes = Object.keys(llmAttributes).length > 0;

	let showRawJSON = false;
</script>

<div class="space-y-4">
	<!-- Basic Info -->
	<div class="grid grid-cols-2 gap-4">
		<div>
			<p class="text-sm text-slate-400">Span ID</p>
			<p class="text-sm font-mono text-white mt-1 break-all">
				{span.span_id}
			</p>
		</div>
		<div>
			<p class="text-sm text-slate-400">Parent Span ID</p>
			<p class="text-sm font-mono text-white mt-1 break-all">
				{span.parent_span_id || 'None (Root)'}
			</p>
		</div>
		<div>
			<p class="text-sm text-slate-400">Timestamp</p>
			<p class="text-sm text-white mt-1">
				{formatTimestamp(span.timestamp)}
			</p>
		</div>
		<div>
			<p class="text-sm text-slate-400">Duration</p>
			<p class="text-sm font-semibold text-white mt-1">
				{formatDuration(span.duration)}
			</p>
		</div>
		<div>
			<p class="text-sm text-slate-400">Status</p>
			<p
				class="text-sm font-semibold mt-1 {span.status_code === 'ERROR' || span.status_code === 'UNSET'
					? 'text-red-400'
					: 'text-emerald-400'}"
			>
				{span.status_code}
			</p>
		</div>
		<div>
			<p class="text-sm text-slate-400">Span Kind</p>
			<p class="text-sm text-white mt-1">
				{span.span_kind}
			</p>
		</div>
	</div>

	{#if span.status_message}
		<div>
			<p class="text-sm text-slate-400 mb-1">Status Message</p>
			<div class="bg-slate-800/50 rounded-lg p-3 border border-slate-700/50">
				<p class="text-sm text-white">{span.status_message}</p>
			</div>
		</div>
	{/if}

	<!-- LLM Call Details -->
	{#if isLLMCall(span) || hasLLMAttributes}
		<div class="border-t border-slate-700/50 pt-4">
			<h4 class="text-md font-semibold text-white mb-3">🤖 LLM Call Details</h4>
			<div class="space-y-3">
				<!-- Model Info -->
				{#if span.span_attributes.model || span.span_attributes['llm.model'] || span.span_attributes['llm.response.model']}
					<div class="flex flex-wrap gap-4">
						<div>
							<p class="text-sm text-slate-400">Model</p>
							<p class="text-sm font-mono bg-blue-500/20 border border-blue-500/30 px-2 py-1 rounded text-blue-400 mt-1">
								{span.span_attributes.model || span.span_attributes['llm.model'] || span.span_attributes['llm.response.model']}
							</p>
						</div>
						{#if span.span_attributes['llm.node']}
							<div>
								<p class="text-sm text-slate-400">Node</p>
								<p class="text-sm font-mono bg-purple-500/20 border border-purple-500/30 px-2 py-1 rounded text-purple-400 mt-1">
									{span.span_attributes['llm.node']}
								</p>
							</div>
						{/if}
						{#if span.span_attributes['llm.temperature'] !== undefined}
							<div>
								<p class="text-sm text-slate-400">Temperature</p>
								<p class="text-sm font-mono text-white mt-1">
									{span.span_attributes['llm.temperature']}
								</p>
							</div>
						{/if}
					</div>
				{/if}

				<!-- Token Usage -->
				<div class="grid grid-cols-4 gap-4">
					{#if span.span_attributes.prompt_tokens !== undefined || span.span_attributes['llm.usage.prompt_tokens'] !== undefined}
						<div class="bg-emerald-500/20 border border-emerald-500/30 rounded-lg p-2">
							<p class="text-xs text-slate-400">Prompt Tokens</p>
							<p class="text-lg font-semibold text-emerald-400">
								{span.span_attributes.prompt_tokens ?? span.span_attributes['llm.usage.prompt_tokens']}
							</p>
						</div>
					{/if}
					{#if span.span_attributes.completion_tokens !== undefined || span.span_attributes['llm.usage.completion_tokens'] !== undefined}
						<div class="bg-blue-500/20 border border-blue-500/30 rounded-lg p-2">
							<p class="text-xs text-slate-400">Completion Tokens</p>
							<p class="text-lg font-semibold text-blue-400">
								{span.span_attributes.completion_tokens ?? span.span_attributes['llm.usage.completion_tokens']}
							</p>
						</div>
					{/if}
					{#if span.span_attributes.total_tokens !== undefined || span.span_attributes['llm.usage.total_tokens'] !== undefined}
						<div class="bg-purple-500/20 border border-purple-500/30 rounded-lg p-2">
							<p class="text-xs text-slate-400">Total Tokens</p>
							<p class="text-lg font-semibold text-purple-400">
								{span.span_attributes.total_tokens ?? span.span_attributes['llm.usage.total_tokens']}
							</p>
						</div>
					{/if}
					{#if span.span_attributes['llm.latency_ms'] !== undefined}
						<div class="bg-amber-500/20 border border-amber-500/30 rounded-lg p-2">
							<p class="text-xs text-slate-400">Latency</p>
							<p class="text-lg font-semibold text-amber-400">
								{(span.span_attributes['llm.latency_ms'] / 1000).toFixed(2)}s
							</p>
						</div>
					{/if}
				</div>

				{#if extractCost(span.span_attributes) > 0}
					{@const cost = extractCost(span.span_attributes)}
					<div>
						<p class="text-sm text-slate-400">Cost</p>
						<p class="text-sm font-semibold text-cyan-400 mt-1">
							${cost.toFixed(6)}
						</p>
					</div>
				{/if}

				<!-- Request Messages (beautified) -->
				{#if span.span_attributes.prompt || span.span_attributes['llm.request.messages']}
					{@const rawMessages = span.span_attributes.prompt || span.span_attributes['llm.request.messages']}
					{@const { formatted } = beautifyValue(rawMessages)}
					<div>
						<p class="text-sm font-medium text-slate-300 mb-2">📥 Request Messages</p>
						<div class="bg-slate-800/50 rounded-lg p-3 max-h-64 overflow-y-auto border border-slate-700/50">
							<pre class="text-xs text-slate-200 whitespace-pre-wrap font-mono leading-relaxed">{formatted}</pre>
						</div>
					</div>
				{/if}

				<!-- Agent Response Content (최종 분석 결과) -->
				{#if span.span_attributes['agent.response.content']}
					{@const rawAgentResponse = span.span_attributes['agent.response.content']}
					{@const { formatted } = beautifyValue(rawAgentResponse)}
					<div>
						<p class="text-sm font-medium text-slate-300 mb-2">🤖 Agent Response (최종 분석 결과)</p>
						<div class="bg-purple-500/20 border border-purple-500/30 rounded-lg p-3 max-h-96 overflow-y-auto">
							<pre class="text-xs text-purple-200 whitespace-pre-wrap font-mono leading-relaxed">{formatted}</pre>
						</div>
						{#if span.span_attributes['agent.response.length']}
							<p class="text-xs text-slate-400 mt-1">
								전체 길이: {span.span_attributes['agent.response.length']}자
							</p>
						{/if}
					</div>
				{/if}

				<!-- Response Content (LLM 응답) -->
				{#if span.span_attributes.response || span.span_attributes['llm.response.content']}
					{@const rawResponse = span.span_attributes.response || span.span_attributes['llm.response.content']}
					{@const { formatted } = beautifyValue(rawResponse)}
					<div>
						<p class="text-sm font-medium text-slate-300 mb-2">📤 LLM Response Content</p>
						<div class="bg-emerald-500/20 border border-emerald-500/30 rounded-lg p-3 max-h-64 overflow-y-auto">
							<pre class="text-xs text-emerald-200 whitespace-pre-wrap font-mono leading-relaxed">{formatted}</pre>
						</div>
					</div>
				{/if}

				{#if span.span_attributes['llm.response.finish_reason']}
					<div>
						<p class="text-sm text-slate-400">Finish Reason</p>
						<p class="text-sm font-mono text-white mt-1">
							{span.span_attributes['llm.response.finish_reason']}
						</p>
					</div>
				{/if}
			</div>
		</div>
	{/if}

	<!-- Tool Use Details -->
	{#if isToolUse(span)}
		<div class="border-t border-slate-700/50 pt-4">
			<h4 class="text-md font-semibold text-white mb-3">Tool Use Details</h4>
			<div class="space-y-3">
				<div>
					<p class="text-sm text-slate-400">Tool Name</p>
					<p class="text-sm font-mono text-white mt-1">
						{span.span_attributes.tool_name}
					</p>
				</div>

				{#if span.span_attributes.input}
					<div>
						<p class="text-sm text-slate-400 mb-1">Input</p>
						<div class="bg-slate-800/50 rounded-lg p-3 max-h-40 overflow-y-auto border border-slate-700/50">
							<pre
								class="text-xs text-slate-200 whitespace-pre-wrap">{formatJSON(span.span_attributes.input)}</pre>
						</div>
					</div>
				{/if}

				{#if span.span_attributes.output}
					<div>
						<p class="text-sm text-slate-400 mb-1">Output</p>
						<div class="bg-slate-800/50 rounded-lg p-3 max-h-40 overflow-y-auto border border-slate-700/50">
							<pre
								class="text-xs text-slate-200 whitespace-pre-wrap">{formatJSON(span.span_attributes.output)}</pre>
						</div>
					</div>
				{/if}
			</div>
		</div>
	{/if}

	<!-- Raw Attributes -->
	<div class="border-t border-slate-700/50 pt-4">
		<div class="flex items-center justify-between mb-3">
			<h4 class="text-md font-semibold text-white">📋 Span Attributes</h4>
			<button
				on:click={() => (showRawJSON = !showRawJSON)}
				class="text-sm text-cyan-400 hover:text-cyan-300 hover:underline transition-colors"
			>
				{showRawJSON ? 'Hide' : 'Show'} Raw JSON
			</button>
		</div>

		{#if showRawJSON}
			<div class="bg-slate-800/50 rounded-lg p-3 max-h-96 overflow-y-auto border border-slate-700/50">
				<pre
					class="text-xs text-slate-200 whitespace-pre-wrap font-mono">{formatJSON(span.span_attributes)}</pre>
			</div>
		{:else}
			<div class="space-y-3">
				{#each Object.entries(span.span_attributes) as [key, value]}
					{#if !shouldHideAttribute(key) && !isLLMAttribute(key)}
						{@const { formatted, isStructured } = beautifyValue(value)}
						<div>
							<p class="text-sm font-medium text-slate-400 mb-1">{key}</p>
							{#if isStructured}
								<div class="bg-slate-800/50 rounded-lg p-2 max-h-40 overflow-y-auto border border-slate-700/50">
									<pre class="text-xs text-slate-200 whitespace-pre-wrap font-mono leading-relaxed">{formatted}</pre>
								</div>
							{:else}
								<p class="text-sm text-white break-all">
									{formatted}
								</p>
							{/if}
						</div>
					{/if}
				{/each}
			</div>
		{/if}
	</div>
</div>

