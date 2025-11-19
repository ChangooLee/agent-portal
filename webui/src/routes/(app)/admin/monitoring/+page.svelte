<script lang="ts">
	import { getContext, onMount, onDestroy } from 'svelte';
	import { user, WEBUI_NAME } from '$lib/stores';
	import {
		getTraces,
		getMetrics,
		getCostTrend,
		getTokenUsage,
		getPerformanceMetrics,
		getAgentFlowGraph,
		getAgentUsageStats,
		agentOpsWS,
		type Trace,
		type Metrics
	} from '$lib/agentops/api-client';
	import type {
		TraceFilters,
		FilterPreset,
		CostDataPoint,
		TokenDataPoint,
		PerformanceDataPoint,
		AgentFlowGraph,
		AgentUsageStats
	} from '$lib/agentops/types';

	// Import all new components
	import TraceDrawer from '$lib/components/agentops/TraceDrawer.svelte';
	import ReplayPlayer from '$lib/components/agentops/ReplayPlayer.svelte';
	import CostChart from '$lib/components/agentops/CostChart.svelte';
	import TokenChart from '$lib/components/agentops/TokenChart.svelte';
	import PerformanceChart from '$lib/components/agentops/PerformanceChart.svelte';
	import AgentFlowGraphComponent from '$lib/components/agentops/AgentFlowGraph.svelte';
	import FilterPanel from '$lib/components/agentops/FilterPanel.svelte';
	import ExportDialog from '$lib/components/agentops/ExportDialog.svelte';

	const i18n = getContext('i18n');

	// Tab state
	let activeTab: 'traces' | 'overview' | 'replay' | 'analytics' = 'overview'; // 메인 화면: Overview
	let loading = true;
	let error: string | null = null;

	// Traces state
	let traces: Trace[] = [];
	let totalTraces = 0;
	let currentPage = 1;
	let pageSize = 20;
	let selectedTraceId: string | null = null;

	// Metrics state
	let metrics: Metrics | null = null;

	// Analytics state
	let costData: CostDataPoint[] = [];
	let tokenData: TokenDataPoint[] = [];
	let performanceData: PerformanceDataPoint[] = [];
	let agentFlowGraph: AgentFlowGraph | null = null;
	
	// Agent Usage state
	let agentUsageStats: AgentUsageStats[] = [];

	// Filter state
	let filters: TraceFilters = {
		start_time: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString(),
		end_time: new Date().toISOString()
	};
	let filterPresets: FilterPreset[] = [];
	let showFilters = false;

	// Export state
	let showExportDialog = false;

	// Replay state
	let replayTraceId: string | null = null;

	const projectId = 'default-project';

	onMount(async () => {
		// WebSocket 실시간 업데이트 (Loader.svelte 수정 후 안정화됨)
		agentOpsWS.connect(projectId);
		agentOpsWS.on('trace_new', handleNewTrace);
		agentOpsWS.on('trace_update', handleTraceUpdate);

		// Load initial data
		await loadData();

		// Load saved filter presets from localStorage
		const savedPresets = localStorage.getItem('agentops_filter_presets');
		if (savedPresets) {
			filterPresets = JSON.parse(savedPresets);
		}
	});

	onDestroy(() => {
		agentOpsWS.disconnect();
	});

	async function loadData() {
		loading = true;
		error = null;

		try {
			if (activeTab === 'traces') {
				await loadTraces();
			} else if (activeTab === 'overview') {
				await Promise.all([loadMetrics(), loadCostTrend(), loadTokenUsage(), loadAgentUsageStats()]);
			} else if (activeTab === 'analytics') {
				await Promise.all([loadPerformanceMetrics(), loadAgentFlowGraph()]);
			}
		} catch (e: any) {
			error = e.message || 'Failed to load data';
			console.error('Error loading data:', e);
		} finally {
			loading = false;
		}
	}

	async function loadTraces() {
		const result = await getTraces({
			project_id: projectId,
			start_time: filters.start_time,
			end_time: filters.end_time,
			page: currentPage,
			size: pageSize,
			search: filters.search || undefined
		});

		traces = result.traces;
		totalTraces = result.total;
	}

	async function loadMetrics() {
		metrics = await getMetrics({
			project_id: projectId,
			start_time: filters.start_time,
			end_time: filters.end_time
		});
	}

	async function loadCostTrend() {
		costData = await getCostTrend({
			project_id: projectId,
			start_time: filters.start_time,
			end_time: filters.end_time,
			interval: 'day'
		});
	}

	async function loadTokenUsage() {
		tokenData = await getTokenUsage({
			project_id: projectId,
			start_time: filters.start_time,
			end_time: filters.end_time,
			interval: 'day'
		});
	}

	async function loadPerformanceMetrics() {
		performanceData = await getPerformanceMetrics({
			project_id: projectId,
			start_time: filters.start_time,
			end_time: filters.end_time
		});
	}

	async function loadAgentFlowGraph() {
		agentFlowGraph = await getAgentFlowGraph({
			project_id: projectId,
			start_time: filters.start_time,
			end_time: filters.end_time
		});
	}
	
	async function loadAgentUsageStats() {
		agentUsageStats = await getAgentUsageStats({
			project_id: projectId,
			start_time: filters.start_time,
			end_time: filters.end_time
		});
	}

	function handleApplyFilters(event: CustomEvent<TraceFilters>) {
		filters = event.detail;
		currentPage = 1;
		loadData();
	}

	function handleSavePreset(event: CustomEvent<FilterPreset>) {
		filterPresets = [...filterPresets, event.detail];
		localStorage.setItem('agentops_filter_presets', JSON.stringify(filterPresets));
	}

	function handleDeletePreset(event: CustomEvent<string>) {
		filterPresets = filterPresets.filter((p) => p.id !== event.detail);
		localStorage.setItem('agentops_filter_presets', JSON.stringify(filterPresets));
	}

	function handlePageChange(newPage: number) {
		currentPage = newPage;
		loadTraces();
	}

	function openTraceDrawer(traceId: string) {
		selectedTraceId = traceId;
	}

	function closeTraceDrawer() {
		selectedTraceId = null;
	}

	function openReplay(traceId: string) {
		replayTraceId = traceId;
		activeTab = 'replay';
	}

	function handleNewTrace(data: any) {
		// Add new trace to the top of the list
		traces = [data, ...traces];
		totalTraces++;
	}

	function handleTraceUpdate(data: any) {
		// Update existing trace
		const index = traces.findIndex((t) => t.trace_id === data.trace_id);
		if (index !== -1) {
			traces[index] = { ...traces[index], ...data };
			traces = traces; // Trigger reactivity
		}
	}

	function formatDuration(ms: number): string {
		if (ms < 1000) return `${ms.toFixed(0)}ms`;
		return `${(ms / 1000).toFixed(2)}s`;
	}

	function formatCost(cost: number): string {
		return `$${cost.toFixed(4)}`;
	}

	function formatNumber(num: number): string {
		if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`;
		if (num >= 1000) return `${(num / 1000).toFixed(1)}K`;
		return num.toString();
	}

	$: totalPages = Math.ceil(totalTraces / pageSize);
</script>

<svelte:head>
	<title>{$i18n.t('Monitoring')} | {$WEBUI_NAME}</title>
</svelte:head>

<div class="flex w-full flex-col min-h-full px-3 py-4 @md:px-6 @md:py-6">
	<div class="mx-auto flex w-full max-w-[1800px] flex-col gap-6">
		{#if $user?.role !== 'admin'}
			<div class="text-red-500">
				{$i18n.t('Access Denied: Only administrators can view this page.')}
			</div>
		{:else}
			<!-- Glassmorphism Hero -->
			<section
				class="relative overflow-hidden rounded-3xl border border-white/20 bg-white/60 p-6 shadow-xl shadow-primary/10 backdrop-blur-2xl dark:border-gray-700/30 dark:bg-gray-900/60"
			>
				<div class="absolute inset-0 bg-gradient-to-br from-primary/20 via-secondary/10 to-accent/20 opacity-60" />
				<div class="relative flex items-center justify-between">
					<div>
						<h1 class="text-2xl font-semibold tracking-tight text-gray-900 dark:text-gray-100">
							🔍 Agent Monitoring
						</h1>
						<p class="mt-2 text-sm text-gray-700 dark:text-gray-300">
							실시간 에이전트 실행 모니터링, 비용 추적, 세션 리플레이
						</p>
					</div>
					<div class="flex items-center gap-3">
						<button
							on:click={() => (showFilters = !showFilters)}
							class="px-4 py-2 rounded-lg border border-white/20 bg-white/60 dark:bg-gray-800/60 text-gray-700 dark:text-gray-300 hover:bg-white/80 dark:hover:bg-gray-800/80 transition-all backdrop-blur-sm shadow-sm"
						>
							<svg class="w-5 h-5 inline-block mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z" />
							</svg>
							Filters
						</button>
						<button
							on:click={() => (showExportDialog = true)}
							class="px-4 py-2 rounded-lg bg-primary text-white hover:opacity-90 transition-opacity shadow-sm"
						>
							<svg class="w-5 h-5 inline-block mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
							</svg>
							Export
						</button>
					</div>
				</div>
			</section>

			<!-- Filter Panel -->
			{#if showFilters}
				<FilterPanel
					{filters}
					presets={filterPresets}
					on:apply={handleApplyFilters}
					on:savePreset={handleSavePreset}
					on:deletePreset={handleDeletePreset}
				/>
			{/if}

		<!-- Tab Navigation (AgentOps 순서: Overview → Analytics → Replay → Traces) -->
		<div class="flex gap-2 overflow-x-auto">
			<button
				class="px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 whitespace-nowrap {activeTab === 'overview'
					? 'bg-[#0072CE] text-white shadow-sm'
					: 'text-gray-600 hover:bg-gray-50 dark:text-gray-300 dark:hover:bg-gray-800'}"
				on:click={() => {
					activeTab = 'overview';
					loadData();
				}}
			>
				📈 Overview
			</button>
			<button
				class="px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 whitespace-nowrap {activeTab === 'analytics'
					? 'bg-[#0072CE] text-white shadow-sm'
					: 'text-gray-600 hover:bg-gray-50 dark:text-gray-300 dark:hover:bg-gray-800'}"
				on:click={() => {
					activeTab = 'analytics';
					loadData();
				}}
			>
				🎯 Analytics
			</button>
			<button
				class="px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 whitespace-nowrap {activeTab === 'replay'
					? 'bg-[#0072CE] text-white shadow-sm'
					: 'text-gray-600 hover:bg-gray-50 dark:text-gray-300 dark:hover:bg-gray-800'}"
				on:click={() => {
					activeTab = 'replay';
				}}
			>
				▶️ Replay
			</button>
			<button
				class="px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 whitespace-nowrap {activeTab === 'traces'
					? 'bg-[#0072CE] text-white shadow-sm'
					: 'text-gray-600 hover:bg-gray-50 dark:text-gray-300 dark:hover:bg-gray-800'}"
				on:click={() => {
					activeTab = 'traces';
					loadData();
				}}
			>
				📊 Traces
			</button>
		</div>

			<!-- Content Area -->
			<div class="flex-1">
				{#if loading}
					<div class="flex items-center justify-center h-64">
						<div class="flex flex-col items-center gap-3">
							<div class="loading loading-spinner loading-lg text-primary"></div>
							<p class="text-gray-600 dark:text-gray-400">Loading data...</p>
						</div>
					</div>
				{:else if error}
					<div
						class="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-6"
					>
						<p class="text-red-800 dark:text-red-400 font-medium">Error loading data</p>
						<p class="text-red-600 dark:text-red-500 text-sm mt-1">{error}</p>
						<button
							on:click={loadData}
							class="mt-4 px-4 py-2 rounded-lg bg-red-600 text-white hover:bg-red-700 transition-colors"
						>
							Retry
						</button>
					</div>
				{:else}
					<!-- Traces Tab -->
					{#if activeTab === 'traces'}
						<div class="space-y-4">
							<!-- Traces Table -->
							<div
								class="overflow-x-auto rounded-lg border border-white/20 bg-white/60 shadow-xl backdrop-blur-sm dark:border-gray-700/30 dark:bg-gray-900/60"
							>
								<table class="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
									<thead class="bg-gray-50 dark:bg-gray-800/50">
										<tr>
											<th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Trace ID</th>
											<th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Service</th>
											<th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Span</th>
											<th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Duration</th>
											<th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Cost</th>
											<th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Spans</th>
											<th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">Errors</th>
											<th scope="col" class="relative px-6 py-3"><span class="sr-only">Actions</span></th>
										</tr>
									</thead>
									<tbody class="bg-white dark:bg-gray-900/50 divide-y divide-gray-200 dark:divide-gray-700">
										{#each traces as trace}
											<tr class="hover:bg-gray-50 dark:hover:bg-gray-800/30 transition-colors duration-150">
												<td class="px-6 py-4 whitespace-nowrap text-sm font-mono text-gray-900 dark:text-gray-100">
													{trace.trace_id.substring(0, 8)}...
												</td>
												<td class="px-6 py-4 whitespace-nowrap text-sm text-gray-700 dark:text-gray-300">
													{trace.service_name}
												</td>
												<td class="px-6 py-4 whitespace-nowrap text-sm text-gray-700 dark:text-gray-300">
													{trace.span_name}
												</td>
												<td class="px-6 py-4 whitespace-nowrap text-sm text-gray-700 dark:text-gray-300">
													{formatDuration(trace.duration)}
												</td>
												<td class="px-6 py-4 whitespace-nowrap text-sm text-gray-700 dark:text-gray-300">
													{formatCost(trace.total_cost)}
												</td>
												<td class="px-6 py-4 whitespace-nowrap text-sm text-gray-700 dark:text-gray-300">
													{trace.span_count}
												</td>
												<td class="px-6 py-4 whitespace-nowrap text-sm">
													{#if trace.error_count > 0}
														<span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400">
															{trace.error_count}
														</span>
													{:else}
														<span class="text-gray-400">-</span>
													{/if}
												</td>
												<td class="px-6 py-4 whitespace-nowrap text-right text-sm font-medium space-x-2">
													<button
														on:click={() => openTraceDrawer(trace.trace_id)}
														class="text-primary hover:text-primary-dark dark:text-primary-light dark:hover:text-primary-light-dark"
													>
														View
													</button>
													<button
														on:click={() => openReplay(trace.trace_id)}
														class="text-green-600 hover:text-green-700 dark:text-green-400 dark:hover:text-green-500"
													>
														Replay
													</button>
												</td>
											</tr>
										{:else}
											<tr>
												<td colspan="8" class="px-6 py-4 whitespace-nowrap text-center text-sm text-gray-500 dark:text-gray-400">
													No traces found.
												</td>
											</tr>
										{/each}
									</tbody>
								</table>
							</div>

							<!-- Pagination -->
							<div class="flex justify-between items-center">
								<button
									on:click={() => handlePageChange(currentPage - 1)}
									disabled={currentPage === 1}
									class="px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed"
								>
									Previous
								</button>
								<span class="text-sm text-gray-700 dark:text-gray-300">
									Page {currentPage} of {totalPages}
								</span>
								<button
									on:click={() => handlePageChange(currentPage + 1)}
									disabled={currentPage >= totalPages}
									class="px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed"
								>
									Next
								</button>
							</div>
						</div>
					{:else if activeTab === 'overview'}
						<!-- Overview Tab: AgentOps 스타일 대시보드 -->
						<div class="space-y-6">
							<!-- Metrics Cards (AgentOps 스타일) -->
							<!-- 빈 상태에서도 기본값(0)으로 표시 -->
							<div class="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
									<!-- Total Events/Traces -->
									<div
										class="group relative overflow-hidden rounded-xl border border-gray-200/50 dark:border-gray-700/50 bg-white dark:bg-gray-800 p-6 shadow-lg hover:shadow-xl transition-all duration-200"
									>
										<div class="absolute top-0 right-0 w-32 h-32 bg-gradient-to-br from-blue-500/10 to-purple-500/10 rounded-full blur-3xl"></div>
										<div class="relative flex items-start justify-between">
											<div class="flex-1">
												<p class="text-sm font-medium text-gray-600 dark:text-gray-400 mb-2">Total Events</p>
												<p class="text-3xl font-bold text-gray-900 dark:text-gray-100">{formatNumber(metrics?.trace_count || 0)}</p>
											</div>
											<div class="flex-shrink-0">
												<div class="flex h-12 w-12 items-center justify-center rounded-lg bg-blue-50 dark:bg-blue-900/20">
													<svg class="h-6 w-6 text-blue-600 dark:text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
														<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
													</svg>
												</div>
											</div>
										</div>
									</div>

									<!-- Total Cost -->
									<div
										class="group relative overflow-hidden rounded-xl border border-gray-200/50 dark:border-gray-700/50 bg-white dark:bg-gray-800 p-6 shadow-lg hover:shadow-xl transition-all duration-200"
									>
										<div class="absolute top-0 right-0 w-32 h-32 bg-gradient-to-br from-green-500/10 to-emerald-500/10 rounded-full blur-3xl"></div>
										<div class="relative flex items-start justify-between">
											<div class="flex-1">
												<p class="text-sm font-medium text-gray-600 dark:text-gray-400 mb-2">Total Cost</p>
												<p class="text-3xl font-bold text-gray-900 dark:text-gray-100">{formatCost(metrics?.total_cost || 0)}</p>
											</div>
											<div class="flex-shrink-0">
												<div class="flex h-12 w-12 items-center justify-center rounded-lg bg-green-50 dark:bg-green-900/20">
													<svg class="h-6 w-6 text-green-600 dark:text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
														<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
													</svg>
												</div>
											</div>
										</div>
									</div>

									<!-- Avg Latency -->
									<div
										class="group relative overflow-hidden rounded-xl border border-gray-200/50 dark:border-gray-700/50 bg-white dark:bg-gray-800 p-6 shadow-lg hover:shadow-xl transition-all duration-200"
									>
										<div class="absolute top-0 right-0 w-32 h-32 bg-gradient-to-br from-orange-500/10 to-amber-500/10 rounded-full blur-3xl"></div>
										<div class="relative flex items-start justify-between">
											<div class="flex-1">
												<p class="text-sm font-medium text-gray-600 dark:text-gray-400 mb-2">Avg Latency</p>
												<p class="text-3xl font-bold text-gray-900 dark:text-gray-100">{formatDuration(metrics?.avg_duration || 0)}</p>
											</div>
											<div class="flex-shrink-0">
												<div class="flex h-12 w-12 items-center justify-center rounded-lg bg-orange-50 dark:bg-orange-900/20">
													<svg class="h-6 w-6 text-orange-600 dark:text-orange-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
														<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
													</svg>
												</div>
											</div>
										</div>
									</div>

									<!-- Error Rate -->
									<div
										class="group relative overflow-hidden rounded-xl border border-gray-200/50 dark:border-gray-700/50 bg-white dark:bg-gray-800 p-6 shadow-lg hover:shadow-xl transition-all duration-200"
									>
										<div class="absolute top-0 right-0 w-32 h-32 bg-gradient-to-br from-red-500/10 to-pink-500/10 rounded-full blur-3xl"></div>
										<div class="relative flex items-start justify-between">
											<div class="flex-1">
												<p class="text-sm font-medium text-gray-600 dark:text-gray-400 mb-2">Error Count</p>
												<p class="text-3xl font-bold text-red-600 dark:text-red-400">{metrics?.error_count || 0}</p>
												<p class="text-xs text-gray-500 dark:text-gray-500 mt-1">
													{metrics?.trace_count ? (((metrics.error_count || 0) / metrics.trace_count) * 100).toFixed(1) : '0.0'}% error rate
												</p>
											</div>
											<div class="flex-shrink-0">
												<div class="flex h-12 w-12 items-center justify-center rounded-lg bg-red-50 dark:bg-red-900/20">
													<svg class="h-6 w-6 text-red-600 dark:text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
														<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
													</svg>
												</div>
											</div>
										</div>
									</div>
								</div>

								<!-- Token Usage Metric (추가) -->
								<div class="grid gap-6 md:grid-cols-3">
									<!-- Total Tokens -->
									<div
										class="relative overflow-hidden rounded-xl border border-gray-200/50 dark:border-gray-700/50 bg-white dark:bg-gray-800 p-6 shadow-lg"
									>
										<div class="flex items-center justify-between mb-4">
											<h3 class="text-sm font-semibold text-gray-700 dark:text-gray-300">Token Usage</h3>
											<div class="flex h-10 w-10 items-center justify-center rounded-lg bg-purple-50 dark:bg-purple-900/20">
												<svg class="h-5 w-5 text-purple-600 dark:text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
													<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 12l3-3 3 3 4-4M8 21l4-4 4 4M3 4h18M4 4h16v12a1 1 0 01-1 1H5a1 1 0 01-1-1V4z" />
												</svg>
											</div>
										</div>
										<div class="space-y-2">
											<div class="flex items-baseline gap-2">
												<span class="text-2xl font-bold text-gray-900 dark:text-gray-100">
													{formatNumber(metrics?.total_tokens || 0)}
												</span>
												<span class="text-sm text-gray-500 dark:text-gray-500">tokens</span>
											</div>
											<p class="text-xs text-gray-500 dark:text-gray-500">Total tokens processed</p>
										</div>
									</div>

									<!-- Success Rate -->
									<div
										class="relative overflow-hidden rounded-xl border border-gray-200/50 dark:border-gray-700/50 bg-white dark:bg-gray-800 p-6 shadow-lg"
									>
										<div class="flex items-center justify-between mb-4">
											<h3 class="text-sm font-semibold text-gray-700 dark:text-gray-300">Success Rate</h3>
											<div class="flex h-10 w-10 items-center justify-center rounded-lg bg-teal-50 dark:bg-teal-900/20">
												<svg class="h-5 w-5 text-teal-600 dark:text-teal-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
													<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
												</svg>
											</div>
										</div>
										<div class="space-y-2">
											<div class="flex items-baseline gap-2">
												<span class="text-2xl font-bold text-teal-600 dark:text-teal-400">
													{metrics?.trace_count ? ((((metrics.trace_count || 0) - (metrics.error_count || 0)) / metrics.trace_count) * 100).toFixed(1) : '100.0'}%
												</span>
											</div>
											<p class="text-xs text-gray-500 dark:text-gray-500">
												{formatNumber((metrics?.trace_count || 0) - (metrics?.error_count || 0))} / {formatNumber(metrics?.trace_count || 0)} successful
											</p>
										</div>
									</div>

									<!-- Avg Cost per Request -->
									<div
										class="relative overflow-hidden rounded-xl border border-gray-200/50 dark:border-gray-700/50 bg-white dark:bg-gray-800 p-6 shadow-lg"
									>
										<div class="flex items-center justify-between mb-4">
											<h3 class="text-sm font-semibold text-gray-700 dark:text-gray-300">Avg Cost/Request</h3>
											<div class="flex h-10 w-10 items-center justify-center rounded-lg bg-indigo-50 dark:bg-indigo-900/20">
												<svg class="h-5 w-5 text-indigo-600 dark:text-indigo-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
													<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
												</svg>
											</div>
										</div>
										<div class="space-y-2">
											<div class="flex items-baseline gap-2">
												<span class="text-2xl font-bold text-gray-900 dark:text-gray-100">
													{formatCost(metrics?.trace_count ? (metrics.total_cost || 0) / metrics.trace_count : 0)}
												</span>
											</div>
											<p class="text-xs text-gray-500 dark:text-gray-500">Per event cost</p>
										</div>
									</div>
								</div>

							<!-- Charts -->
							<div class="grid gap-6 lg:grid-cols-2">
								<div
									class="rounded-xl border border-gray-200/50 dark:border-gray-700/50 bg-white dark:bg-gray-800 p-6 shadow-lg"
								>
									<CostChart {costData} title="Cost Trend (Last 7 Days)" interval="day" />
								</div>
								<div
									class="rounded-xl border border-gray-200/50 dark:border-gray-700/50 bg-white dark:bg-gray-800 p-6 shadow-lg"
								>
									<TokenChart {tokenData} title="Token Usage (Last 7 Days)" interval="day" />
								</div>
							</div>
							
							<!-- Agents Section -->
							<div class="space-y-4">
								<div class="flex items-center justify-between">
									<h2 class="text-xl font-semibold text-gray-900 dark:text-gray-100">
										Agent Usage
									</h2>
									<span class="text-sm text-gray-500 dark:text-gray-400">
										{agentUsageStats.length} agents
									</span>
								</div>
								
								{#if agentUsageStats.length === 0}
									<div class="rounded-xl border border-gray-200/50 dark:border-gray-700/50 bg-white dark:bg-gray-800 p-12 shadow-lg text-center">
										<svg class="w-16 h-16 mx-auto text-gray-400 dark:text-gray-600 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
											<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
										</svg>
										<p class="text-gray-600 dark:text-gray-400">No agents found</p>
										<p class="text-sm text-gray-500 dark:text-gray-500 mt-2">
											Agent usage data will appear here once agents start processing requests.
										</p>
									</div>
								{:else}
									<div class="rounded-xl border border-gray-200/50 dark:border-gray-700/50 bg-white dark:bg-gray-800 shadow-lg overflow-hidden">
										<div class="overflow-x-auto">
											<table class="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
												<thead class="bg-gray-50 dark:bg-gray-900">
													<tr>
														<th scope="col" class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
															Agent Name
														</th>
														<th scope="col" class="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
															Events
														</th>
														<th scope="col" class="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
															Tokens
														</th>
														<th scope="col" class="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
															Cost
														</th>
														<th scope="col" class="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
															Avg Latency
														</th>
														<th scope="col" class="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
															Errors
														</th>
														<th scope="col" class="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
															Success Rate
														</th>
													</tr>
												</thead>
												<tbody class="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
													{#each agentUsageStats as agent}
														<tr class="hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors">
															<td class="px-6 py-4 whitespace-nowrap">
																<div class="flex items-center">
																	<div class="flex-shrink-0 h-8 w-8 rounded-lg bg-blue-50 dark:bg-blue-900/20 flex items-center justify-center">
																		<svg class="h-4 w-4 text-blue-600 dark:text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
																			<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z" />
																		</svg>
																	</div>
																	<span class="ml-3 text-sm font-medium text-gray-900 dark:text-gray-100">{agent.agent_name}</span>
																</div>
															</td>
															<td class="px-6 py-4 whitespace-nowrap text-right text-sm text-gray-900 dark:text-gray-100">
																{formatNumber(agent.event_count)}
															</td>
															<td class="px-6 py-4 whitespace-nowrap text-right text-sm text-gray-900 dark:text-gray-100">
																{formatNumber(agent.total_tokens)}
															</td>
															<td class="px-6 py-4 whitespace-nowrap text-right text-sm font-medium text-gray-900 dark:text-gray-100">
																{formatCost(agent.total_cost)}
															</td>
															<td class="px-6 py-4 whitespace-nowrap text-right text-sm text-gray-900 dark:text-gray-100">
																{formatDuration(agent.avg_latency)}
															</td>
															<td class="px-6 py-4 whitespace-nowrap text-right text-sm">
																<span class="text-red-600 dark:text-red-400">{agent.error_count}</span>
															</td>
															<td class="px-6 py-4 whitespace-nowrap text-right text-sm">
																<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium {agent.success_rate >= 95 ? 'bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-400' : agent.success_rate >= 80 ? 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/20 dark:text-yellow-400' : 'bg-red-100 text-red-800 dark:bg-red-900/20 dark:text-red-400'}">
																	{agent.success_rate.toFixed(1)}%
																</span>
															</td>
														</tr>
													{/each}
												</tbody>
											</table>
										</div>
									</div>
								{/if}
							</div>
						</div>
					{:else if activeTab === 'replay'}
						<!-- Replay Tab -->
						<div>
							{#if replayTraceId}
								<ReplayPlayer traceId={replayTraceId} />
							{:else}
								<div
									class="rounded-lg border border-white/20 bg-white/60 dark:bg-gray-800/60 p-12 backdrop-blur-sm shadow-sm text-center"
								>
									<svg
										class="w-16 h-16 mx-auto text-gray-400 dark:text-gray-600"
										fill="none"
										stroke="currentColor"
										viewBox="0 0 24 24"
									>
										<path
											stroke-linecap="round"
											stroke-linejoin="round"
											stroke-width="2"
											d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"
										/>
										<path
											stroke-linecap="round"
											stroke-linejoin="round"
											stroke-width="2"
											d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
										/>
									</svg>
									<h3 class="mt-4 text-lg font-semibold text-gray-900 dark:text-gray-100">
										No Replay Selected
									</h3>
									<p class="mt-2 text-sm text-gray-600 dark:text-gray-400">
										Select a trace from the Traces tab to view its session replay.
									</p>
								</div>
							{/if}
						</div>
					{:else if activeTab === 'analytics'}
						<!-- Analytics Tab -->
						<div class="space-y-6">
							<!-- Performance Metrics -->
							<div
								class="rounded-lg border border-white/20 bg-white/60 dark:bg-gray-800/60 p-6 backdrop-blur-sm shadow-sm"
							>
								<PerformanceChart {performanceData} title="Latency Distribution" />
							</div>

							<!-- Agent Flow Graph -->
							{#if agentFlowGraph}
								<div
									class="rounded-lg border border-white/20 bg-white/60 dark:bg-gray-800/60 p-6 backdrop-blur-sm shadow-sm"
								>
									<h3 class="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
										Agent Communication Flow
									</h3>
									<AgentFlowGraphComponent flowGraph={agentFlowGraph} />
								</div>
							{/if}
						</div>
					{/if}
				{/if}
			</div>
		{/if}
	</div>
</div>

<!-- Trace Drawer (Slide-out Panel) -->
<TraceDrawer traceId={selectedTraceId} onClose={closeTraceDrawer} />

<!-- Export Dialog -->
<ExportDialog bind:isOpen={showExportDialog} {projectId} />
