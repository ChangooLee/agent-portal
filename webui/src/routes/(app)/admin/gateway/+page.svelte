<script lang="ts">
	import { onMount } from 'svelte';
	import { getContext } from 'svelte';
	import { page } from '$app/stores';
	import { WEBUI_NAME } from '$lib/stores';
	import GlobeAlt from '$lib/components/icons/GlobeAlt.svelte';
	import Cube from '$lib/components/icons/Cube.svelte';
	import Check from '$lib/components/icons/Check.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import ArrowPath from '$lib/components/icons/ArrowPath.svelte';
	import ChevronRight from '$lib/components/icons/ChevronRight.svelte';
	import LockClosed from '$lib/components/icons/LockClosed.svelte';
	import Calendar from '$lib/components/icons/Calendar.svelte';
	import Cog6 from '$lib/components/icons/Cog6.svelte';
	
	const i18n = getContext('i18n');

	let loading = true;
	let error: string | null = null;
	let activeTab = 'overview';

	const BFF_BASE_URL = import.meta.env.VITE_BFF_BASE_URL || 'http://localhost:8000';
	const kongAdminUrl = `${BFF_BASE_URL}/embed/kong-admin/`;

	// Gateway Overview Data
	interface GatewayOverview {
		services: any[];
		consumers: any[];
		mcp_servers: any[];
		stats: {
			services_count: number;
			consumers_count: number;
			mcp_servers_count: number;
			active_mcp_count: number;
		};
	}

	let overview: GatewayOverview = {
		services: [],
		consumers: [],
		mcp_servers: [],
		stats: {
			services_count: 0,
			consumers_count: 0,
			mcp_servers_count: 0,
			active_mcp_count: 0
		}
	};

	let gatewayStatus = {
		status: 'unknown',
		kong_status: {},
		services_count: 0,
		consumers_count: 0,
		routes_count: 0,
		plugins_count: 0
	};

	async function loadOverview() {
		loading = true;
		error = null;
		
		try {
			const response = await fetch(`${BFF_BASE_URL}/gateway/overview`);
			if (!response.ok) {
				throw new Error(`Failed to load gateway overview: ${response.statusText}`);
			}
			overview = await response.json();
		} catch (e: any) {
			console.error('Failed to load gateway overview:', e);
			error = e.message;
		} finally {
			loading = false;
		}
	}

	async function loadStatus() {
		try {
			const response = await fetch(`${BFF_BASE_URL}/gateway/status`);
			if (response.ok) {
				gatewayStatus = await response.json();
			}
		} catch (e) {
			console.error('Failed to load gateway status:', e);
		}
	}

	onMount(() => {
		loadOverview();
		loadStatus();
	});

	function handleIframeLoad() {
		loading = false;
		error = null;
	}

	function handleIframeError() {
		loading = false;
		error = 'Failed to load Kong Admin UI. Please ensure the backend service is running.';
	}

	function formatDate(timestamp: number | string | null): string {
		if (!timestamp) return '-';
		const date = typeof timestamp === 'number' 
			? new Date(timestamp * 1000) 
			: new Date(timestamp);
		return date.toLocaleDateString('ko-KR', {
			year: 'numeric',
			month: '2-digit',
			day: '2-digit',
			hour: '2-digit',
			minute: '2-digit'
		});
	}
</script>

<svelte:head>
	<title>{$i18n.t('Gateway')} | {$WEBUI_NAME}</title>
</svelte:head>

