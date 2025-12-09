<script lang="ts">
	import type {
		ReplayEvent,
		LLMCallData,
		ToolUseData,
		ErrorData,
		DecisionData
	} from '$lib/monitoring/types';

	export let event: ReplayEvent;

	function formatTime(ms: number): string {
		const seconds = Math.floor(ms / 1000);
		const minutes = Math.floor(seconds / 60);
		const remainingSeconds = seconds % 60;
		return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
	}

	function getEventIcon(type: string): string {
		switch (type) {
			case 'llm_call':
				return '🤖';
			case 'tool_use':
				return '🔧';
			case 'error':
				return '❌';
			case 'decision':
				return '🎯';
			case 'span_start':
				return '▶️';
			case 'span_end':
				return '⏹️';
			default:
				return '📝';
		}
	}

	function getEventColor(type: string): string {
		switch (type) {
			case 'llm_call':
				return 'border-blue-500/30 bg-blue-500/10';
			case 'tool_use':
				return 'border-emerald-500/30 bg-emerald-500/10';
			case 'error':
				return 'border-red-500/30 bg-red-500/10';
			case 'decision':
				return 'border-purple-500/30 bg-purple-500/10';
			default:
				return 'border-slate-800/50 bg-slate-900/80';
		}
	}

	function getEventTitle(type: string): string {
		switch (type) {
			case 'llm_call':
				return 'LLM Call';
			case 'tool_use':
				return 'Tool Use';
			case 'error':
				return 'Error';
			case 'decision':
				return 'Decision';
			case 'span_start':
				return 'Span Start';
			case 'span_end':
				return 'Span End';
			default:
				return 'Event';
		}
	}
</script>

