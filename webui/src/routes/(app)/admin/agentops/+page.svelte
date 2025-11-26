<script lang="ts">
	import { onMount } from 'svelte';
	import ChartBar from '$lib/components/icons/ChartBar.svelte';
	import DocumentChartBar from '$lib/components/icons/DocumentChartBar.svelte';
	import ArrowPath from '$lib/components/icons/ArrowPath.svelte';

	let dashboardStatus = 'checking'; // 'checking' | 'online' | 'offline'
	let apiStatus = 'checking';
	let clickhouseStatus = 'checking';
	let traceCount = 0;

	const DASHBOARD_URL = 'http://localhost:3006';
	const API_URL = 'http://localhost:8003';

	const features = [
		{ 
			id: 'overview', 
			label: 'Overview', 
			icon: ChartBar, 
			path: '/overview', 
			description: '전체 메트릭 대시보드 - 비용, 토큰 사용량, 성공률 등'
		},
		{ 
			id: 'traces', 
			label: 'Traces', 
			icon: DocumentChartBar, 
			path: '/traces', 
			description: 'LLM 호출 상세 트레이스 - 요청/응답, 지연시간, 에러'
		},
		{ 
			id: 'replay', 
			label: 'Session Replay', 
			icon: ArrowPath, 
			path: '/timetravel', 
			description: '에이전트 세션 리플레이 - 단계별 실행 과정 시각화'
		}
	];

	async function checkStatus() {
		// Check Dashboard
		try {
			const response = await fetch(DASHBOARD_URL, { mode: 'no-cors' });
			dashboardStatus = 'online';
		} catch {
			dashboardStatus = 'offline';
		}

		// Check API
		try {
			const response = await fetch(`${API_URL}/health`);
			if (response.ok) {
				apiStatus = 'online';
			} else {
				apiStatus = 'offline';
			}
		} catch {
			apiStatus = 'offline';
		}

		// Check ClickHouse (via API or direct)
		try {
			const response = await fetch('http://localhost:8124/?query=SELECT%20count()%20FROM%20otel_2.otel_traces');
			if (response.ok) {
				const text = await response.text();
				traceCount = parseInt(text.trim()) || 0;
				clickhouseStatus = 'online';
			} else {
				clickhouseStatus = 'offline';
			}
		} catch {
			clickhouseStatus = 'offline';
		}
	}

	onMount(() => {
		checkStatus();
		// Refresh status every 30 seconds
		const interval = setInterval(checkStatus, 30000);
		return () => clearInterval(interval);
	});

	function openDashboard(path: string = '') {
		window.open(`${DASHBOARD_URL}${path}`, '_blank', 'noopener,noreferrer');
	}
</script>

<svelte:head>
	<title>AgentOps - LLM Observability | Agent Portal</title>
</svelte:head>

