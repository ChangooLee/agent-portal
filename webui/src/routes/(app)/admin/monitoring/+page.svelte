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
		monitoringWS,
		type Trace,
		type Metrics
	} from '$lib/monitoring/api-client';
	import type {
		TraceFilters,
		FilterPreset,
		CostDataPoint,
		TokenDataPoint,
		PerformanceDataPoint,
		AgentFlowGraph,
		AgentUsageStats
	} from '$lib/monitoring/types';

	// Import all new components
	import TraceDrawer from '$lib/components/monitoring/TraceDrawer.svelte';
	import ReplayPlayer from '$lib/components/monitoring/ReplayPlayer.svelte';
	import CostChart from '$lib/components/monitoring/CostChart.svelte';
	import TokenChart from '$lib/components/monitoring/TokenChart.svelte';
	import PerformanceChart from '$lib/components/monitoring/PerformanceChart.svelte';
	import AgentFlowGraphComponent from '$lib/components/monitoring/AgentFlowGraph.svelte';
	import FilterPanel from '$lib/components/monitoring/FilterPanel.svelte';
	import ExportDialog from '$lib/components/monitoring/ExportDialog.svelte';

	// 모니터링 화면 전용 스타일
	import './styles.css';

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
	
	// Traces sub-tab state
	let tracesSubTab: 'agent' | 'llm' | 'all' = 'agent';
	
	// Filtered traces based on sub-tab
	$: filteredTraces = traces.filter(trace => {
		if (tracesSubTab === 'all') return true;
		if (tracesSubTab === 'agent') {
			// Agent traces: span_name contains 'agent' or service_name contains 'agent'
			const spanName = trace.span_name?.toLowerCase() || '';
			const serviceName = trace.service_name?.toLowerCase() || '';
			return spanName.includes('agent') || spanName.includes('text2sql') || 
			       serviceName.includes('agent') || spanName.includes('entry') ||
			       spanName.includes('analyze') || spanName.includes('generate') ||
			       spanName.includes('validate') || spanName.includes('execute') ||
			       spanName.includes('format') || spanName.includes('complete');
		}
		if (tracesSubTab === 'llm') {
			// LLM Call traces: span_name contains 'litellm' or 'chat' or 'completion'
			const spanName = trace.span_name?.toLowerCase() || '';
			const serviceName = trace.service_name?.toLowerCase() || '';
			return spanName.includes('litellm') || spanName.includes('chat_completion') ||
			       spanName.includes('llm') || serviceName.includes('litellm') ||
			       (trace.prompt_tokens && trace.prompt_tokens > 0);
		}
		return true;
	});

	// Metrics state
	let metrics: Metrics | null = null;

	// Analytics state
	let costData: CostDataPoint[] = [];
	let tokenData: TokenDataPoint[] = [];
	let performanceData: PerformanceDataPoint[] = [];
	let agentFlowGraph: AgentFlowGraph | null = null;
	
	// Agent Usage state
	let agentUsageStats: AgentUsageStats[] = [];
	let agentUsageStatsLoading: boolean = true; // 초기값을 true로 설정하여 로딩 상태 표시
	let agentUsageStatsError: string | null = null;

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

	// Project selection
	interface Project {
		id: string;
		name: string;
		description: string | null;
	}
	let projects: Project[] = [];
	let selectedProjectId = '8c59e361-3727-418c-bc68-086b69f7598b'; // Default project

	// Legacy alias for backward compatibility
	$: projectId = selectedProjectId;

	async function loadProjects() {
		try {
			const response = await fetch('/api/projects');
			if (response.ok) {
				const data = await response.json();
				projects = data.projects || [];
			}
		} catch (e) {
			console.error('Failed to load projects:', e);
			// Use default project if API fails
			projects = [{
				id: '8c59e361-3727-418c-bc68-086b69f7598b',
				name: 'Default Project',
				description: 'Default project for LLM monitoring'
			}];
		}
	}

	function handleProjectChange(event: Event) {
		const select = event.target as HTMLSelectElement;
		selectedProjectId = select.value;
		loadData();
	}

	onMount(async () => {
		// Load projects first
		await loadProjects();

		// WebSocket 실시간 업데이트
		monitoringWS.connect(selectedProjectId);
		monitoringWS.on('trace_new', handleNewTrace);
		monitoringWS.on('trace_update', handleTraceUpdate);

		// Load initial data
		await loadData();

		// Load saved filter presets from localStorage
		const savedPresets = localStorage.getItem('monitoring_filter_presets');
		if (savedPresets) {
			filterPresets = JSON.parse(savedPresets);
		}
	});

	onDestroy(() => {
		monitoringWS.disconnect();
	});

	async function loadData() {
		loading = true;
		error = null;

		try {
			if (activeTab === 'traces') {
				await loadTraces();
			} else if (activeTab === 'overview') {
				// 다른 데이터는 병렬로 로드
				await Promise.all([loadMetrics(), loadCostTrend(), loadTokenUsage()]);
				// Agent Usage는 독립적으로 로드 (에러가 발생해도 다른 데이터에 영향 없음)
				await loadAgentUsageStats().catch(err => {
					console.error('Failed to load agent usage stats:', err);
					// 에러는 loadAgentUsageStats() 내부에서 처리됨
				});
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
		agentUsageStatsLoading = true;
		agentUsageStatsError = null;
		
		try {
			agentUsageStats = await getAgentUsageStats({
				project_id: projectId,
				start_time: filters.start_time,
				end_time: filters.end_time
			});
		} catch (e: any) {
			console.error('Failed to load agent usage stats:', e);
			agentUsageStatsError = e.message || 'Failed to load agent usage stats';
			agentUsageStats = []; // 에러 발생 시 빈 배열로 초기화
		} finally {
			agentUsageStatsLoading = false;
		}
	}

	function handleApplyFilters(event: CustomEvent<TraceFilters>) {
		filters = event.detail;
		currentPage = 1;
		loadData();
	}

	function handleSavePreset(event: CustomEvent<FilterPreset>) {
		filterPresets = [...filterPresets, event.detail];
		localStorage.setItem('monitoring_filter_presets', JSON.stringify(filterPresets));
	}

	function handleDeletePreset(event: CustomEvent<string>) {
		filterPresets = filterPresets.filter((p) => p.id !== event.detail);
		localStorage.setItem('monitoring_filter_presets', JSON.stringify(filterPresets));
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
		if (cost === 0) return '$0.000000';
		if (cost < 0.01) return `$${cost.toFixed(6)}`;
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

<div class="min-h-full bg-gray-950 text-slate-50">
	{#if $user?.role !== 'admin'}
		<div class="text-red-500 p-6">
			{$i18n.t('Access Denied: Only administrators can view this page.')}
		</div>
	{:else}
		<!-- Hero Section -->
		<div class="relative overflow-hidden border-b border-slate-800/50">
			<div class="absolute inset-0 bg-gradient-to-br from-cyan-600/5 via-transparent to-teal-600/5"></div>
			<div class="absolute inset-0 bg-[linear-gradient(rgba(6,182,212,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(6,182,212,0.03)_1px,transparent_1px)] bg-[size:64px_64px]"></div>
			
			<div class="relative px-6 py-8">
				<div class="text-center mb-4">
					<h1 class="text-3xl md:text-4xl font-bold text-white mb-3">
						📊 Monitoring
					</h1>
					<p class="text-base text-cyan-200/80 mb-6">
						실시간 에이전트 실행 모니터링, 비용 추적, 세션 리플레이
					</p>
					<div class="flex items-center justify-center gap-3">
						<button
							on:click={() => (showFilters = !showFilters)}
							class="px-4 py-2 rounded-lg bg-slate-800/80 hover:bg-slate-700 text-cyan-200 hover:-translate-y-0.5 transition-all duration-300 flex items-center gap-2"
						>
							<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z" />
							</svg>
							Filters
						</button>
						<button
							on:click={() => (showExportDialog = true)}
							class="px-4 py-2 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-white hover:-translate-y-0.5 transition-all duration-300 flex items-center gap-2 shadow-lg shadow-cyan-500/25"
						>
							<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
							</svg>
							Export
						</button>
					</div>
				</div>
			</div>
		</div>
		
		<div class="px-6 py-8 space-y-6">

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

		<!-- Tab Navigation (순서: Overview → Analytics → Traces → Replay) -->
		<div class="flex gap-2 overflow-x-auto">
			<button
				class="px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 whitespace-nowrap {activeTab === 'overview'
					? 'bg-cyan-600 text-white shadow-sm'
					: 'text-slate-300 hover:bg-slate-800/80 hover:text-white'}"
				on:click={() => {
					activeTab = 'overview';
					loadData();
				}}
			>
				📈 Overview
			</button>
			<button
				class="px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 whitespace-nowrap {activeTab === 'analytics'
					? 'bg-cyan-600 text-white shadow-sm'
					: 'text-slate-300 hover:bg-slate-800/80 hover:text-white'}"
				on:click={() => {
					activeTab = 'analytics';
					loadData();
				}}
			>
				🎯 Analytics
			</button>
			<button
				class="px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 whitespace-nowrap {activeTab === 'traces'
					? 'bg-cyan-600 text-white shadow-sm'
					: 'text-slate-300 hover:bg-slate-800/80 hover:text-white'}"
				on:click={() => {
					activeTab = 'traces';
					loadData();
				}}
			>
				📊 Traces
			</button>
			<button
				class="px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 whitespace-nowrap {activeTab === 'replay'
					? 'bg-cyan-600 text-white shadow-sm'
					: 'text-slate-300 hover:bg-slate-800/80 hover:text-white'}"
				on:click={() => {
					activeTab = 'replay';
				}}
			>
				▶️ Replay
			</button>
		</div>

			<!-- Content Area -->
			<div class="flex-1">
				{#if loading}
					<div class="flex items-center justify-center h-64">
						<div class="flex flex-col items-center gap-3">
							<div class="loading loading-spinner loading-lg text-cyan-400"></div>
							<p class="text-slate-400">Loading data...</p>
						</div>
					</div>
				{:else if error}
					<div
						class="bg-red-500/20 border border-red-500/30 rounded-lg p-6"
					>
						<p class="text-red-400 font-medium">Error loading data</p>
						<p class="text-red-300 text-sm mt-1">{error}</p>
						<button
							on:click={loadData}
							class="mt-4 px-4 py-2 rounded-lg bg-red-600 text-white hover:bg-red-700 transition-colors"
						>
							Retry
						</button>
					</div>
				{:else}
					<!-- Traces Tab (AgentOps 스타일) -->
					{#if activeTab === 'traces'}
						<div class="space-y-4 monitoring-page">
							<!-- Page Title with Sub-tabs -->
							<div class="mt-2 flex items-center justify-between">
								<span class="text-2xl font-bold text-white">Traces</span>
								
								<!-- Sub-tabs -->
								<div class="flex gap-1 p-1 bg-slate-800/80 rounded-lg">
									<button
										class="px-4 py-1.5 text-sm font-medium rounded-md transition-all {tracesSubTab === 'agent'
											? 'bg-cyan-600 text-white shadow-sm'
											: 'text-slate-300 hover:text-white hover:bg-slate-700/50'}"
										on:click={() => tracesSubTab = 'agent'}
									>
										🤖 Agent
										<span class="ml-1 px-1.5 py-0.5 text-xs rounded-full bg-cyan-500/20 text-cyan-400 border border-cyan-500/30">
											{traces.filter(t => {
												const s = t.span_name?.toLowerCase() || '';
												const svc = t.service_name?.toLowerCase() || '';
												return s.includes('agent') || s.includes('text2sql') || svc.includes('agent') || 
												       s.includes('entry') || s.includes('analyze') || s.includes('generate') ||
												       s.includes('validate') || s.includes('execute') || s.includes('format') || s.includes('complete');
											}).length}
										</span>
									</button>
									<button
										class="px-4 py-1.5 text-sm font-medium rounded-md transition-all {tracesSubTab === 'llm'
											? 'bg-cyan-600 text-white shadow-sm'
											: 'text-slate-300 hover:text-white hover:bg-slate-700/50'}"
										on:click={() => tracesSubTab = 'llm'}
									>
										💬 LLM Call
										<span class="ml-1 px-1.5 py-0.5 text-xs rounded-full bg-cyan-500/20 text-cyan-400 border border-cyan-500/30">
											{traces.filter(t => {
												const s = t.span_name?.toLowerCase() || '';
												const svc = t.service_name?.toLowerCase() || '';
												return s.includes('litellm') || s.includes('chat_completion') || s.includes('llm') || 
												       svc.includes('litellm') || (t.prompt_tokens && t.prompt_tokens > 0);
											}).length}
										</span>
									</button>
									<button
										class="px-4 py-1.5 text-sm font-medium rounded-md transition-all {tracesSubTab === 'all'
											? 'bg-cyan-600 text-white shadow-sm'
											: 'text-slate-300 hover:text-white hover:bg-slate-700/50'}"
										on:click={() => tracesSubTab = 'all'}
									>
										📋 All
										<span class="ml-1 px-1.5 py-0.5 text-xs rounded-full bg-slate-500/20 text-slate-400 border border-slate-500/30">
											{traces.length}
										</span>
									</button>
								</div>
							</div>

							<!-- Traces Table (표준 스타일) -->
							<div class="overflow-x-auto">
								<table class="w-full">
									<thead class="bg-slate-800/50 border-b border-slate-700/50">
										<tr>
											<th scope="col" class="px-6 py-3 text-left text-xs font-medium text-white uppercase tracking-wider">Trace ID</th>
											<th scope="col" class="px-6 py-3 text-left text-xs font-medium text-white uppercase tracking-wider">Service</th>
											<th scope="col" class="px-6 py-3 text-left text-xs font-medium text-white uppercase tracking-wider">Span</th>
											<th scope="col" class="px-6 py-3 text-left text-xs font-medium text-white uppercase tracking-wider">Status</th>
											<th scope="col" class="px-6 py-3 text-left text-xs font-medium text-white uppercase tracking-wider">Duration</th>
											<th scope="col" class="px-6 py-3 text-left text-xs font-medium text-white uppercase tracking-wider">Tokens</th>
											<th scope="col" class="px-6 py-3 text-left text-xs font-medium text-white uppercase tracking-wider">Cost</th>
											<th scope="col" class="px-6 py-3 text-left text-xs font-medium text-white uppercase tracking-wider">Errors</th>
											<th scope="col" class="relative px-6 py-3"><span class="sr-only">Actions</span></th>
										</tr>
									</thead>
									<tbody class="divide-y divide-slate-800/50">
										{#each filteredTraces as trace}
											{@const maxDuration = 120000}
											{@const durationPercent = Math.min((trace.duration / maxDuration) * 100, 100)}
											{@const barColor = trace.duration >= 60000 ? 'bg-amber-400/60' : trace.duration >= 30000 ? 'bg-slate-400/60' : 'bg-emerald-400/60'}
											<tr class="border-b border-slate-800/50 hover:bg-slate-800/80 hover:border-cyan-500/50 transition-all duration-200 cursor-pointer">
												<td class="px-6 py-4 whitespace-nowrap text-sm font-mono text-white font-medium">
													{trace.trace_id.substring(0, 8)}...
												</td>
												<td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-white">
													{trace.service_name}
												</td>
												<td class="px-6 py-4 whitespace-nowrap text-sm text-slate-300">
													{trace.span_name}
												</td>
												<td class="px-6 py-4 whitespace-nowrap text-sm font-medium">
													{#if Number(trace.error_count) > 0}
														<span class="bg-red-500/20 text-red-400 border border-red-500/30 px-2 py-0.5 rounded-full text-xs font-medium">ERROR</span>
													{:else}
														<span class="bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 px-2 py-0.5 rounded-full text-xs font-medium">OK</span>
													{/if}
												</td>
												<td class="px-6 py-4 whitespace-nowrap text-sm text-slate-300">
													<div class="flex items-center gap-2">
														<!-- Duration Progress Bar -->
														<div class="h-2 w-16 rounded-full bg-slate-700/30">
															<div
																class="{barColor} h-2 rounded-full transition-all duration-200"
																style="width: {Math.max(durationPercent, 10)}%"
															></div>
														</div>
														<span>{formatDuration(trace.duration)}</span>
													</div>
												</td>
												<td class="px-6 py-4 whitespace-nowrap text-sm text-slate-300">
													{#if trace.prompt_tokens || trace.completion_tokens}
														<span class="text-cyan-400">{trace.prompt_tokens || 0}</span>
														<span class="text-slate-500 mx-1">/</span>
														<span class="text-emerald-400">{trace.completion_tokens || 0}</span>
													{:else}
														<span class="text-slate-500">-</span>
													{/if}
												</td>
												<td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-white">
													{formatCost(trace.total_cost)}
												</td>
												<td class="px-6 py-4 whitespace-nowrap text-sm">
													{#if trace.error_count > 0}
														<span class="px-2.5 py-0.5 inline-flex text-xs font-medium rounded-full bg-red-500/20 text-red-400 border border-red-500/30">
															{trace.error_count}
														</span>
													{:else}
														<span class="text-slate-500">-</span>
													{/if}
												</td>
												<td class="px-6 py-4 whitespace-nowrap text-right text-sm font-medium space-x-2">
													<button
														on:click={() => openTraceDrawer(trace.trace_id)}
														class="text-cyan-400 hover:text-cyan-300 transition-colors"
													>
														View
													</button>
													<button
														on:click={() => openReplay(trace.trace_id)}
														class="text-emerald-400 hover:text-emerald-300 transition-colors"
													>
														Replay
													</button>
												</td>
											</tr>
										{:else}
											<tr>
												<td colspan="9" class="px-6 py-12 whitespace-nowrap text-center text-sm text-slate-400">
													<svg class="w-16 h-16 mx-auto text-slate-500 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
														<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
													</svg>
													<p class="font-medium text-white">No {tracesSubTab === 'agent' ? 'agent' : tracesSubTab === 'llm' ? 'LLM call' : ''} traces found.</p>
													<p class="text-xs mt-2 text-slate-400">{tracesSubTab === 'all' ? 'Traces will appear here once agents start processing requests.' : 'Try switching to "All" tab to see all traces.'}</p>
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
									class="px-4 py-2 rounded-lg border border-slate-700/50 bg-slate-800/80 text-slate-300 hover:bg-slate-700/80 hover:text-white disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200"
								>
									Previous
								</button>
								<span class="text-sm text-slate-300">
									Page {currentPage} of {totalPages}
								</span>
								<button
									on:click={() => handlePageChange(currentPage + 1)}
									disabled={currentPage >= totalPages}
									class="px-4 py-2 rounded-lg border border-slate-700/50 bg-slate-800/80 text-slate-300 hover:bg-slate-700/80 hover:text-white disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200"
								>
									Next
								</button>
							</div>
						</div>
					{:else if activeTab === 'overview'}
						<!-- Overview Tab: 표준 스타일 대시보드 -->
						<div class="space-y-6">
							<!-- Page Title -->
							<div class="mt-2 flex items-center gap-2">
								<span class="text-2xl font-bold text-white">Overview</span>
							</div>

							<!-- Metrics Cards (표준 스타일) -->
							<div class="grid gap-4 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-5">
								<!-- Total Cost -->
								<div class="bg-slate-900/80 border border-slate-800/50 rounded-xl p-6 shadow-lg shadow-black/20 hover:shadow-xl hover:shadow-black/30 hover:bg-slate-800/80 hover:border-cyan-500/50 hover:-translate-y-1 transition-all duration-300">
									<div class="text-sm text-slate-400 mb-2">Total Cost</div>
									<div class="text-2xl font-bold text-white">
										{formatCost(metrics?.total_cost || 0)}
									</div>
								</div>

								<!-- LLM Calls -->
								<div class="bg-slate-900/80 border border-slate-800/50 rounded-xl p-6 shadow-lg shadow-black/20 hover:shadow-xl hover:shadow-black/30 hover:bg-slate-800/80 hover:border-cyan-500/50 hover:-translate-y-1 transition-all duration-300">
									<div class="text-sm text-slate-400 mb-2">🤖 LLM Calls</div>
									<div class="text-2xl font-bold text-cyan-400">
										{formatNumber(metrics?.llm_call_count || 0)}
									</div>
								</div>

								<!-- Agent Calls -->
								<div class="bg-slate-900/80 border border-slate-800/50 rounded-xl p-6 shadow-lg shadow-black/20 hover:shadow-xl hover:shadow-black/30 hover:bg-slate-800/80 hover:border-cyan-500/50 hover:-translate-y-1 transition-all duration-300">
									<div class="text-sm text-slate-400 mb-2">🔧 Agent Calls</div>
									<div class="text-2xl font-bold text-emerald-400">
										{formatNumber(metrics?.agent_call_count || 0)}
									</div>
								</div>

								<!-- Avg Latency -->
								<div class="bg-slate-900/80 border border-slate-800/50 rounded-xl p-6 shadow-lg shadow-black/20 hover:shadow-xl hover:shadow-black/30 hover:bg-slate-800/80 hover:border-cyan-500/50 hover:-translate-y-1 transition-all duration-300">
									<div class="text-sm text-slate-400 mb-2">Avg Latency</div>
									<div class="text-2xl font-bold text-white">
										{formatDuration(metrics?.avg_duration || 0)}
									</div>
								</div>

								<!-- Fail Rate (Error Rate) -->
								<div class="bg-slate-900/80 border border-slate-800/50 rounded-xl p-6 shadow-lg shadow-black/20 hover:shadow-xl hover:shadow-black/30 hover:bg-slate-800/80 hover:border-cyan-500/50 hover:-translate-y-1 transition-all duration-300">
									<div class="text-sm text-slate-400 mb-2">Fail Rate</div>
									<div class="text-2xl font-bold text-white">
										{metrics?.trace_count ? (((metrics.error_count || 0) / metrics.trace_count) * 100).toFixed(1) : '0.0'}%
									</div>
								</div>
							</div>

							<!-- Separator -->
							<div class="pt-3">
								<hr class="border-slate-800/50" />
							</div>

							<!-- Analytics Section -->
							<div class="flex justify-between pt-8">
								<div class="flex items-center gap-2">
									<div class="text-2xl font-bold text-white">Analytics</div>
								</div>
							</div>

							<!-- Charts (표준 스타일 컨테이너) -->
							<div class="grid gap-4 lg:grid-cols-2">
								<div class="bg-slate-900/80 border border-slate-800/50 rounded-xl p-6 shadow-lg shadow-black/20">
									<CostChart {costData} title="Cost Trend (Last 7 Days)" interval="day" />
								</div>
								<div class="bg-slate-900/80 border border-slate-800/50 rounded-xl p-6 shadow-lg shadow-black/20">
									<TokenChart {tokenData} title="Token Usage (Last 7 Days)" interval="day" />
								</div>
							</div>
							
							<!-- Agents Section (항상 표시) -->
							<div class="space-y-4">
								<div class="flex items-center justify-between">
									<h2 class="text-xl font-bold text-white">
										Agent Usage
									</h2>
									{#if !agentUsageStatsLoading && !agentUsageStatsError}
										<span class="text-sm text-slate-400">
											{agentUsageStats.length} agents
										</span>
									{/if}
								</div>
								
								{#if agentUsageStatsLoading}
									<!-- 로딩 상태 -->
									<div class="bg-slate-800/50 border border-slate-700/50 rounded-xl p-12 text-center">
										<div class="flex flex-col items-center gap-3">
											<div class="loading loading-spinner loading-lg text-cyan-400"></div>
											<p class="text-slate-400">Loading agent usage data...</p>
										</div>
									</div>
								{:else if agentUsageStatsError}
									<!-- 에러 상태 -->
									<div class="bg-red-500/20 border border-red-500/30 rounded-xl p-12 text-center">
										<svg class="w-16 h-16 mx-auto text-red-400 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
											<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
										</svg>
										<p class="text-red-400 font-medium mb-2">Failed to load agent usage data</p>
										<p class="text-sm text-red-300 mb-4">{agentUsageStatsError}</p>
										<button
											on:click={loadAgentUsageStats}
											class="px-4 py-2 rounded-lg bg-red-600 text-white hover:bg-red-700 transition-colors"
										>
											Retry
										</button>
									</div>
								{:else if agentUsageStats.length === 0}
									<!-- 빈 상태 -->
									<div class="bg-slate-800/50 border border-slate-700/50 rounded-xl p-12 text-center">
										<svg class="w-16 h-16 mx-auto text-slate-500 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
											<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
										</svg>
										<p class="text-slate-300">No agents found</p>
										<p class="text-sm text-slate-400 mt-2">
											Agent usage data will appear here once agents start processing requests.
										</p>
									</div>
								{:else}
									<div class="bg-slate-900/80 border border-slate-800/50 rounded-xl shadow-lg overflow-hidden">
										<div class="overflow-x-auto">
											<table class="w-full">
												<thead class="bg-slate-800/50 border-b border-slate-700/50">
													<tr>
														<th scope="col" class="px-6 py-3 text-left text-xs font-medium text-white uppercase tracking-wider">
															Agent Name
														</th>
														<th scope="col" class="px-6 py-3 text-right text-xs font-medium text-white uppercase tracking-wider">
															Events
														</th>
														<th scope="col" class="px-6 py-3 text-right text-xs font-medium text-white uppercase tracking-wider">
															Tokens
														</th>
														<th scope="col" class="px-6 py-3 text-right text-xs font-medium text-white uppercase tracking-wider">
															Cost
														</th>
														<th scope="col" class="px-6 py-3 text-right text-xs font-medium text-white uppercase tracking-wider">
															Avg Latency
														</th>
														<th scope="col" class="px-6 py-3 text-right text-xs font-medium text-white uppercase tracking-wider">
															Errors
														</th>
														<th scope="col" class="px-6 py-3 text-right text-xs font-medium text-white uppercase tracking-wider">
															Success Rate
														</th>
														<th scope="col" class="px-6 py-3 text-center text-xs font-medium text-white uppercase tracking-wider">
															Actions
														</th>
													</tr>
												</thead>
												<tbody class="divide-y divide-slate-800/50">
													{#each agentUsageStats as agent}
														<tr class="border-b border-slate-800/50 hover:bg-slate-800/80 hover:border-cyan-500/50 transition-all duration-200">
															<td class="px-6 py-4 whitespace-nowrap">
																<div class="flex items-center">
																	<div class="flex-shrink-0 h-8 w-8 rounded-lg bg-cyan-500/20 flex items-center justify-center">
																		<svg class="h-4 w-4 text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
																			<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z" />
																		</svg>
																	</div>
																	<span class="ml-3 text-sm font-medium text-white">{agent.agent_name}</span>
																</div>
															</td>
															<td class="px-6 py-4 whitespace-nowrap text-right text-sm text-white">
																{formatNumber(agent.event_count)}
															</td>
															<td class="px-6 py-4 whitespace-nowrap text-right text-sm text-white">
																{formatNumber(agent.total_tokens)}
															</td>
															<td class="px-6 py-4 whitespace-nowrap text-right text-sm font-medium text-white">
																{formatCost(agent.total_cost)}
															</td>
															<td class="px-6 py-4 whitespace-nowrap text-right text-sm text-white">
																{formatDuration(agent.avg_latency)}
															</td>
															<td class="px-6 py-4 whitespace-nowrap text-right text-sm">
																<span class="text-red-400">{agent.error_count}</span>
															</td>
															<td class="px-6 py-4 whitespace-nowrap text-right text-sm">
																<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium {agent.success_rate >= 95 ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' : agent.success_rate >= 80 ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30' : 'bg-red-500/20 text-red-400 border border-red-500/30'}">
																	{agent.success_rate.toFixed(1)}%
																</span>
															</td>
															<td class="px-6 py-4 whitespace-nowrap text-center text-sm">
																<a 
																	href="/admin/monitoring/agents/{agent.agent_id || agent.agent_name}" 
																	class="inline-flex items-center px-3 py-1 text-xs font-medium text-cyan-400 hover:text-cyan-300 border border-cyan-500/30 rounded-lg hover:bg-cyan-500/20 transition-colors"
																>
																	<svg class="w-3 h-3 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
																		<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
																	</svg>
																	Details
																</a>
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
						<!-- Replay Tab (표준 스타일) -->
						<div>
							<!-- Page Title -->
							<div class="mt-2 flex items-center gap-2 mb-6">
								<span class="text-2xl font-bold text-white">Replay</span>
							</div>

							{#if replayTraceId}
								<div class="bg-slate-900/80 border border-slate-800/50 rounded-xl p-6 shadow-lg shadow-black/20">
									<ReplayPlayer traceId={replayTraceId} />
								</div>
							{:else}
								<div class="bg-slate-800/50 border border-slate-700/50 rounded-xl p-12 text-center">
									<svg
										class="w-16 h-16 mx-auto text-slate-500 mb-4"
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
									<h3 class="text-lg font-semibold text-white">
										No Replay Selected
									</h3>
									<p class="mt-2 text-sm text-slate-400">
										Select a trace from the Traces tab to view its session replay.
									</p>
								</div>
							{/if}
						</div>
					{:else if activeTab === 'analytics'}
						<!-- Analytics Tab (표준 스타일) -->
						<div class="space-y-6">
							<!-- Page Title -->
							<div class="mt-2 flex items-center gap-2">
								<span class="text-2xl font-bold text-white">Analytics</span>
							</div>

							<!-- Performance Metrics (표준 스타일) -->
							<div class="bg-slate-900/80 border border-slate-800/50 rounded-xl p-6 shadow-lg shadow-black/20">
								<PerformanceChart {performanceData} title="Latency Distribution" />
							</div>

							<!-- Agent Flow Graph (표준 스타일) -->
							{#if agentFlowGraph}
								<div class="bg-slate-900/80 border border-slate-800/50 rounded-xl p-6 shadow-lg shadow-black/20">
									<h3 class="text-lg font-bold mb-4 text-white">
										Agent Communication Flow
									</h3>
									<AgentFlowGraphComponent flowGraph={agentFlowGraph} />
								</div>
							{:else}
								<div class="bg-slate-800/50 border border-slate-700/50 rounded-xl p-12 text-center">
									<svg class="w-16 h-16 mx-auto text-slate-500 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
										<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
									</svg>
									<h3 class="text-lg font-semibold text-white mb-2">
										No Agent Flow Data
									</h3>
									<p class="text-sm text-slate-400">
										Agent communication flow data will appear here once agents start processing requests.
									</p>
								</div>
							{/if}
						</div>
					{/if}
				{/if}
			</div>
		</div>
	{/if}
</div>

<!-- Trace Drawer (Slide-out Panel) -->
<TraceDrawer traceId={selectedTraceId} onClose={closeTraceDrawer} />

<!-- Export Dialog -->
<ExportDialog bind:isOpen={showExportDialog} {projectId} />
