<script lang="ts">
	import { fly, fade } from 'svelte/transition';
	import { quintOut } from 'svelte/easing';
	import type { TraceDetail, Span } from '$lib/monitoring/types';
	import { getTraceDetail } from '$lib/monitoring/api-client';
	import { onMount } from 'svelte';
	import SpanTimeline from './SpanTimeline.svelte';
	import SpanDetails from './SpanDetails.svelte';

	export let traceId: string | null = null;
	export let onClose: () => void;

	let loading = true;
	let error: string | null = null;
	let traceDetail: TraceDetail | null = null;
	let selectedSpan: Span | null = null;
	let expandedSpans: Set<string> = new Set();

	$: if (traceId) {
		loadTraceDetail();
	}

	async function loadTraceDetail() {
		if (!traceId) return;

		loading = true;
		error = null;

		try {
			traceDetail = await getTraceDetail(traceId);
			// Auto-expand ALL spans (default fully expanded)
			const newExpanded = new Set<string>();
			traceDetail.spans.forEach((s) => newExpanded.add(s.span_id));
			expandedSpans = newExpanded;
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load trace details';
			console.error('Failed to load trace:', e);
		} finally {
			loading = false;
		}
	}

	function toggleSpan(spanId: string) {
		if (expandedSpans.has(spanId)) {
			expandedSpans.delete(spanId);
		} else {
			expandedSpans.add(spanId);
		}
		// Create a new Set to trigger Svelte reactivity
		expandedSpans = new Set(expandedSpans);
	}

	function selectSpan(span: Span) {
		selectedSpan = span;
	}

	function getSpanChildren(spanId: string): Span[] {
		if (!traceDetail) return [];
		return traceDetail.spans.filter((s) => s.parent_span_id === spanId);
	}

	function getSpanDepth(span: Span): number {
		let depth = 0;
		let current = span;
		while (current.parent_span_id && traceDetail) {
			const parent = traceDetail.spans.find((s) => s.span_id === current.parent_span_id);
			if (!parent) break;
			current = parent;
			depth++;
		}
		return depth;
	}

	// 모든 스팬을 트리 구조로 정렬하여 flat 리스트로 반환
	function getOrderedSpans(): Span[] {
		if (!traceDetail) return [];
		
		const result: Span[] = [];
		const visited = new Set<string>();
		
		function visit(span: Span) {
			if (visited.has(span.span_id)) return;
			visited.add(span.span_id);
			result.push(span);
			
			// 자식 스팬들을 재귀적으로 방문
			const children = traceDetail!.spans.filter(s => s.parent_span_id === span.span_id);
			children.forEach(child => visit(child));
		}
		
		// Root span들부터 시작
		const rootSpans = traceDetail.spans.filter(s => !s.parent_span_id);
		rootSpans.forEach(root => visit(root));
		
		return result;
	}

	// 특정 스팬이 보여져야 하는지 확인 (조상이 모두 expanded인 경우에만)
	function isSpanVisible(span: Span, expanded: Set<string>): boolean {
		if (!span.parent_span_id) return true; // root는 항상 보임
		
		// 조상들을 모두 확인
		let current = span;
		while (current.parent_span_id && traceDetail) {
			const parent = traceDetail.spans.find(s => s.span_id === current.parent_span_id);
			if (!parent) break;
			if (!expanded.has(parent.span_id)) return false;
			current = parent;
		}
		return true;
	}

	// Reactive statements for expandedSpans dependency
	$: orderedSpans = traceDetail ? getOrderedSpans() : [];
	$: visibilityMap = new Map(orderedSpans.map(s => [s.span_id, isSpanVisible(s, expandedSpans)]));

	function formatDuration(ms: number): string {
		if (ms < 1000) return `${ms.toFixed(0)}ms`;
		return `${(ms / 1000).toFixed(2)}s`;
	}

	function getStatusColor(status: string): string {
		if (status === 'ERROR' || status === 'UNSET') return 'text-red-400';
		return 'text-emerald-400';
	}

	function getStatusBg(status: string): string {
		if (status === 'ERROR' || status === 'UNSET')
			return 'bg-red-500/20 border-red-500/30';
		return 'bg-emerald-500/20 border-emerald-500/30';
	}

	onMount(() => {
		// Prevent body scroll when drawer is open
		document.body.style.overflow = 'hidden';
		return () => {
			document.body.style.overflow = '';
		};
	});
</script>

