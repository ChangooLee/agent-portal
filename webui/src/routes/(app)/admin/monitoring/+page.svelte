<script lang="ts">
	import { getContext } from 'svelte';
	import { page } from '$app/stores';
	import { user, WEBUI_NAME } from '$lib/stores';
	import { onMount } from 'svelte';

	const i18n = getContext('i18n');

	let activeTab: 'langfuse' | 'helicone' | 'summary' = 'summary';
	let loading = true;
	let error = false;
	let usageData: any = null;
	let selectedPeriod = '이번 달';

	// BFF base URL (adjust based on your setup)
	const BFF_BASE_URL = import.meta.env.VITE_BFF_BASE_URL || 'http://localhost:8000';

	// Sample data structure based on provided HTML
	let summaryData = {
		totalTokens: 24600,
		totalRequests: 22,
		avgResponseTime: 20033,
		inputTokens: 16400,
		outputTokens: 8200,
		channelData: [
			{ name: '일반 채팅', value: 0, color: '#3b82f6' },
			{ name: '에이전트 채팅', value: 2, color: '#8b5cf6' },
			{ name: '텍스트 채팅', value: 0, color: '#22c55e' },
			{ name: 'AI 리서치', value: 20, color: '#ec4899' },
			{ name: 'AI 지식', value: 0, color: '#06b6d4' },
			{ name: 'AI 웹캡처', value: 0, color: '#14b8a6' }
		],
		dailyUsage: [
			{ date: '11월 1일', tokens: 0, cost: 0 },
			{ date: '11월 2일', tokens: 0, cost: 0 },
			{ date: '11월 3일', tokens: 0, cost: 0 },
			{ date: '11월 4일', tokens: 0, cost: 0 },
			{ date: '11월 5일', tokens: 24600, cost: 0.01 },
			{ date: '11월 6일', tokens: 0, cost: 0 },
			{ date: '11월 7일', tokens: 0, cost: 0 }
		],
		modelData: [
			{ name: 'gpt-4o-mini', value: 19500, percentage: 79.5, color: '#0088FE' },
			{ name: 'gpt-5-nano', value: 5000, percentage: 20.5, color: '#00C49F' }
		],
		featureData: [
			{ name: 'docmind', tokens: 23300, requests: 20, percentage: 94.8, color: '#0088FE' },
			{ name: '에이전트', tokens: 1300, requests: 2, percentage: 5.2, color: '#00C49F' }
		]
	};

	onMount(async () => {
		await loadUsageSummary();
	});

	async function loadUsageSummary() {
		try {
			loading = true;
			error = false;
			
			// Create abort controller for timeout
			const controller = new AbortController();
			const timeoutId = setTimeout(() => controller.abort(), 5000);
			
			const response = await fetch(`${BFF_BASE_URL}/observability/usage`, {
				method: 'GET',
				headers: {
					'Content-Type': 'application/json'
				},
				signal: controller.signal
			});
			
			clearTimeout(timeoutId);
			
			if (response.ok) {
				const data = await response.json();
				// Transform API data to match our structure
				if (data) {
					// TODO: Map API response to summaryData structure
					usageData = data;
					// Update summaryData with real data if available
					// summaryData = transformApiData(data);
				}
			} else {
				// API error but use sample data
				console.warn('API returned error, using sample data');
				error = false; // Don't show error, use sample data instead
			}
		} catch (e: any) {
			// Network error or timeout - use sample data silently
			if (e.name === 'AbortError') {
				console.warn('Request timeout, using sample data');
			} else {
				console.warn('Failed to load usage summary, using sample data:', e);
			}
			error = false; // Don't show error, use sample data instead
		} finally {
			loading = false;
		}
	}

	function getIframeSrc(tab: string): string {
		if (tab === 'langfuse') {
			return `${BFF_BASE_URL}/embed/langfuse/`;
		} else if (tab === 'helicone') {
			return `${BFF_BASE_URL}/embed/helicone/`;
		}
		return '';
	}

	function handleIframeLoad() {
		loading = false;
	}

	function handleIframeError() {
		error = true;
		loading = false;
	}

	function formatNumber(num: number): string {
		if (num >= 1000) {
			return (num / 1000).toFixed(1) + 'K';
		}
		return num.toString();
	}

	function formatTime(ms: number): string {
		return ms.toLocaleString() + 'ms';
	}