<div class="rounded-xl border {getEventColor(event.type)} p-6 shadow-lg shadow-black/20">
	<!-- Header -->
	<div class="flex items-start justify-between mb-4">
		<div class="flex items-center gap-3">
			<span class="text-3xl">{getEventIcon(event.type)}</span>
			<div>
				<h3 class="text-lg font-bold text-white">
					{getEventTitle(event.type)}
				</h3>
				<p class="text-sm text-slate-300 mt-1">{event.span_name}</p>
			</div>
		</div>
		<div class="text-right">
			<p class="text-sm font-mono text-slate-300">
				{formatTime(event.relative_time)}
			</p>
			<p class="text-xs text-slate-400 mt-1">
				{new Date(event.timestamp).toLocaleTimeString()}
			</p>
		</div>
	</div>

	<!-- Event-Specific Content -->
	{#if event.type === 'llm_call'}
		{@const data = event.data}
		<div class="space-y-4">
			<div class="grid grid-cols-2 gap-4">
				<div>
					<p class="text-sm text-slate-400">Model</p>
					<p class="text-sm font-mono text-white mt-1">{data.model}</p>
				</div>
				<div>
					<p class="text-sm text-slate-400">Latency</p>
					<p class="text-sm font-semibold text-white mt-1">
						{data.latency.toFixed(0)}ms
					</p>
				</div>
			</div>

			<div>
				<p class="text-sm text-slate-400 mb-2">Prompt</p>
				<div class="bg-slate-800/50 border border-slate-700/50 rounded-lg p-3 max-h-40 overflow-y-auto">
					<pre class="text-xs text-slate-200 whitespace-pre-wrap">{data.prompt}</pre>
				</div>
			</div>

			<div>
				<p class="text-sm text-slate-400 mb-2">Response</p>
				<div class="bg-slate-800/50 border border-slate-700/50 rounded-lg p-3 max-h-40 overflow-y-auto">
					<pre
						class="text-xs text-slate-200 whitespace-pre-wrap">{data.response}</pre>
				</div>
			</div>

			<div class="grid grid-cols-4 gap-4 pt-4 border-t border-slate-700/50">
				<div>
					<p class="text-xs text-slate-400">Prompt Tokens</p>
					<p class="text-sm font-semibold text-white mt-1">
						{data.prompt_tokens}
					</p>
				</div>
				<div>
					<p class="text-xs text-slate-400">Completion Tokens</p>
					<p class="text-sm font-semibold text-white mt-1">
						{data.completion_tokens}
					</p>
				</div>
				<div>
					<p class="text-xs text-slate-400">Total Tokens</p>
					<p class="text-sm font-semibold text-white mt-1">
						{data.total_tokens}
					</p>
				</div>
				<div>
					<p class="text-xs text-slate-400">Cost</p>
					<p class="text-sm font-semibold text-cyan-400 mt-1">
						${data.cost.toFixed(4)}
					</p>
				</div>
			</div>
		</div>
	{:else if event.type === 'tool_use'}
		{@const data = event.data}
		<div class="space-y-4">
			<div class="grid grid-cols-2 gap-4">
				<div>
					<p class="text-sm text-slate-400">Tool Name</p>
					<p class="text-sm font-mono text-white mt-1">{data.tool_name}</p>
				</div>
				<div>
					<p class="text-sm text-slate-400">Duration</p>
					<p class="text-sm font-semibold text-white mt-1">
						{data.duration.toFixed(0)}ms
					</p>
				</div>
			</div>

			<div>
				<p class="text-sm text-slate-400 mb-2">Input</p>
				<div class="bg-slate-800/50 border border-slate-700/50 rounded-lg p-3 max-h-40 overflow-y-auto">
					<pre
						class="text-xs text-slate-200 whitespace-pre-wrap">{JSON.stringify(data.input, null, 2)}</pre>
				</div>
			</div>

			<div>
				<p class="text-sm text-slate-400 mb-2">Output</p>
				<div class="bg-slate-800/50 border border-slate-700/50 rounded-lg p-3 max-h-40 overflow-y-auto">
					<pre
						class="text-xs text-slate-200 whitespace-pre-wrap">{JSON.stringify(data.output, null, 2)}</pre>
				</div>
			</div>

			<div class="pt-4 border-t border-slate-700/50">
				<span
					class="inline-flex items-center px-3 py-1 rounded-full text-sm font-medium {data.status ===
					'success'
						? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
						: 'bg-red-500/20 text-red-400 border border-red-500/30'}"
				>
					{data.status === 'success' ? '✓ Success' : '✗ Error'}
				</span>
			</div>
		</div>
	{:else if event.type === 'error'}
		{@const data = event.data}
		<div class="space-y-4">
			<div>
				<p class="text-sm text-slate-400">Error Type</p>
				<p class="text-sm font-semibold text-red-400 mt-1">{data.error_type}</p>
			</div>

			<div>
				<p class="text-sm text-slate-400 mb-2">Error Message</p>
				<div class="bg-slate-800/50 border border-slate-700/50 rounded-lg p-3">
					<p class="text-sm text-red-400">{data.error_message}</p>
				</div>
			</div>

			{#if data.stack_trace}
				<div>
					<p class="text-sm text-slate-400 mb-2">Stack Trace</p>
					<div class="bg-slate-800/50 border border-slate-700/50 rounded-lg p-3 max-h-60 overflow-y-auto">
						<pre
							class="text-xs text-slate-200 whitespace-pre-wrap">{data.stack_trace}</pre>
					</div>
				</div>
			{/if}
		</div>
	{:else if event.type === 'decision'}
		{@const data = event.data}
		<div class="space-y-4">
			<div>
				<p class="text-sm text-slate-400">Decision Type</p>
				<p class="text-sm font-semibold text-white mt-1">
					{data.decision_type}
				</p>
			</div>

			<div>
				<p class="text-sm text-slate-400 mb-2">Reasoning</p>
				<div class="bg-slate-800/50 border border-slate-700/50 rounded-lg p-3">
					<p class="text-sm text-slate-200">{data.reasoning}</p>
				</div>
			</div>

			<div>
				<p class="text-sm text-slate-400 mb-2">Selected Option</p>
				<div class="bg-purple-500/20 border border-purple-500/30 rounded-lg p-3">
					<p class="text-sm font-semibold text-purple-400">
						{data.selected_option}
					</p>
				</div>
			</div>

			{#if data.alternatives.length > 0}
				<div>
					<p class="text-sm text-slate-400 mb-2">Alternatives Considered</p>
					<div class="space-y-2">
						{#each data.alternatives as alt}
							<div class="bg-slate-800/50 border border-slate-700/50 rounded-lg p-2">
								<p class="text-sm text-slate-300">{alt}</p>
							</div>
						{/each}
					</div>
				</div>
			{/if}
		</div>
	{:else}
		<!-- Generic span event -->
		<div class="space-y-2">
			<div>
				<p class="text-sm text-slate-400">Span ID</p>
				<p class="text-sm font-mono text-white mt-1">{event.span_id}</p>
			</div>
		</div>
	{/if}
</div>

