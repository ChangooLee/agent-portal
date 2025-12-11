<script lang="ts">
	import { page } from '$app/stores';
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	
	// Get agent_id from URL
	$: agentId = $page.params.agent_id;
	
	interface AgentMetrics {
		trace_count: number;
		span_count: number;
		total_tokens: number;
		total_cost: number;
		avg_latency_ms: number;
		p50_latency_ms: number;
		p95_latency_ms: number;
		error_count: number;
		success_rate: number;
	}
	
	interface TraceItem {
		trace_id: string;
		span_name: string;
		duration_ms: number;
		status: string;
		timestamp: string;
		agent_name: string;
	}
	
	interface TrendItem {
		hour: string;
		call_count: number;
		error_count: number;
	}
	
	interface AgentDetail {
		agent_id: string;
		metrics: AgentMetrics;
		traces: TraceItem[];
		trend: TrendItem[];
	}
	
	let loading = true;
	let error = '';
	let agentDetail: AgentDetail | null = null;
	
	// Date range (last 24 hours by default)
	let startTime = new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString();
	let endTime = new Date().toISOString();
	
	async function loadAgentDetail() {
		loading = true;
		error = '';
		
		try {
			const params = new URLSearchParams({
				start_time: startTime,
				end_time: endTime
			});
			
			const response = await fetch(`/api/monitoring/agents/${agentId}/detail?${params}`);
			
			if (!response.ok) {
				throw new Error(`Failed to fetch agent detail: ${response.statusText}`);
			}
			
			agentDetail = await response.json();
		} catch (e) {
			error = e instanceof Error ? e.message : 'Unknown error';
		} finally {
			loading = false;
		}
	}
	
	function formatNumber(num: number): string {
		if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
		if (num >= 1000) return (num / 1000).toFixed(1) + 'K';
		return num.toString();
	}
	
	function formatCost(cost: number): string {
		if (cost < 0.01) return '$' + cost.toFixed(6);
		if (cost < 1) return '$' + cost.toFixed(4);
		return '$' + cost.toFixed(2);
	}
	
	function formatDuration(ms: number): string {
		if (ms < 1000) return ms.toFixed(0) + 'ms';
		return (ms / 1000).toFixed(2) + 's';
	}
	
	function formatDate(isoString: string): string {
		return new Date(isoString).toLocaleString();
	}
	
	onMount(() => {
		loadAgentDetail();
	});
</script>

<svelte:head>
	<title>Agent Detail - {agentId}</title>
</svelte:head>

