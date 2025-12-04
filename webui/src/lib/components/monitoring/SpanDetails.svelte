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
			<p class="text-sm text-gray-600 dark:text-gray-400">Span ID</p>
			<p class="text-sm font-mono text-gray-900 dark:text-gray-100 mt-1 break-all">
				{span.span_id}
			</p>
		</div>
		<div>
			<p class="text-sm text-gray-600 dark:text-gray-400">Parent Span ID</p>
			<p class="text-sm font-mono text-gray-900 dark:text-gray-100 mt-1 break-all">
				{span.parent_span_id || 'None (Root)'}
			</p>
		</div>
		<div>
			<p class="text-sm text-gray-600 dark:text-gray-400">Timestamp</p>
			<p class="text-sm text-gray-900 dark:text-gray-100 mt-1">
				{formatTimestamp(span.timestamp)}
			</p>
		</div>
		<div>
			<p class="text-sm text-gray-600 dark:text-gray-400">Duration</p>
			<p class="text-sm font-semibold text-gray-900 dark:text-gray-100 mt-1">
				{formatDuration(span.duration)}
			</p>
		</div>
		<div>
			<p class="text-sm text-gray-600 dark:text-gray-400">Status</p>
			<p
				class="text-sm font-semibold mt-1 {span.status_code === 'ERROR' || span.status_code === 'UNSET'
					? 'text-red-600 dark:text-red-400'
					: 'text-green-600 dark:text-green-400'}"
			>
				{span.status_code}
			</p>
		</div>
		<div>
			<p class="text-sm text-gray-600 dark:text-gray-400">Span Kind</p>
			<p class="text-sm text-gray-900 dark:text-gray-100 mt-1">
				{span.span_kind}
			</p>
		</div>
	</div>

	{#if span.status_message}
		<div>
			<p class="text-sm text-gray-600 dark:text-gray-400 mb-1">Status Message</p>
			<div class="bg-gray-50 dark:bg-gray-800 rounded-lg p-3">
				<p class="text-sm text-gray-900 dark:text-gray-100">{span.status_message}</p>
			</div>
		</div>
	{/if}

	<!-- LLM Call Details -->
	{#if isLLMCall(span) || hasLLMAttributes}
		<div class="border-t border-gray-200 dark:border-gray-700 pt-4">
			<h4 class="text-md font-semibold text-gray-900 dark:text-gray-100 mb-3">🤖 LLM Call Details</h4>
			<div class="space-y-3">
				<!-- Model Info -->
				{#if span.span_attributes.model || span.span_attributes['llm.model'] || span.span_attributes['llm.response.model']}
					<div class="flex flex-wrap gap-4">
						<div>
							<p class="text-sm text-gray-600 dark:text-gray-400">Model</p>
							<p class="text-sm font-mono bg-blue-50 dark:bg-blue-900/30 px-2 py-1 rounded text-blue-700 dark:text-blue-300 mt-1">
								{span.span_attributes.model || span.span_attributes['llm.model'] || span.span_attributes['llm.response.model']}
							</p>
						</div>
						{#if span.span_attributes['llm.node']}
							<div>
								<p class="text-sm text-gray-600 dark:text-gray-400">Node</p>
								<p class="text-sm font-mono bg-purple-50 dark:bg-purple-900/30 px-2 py-1 rounded text-purple-700 dark:text-purple-300 mt-1">
									{span.span_attributes['llm.node']}
								</p>
							</div>
						{/if}
						{#if span.span_attributes['llm.temperature'] !== undefined}
							<div>
								<p class="text-sm text-gray-600 dark:text-gray-400">Temperature</p>
								<p class="text-sm font-mono text-gray-900 dark:text-gray-100 mt-1">
									{span.span_attributes['llm.temperature']}
								</p>
							</div>
						{/if}
					</div>
				{/if}

				<!-- Token Usage -->
				<div class="grid grid-cols-4 gap-4">
					{#if span.span_attributes.prompt_tokens !== undefined || span.span_attributes['llm.usage.prompt_tokens'] !== undefined}
						<div class="bg-green-50 dark:bg-green-900/20 rounded-lg p-2">
							<p class="text-xs text-gray-600 dark:text-gray-400">Prompt Tokens</p>
							<p class="text-lg font-semibold text-green-700 dark:text-green-300">
								{span.span_attributes.prompt_tokens ?? span.span_attributes['llm.usage.prompt_tokens']}
							</p>
						</div>
					{/if}
					{#if span.span_attributes.completion_tokens !== undefined || span.span_attributes['llm.usage.completion_tokens'] !== undefined}
						<div class="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-2">
							<p class="text-xs text-gray-600 dark:text-gray-400">Completion Tokens</p>
							<p class="text-lg font-semibold text-blue-700 dark:text-blue-300">
								{span.span_attributes.completion_tokens ?? span.span_attributes['llm.usage.completion_tokens']}
							</p>
						</div>
					{/if}
					{#if span.span_attributes.total_tokens !== undefined || span.span_attributes['llm.usage.total_tokens'] !== undefined}
						<div class="bg-purple-50 dark:bg-purple-900/20 rounded-lg p-2">
							<p class="text-xs text-gray-600 dark:text-gray-400">Total Tokens</p>
							<p class="text-lg font-semibold text-purple-700 dark:text-purple-300">
								{span.span_attributes.total_tokens ?? span.span_attributes['llm.usage.total_tokens']}
							</p>
						</div>
					{/if}
					{#if span.span_attributes['llm.latency_ms'] !== undefined}
						<div class="bg-orange-50 dark:bg-orange-900/20 rounded-lg p-2">
							<p class="text-xs text-gray-600 dark:text-gray-400">Latency</p>
							<p class="text-lg font-semibold text-orange-700 dark:text-orange-300">
								{(span.span_attributes['llm.latency_ms'] / 1000).toFixed(2)}s
							</p>
						</div>
					{/if}
				</div>

				{#if span.span_attributes.cost !== undefined}
					<div>
						<p class="text-sm text-gray-600 dark:text-gray-400">Cost</p>
						<p class="text-sm font-semibold text-primary dark:text-primary-light mt-1">
							${span.span_attributes.cost.toFixed(4)}
						</p>
					</div>
				{/if}

				<!-- Request Messages (beautified) -->
				{#if span.span_attributes.prompt || span.span_attributes['llm.request.messages']}
					{@const rawMessages = span.span_attributes.prompt || span.span_attributes['llm.request.messages']}
					{@const { formatted } = beautifyValue(rawMessages)}
					<div>
						<p class="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">📥 Request Messages</p>
						<div class="bg-slate-50 dark:bg-slate-800/80 rounded-lg p-3 max-h-64 overflow-y-auto border border-slate-200 dark:border-slate-700">
							<pre class="text-xs text-gray-800 dark:text-gray-200 whitespace-pre-wrap font-mono leading-relaxed">{formatted}</pre>
						</div>
					</div>
				{/if}

				<!-- Response Content (beautified) -->
				{#if span.span_attributes.response || span.span_attributes['llm.response.content']}
					{@const rawResponse = span.span_attributes.response || span.span_attributes['llm.response.content']}
					{@const { formatted } = beautifyValue(rawResponse)}
					<div>
						<p class="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">📤 Response Content</p>
						<div class="bg-emerald-50 dark:bg-emerald-900/20 rounded-lg p-3 max-h-64 overflow-y-auto border border-emerald-200 dark:border-emerald-700">
							<pre class="text-xs text-gray-800 dark:text-gray-200 whitespace-pre-wrap font-mono leading-relaxed">{formatted}</pre>
						</div>
					</div>
				{/if}

				{#if span.span_attributes['llm.response.finish_reason']}
					<div>
						<p class="text-sm text-gray-600 dark:text-gray-400">Finish Reason</p>
						<p class="text-sm font-mono text-gray-900 dark:text-gray-100 mt-1">
							{span.span_attributes['llm.response.finish_reason']}
						</p>
					</div>
				{/if}
			</div>
		</div>
	{/if}

	<!-- Tool Use Details -->
	{#if isToolUse(span)}
		<div class="border-t border-gray-200 dark:border-gray-700 pt-4">
			<h4 class="text-md font-semibold text-gray-900 dark:text-gray-100 mb-3">Tool Use Details</h4>
			<div class="space-y-3">
				<div>
					<p class="text-sm text-gray-600 dark:text-gray-400">Tool Name</p>
					<p class="text-sm font-mono text-gray-900 dark:text-gray-100 mt-1">
						{span.span_attributes.tool_name}
					</p>
				</div>

				{#if span.span_attributes.input}
					<div>
						<p class="text-sm text-gray-600 dark:text-gray-400 mb-1">Input</p>
						<div class="bg-gray-50 dark:bg-gray-800 rounded-lg p-3 max-h-40 overflow-y-auto">
							<pre
								class="text-xs text-gray-900 dark:text-gray-100 whitespace-pre-wrap">{formatJSON(span.span_attributes.input)}</pre>
						</div>
					</div>
				{/if}

				{#if span.span_attributes.output}
					<div>
						<p class="text-sm text-gray-600 dark:text-gray-400 mb-1">Output</p>
						<div class="bg-gray-50 dark:bg-gray-800 rounded-lg p-3 max-h-40 overflow-y-auto">
							<pre
								class="text-xs text-gray-900 dark:text-gray-100 whitespace-pre-wrap">{formatJSON(span.span_attributes.output)}</pre>
						</div>
					</div>
				{/if}
			</div>
		</div>
	{/if}

	<!-- Raw Attributes -->
	<div class="border-t border-gray-200 dark:border-gray-700 pt-4">
		<div class="flex items-center justify-between mb-3">
			<h4 class="text-md font-semibold text-gray-900 dark:text-gray-100">📋 Span Attributes</h4>
			<button
				on:click={() => (showRawJSON = !showRawJSON)}
				class="text-sm text-primary dark:text-primary-light hover:underline"
			>
				{showRawJSON ? 'Hide' : 'Show'} Raw JSON
			</button>
		</div>

		{#if showRawJSON}
			<div class="bg-gray-50 dark:bg-gray-800 rounded-lg p-3 max-h-96 overflow-y-auto">
				<pre
					class="text-xs text-gray-900 dark:text-gray-100 whitespace-pre-wrap font-mono">{formatJSON(span.span_attributes)}</pre>
			</div>
		{:else}
			<div class="space-y-3">
				{#each Object.entries(span.span_attributes) as [key, value]}
					{#if !shouldHideAttribute(key) && !isLLMAttribute(key)}
						{@const { formatted, isStructured } = beautifyValue(value)}
						<div>
							<p class="text-sm font-medium text-gray-600 dark:text-gray-400 mb-1">{key}</p>
							{#if isStructured}
								<div class="bg-gray-50 dark:bg-gray-800 rounded-lg p-2 max-h-40 overflow-y-auto border border-gray-200 dark:border-gray-700">
									<pre class="text-xs text-gray-800 dark:text-gray-200 whitespace-pre-wrap font-mono leading-relaxed">{formatted}</pre>
								</div>
							{:else}
								<p class="text-sm text-gray-900 dark:text-gray-100 break-all">
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

