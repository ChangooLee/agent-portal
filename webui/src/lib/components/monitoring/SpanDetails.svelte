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
			span.span_attributes?.prompt_tokens !== undefined
		);
	}

	function isToolUse(span: Span): boolean {
		return span.span_attributes?.tool_name !== undefined;
	}

	function formatJSON(obj: any): string {
		return JSON.stringify(obj, null, 2);
	}

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
	{#if isLLMCall(span)}
		<div class="border-t border-gray-200 dark:border-gray-700 pt-4">
			<h4 class="text-md font-semibold text-gray-900 dark:text-gray-100 mb-3">LLM Call Details</h4>
			<div class="space-y-3">
				{#if span.span_attributes.model}
					<div>
						<p class="text-sm text-gray-600 dark:text-gray-400">Model</p>
						<p class="text-sm font-mono text-gray-900 dark:text-gray-100 mt-1">
							{span.span_attributes.model}
						</p>
					</div>
				{/if}

				{#if span.span_attributes.prompt}
					<div>
						<p class="text-sm text-gray-600 dark:text-gray-400 mb-1">Prompt</p>
						<div class="bg-gray-50 dark:bg-gray-800 rounded-lg p-3 max-h-40 overflow-y-auto">
							<pre
								class="text-xs text-gray-900 dark:text-gray-100 whitespace-pre-wrap">{span.span_attributes.prompt}</pre>
						</div>
					</div>
				{/if}

				{#if span.span_attributes.response}
					<div>
						<p class="text-sm text-gray-600 dark:text-gray-400 mb-1">Response</p>
						<div class="bg-gray-50 dark:bg-gray-800 rounded-lg p-3 max-h-40 overflow-y-auto">
							<pre
								class="text-xs text-gray-900 dark:text-gray-100 whitespace-pre-wrap">{span.span_attributes.response}</pre>
						</div>
					</div>
				{/if}

				<div class="grid grid-cols-3 gap-4">
					{#if span.span_attributes.prompt_tokens !== undefined}
						<div>
							<p class="text-sm text-gray-600 dark:text-gray-400">Prompt Tokens</p>
							<p class="text-sm font-semibold text-gray-900 dark:text-gray-100 mt-1">
								{span.span_attributes.prompt_tokens}
							</p>
						</div>
					{/if}
					{#if span.span_attributes.completion_tokens !== undefined}
						<div>
							<p class="text-sm text-gray-600 dark:text-gray-400">Completion Tokens</p>
							<p class="text-sm font-semibold text-gray-900 dark:text-gray-100 mt-1">
								{span.span_attributes.completion_tokens}
							</p>
						</div>
					{/if}
					{#if span.span_attributes.total_tokens !== undefined}
						<div>
							<p class="text-sm text-gray-600 dark:text-gray-400">Total Tokens</p>
							<p class="text-sm font-semibold text-gray-900 dark:text-gray-100 mt-1">
								{span.span_attributes.total_tokens}
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
			<h4 class="text-md font-semibold text-gray-900 dark:text-gray-100">Span Attributes</h4>
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
					class="text-xs text-gray-900 dark:text-gray-100 whitespace-pre-wrap">{formatJSON(span.span_attributes)}</pre>
			</div>
		{:else}
			<div class="grid grid-cols-2 gap-3">
				{#each Object.entries(span.span_attributes) as [key, value]}
					{#if !['prompt', 'response', 'input', 'output', 'model', 'tool_name', 'prompt_tokens', 'completion_tokens', 'total_tokens', 'cost'].includes(key)}
						<div>
							<p class="text-sm text-gray-600 dark:text-gray-400">{key}</p>
							<p class="text-sm text-gray-900 dark:text-gray-100 mt-1 break-all">
								{typeof value === 'object' ? JSON.stringify(value) : value}
							</p>
						</div>
					{/if}
				{/each}
			</div>
		{/if}
	</div>
</div>