<div class="flex flex-col w-full h-full min-h-screen p-6 space-y-6">
	<!-- Hero Section -->
	<div
		class="relative overflow-hidden rounded-2xl bg-gradient-to-br from-blue-500/10 via-indigo-500/10 to-purple-500/10 dark:from-blue-400/5 dark:via-indigo-400/5 dark:to-purple-400/5"
	>
		<div class="absolute inset-0 bg-white/40 dark:bg-gray-900/40 backdrop-blur-xl"></div>

		<div class="relative px-8 py-6">
			<!-- Badge -->
			<div
				class="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-blue-500/10 dark:bg-blue-400/10 text-blue-600 dark:text-blue-400 text-sm font-medium mb-3 backdrop-blur-sm border border-blue-500/20 dark:border-blue-400/20"
			>
				<ChartBar className="size-4" />
				<span>LLM Observability & Monitoring</span>
			</div>

			<!-- Title & Open Button -->
			<div class="flex items-center justify-between flex-wrap gap-4">
				<div>
					<h1 class="text-3xl font-bold text-gray-900 dark:text-white mb-2">
						AgentOps Dashboard
					</h1>
					<p class="text-base text-gray-600 dark:text-gray-300 max-w-2xl">
						LLM 호출 트레이싱, 비용 추적, 성능 모니터링을 제공하는 Self-Hosted AgentOps 대시보드입니다.
					</p>
				</div>
				
				<button
					on:click={() => openDashboard()}
					class="flex items-center gap-2 px-6 py-3 rounded-xl text-base font-semibold transition-all duration-300 ease-out
						bg-gradient-to-br from-blue-600 via-indigo-600 to-purple-600 text-white shadow-lg shadow-blue-500/30 
						hover:shadow-xl hover:shadow-blue-500/40 hover:scale-105 border border-white/20"
				>
					<svg class="size-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
					</svg>
					<span>Open Dashboard</span>
				</button>
			</div>
		</div>
	</div>

	<!-- Status Cards -->
	<div class="grid grid-cols-1 md:grid-cols-3 gap-4">
		<!-- Dashboard Status -->
		<div class="rounded-xl bg-white/60 dark:bg-gray-800/60 backdrop-blur-sm border border-white/20 dark:border-gray-700/20 p-5">
			<div class="flex items-center justify-between mb-3">
				<span class="text-sm font-medium text-gray-500 dark:text-gray-400">Dashboard</span>
				<span class="flex items-center gap-1.5">
					{#if dashboardStatus === 'checking'}
						<span class="size-2.5 rounded-full bg-yellow-400 animate-pulse"></span>
						<span class="text-xs text-yellow-600 dark:text-yellow-400">Checking...</span>
					{:else if dashboardStatus === 'online'}
						<span class="size-2.5 rounded-full bg-green-500"></span>
						<span class="text-xs text-green-600 dark:text-green-400">Online</span>
					{:else}
						<span class="size-2.5 rounded-full bg-red-500"></span>
						<span class="text-xs text-red-600 dark:text-red-400">Offline</span>
					{/if}
				</span>
			</div>
			<p class="text-2xl font-bold text-gray-900 dark:text-white">localhost:3006</p>
			<p class="text-sm text-gray-500 dark:text-gray-400 mt-1">Next.js Dashboard UI</p>
		</div>

		<!-- API Status -->
		<div class="rounded-xl bg-white/60 dark:bg-gray-800/60 backdrop-blur-sm border border-white/20 dark:border-gray-700/20 p-5">
			<div class="flex items-center justify-between mb-3">
				<span class="text-sm font-medium text-gray-500 dark:text-gray-400">API Server</span>
				<span class="flex items-center gap-1.5">
					{#if apiStatus === 'checking'}
						<span class="size-2.5 rounded-full bg-yellow-400 animate-pulse"></span>
						<span class="text-xs text-yellow-600 dark:text-yellow-400">Checking...</span>
					{:else if apiStatus === 'online'}
						<span class="size-2.5 rounded-full bg-green-500"></span>
						<span class="text-xs text-green-600 dark:text-green-400">Online</span>
					{:else}
						<span class="size-2.5 rounded-full bg-red-500"></span>
						<span class="text-xs text-red-600 dark:text-red-400">Offline</span>
					{/if}
				</span>
			</div>
			<p class="text-2xl font-bold text-gray-900 dark:text-white">localhost:8003</p>
			<p class="text-sm text-gray-500 dark:text-gray-400 mt-1">FastAPI Backend</p>
		</div>

		<!-- ClickHouse Status -->
		<div class="rounded-xl bg-white/60 dark:bg-gray-800/60 backdrop-blur-sm border border-white/20 dark:border-gray-700/20 p-5">
			<div class="flex items-center justify-between mb-3">
				<span class="text-sm font-medium text-gray-500 dark:text-gray-400">ClickHouse</span>
				<span class="flex items-center gap-1.5">
					{#if clickhouseStatus === 'checking'}
						<span class="size-2.5 rounded-full bg-yellow-400 animate-pulse"></span>
						<span class="text-xs text-yellow-600 dark:text-yellow-400">Checking...</span>
					{:else if clickhouseStatus === 'online'}
						<span class="size-2.5 rounded-full bg-green-500"></span>
						<span class="text-xs text-green-600 dark:text-green-400">Online</span>
					{:else}
						<span class="size-2.5 rounded-full bg-red-500"></span>
						<span class="text-xs text-red-600 dark:text-red-400">Offline</span>
					{/if}
				</span>
			</div>
			<p class="text-2xl font-bold text-gray-900 dark:text-white">
				{#if clickhouseStatus === 'online'}
					{traceCount.toLocaleString()} traces
				{:else}
					-
				{/if}
			</p>
			<p class="text-sm text-gray-500 dark:text-gray-400 mt-1">OTEL Trace Storage</p>
		</div>
	</div>

	<!-- Feature Cards -->
	<div class="grid grid-cols-1 md:grid-cols-3 gap-4">
		{#each features as feature}
			<button
				on:click={() => openDashboard(feature.path)}
				class="group text-left rounded-xl bg-white/60 dark:bg-gray-800/60 backdrop-blur-sm border border-white/20 dark:border-gray-700/20 p-6 
					hover:bg-white/80 dark:hover:bg-gray-800/80 hover:shadow-lg hover:scale-[1.02] transition-all duration-300"
			>
				<div class="flex items-center gap-3 mb-3">
					<div class="p-2.5 rounded-lg bg-blue-500/10 dark:bg-blue-400/10 text-blue-600 dark:text-blue-400 group-hover:bg-blue-500/20 transition-colors">
						<svelte:component this={feature.icon} className="size-5" />
					</div>
					<h3 class="text-lg font-semibold text-gray-900 dark:text-white">{feature.label}</h3>
					<svg class="size-4 ml-auto text-gray-400 group-hover:text-blue-500 group-hover:translate-x-1 transition-all" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
					</svg>
				</div>
				<p class="text-sm text-gray-600 dark:text-gray-300">{feature.description}</p>
			</button>
		{/each}
	</div>

	<!-- Architecture Info -->
	<div class="rounded-xl bg-white/60 dark:bg-gray-800/60 backdrop-blur-sm border border-white/20 dark:border-gray-700/20 p-6">
		<h2 class="text-lg font-semibold text-gray-900 dark:text-white mb-4">아키텍처</h2>
		<div class="flex items-center justify-center gap-2 flex-wrap text-sm">
			<div class="px-3 py-1.5 rounded-lg bg-green-500/10 text-green-700 dark:text-green-400 border border-green-500/20">
				LiteLLM (4000)
			</div>
			<span class="text-gray-400">→</span>
			<div class="px-3 py-1.5 rounded-lg bg-blue-500/10 text-blue-700 dark:text-blue-400 border border-blue-500/20">
				OTEL Collector (4318)
			</div>
			<span class="text-gray-400">→</span>
			<div class="px-3 py-1.5 rounded-lg bg-yellow-500/10 text-yellow-700 dark:text-yellow-400 border border-yellow-500/20">
				ClickHouse (8124)
			</div>
			<span class="text-gray-400">→</span>
			<div class="px-3 py-1.5 rounded-lg bg-purple-500/10 text-purple-700 dark:text-purple-400 border border-purple-500/20">
				AgentOps API (8003)
			</div>
			<span class="text-gray-400">→</span>
			<div class="px-3 py-1.5 rounded-lg bg-indigo-500/10 text-indigo-700 dark:text-indigo-400 border border-indigo-500/20">
				Dashboard (3006)
			</div>
		</div>
		<p class="text-center text-xs text-gray-500 dark:text-gray-400 mt-4">
			LLM 호출 → OpenTelemetry 트레이스 → ClickHouse 저장 → AgentOps 시각화
		</p>
	</div>

	<!-- Quick Actions -->
	<div class="rounded-xl bg-white/60 dark:bg-gray-800/60 backdrop-blur-sm border border-white/20 dark:border-gray-700/20 p-6">
		<h2 class="text-lg font-semibold text-gray-900 dark:text-white mb-4">빠른 링크</h2>
		<div class="flex flex-wrap gap-3">
			<a 
				href="http://localhost:4000/ui" 
				target="_blank" 
				rel="noopener noreferrer"
				class="px-4 py-2 rounded-lg bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-200 text-sm hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
			>
				LiteLLM UI
			</a>
			<a 
				href="http://localhost:8124/play" 
				target="_blank" 
				rel="noopener noreferrer"
				class="px-4 py-2 rounded-lg bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-200 text-sm hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
			>
				ClickHouse Playground
			</a>
			<a 
				href="http://localhost:55321" 
				target="_blank" 
				rel="noopener noreferrer"
				class="px-4 py-2 rounded-lg bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-200 text-sm hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
			>
				Supabase Studio
			</a>
			<button
				on:click={checkStatus}
				class="px-4 py-2 rounded-lg bg-blue-500/10 text-blue-600 dark:text-blue-400 text-sm hover:bg-blue-500/20 transition-colors"
			>
				🔄 Refresh Status
			</button>
		</div>
	</div>
</div>