<div class="min-h-screen bg-gradient-to-br from-slate-50 via-blue-50/30 to-slate-100 dark:from-gray-900 dark:via-gray-800/50 dark:to-gray-900 p-6">
	<!-- Header -->
	<div class="mb-6">
		<button 
			on:click={() => goto('/operate/monitoring')}
			class="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white mb-4"
		>
			<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
			</svg>
			Back to Monitoring
		</button>
		
		<div class="bg-white/60 dark:bg-gray-800/60 backdrop-blur-sm rounded-2xl border border-white/20 dark:border-gray-700/20 shadow-sm p-6">
			<div class="flex items-center justify-between">
				<div class="flex items-center gap-4">
					<div class="h-12 w-12 rounded-xl bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center">
						<svg class="h-6 w-6 text-blue-600 dark:text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z" />
						</svg>
					</div>
					<div>
						<h1 class="text-2xl font-bold text-gray-900 dark:text-white">Agent Detail</h1>
						<p class="text-sm text-gray-500 dark:text-gray-400">{agentId}</p>
					</div>
				</div>
				
				<button 
					on:click={loadAgentDetail}
					class="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
				>
					<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
					</svg>
					Refresh
				</button>
			</div>
		</div>
	</div>
	
	{#if loading}
		<div class="flex items-center justify-center h-64">
			<div class="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
		</div>
	{:else if error}
		<div class="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl p-6 text-center">
			<p class="text-red-600 dark:text-red-400">{error}</p>
		</div>
	{:else if agentDetail}
		<!-- Metrics Cards -->
		<div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
			<div class="bg-white/60 dark:bg-gray-800/60 backdrop-blur-sm rounded-xl border border-white/20 dark:border-gray-700/20 p-4">
				<p class="text-sm text-gray-500 dark:text-gray-400">Total Traces</p>
				<p class="text-2xl font-bold text-gray-900 dark:text-white">{formatNumber(agentDetail.metrics.trace_count)}</p>
			</div>
			
			<div class="bg-white/60 dark:bg-gray-800/60 backdrop-blur-sm rounded-xl border border-white/20 dark:border-gray-700/20 p-4">
				<p class="text-sm text-gray-500 dark:text-gray-400">Total Tokens</p>
				<p class="text-2xl font-bold text-gray-900 dark:text-white">{formatNumber(agentDetail.metrics.total_tokens)}</p>
			</div>
			
			<div class="bg-white/60 dark:bg-gray-800/60 backdrop-blur-sm rounded-xl border border-white/20 dark:border-gray-700/20 p-4">
				<p class="text-sm text-gray-500 dark:text-gray-400">Total Cost</p>
				<p class="text-2xl font-bold text-gray-900 dark:text-white">{formatCost(agentDetail.metrics.total_cost)}</p>
			</div>
			
			<div class="bg-white/60 dark:bg-gray-800/60 backdrop-blur-sm rounded-xl border border-white/20 dark:border-gray-700/20 p-4">
				<p class="text-sm text-gray-500 dark:text-gray-400">Success Rate</p>
				<p class="text-2xl font-bold {agentDetail.metrics.success_rate >= 95 ? 'text-green-600' : agentDetail.metrics.success_rate >= 80 ? 'text-yellow-600' : 'text-red-600'}">
					{agentDetail.metrics.success_rate.toFixed(1)}%
				</p>
			</div>
		</div>
		
		<!-- Latency Stats -->
		<div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
			<div class="bg-white/60 dark:bg-gray-800/60 backdrop-blur-sm rounded-xl border border-white/20 dark:border-gray-700/20 p-4">
				<p class="text-sm text-gray-500 dark:text-gray-400">Avg Latency</p>
				<p class="text-xl font-semibold text-gray-900 dark:text-white">{formatDuration(agentDetail.metrics.avg_latency_ms)}</p>
			</div>
			
			<div class="bg-white/60 dark:bg-gray-800/60 backdrop-blur-sm rounded-xl border border-white/20 dark:border-gray-700/20 p-4">
				<p class="text-sm text-gray-500 dark:text-gray-400">P50 Latency</p>
				<p class="text-xl font-semibold text-gray-900 dark:text-white">{formatDuration(agentDetail.metrics.p50_latency_ms)}</p>
			</div>
			
			<div class="bg-white/60 dark:bg-gray-800/60 backdrop-blur-sm rounded-xl border border-white/20 dark:border-gray-700/20 p-4">
				<p class="text-sm text-gray-500 dark:text-gray-400">P95 Latency</p>
				<p class="text-xl font-semibold text-gray-900 dark:text-white">{formatDuration(agentDetail.metrics.p95_latency_ms)}</p>
			</div>
		</div>
		
		<!-- Recent Traces -->
		<div class="bg-white/60 dark:bg-gray-800/60 backdrop-blur-sm rounded-2xl border border-white/20 dark:border-gray-700/20 shadow-sm p-6 mb-6">
			<h2 class="text-lg font-semibold text-gray-900 dark:text-white mb-4">Recent Traces</h2>
			
			{#if agentDetail.traces.length === 0}
				<p class="text-gray-500 dark:text-gray-400 text-center py-8">No traces found</p>
			{:else}
				<div class="overflow-x-auto">
					<table class="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
						<thead>
							<tr>
								<th class="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Trace ID</th>
								<th class="px-4 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Span Name</th>
								<th class="px-4 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Duration</th>
								<th class="px-4 py-3 text-center text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Status</th>
								<th class="px-4 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase">Timestamp</th>
							</tr>
						</thead>
						<tbody class="divide-y divide-gray-200 dark:divide-gray-700">
							{#each agentDetail.traces as trace}
								<tr class="hover:bg-gray-50 dark:hover:bg-gray-700/50">
									<td class="px-4 py-3 text-sm font-mono text-gray-600 dark:text-gray-400">
										{trace.trace_id.slice(0, 12)}...
									</td>
									<td class="px-4 py-3 text-sm text-gray-900 dark:text-white">
										{trace.span_name}
									</td>
									<td class="px-4 py-3 text-sm text-right text-gray-900 dark:text-white">
										{formatDuration(trace.duration_ms)}
									</td>
									<td class="px-4 py-3 text-center">
										<span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium {trace.status === 'OK' ? 'bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-400' : 'bg-red-100 text-red-800 dark:bg-red-900/20 dark:text-red-400'}">
											{trace.status}
										</span>
									</td>
									<td class="px-4 py-3 text-sm text-right text-gray-500 dark:text-gray-400">
										{formatDate(trace.timestamp)}
									</td>
								</tr>
							{/each}
						</tbody>
					</table>
				</div>
			{/if}
		</div>
		
		<!-- Hourly Trend -->
		{#if agentDetail.trend.length > 0}
			<div class="bg-white/60 dark:bg-gray-800/60 backdrop-blur-sm rounded-2xl border border-white/20 dark:border-gray-700/20 shadow-sm p-6">
				<h2 class="text-lg font-semibold text-gray-900 dark:text-white mb-4">Hourly Trend</h2>
				
				<div class="grid grid-cols-6 md:grid-cols-12 gap-2">
					{#each agentDetail.trend as item}
						<div class="text-center">
							<div class="h-16 flex flex-col justify-end">
								<div 
									class="bg-blue-500 rounded-t"
									style="height: {Math.max(4, (item.call_count / Math.max(...agentDetail.trend.map(t => t.call_count))) * 100)}%"
								></div>
							</div>
							<p class="text-xs text-gray-500 dark:text-gray-400 mt-1">
								{new Date(item.hour).getHours()}h
							</p>
							<p class="text-xs text-gray-700 dark:text-gray-300">
								{item.call_count}
							</p>
						</div>
					{/each}
				</div>
			</div>
		{/if}
	{/if}
</div>

