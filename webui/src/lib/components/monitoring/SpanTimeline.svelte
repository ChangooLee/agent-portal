<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import type { TraceTimeline, SpanNode } from '$lib/monitoring/types';

	export let timeline: TraceTimeline;

	const dispatch = createEventDispatcher();

	function calculatePosition(span: SpanNode) {
		const start = ((span.start_time - timeline.start_time) / timeline.total_duration) * 100;
		const width = (span.duration / timeline.total_duration) * 100;
		return { left: `${start}%`, width: `${Math.max(width, 0.5)}%` };
	}

	function getSpanColor(span: SpanNode): string {
		if (span.status === 'ERROR') return 'bg-red-500 dark:bg-red-600';
		if (span.is_critical_path) return 'bg-primary dark:bg-primary-light';
		return 'bg-gray-400 dark:bg-gray-600';
	}

	function formatDuration(ms: number): string {
		if (ms < 1000) return `${ms.toFixed(0)}ms`;
		return `${(ms / 1000).toFixed(2)}s`;
	}

	function handleSpanClick(span: SpanNode) {
		dispatch('selectSpan', span);
	}

	// Flatten spans for timeline view
	function flattenSpans(spans: SpanNode[]): SpanNode[] {
		const result: SpanNode[] = [];
		function traverse(span: SpanNode) {
			result.push(span);
			span.children.forEach(traverse);
		}
		spans.forEach(traverse);
		return result;
	}

	$: flatSpans = flattenSpans(timeline.spans);
</script>

<div class="space-y-4">
	<!-- Timeline Header -->
	<div class="flex items-center justify-between text-sm text-gray-600 dark:text-gray-400">
		<span>Start: {new Date(timeline.start_time).toLocaleTimeString()}</span>
		<span>Duration: {formatDuration(timeline.total_duration)}</span>
		<span>End: {new Date(timeline.end_time).toLocaleTimeString()}</span>
	</div>

	<!-- Timeline Ruler -->
	<div class="relative h-8 bg-gray-100 dark:bg-gray-800 rounded-lg overflow-hidden">
		<div class="absolute inset-0 flex">
			{#each Array(10) as _, i}
				<div class="flex-1 border-r border-gray-300 dark:border-gray-700 last:border-r-0">
					<span class="text-xs text-gray-500 dark:text-gray-500 ml-1">
						{formatDuration((timeline.total_duration / 10) * (i + 1))}
					</span>
				</div>
			{/each}
		</div>
	</div>

	<!-- Span Bars (Gantt Chart) -->
	<div class="space-y-2">
		{#each flatSpans as span}
			{@const position = calculatePosition(span)}
			<div class="relative">
				<!-- Span Label -->
				<div class="flex items-center mb-1">
					<div style="margin-left: {span.depth * 16}px" class="flex items-center gap-2">
						<span class="text-sm text-gray-700 dark:text-gray-300 truncate max-w-xs">
							{span.span_name}
						</span>
						{#if span.is_critical_path}
							<span
								class="text-xs bg-primary/20 text-primary dark:bg-primary-light/20 dark:text-primary-light px-2 py-0.5 rounded-full font-medium"
							>
								Critical
							</span>
						{/if}
					</div>
				</div>

				<!-- Span Bar -->
				<div class="relative h-8 bg-gray-50 dark:bg-gray-900 rounded-lg overflow-hidden">
					<button
						class="absolute top-1/2 -translate-y-1/2 h-6 {getSpanColor(
							span
						)} rounded shadow-sm hover:shadow-md transition-all cursor-pointer group"
						style="left: {position.left}; width: {position.width}"
						on:click={() => handleSpanClick(span)}
					>
						<!-- Tooltip on Hover -->
						<div
							class="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 hidden group-hover:block z-10 w-max"
						>
							<div
								class="bg-gray-900 dark:bg-gray-100 text-white dark:text-gray-900 text-xs rounded-lg px-3 py-2 shadow-xl"
							>
								<p class="font-semibold">{span.span_name}</p>
								<p class="mt-1">Duration: {formatDuration(span.duration)}</p>
								<p>Status: {span.status}</p>
								{#if span.attributes.model}
									<p>Model: {span.attributes.model}</p>
								{/if}
								{#if span.attributes.total_tokens}
									<p>Tokens: {span.attributes.total_tokens}</p>
								{/if}
							</div>
							<div
								class="absolute top-full left-1/2 -translate-x-1/2 w-0 h-0 border-l-4 border-r-4 border-t-4 border-transparent border-t-gray-900 dark:border-t-gray-100"
							></div>
						</div>
					</button>
				</div>
			</div>
		{/each}
	</div>

	<!-- Legend -->
	<div class="flex items-center gap-4 text-sm text-gray-600 dark:text-gray-400 pt-4 border-t">
		<div class="flex items-center gap-2">
			<div class="w-4 h-4 bg-primary rounded"></div>
			<span>Critical Path</span>
		</div>
		<div class="flex items-center gap-2">
			<div class="w-4 h-4 bg-gray-400 rounded"></div>
			<span>Normal</span>
		</div>
		<div class="flex items-center gap-2">
			<div class="w-4 h-4 bg-red-500 rounded"></div>
			<span>Error</span>
		</div>
	</div>
</div>