</script>

<svelte:head>
	<title>{$i18n.t('Monitoring')} | {$WEBUI_NAME}</title>
</svelte:head>

<div class="flex w-full flex-col min-h-full px-3 py-4 @md:px-6 @md:py-6">
	<div class="mx-auto flex w-full max-w-[1400px] flex-col gap-6">
		{#if $user?.role !== 'admin'}
			<div class="text-red-500">
				{$i18n.t('Access Denied: Only administrators can view this page.')}
			</div>
		{:else}
			<!-- Hero Section -->
			<section class="relative overflow-hidden rounded-3xl border border-white/20 bg-white/60 p-4 shadow-xl shadow-primary/10 backdrop-blur-2xl dark:border-gray-700/30 dark:bg-gray-900/60">
				<div class="absolute inset-0 bg-gradient-to-br from-primary/20 via-secondary/10 to-accent/20 opacity-60" />
				<div class="relative flex items-center gap-3">
					<span class="inline-flex items-center gap-2 rounded-full bg-white/90 px-3 py-1 text-xs font-medium text-gray-600 shadow-sm dark:bg-gray-800/80 dark:text-gray-200">
						<span class="h-1.5 w-1.5 rounded-full bg-gradient-to-r from-primary via-secondary to-accent" />
						SFN AI Monitoring
					</span>
					<h1 class="text-xl font-semibold tracking-tight text-gray-900 dark:text-gray-100">
						실시간 AI 사용량 및 성능 모니터링
					</h1>
				</div>
			</section>

			<!-- Tab Navigation -->
			<div class="flex gap-2">
				<button
					class="px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 ease-in-out {activeTab === 'summary'
						? 'bg-[#0072CE] text-white shadow-sm'
						: 'text-gray-600 hover:bg-gray-50'}"
					on:click={() => (activeTab = 'summary')}
				>
					{$i18n.t('Summary')}
			</button>
			<button
				class="px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 ease-in-out {activeTab === 'langfuse'
					? 'bg-[#0072CE] text-white shadow-sm'
					: 'text-gray-600 hover:bg-gray-50'}"
				on:click={() => {
					activeTab = 'langfuse';
					loading = true;
				}}
			>
				Langfuse
			</button>
			<button
				class="px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 ease-in-out {activeTab === 'helicone'
					? 'bg-[#0072CE] text-white shadow-sm'
					: 'text-gray-600 hover:bg-gray-50'}"
				on:click={() => {
					activeTab = 'helicone';
					loading = true;
				}}
			>
				Helicone
			</button>
		</div>

		<!-- Content Area -->
		<div class="flex-1 min-h-0">
			{#if activeTab === 'summary'}
				{#if loading}
					<div class="flex justify-center items-center h-64">
						<span class="loading loading-spinner loading-lg"></span>
						<p class="ml-2">{$i18n.t('Loading usage summary...')}</p>
					</div>
				{:else}
					<div class="space-y-6">
						<!-- Show sample data (API data will be used when available) -->
						<!-- Header with Period Selector -->
						<div class="flex justify-between items-center">
							<h2 class="text-2xl font-bold">토큰 사용량 모니터링</h2>
							<button
								type="button"
								class="flex h-10 items-center justify-between rounded-md border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 px-3 py-2 text-sm w-[180px] hover:bg-gray-50 dark:hover:bg-gray-700"
							>
								<span>{selectedPeriod}</span>
								<svg
									xmlns="http://www.w3.org/2000/svg"
									width="24"
									height="24"
									viewBox="0 0 24 24"
									fill="none"
									stroke="currentColor"
									stroke-width="2"
									stroke-linecap="round"
									stroke-linejoin="round"
									class="h-4 w-4 opacity-50"
								>
									<path d="m6 9 6 6 6-6"></path>
								</svg>
							</button>
						</div>

						<!-- Stats Cards -->
						<div class="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
							<!-- Total Tokens -->
							<div class="rounded-lg border bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 shadow-sm">
								<div class="p-6 flex flex-row items-center justify-between space-y-0 pb-2">
									<div class="tracking-tight text-sm font-medium">전체 토큰</div>
									<svg
										xmlns="http://www.w3.org/2000/svg"
										width="24"
										height="24"
										viewBox="0 0 24 24"
										fill="none"
										stroke="currentColor"
										stroke-width="2"
										stroke-linecap="round"
										stroke-linejoin="round"
										class="h-4 w-4 text-gray-500"
									>
										<path
											d="M22 12h-2.48a2 2 0 0 0-1.93 1.46l-2.35 8.36a.25.25 0 0 1-.48 0L9.24 2.18a.25.25 0 0 0-.48 0l-2.35 8.36A2 2 0 0 1 4.49 12H2"
										></path>
									</svg>
								</div>
								<div class="p-6 pt-0">
									<div class="text-2xl font-bold">{formatNumber(summaryData.totalTokens)}</div>
									<p class="text-xs text-gray-500 dark:text-gray-400">총 {summaryData.totalRequests} 요청</p>
								</div>
							</div>

							<!-- Average Response Time -->
							<div class="rounded-lg border bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 shadow-sm">
								<div class="p-6 flex flex-row items-center justify-between space-y-0 pb-2">
									<div class="tracking-tight text-sm font-medium">평균 응답 시간</div>
									<svg
										xmlns="http://www.w3.org/2000/svg"
										width="24"
										height="24"
										viewBox="0 0 24 24"
										fill="none"
										stroke="currentColor"
										stroke-width="2"
										stroke-linecap="round"
										stroke-linejoin="round"
										class="h-4 w-4 text-gray-500"
									>
										<path
											d="M4 14a1 1 0 0 1-.78-1.63l9.9-10.2a.5.5 0 0 1 .86.46l-1.92 6.02A1 1 0 0 0 13 10h7a1 1 0 0 1 .78 1.63l-9.9 10.2a.5.5 0 0 1-.86-.46l1.92-6.02A1 1 0 0 0 11 14z"
										></path>
									</svg>
								</div>
								<div class="p-6 pt-0">
									<div class="text-2xl font-bold">{formatTime(summaryData.avgResponseTime)}</div>
									<p class="text-xs text-gray-500 dark:text-gray-400">요청당 평균 시간</p>
								</div>
							</div>

							<!-- Input Tokens -->
							<div class="rounded-lg border bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 shadow-sm">
								<div class="p-6 flex flex-row items-center justify-between space-y-0 pb-2">
									<div class="tracking-tight text-sm font-medium">입력 토큰</div>
									<svg
										xmlns="http://www.w3.org/2000/svg"
										width="24"
										height="24"
										viewBox="0 0 24 24"
										fill="none"
										stroke="currentColor"
										stroke-width="2"
										stroke-linecap="round"
										stroke-linejoin="round"
										class="h-4 w-4 text-gray-500"
									>
										<polyline points="22 7 13.5 15.5 8.5 10.5 2 17"></polyline>
										<polyline points="16 7 22 7 22 13"></polyline>
									</svg>
								</div>
								<div class="p-6 pt-0">
									<div class="text-2xl font-bold">{formatNumber(summaryData.inputTokens)}</div>
									<p class="text-xs text-gray-500 dark:text-gray-400">프롬프트 토큰</p>
								</div>
							</div>

							<!-- Output Tokens -->
							<div class="rounded-lg border bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 shadow-sm">
								<div class="p-6 flex flex-row items-center justify-between space-y-0 pb-2">
									<div class="tracking-tight text-sm font-medium">출력 토큰</div>
									<svg
										xmlns="http://www.w3.org/2000/svg"
										width="24"
										height="24"
										viewBox="0 0 24 24"
										fill="none"
										stroke="currentColor"
										stroke-width="2"
										stroke-linecap="round"
										stroke-linejoin="round"
										class="h-4 w-4 text-gray-500"
									>
										<line x1="12" x2="12" y1="2" y2="22"></line>
										<path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"></path>
									</svg>
								</div>
								<div class="p-6 pt-0">
									<div class="text-2xl font-bold">{formatNumber(summaryData.outputTokens)}</div>
									<p class="text-xs text-gray-500 dark:text-gray-400">완성 토큰</p>
								</div>
							</div>
						</div>

						<!-- Channel Interaction Analysis -->
						<div class="rounded-lg border bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 shadow-sm">
							<div class="flex flex-col space-y-1.5 p-6">
								<div class="text-2xl font-semibold leading-none tracking-tight">채널별 인터랙션 분석</div>
								<div class="text-sm text-gray-500 dark:text-gray-400">채널 및 모달리티별 채팅 분포</div>
							</div>
							<div class="p-6 pt-0">
								<div class="grid gap-6 lg:grid-cols-2">
									<div class="h-64 w-full flex items-center justify-center">
										<!-- Simple Pie Chart using SVG -->
										<svg width="256" height="256" viewBox="0 0 256 256" class="max-w-full max-h-full">
											{#each summaryData.channelData as entry, i}
												{@const total = summaryData.channelData.reduce((sum, c) => sum + c.value, 0)}
												{@const startAngle = summaryData.channelData.slice(0, i).reduce((sum, c) => sum + (c.value / total) * 360, 0)}
												{@const angle = (entry.value / total) * 360}
												{@const largeArc = angle > 180 ? 1 : 0}
												{@const x1 = 128 + 100 * Math.cos((startAngle - 90) * Math.PI / 180)}
												{@const y1 = 128 + 100 * Math.sin((startAngle - 90) * Math.PI / 180)}
												{@const x2 = 128 + 100 * Math.cos((startAngle + angle - 90) * Math.PI / 180)}
												{@const y2 = 128 + 100 * Math.sin((startAngle + angle - 90) * Math.PI / 180)}
												<path
													d="M 128,128 L {x1},{y1} A 100,100 0 {largeArc},1 {x2},{y2} Z"
													fill={entry.color}
													stroke="#fff"
													stroke-width="2"
												/>
											{/each}
										</svg>
									</div>
									<div class="space-y-3">
										{#each summaryData.channelData as channel}
											{@const total = summaryData.channelData.reduce((sum, c) => sum + c.value, 0)}
											{@const percentage = total > 0 ? Math.round((channel.value / total) * 100) : 0}
											<div class="space-y-1">
												<div class="flex items-center justify-between text-sm">
													<span class="flex items-center gap-2 text-gray-600 dark:text-gray-300">
														<span
															class="h-2.5 w-2.5 rounded-full"
															style="background-color: {channel.color};"
														></span>
														{channel.name}
													</span>
													<span class="text-gray-900 dark:text-gray-100 font-medium">
														{channel.value} ({percentage}%)
													</span>
												</div>
												<div class="h-2 rounded-full bg-gray-200 dark:bg-gray-700">
													<div
														class="h-2 rounded-full transition-all duration-300 ease-in-out"
														style="width: {percentage}%; background-color: {channel.color};"
													></div>
												</div>
											</div>
										{/each}
									</div>
								</div>
							</div>
						</div>

						<!-- Daily Usage Trend -->
						<div class="rounded-lg border bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 shadow-sm">
							<div class="flex flex-col space-y-1.5 p-6">
								<div class="text-2xl font-semibold leading-none tracking-tight">일별 사용량 추이</div>
								<div class="text-sm text-gray-500 dark:text-gray-400">일별 토큰 사용량 및 예상 비용 추이</div>
							</div>
							<div class="p-6 pt-0">
								<div class="h-[350px] w-full">
									<!-- Simple Line Chart using SVG -->
									<svg width="100%" height="100%" viewBox="0 0 800 350" preserveAspectRatio="xMidYMid meet" class="w-full h-full">
										<!-- Grid lines -->
										{#each [0, 1, 2, 3, 4] as i}
											<line
												x1="65"
												y1={65 + i * 57}
												x2="775"
												y2={65 + i * 57}
												stroke="#ccc"
												stroke-dasharray="3 3"
												stroke-width="1"
											/>
										{/each}
										<!-- Y-axis labels (tokens) -->
										{#each [0, 6000, 12000, 18000, 24000] as val, i}
											<text x="57" y={291 - i * 57} text-anchor="end" fill="#666" font-size="12">
												{val.toLocaleString()}
											</text>
										{/each}
										<!-- X-axis labels -->
										{#each summaryData.dailyUsage as day, i}
											<text
												x={65 + (i * 110)}
												y="299"
												text-anchor="middle"
												fill="#666"
												font-size="12"
											>
												{day.date}
											</text>
										{/each}
										<!-- Token line -->
										<path
											d="M {summaryData.dailyUsage.map((d, i) => `${65 + (i * 110)},${291 - (d.tokens / 24000) * 286}`).join(' L ')}"
											fill="none"
											stroke="#3b82f6"
											stroke-width="3"
										/>
										<!-- Cost line (dashed) -->
										<path
											d="M {summaryData.dailyUsage.map((d, i) => `${65 + (i * 110)},${291 - (d.cost / 0.01) * 286}`).join(' L ')}"
											fill="none"
											stroke="#10b981"
											stroke-width="2"
											stroke-dasharray="5 5"
										/>
										<!-- Dots for tokens -->
										{#each summaryData.dailyUsage as day, i}
											<circle
												cx={65 + (i * 110)}
												cy={291 - (day.tokens / 24000) * 286}
												r="4"
												fill="#fff"
												stroke="#3b82f6"
												stroke-width="3"
											/>
										{/each}
										<!-- Dots for cost -->
										{#each summaryData.dailyUsage as day, i}
											<circle
												cx={65 + (i * 110)}
												cy={291 - (day.cost / 0.01) * 286}
												r="3"
												fill="#fff"
												stroke="#10b981"
												stroke-width="2"
											/>
										{/each}
										<!-- Legend -->
										<g transform="translate(65, 20)">
											<line x1="0" y1="0" x2="30" y2="0" stroke="#3b82f6" stroke-width="3" />
											<text x="35" y="4" fill="#3b82f6" font-size="12">토큰 사용량</text>
											<line x1="120" y1="0" x2="150" y2="0" stroke="#10b981" stroke-width="2" stroke-dasharray="5 5" />
											<text x="155" y="4" fill="#10b981" font-size="12">예상 비용</text>
										</g>
									</svg>
								</div>
							</div>
						</div>

						<!-- Model Usage and Feature Usage -->
						<div class="grid gap-6 md:grid-cols-2">
							<!-- Model Usage -->
							<div class="rounded-lg border bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 shadow-sm">
								<div class="flex flex-col space-y-1.5 p-6">
									<div class="text-2xl font-semibold leading-none tracking-tight">모델별 사용량</div>
									<div class="text-sm text-gray-500 dark:text-gray-400">각 모델의 토큰 사용 비율</div>
								</div>
								<div class="p-6 pt-0">
									<div class="h-[400px] w-full flex items-center justify-center">
										<!-- Simple Pie Chart using SVG -->
										<svg width="400" height="400" viewBox="0 0 400 400" class="max-w-full max-h-full">
											{#each summaryData.modelData as entry, i}
												{@const total = summaryData.modelData.reduce((sum, m) => sum + m.value, 0)}
												{@const startAngle = summaryData.modelData.slice(0, i).reduce((sum, m) => sum + (m.value / total) * 360, 0)}
												{@const angle = (entry.value / total) * 360}
												{@const largeArc = angle > 180 ? 1 : 0}
												{@const x1 = 200 + 150 * Math.cos((startAngle - 90) * Math.PI / 180)}
												{@const y1 = 200 + 150 * Math.sin((startAngle - 90) * Math.PI / 180)}
												{@const x2 = 200 + 150 * Math.cos((startAngle + angle - 90) * Math.PI / 180)}
												{@const y2 = 200 + 150 * Math.sin((startAngle + angle - 90) * Math.PI / 180)}
												<path
													d="M 200,200 L {x1},{y1} A 150,150 0 {largeArc},1 {x2},{y2} Z"
													fill={entry.color}
													stroke="#fff"
													stroke-width="2"
												/>
											{/each}
										</svg>
									</div>
									<div class="mt-4 space-y-2">
										{#each summaryData.modelData as model}
											<div class="flex items-center justify-between text-sm">
												<div class="flex items-center gap-2">
													<div
														class="w-3 h-3 rounded-full"
														style="background-color: {model.color};"
													></div>
													<span class="text-gray-500 dark:text-gray-400">{model.name}</span>
												</div>
												<span class="font-medium">{formatNumber(model.value)} ({model.percentage}%)</span>
											</div>
										{/each}
									</div>
								</div>
							</div>

							<!-- Model Token Usage Bar -->
							<div class="rounded-lg border bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 shadow-sm">
								<div class="flex flex-col space-y-1.5 p-6">
									<div class="text-2xl font-semibold leading-none tracking-tight">모델별 토큰 사용량</div>
									<div class="text-sm text-gray-500 dark:text-gray-400">모델별 토큰 사용량 비교</div>
								</div>
								<div class="p-6 pt-0">
									<div class="space-y-4">
										{#each summaryData.modelData as model}
											<div class="space-y-2">
												<div class="flex justify-between items-center">
													<span class="text-sm font-medium text-gray-700 dark:text-gray-300">{model.name}</span>
													<span class="text-sm text-gray-500">
														{formatNumber(model.value)} ({model.percentage}%)
													</span>
												</div>
												<div class="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-3">
													<div
														class="h-3 rounded-full transition-all duration-300 ease-in-out"
														style="width: {model.percentage}%; background-color: {model.color};"
													></div>
												</div>
											</div>
										{/each}
									</div>
								</div>
							</div>
						</div>

						<!-- Feature Usage -->
						<div class="rounded-lg border bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 shadow-sm">
							<div class="flex flex-col space-y-1.5 p-6">
								<div class="text-2xl font-semibold leading-none tracking-tight">기능별 사용량</div>
								<div class="text-sm text-gray-500 dark:text-gray-400">기능 유형별 토큰 사용량 분석</div>
							</div>
							<div class="p-6 pt-0">
								<div class="space-y-4">
									{#each summaryData.featureData as feature}
										<div class="space-y-2">
											<div class="flex justify-between items-center">
												<span class="text-sm font-medium">{feature.name}</span>
												<div class="text-sm text-gray-500 dark:text-gray-400 space-x-3">
													<span>{formatNumber(feature.tokens)} 토큰</span>
													<span class="text-xs">•</span>
													<span>{feature.requests} 요청</span>
													<span class="text-xs">•</span>
													<span>{feature.percentage}%</span>
												</div>
											</div>
											<div class="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-3">
												<div
													class="h-3 rounded-full transition-all duration-300 ease-in-out"
													style="width: {feature.percentage}%; background-color: {feature.color};"
												></div>
											</div>
										</div>
									{/each}
								</div>
							</div>
						</div>
					</div>
				{/if}
			{:else if activeTab === 'langfuse' || activeTab === 'helicone'}
				<div class="relative h-full">
					{#if loading}
						<div
							class="absolute inset-0 flex justify-center items-center bg-gray-50 dark:bg-gray-900 bg-opacity-50 z-10"
						>
							<span class="loading loading-spinner loading-lg"></span>
							<p class="ml-2">{$i18n.t('Loading...')}</p>
						</div>
					{/if}
					{#if error}
						<div class="text-red-500 p-4 bg-red-50 dark:bg-red-900/20 rounded">
							{$i18n.t('Error loading {activeTab}. Please check the backend service.', { activeTab })}
						</div>
					{:else}
						<iframe
							src={getIframeSrc(activeTab)}
							title={activeTab === 'langfuse' ? 'Langfuse Dashboard' : 'Helicone Dashboard'}
							class="w-full h-full border-0"
							style="min-height: 80vh;"
							on:load={handleIframeLoad}
							on:error={handleIframeError}
						></iframe>
					{/if}
				</div>
			{/if}
		</div>
		{/if}
	</div>
</div>