<div class="flex w-full flex-col min-h-full px-3 py-4 @md:px-6 @md:py-6">
	<div class="mx-auto flex w-full max-w-[1400px] flex-col gap-6">
		<!-- Hero Section -->
		<section class="relative overflow-hidden rounded-3xl border border-white/20 bg-white/60 p-4 shadow-xl shadow-primary/10 backdrop-blur-2xl dark:border-gray-700/30 dark:bg-gray-900/60">
			<div class="absolute inset-0 bg-gradient-to-br from-primary/20 via-secondary/10 to-accent/20 opacity-60" />
			<div class="relative flex items-center justify-between">
				<div class="flex items-center gap-3">
					<span class="inline-flex items-center gap-2 rounded-full bg-white/90 px-3 py-1 text-xs font-medium text-gray-600 shadow-sm dark:bg-gray-800/80 dark:text-gray-200">
						<span class="h-1.5 w-1.5 rounded-full bg-gradient-to-r from-primary via-secondary to-accent" />
						SFN AI Gateway
					</span>
					<h1 class="text-xl font-semibold tracking-tight text-gray-900 dark:text-gray-100">
						API 게이트웨이 관리 및 보안 설정
					</h1>
				</div>
				
				<!-- Status Badge -->
				<div class="flex items-center gap-2">
					{#if gatewayStatus.status === 'healthy'}
						<span class="inline-flex items-center gap-1.5 rounded-full bg-green-100 px-3 py-1 text-xs font-medium text-green-700 dark:bg-green-900/30 dark:text-green-400">
							<Check className="size-3.5" />
							Gateway 정상
						</span>
					{:else}
						<span class="inline-flex items-center gap-1.5 rounded-full bg-red-100 px-3 py-1 text-xs font-medium text-red-700 dark:bg-red-900/30 dark:text-red-400">
							<XMark className="size-3.5" />
							Gateway 오류
						</span>
					{/if}
					<button
						on:click={() => { loadOverview(); loadStatus(); }}
						class="p-2 rounded-lg hover:bg-white/50 dark:hover:bg-gray-800/50 transition-colors"
						title="새로고침"
					>
						<ArrowPath className="size-4 text-gray-500 dark:text-gray-400" />
					</button>
				</div>
			</div>
		</section>

		<!-- Tab Navigation -->
		<div class="flex gap-2">
			<button
				class="px-4 py-2 rounded-xl text-sm font-medium transition-all duration-300 ease-out flex items-center gap-2 {activeTab === 'overview'
					? 'bg-gradient-to-br from-primary/90 via-secondary/90 to-accent/90 text-white backdrop-blur-md shadow-lg shadow-primary/30'
					: 'bg-white/40 dark:bg-gray-800/40 text-gray-700 dark:text-gray-200 backdrop-blur-sm hover:bg-white/60 dark:hover:bg-gray-800/60 border border-gray-200/30 dark:border-gray-700/30 hover:shadow-md hover:scale-105'}"
				on:click={() => {
					activeTab = 'overview';
					loadOverview();
				}}
			>
				<GlobeAlt className="size-4" />
				개요
			</button>
			<button
				class="px-4 py-2 rounded-xl text-sm font-medium transition-all duration-300 ease-out flex items-center gap-2 {activeTab === 'kong-admin'
					? 'bg-gradient-to-br from-primary/90 via-secondary/90 to-accent/90 text-white backdrop-blur-md shadow-lg shadow-primary/30'
					: 'bg-white/40 dark:bg-gray-800/40 text-gray-700 dark:text-gray-200 backdrop-blur-sm hover:bg-white/60 dark:hover:bg-gray-800/60 border border-gray-200/30 dark:border-gray-700/30 hover:shadow-md hover:scale-105'}"
				on:click={() => {
					activeTab = 'kong-admin';
				}}
			>
				<Cog6 className="size-4" />
				Kong Admin
			</button>
		</div>

		<div class="flex-1 relative">
			{#if activeTab === 'overview'}
				<!-- Overview Tab -->
				{#if loading}
					<div class="flex items-center justify-center py-12">
						<div class="flex flex-col items-center gap-2">
							<div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
							<p class="text-sm text-gray-500 dark:text-gray-400">데이터 로딩 중...</p>
						</div>
					</div>
				{:else if error}
					<div class="flex items-center justify-center py-12">
						<div class="text-center p-4">
							<p class="text-red-500 dark:text-red-400 mb-2">{error}</p>
							<button
								on:click={loadOverview}
								class="text-sm text-blue-500 hover:underline"
							>
								다시 시도
							</button>
						</div>
					</div>
				{:else}
					<!-- Stats Cards -->
					<div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
						<div class="bg-white/60 dark:bg-gray-800/60 backdrop-blur-sm rounded-2xl p-4 border border-white/20 dark:border-gray-700/20 shadow-sm">
							<div class="flex items-center gap-3">
								<div class="p-2 rounded-lg bg-blue-100 dark:bg-blue-900/30">
									<GlobeAlt className="size-5 text-blue-600 dark:text-blue-400" />
								</div>
								<div>
									<div class="text-2xl font-bold text-gray-900 dark:text-gray-100">{overview.stats.services_count}</div>
									<div class="text-xs text-gray-500 dark:text-gray-400">Kong Services</div>
								</div>
							</div>
						</div>
						<div class="bg-white/60 dark:bg-gray-800/60 backdrop-blur-sm rounded-2xl p-4 border border-white/20 dark:border-gray-700/20 shadow-sm">
							<div class="flex items-center gap-3">
								<div class="p-2 rounded-lg bg-purple-100 dark:bg-purple-900/30">
									<Cube className="size-5 text-purple-600 dark:text-purple-400" />
								</div>
								<div>
									<div class="text-2xl font-bold text-gray-900 dark:text-gray-100">{overview.stats.mcp_servers_count}</div>
									<div class="text-xs text-gray-500 dark:text-gray-400">MCP Servers</div>
								</div>
							</div>
						</div>
						<div class="bg-white/60 dark:bg-gray-800/60 backdrop-blur-sm rounded-2xl p-4 border border-white/20 dark:border-gray-700/20 shadow-sm">
							<div class="flex items-center gap-3">
								<div class="p-2 rounded-lg bg-green-100 dark:bg-green-900/30">
									<Check className="size-5 text-green-600 dark:text-green-400" />
								</div>
								<div>
									<div class="text-2xl font-bold text-gray-900 dark:text-gray-100">{overview.stats.active_mcp_count}</div>
									<div class="text-xs text-gray-500 dark:text-gray-400">Active MCP</div>
								</div>
							</div>
						</div>
						<div class="bg-white/60 dark:bg-gray-800/60 backdrop-blur-sm rounded-2xl p-4 border border-white/20 dark:border-gray-700/20 shadow-sm">
							<div class="flex items-center gap-3">
								<div class="p-2 rounded-lg bg-orange-100 dark:bg-orange-900/30">
									<LockClosed className="size-5 text-orange-600 dark:text-orange-400" />
								</div>
								<div>
									<div class="text-2xl font-bold text-gray-900 dark:text-gray-100">{overview.stats.consumers_count}</div>
									<div class="text-xs text-gray-500 dark:text-gray-400">API Keys</div>
								</div>
							</div>
						</div>
					</div>

					<!-- 3 Column Layout -->
					<div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
						<!-- Kong Services -->
						<div class="bg-white/60 dark:bg-gray-800/60 backdrop-blur-sm rounded-2xl border border-white/20 dark:border-gray-700/20 shadow-sm overflow-hidden">
							<div class="px-4 py-3 border-b border-gray-200/50 dark:border-gray-700/50 flex items-center justify-between">
								<h3 class="font-semibold text-gray-900 dark:text-gray-100 flex items-center gap-2">
									<GlobeAlt className="size-4 text-blue-500" />
									Kong Services
								</h3>
								<span class="text-xs text-gray-500 dark:text-gray-400">{overview.services.length}개</span>
							</div>
							<div class="max-h-[400px] overflow-y-auto">
								{#if overview.services.length === 0}
									<div class="p-4 text-center text-gray-500 dark:text-gray-400 text-sm">
										등록된 서비스가 없습니다
									</div>
								{:else}
									{#each overview.services as service}
										<div class="px-4 py-3 border-b border-gray-100 dark:border-gray-700/50 last:border-b-0 hover:bg-white/50 dark:hover:bg-gray-700/30 transition-colors">
											<div class="flex items-start justify-between">
												<div class="flex-1 min-w-0">
													<div class="font-medium text-gray-900 dark:text-gray-100 truncate">{service.name}</div>
													<div class="text-xs text-gray-500 dark:text-gray-400 truncate mt-0.5">
														{service.host || service.url || '-'}
													</div>
													{#if service.plugins && service.plugins.length > 0}
														<div class="flex flex-wrap gap-1 mt-1.5">
															{#each service.plugins as plugin}
																<span class="inline-flex items-center px-1.5 py-0.5 rounded text-xs bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300">
																	{plugin}
																</span>
															{/each}
														</div>
													{/if}
												</div>
												<ChevronRight className="size-4 text-gray-400 flex-shrink-0 ml-2" />
											</div>
										</div>
									{/each}
								{/if}
							</div>
						</div>

						<!-- MCP Servers -->
						<div class="bg-white/60 dark:bg-gray-800/60 backdrop-blur-sm rounded-2xl border border-white/20 dark:border-gray-700/20 shadow-sm overflow-hidden">
							<div class="px-4 py-3 border-b border-gray-200/50 dark:border-gray-700/50 flex items-center justify-between">
								<h3 class="font-semibold text-gray-900 dark:text-gray-100 flex items-center gap-2">
									<Cube className="size-4 text-purple-500" />
									MCP Servers
								</h3>
								<a href="/admin/mcp" class="text-xs text-blue-500 hover:underline">관리</a>
							</div>
							<div class="max-h-[400px] overflow-y-auto">
								{#if overview.mcp_servers.length === 0}
									<div class="p-4 text-center text-gray-500 dark:text-gray-400 text-sm">
										등록된 MCP 서버가 없습니다
									</div>
								{:else}
									{#each overview.mcp_servers as server}
										<div class="px-4 py-3 border-b border-gray-100 dark:border-gray-700/50 last:border-b-0 hover:bg-white/50 dark:hover:bg-gray-700/30 transition-colors">
											<div class="flex items-start justify-between">
												<div class="flex-1 min-w-0">
													<div class="flex items-center gap-2">
														<span class="font-medium text-gray-900 dark:text-gray-100 truncate">{server.name}</span>
														{#if server.enabled}
															<span class="inline-flex items-center px-1.5 py-0.5 rounded text-xs bg-green-100 dark:bg-green-900/30 text-green-700 dark:text-green-300">
																활성
															</span>
														{:else}
															<span class="inline-flex items-center px-1.5 py-0.5 rounded text-xs bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400">
																비활성
															</span>
														{/if}
													</div>
													<div class="text-xs text-gray-500 dark:text-gray-400 truncate mt-0.5">
														{server.endpoint_url}
													</div>
													<div class="flex items-center gap-2 mt-1.5">
														<span class="inline-flex items-center gap-1 text-xs text-gray-500 dark:text-gray-400">
															<Calendar className="size-3" />
															{formatDate(server.created_at)}
														</span>
													</div>
												</div>
												<div class="flex items-center gap-1 flex-shrink-0 ml-2">
													{#if server.health_status === 'healthy'}
														<span class="w-2 h-2 rounded-full bg-green-500"></span>
													{:else if server.health_status === 'unhealthy'}
														<span class="w-2 h-2 rounded-full bg-red-500"></span>
													{:else}
														<span class="w-2 h-2 rounded-full bg-gray-400"></span>
													{/if}
												</div>
											</div>
										</div>
									{/each}
								{/if}
							</div>
						</div>

						<!-- API Keys (Consumers) -->
						<div class="bg-white/60 dark:bg-gray-800/60 backdrop-blur-sm rounded-2xl border border-white/20 dark:border-gray-700/20 shadow-sm overflow-hidden">
							<div class="px-4 py-3 border-b border-gray-200/50 dark:border-gray-700/50 flex items-center justify-between">
								<h3 class="font-semibold text-gray-900 dark:text-gray-100 flex items-center gap-2">
									<LockClosed className="size-4 text-orange-500" />
									API Keys
								</h3>
								<span class="text-xs text-gray-500 dark:text-gray-400">{overview.consumers.length}개</span>
							</div>
							<div class="max-h-[400px] overflow-y-auto">
								{#if overview.consumers.length === 0}
									<div class="p-4 text-center text-gray-500 dark:text-gray-400 text-sm">
										등록된 API Key가 없습니다
									</div>
								{:else}
									{#each overview.consumers as consumer}
										<div class="px-4 py-3 border-b border-gray-100 dark:border-gray-700/50 last:border-b-0 hover:bg-white/50 dark:hover:bg-gray-700/30 transition-colors">
											<div class="flex items-start justify-between">
												<div class="flex-1 min-w-0">
													<div class="font-medium text-gray-900 dark:text-gray-100 truncate">{consumer.username}</div>
													{#if consumer.api_keys && consumer.api_keys.length > 0}
														{#each consumer.api_keys as apiKey}
															<div class="flex items-center gap-2 mt-1.5">
																<code class="text-xs font-mono bg-gray-100 dark:bg-gray-700 px-2 py-0.5 rounded text-gray-600 dark:text-gray-300">
																	{apiKey.key_masked}
																</code>
															</div>
														{/each}
													{:else}
														<div class="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
															API Key 없음
														</div>
													{/if}
													{#if consumer.tags && consumer.tags.length > 0}
														<div class="flex flex-wrap gap-1 mt-1.5">
															{#each consumer.tags as tag}
																<span class="inline-flex items-center px-1.5 py-0.5 rounded text-xs bg-orange-100 dark:bg-orange-900/30 text-orange-700 dark:text-orange-300">
																	{tag}
																</span>
															{/each}
														</div>
													{/if}
												</div>
											</div>
										</div>
									{/each}
								{/if}
							</div>
						</div>
					</div>
				{/if}
			{:else if activeTab === 'kong-admin'}
				<!-- Kong Admin iframe -->
				<div class="min-h-[90vh]">
					{#if loading}
						<div class="absolute inset-0 flex items-center justify-center">
							<div class="flex flex-col items-center gap-2">
								<div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
								<p class="text-sm text-gray-500 dark:text-gray-400">Loading Kong Admin UI...</p>
							</div>
						</div>
					{/if}

					{#if error}
						<div class="absolute inset-0 flex items-center justify-center">
							<div class="text-center p-4">
								<p class="text-red-500 dark:text-red-400 mb-2">{error}</p>
								<p class="text-sm text-gray-500 dark:text-gray-400">
									Please check if the backend service is running and accessible.
								</p>
							</div>
						</div>
					{/if}

					<iframe
						src={kongAdminUrl}
						class="w-full h-full border-0 min-h-[90vh] {loading ? 'opacity-0' : 'opacity-100'} transition-opacity rounded-2xl"
						title="Kong Admin UI"
						on:load={handleIframeLoad}
						on:error={handleIframeError}
						sandbox="allow-same-origin allow-scripts allow-forms allow-popups allow-modals"
					/>
				</div>
			{/if}
		</div>
	</div>
</div>
