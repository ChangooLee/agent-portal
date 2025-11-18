<script lang="ts">
	import { fly, fade } from 'svelte/transition';
	import { quintOut } from 'svelte/easing';
	import type { TraceDetail, Span } from '$lib/agentops/types';
	import { getTraceDetail } from '$lib/agentops/api-client';
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
			// Auto-expand root spans
			traceDetail.spans
				.filter((s) => !s.parent_span_id)
				.forEach((s) => expandedSpans.add(s.span_id));
			expandedSpans = expandedSpans; // Trigger reactivity
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
		expandedSpans = expandedSpans; // Trigger reactivity
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

	function formatDuration(ms: number): string {
		if (ms < 1000) return `${ms.toFixed(0)}ms`;
		return `${(ms / 1000).toFixed(2)}s`;
	}

	function getStatusColor(status: string): string {
		if (status === 'ERROR' || status === 'UNSET') return 'text-red-600 dark:text-red-400';
		return 'text-green-600 dark:text-green-400';
	}

	function getStatusBg(status: string): string {
		if (status === 'ERROR' || status === 'UNSET')
			return 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800';
		return 'bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800';
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

	<!-- Drawer -->
	<div
		class="fixed right-0 top-0 h-full w-full md:w-3/4 lg:w-2/3 xl:w-1/2 bg-white dark:bg-gray-900 shadow-2xl z-50 overflow-hidden flex flex-col"
		transition:fly={{ x: 500, duration: 300, easing: quintOut }}
	>
		<!-- Header -->
		<div
			class="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700 bg-gradient-to-r from-primary/10 to-secondary/10"
		>
			<div class="flex-1 min-w-0">
				<h2 class="text-xl font-semibold text-gray-900 dark:text-gray-100 truncate">
					Trace Details
				</h2>
				<p class="text-sm text-gray-600 dark:text-gray-400 font-mono truncate mt-1">
					{traceId}
				</p>
			</div>
			<button
				on:click={onClose}
				class="ml-4 p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
				aria-label="Close drawer"
			>
				<svg
					class="w-6 h-6 text-gray-600 dark:text-gray-400"
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

		<!-- Content -->
		<div class="flex-1 overflow-y-auto">
			{#if loading}
				<div class="flex items-center justify-center h-64">
					<div class="flex flex-col items-center gap-3">
						<div class="loading loading-spinner loading-lg text-primary"></div>
						<p class="text-gray-600 dark:text-gray-400">Loading trace details...</p>
					</div>
				</div>
			{:else if error}
				<div class="p-6">
					<div
						class="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4"
					>
						<p class="text-red-800 dark:text-red-400 font-medium">Error loading trace</p>
						<p class="text-red-600 dark:text-red-500 text-sm mt-1">{error}</p>
					</div>
				</div>
			{:else if traceDetail}
				<div class="p-6 space-y-6">
					<!-- Trace Metadata -->
					<div
						class="rounded-lg border border-white/20 bg-white/60 dark:bg-gray-800/60 p-4 backdrop-blur-sm shadow-sm"
					>
						<h3 class="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-3">
							Trace Metadata
						</h3>
						<div class="grid grid-cols-2 gap-4">
							<div>
								<p class="text-sm text-gray-600 dark:text-gray-400">Project ID</p>
								<p class="text-sm font-mono text-gray-900 dark:text-gray-100 mt-1">
									{traceDetail.project_id}
								</p>
							</div>
							<div>
								<p class="text-sm text-gray-600 dark:text-gray-400">Total Spans</p>
								<p class="text-sm font-semibold text-gray-900 dark:text-gray-100 mt-1">
									{traceDetail.spans.length}
								</p>
							</div>
						</div>
					</div>

					<!-- Timeline Visualization -->
					{#if traceDetail.timeline}
						<div
							class="rounded-lg border border-white/20 bg-white/60 dark:bg-gray-800/60 p-4 backdrop-blur-sm shadow-sm"
						>
							<h3 class="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-3">
								Timeline
							</h3>
							<SpanTimeline timeline={traceDetail.timeline} on:selectSpan={(e) => selectSpan(e.detail)} />
						</div>
					{/if}

					<!-- Span Hierarchy -->
					<div
						class="rounded-lg border border-white/20 bg-white/60 dark:bg-gray-800/60 p-4 backdrop-blur-sm shadow-sm"
					>
						<h3 class="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-3">Span Hierarchy</h3>
						<div class="space-y-1">
							{#each traceDetail.spans.filter((s) => !s.parent_span_id) as rootSpan}
								{@const depth = getSpanDepth(rootSpan)}
								{@const isExpanded = expandedSpans.has(rootSpan.span_id)}
								{@const hasChildren = getSpanChildren(rootSpan.span_id).length > 0}

								<!-- Root Span -->
								<div
									class="rounded-lg border {getStatusBg(
										rootSpan.status_code
									)} p-3 cursor-pointer hover:shadow-md transition-all"
									style="margin-left: {depth * 20}px"
									on:click={() => {
										selectSpan(rootSpan);
										if (hasChildren) toggleSpan(rootSpan.span_id);
									}}
								>
									<div class="flex items-center justify-between">
										<div class="flex items-center gap-2 flex-1 min-w-0">
											{#if hasChildren}
												<svg
													class="w-4 h-4 text-gray-600 dark:text-gray-400 transition-transform {isExpanded
														? 'rotate-90'
														: ''}"
													fill="none"
													stroke="currentColor"
													viewBox="0 0 24 24"
												>
													<path
														stroke-linecap="round"
														stroke-linejoin="round"
														stroke-width="2"
														d="M9 5l7 7-7 7"
													/>
												</svg>
											{:else}
												<div class="w-4"></div>
											{/if}
											<span class="font-medium text-gray-900 dark:text-gray-100 truncate">
												{rootSpan.span_name}
											</span>
											<span class="text-xs {getStatusColor(rootSpan.status_code)} font-semibold">
												{rootSpan.status_code}
											</span>
										</div>
										<span class="text-sm text-gray-600 dark:text-gray-400 ml-2">
											{formatDuration(rootSpan.duration)}
										</span>
									</div>
								</div>

								<!-- Child Spans (Recursive) -->
								{#if isExpanded}
									{#each getSpanChildren(rootSpan.span_id) as childSpan}
										{@const childDepth = getSpanDepth(childSpan)}
										{@const childExpanded = expandedSpans.has(childSpan.span_id)}
										{@const childHasChildren = getSpanChildren(childSpan.span_id).length > 0}

										<div
											class="rounded-lg border {getStatusBg(
												childSpan.status_code
											)} p-3 cursor-pointer hover:shadow-md transition-all"
											style="margin-left: {(childDepth + 1) * 20}px"
											on:click={() => {
												selectSpan(childSpan);
												if (childHasChildren) toggleSpan(childSpan.span_id);
											}}
										>
											<div class="flex items-center justify-between">
												<div class="flex items-center gap-2 flex-1 min-w-0">
													{#if childHasChildren}
														<svg
															class="w-4 h-4 text-gray-600 dark:text-gray-400 transition-transform {childExpanded
																? 'rotate-90'
																: ''}"
															fill="none"
															stroke="currentColor"
															viewBox="0 0 24 24"
														>
															<path
																stroke-linecap="round"
																stroke-linejoin="round"
																stroke-width="2"
																d="M9 5l7 7-7 7"
															/>
														</svg>
													{:else}
														<div class="w-4"></div>
													{/if}
													<span class="font-medium text-gray-900 dark:text-gray-100 truncate">
														{childSpan.span_name}
													</span>
													<span class="text-xs {getStatusColor(childSpan.status_code)} font-semibold">
														{childSpan.status_code}
													</span>
												</div>
												<span class="text-sm text-gray-600 dark:text-gray-400 ml-2">
													{formatDuration(childSpan.duration)}
												</span>
											</div>
										</div>
									{/each}
								{/if}
							{/each}
						</div>
					</div>

					<!-- Selected Span Details -->
					{#if selectedSpan}
						<div
							class="rounded-lg border border-white/20 bg-white/60 dark:bg-gray-800/60 p-4 backdrop-blur-sm shadow-sm"
						>
							<h3 class="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-3">
								Span Details
							</h3>
							<SpanDetails span={selectedSpan} />
						</div>
					{/if}
				</div>
			{/if}
		</div>
	</div>
{/if}