{#if traceId}
	<!-- Backdrop -->
	<div
		class="fixed inset-0 bg-black/50 backdrop-blur-sm z-40"
		on:click={onClose}
		transition:fade={{ duration: 200 }}
	/>

	<!-- Drawer - Full Screen -->
	<div
		class="fixed inset-0 bg-slate-900 shadow-2xl z-50 overflow-hidden flex flex-col"
		transition:fly={{ x: 500, duration: 300, easing: quintOut }}
	>
		<!-- Header -->
		<div
			class="flex items-center justify-between p-4 border-b border-slate-700/50 bg-slate-800/50"
		>
			<div class="flex-1 min-w-0">
				<h2 class="text-xl font-semibold text-white truncate">
					Trace Details
				</h2>
				<p class="text-sm text-slate-400 font-mono truncate mt-1">
					{traceId}
				</p>
			</div>
			<button
				on:click={onClose}
				class="ml-4 p-2 rounded-lg hover:bg-slate-800/80 transition-colors text-slate-400 hover:text-white"
				aria-label="Close drawer"
			>
				<svg
					class="w-6 h-6"
					fill="none"
					stroke="currentColor"
					viewBox="0 0 24 24"
				>
					<path
						stroke-linecap="round"
						stroke-linejoin="round"
						stroke-width="2"
						d="M6 18L18 6M6 6l12 12"
					/>
				</svg>
			</button>
		</div>

		<!-- Content - Split Layout -->
		<div class="flex-1 overflow-hidden flex">
			{#if loading}
				<div class="flex items-center justify-center w-full h-64">
					<div class="flex flex-col items-center gap-3">
						<div class="loading loading-spinner loading-lg text-cyan-400"></div>
						<p class="text-slate-400">Loading trace details...</p>
					</div>
				</div>
			{:else if error}
				<div class="p-6 w-full">
					<div
						class="bg-red-500/20 border border-red-500/30 rounded-lg p-4"
					>
						<p class="text-red-400 font-medium">Error loading trace</p>
						<p class="text-red-300 text-sm mt-1">{error}</p>
					</div>
				</div>
			{:else if traceDetail}
				<!-- Left Panel: Span Hierarchy -->
				<div class="w-1/2 border-r border-slate-700/50 flex flex-col overflow-hidden">
					<!-- Trace Metadata -->
					<div class="p-4 border-b border-slate-700/50 bg-slate-800/30">
						<div class="flex items-center justify-between">
							<div>
								<h3 class="text-sm font-semibold text-slate-400">Project ID</h3>
								<p class="text-sm font-mono text-white">{traceDetail.project_id}</p>
							</div>
							<div class="text-right">
								<h3 class="text-sm font-semibold text-slate-400">Total Spans</h3>
								<p class="text-sm font-semibold text-white">{traceDetail.spans.length}</p>
							</div>
						</div>
					</div>

					<!-- Timeline (Optional - Collapsible) -->
					{#if traceDetail.timeline}
						<div class="p-4 border-b border-slate-700/50">
							<h3 class="text-sm font-semibold text-slate-400 mb-2">Timeline</h3>
							<SpanTimeline timeline={traceDetail.timeline} on:selectSpan={(e) => selectSpan(e.detail)} />
						</div>
					{/if}

					<!-- Span Hierarchy -->
					<div class="flex-1 overflow-y-auto p-4">
						<h3 class="text-sm font-semibold text-slate-400 mb-3 sticky top-0 bg-slate-900/90 py-2 -mt-2">Span Hierarchy</h3>
						<div class="space-y-1">
							{#each orderedSpans as span (span.span_id)}
								{@const depth = getSpanDepth(span)}
								{@const isExpanded = expandedSpans.has(span.span_id)}
								{@const hasChildren = getSpanChildren(span.span_id).length > 0}
								{@const visible = visibilityMap.get(span.span_id) ?? false}
								{@const isSelected = selectedSpan?.span_id === span.span_id}

							{#if visible}
								<div
									class="rounded-lg border {isSelected ? 'ring-2 ring-cyan-500' : ''} {getStatusBg(span.status_code)} p-2.5 cursor-pointer hover:bg-slate-800/80 hover:shadow-md transition-all"
									style="margin-left: {depth * 16}px"
									on:click={() => selectSpan(span)}
								>
									<div class="flex items-center justify-between">
										<div class="flex items-center gap-1.5 flex-1 min-w-0">
											{#if hasChildren}
												<button
													class="p-0.5 rounded hover:bg-slate-700/50 transition-colors flex-shrink-0"
													on:click|stopPropagation={() => toggleSpan(span.span_id)}
													aria-label={isExpanded ? 'Collapse' : 'Expand'}
												>
													<svg
														class="w-3.5 h-3.5 text-slate-400 transition-transform {isExpanded ? 'rotate-90' : ''}"
														fill="none"
														stroke="currentColor"
														viewBox="0 0 24 24"
													>
														<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
													</svg>
												</button>
											{:else}
												<div class="w-4"></div>
											{/if}
											<span class="text-sm font-medium text-white truncate">{span.span_name}</span>
											<span class="text-xs {getStatusColor(span.status_code)} font-semibold px-1.5 py-0.5 rounded-full border {getStatusBg(span.status_code)} flex-shrink-0">{span.status_code}</span>
										</div>
										<span class="text-xs text-slate-300 ml-2 flex-shrink-0">{formatDuration(span.duration)}</span>
									</div>
								</div>
							{/if}
							{/each}
						</div>
					</div>
				</div>

				<!-- Right Panel: Span Details -->
				<div class="w-1/2 overflow-y-auto bg-slate-800/20">
					{#if selectedSpan}
						<div class="p-6">
							<h3 class="text-lg font-semibold text-white mb-4 sticky top-0 bg-slate-800/90 py-2 -mt-2 z-10">
								Span Details
							</h3>
							<SpanDetails span={selectedSpan} />
						</div>
					{:else}
						<div class="flex items-center justify-center h-full text-slate-400">
							<div class="text-center">
								<svg class="w-16 h-16 mx-auto mb-4 text-slate-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
								</svg>
								<p class="text-lg font-medium">Select a span to view details</p>
								<p class="text-sm text-slate-500 mt-1">Click on any span in the hierarchy</p>
							</div>
						</div>
					{/if}
				</div>
			{/if}
		</div>
	</div>
{/if}

