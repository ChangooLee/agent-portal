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

	// Vite 프록시를 통해 백엔드 API 호출 (CORS 우회)
	const BFF_BASE_URL = '/api';
	const kongAdminUrl = `${BFF_BASE_URL}/embed/kong-admin/`;

	// Gateway Overview Data
	interface GatewayOverview {
		services: any[];
		consumers: any[];
		mcp_servers: any[];
		datacloud_connections: any[];
		stats: {
			services_count: number;
			consumers_count: number;
			mcp_servers_count: number;
			active_mcp_count: number;
			datacloud_count: number;
			datacloud_healthy_count: number;
		};
	}

	let overview: GatewayOverview = {
		services: [],
		consumers: [],
		mcp_servers: [],
		datacloud_connections: [],
		stats: {
			services_count: 0,
			consumers_count: 0,
			mcp_servers_count: 0,
			active_mcp_count: 0,
			datacloud_count: 0,
			datacloud_healthy_count: 0
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

<div class="min-h-full bg-gray-950 text-slate-50">
	<!-- Hero Section -->
	<div class="relative overflow-hidden border-b border-slate-800/50">
		<div class="absolute inset-0 bg-gradient-to-br from-indigo-600/5 via-transparent to-violet-600/5"></div>
		<div class="absolute inset-0 bg-[linear-gradient(rgba(99,102,241,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(99,102,241,0.03)_1px,transparent_1px)] bg-[size:64px_64px]"></div>
		
		<div class="relative px-6 py-8">
			<div class="text-center mb-4">
				<h1 class="text-3xl md:text-4xl font-medium text-white mb-3">
					🌐 API Gateway
				</h1>
				<p class="text-base text-indigo-200/80 mb-6">
					API 게이트웨이 관리 및 보안 설정
				</p>
				<div class="flex items-center justify-center gap-3">
					{#if gatewayStatus.status === 'healthy'}
						<span class="inline-flex items-center gap-1.5 rounded-full bg-emerald-500/20 px-3 py-1.5 text-xs font-medium text-emerald-400 border border-emerald-500/30">
							<Check className="size-3.5" />
							Gateway 정상
						</span>
					{:else}
						<span class="inline-flex items-center gap-1.5 rounded-full bg-red-500/20 px-3 py-1.5 text-xs font-medium text-red-400 border border-red-500/30">
							<XMark className="size-3.5" />
							Gateway 오류
						</span>
					{/if}
					<button
						on:click={() => { loadOverview(); loadStatus(); }}
						class="p-2 rounded-lg bg-slate-800/80 hover:bg-slate-700 hover:-translate-y-0.5 transition-all duration-300"
						title="새로고침"
					>
						<ArrowPath className="size-4 text-indigo-300" />
					</button>
				</div>
			</div>
		</div>
	</div>

	<div class="px-6 py-8 space-y-6">
		<!-- Tab Navigation -->
		<div class="flex gap-2">
			<button
				class="px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 flex items-center gap-2 {activeTab === 'overview'
					? 'bg-indigo-600 text-white shadow-sm'
					: 'text-slate-300 hover:bg-slate-800/80 hover:text-white'}"
				on:click={() => {
					activeTab = 'overview';
					loadOverview();
				}}
			>
				<GlobeAlt className="size-4" />
				개요
			</button>
			<button
				class="px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 flex items-center gap-2 {activeTab === 'kong-admin'
					? 'bg-indigo-600 text-white shadow-sm'
					: 'text-slate-300 hover:bg-slate-800/80 hover:text-white'}"
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
							<div class="loading loading-spinner loading-lg text-indigo-400"></div>
							<p class="text-sm text-slate-400">데이터 로딩 중...</p>
						</div>
					</div>
				{:else if error}
					<div class="flex items-center justify-center py-12">
						<div class="text-center p-4">
							<p class="text-red-400 mb-2">{error}</p>
							<button
								on:click={loadOverview}
								class="text-sm text-indigo-400 hover:text-indigo-300 hover:underline"
							>
								다시 시도
							</button>
						</div>
					</div>
				{:else}
					<!-- Stats Cards -->
					<div class="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
						<div class="bg-slate-900/80 border border-slate-800/50 rounded-xl p-6 shadow-lg shadow-black/20 hover:shadow-xl hover:shadow-black/30 hover:bg-slate-800/80 hover:border-indigo-500/50 hover:-translate-y-1 transition-all duration-300">
							<div class="flex items-center gap-3">
								<div class="p-2 rounded-lg bg-indigo-500/20">
									<GlobeAlt className="size-5 text-indigo-400" />
								</div>
								<div>
									<div class="text-2xl font-medium text-white">{overview.stats.services_count}</div>
									<div class="text-xs text-slate-400">Kong Services</div>
								</div>
							</div>
						</div>
						<div class="bg-slate-900/80 border border-slate-800/50 rounded-xl p-6 shadow-lg shadow-black/20 hover:shadow-xl hover:shadow-black/30 hover:bg-slate-800/80 hover:border-indigo-500/50 hover:-translate-y-1 transition-all duration-300">
							<div class="flex items-center gap-3">
								<div class="p-2 rounded-lg bg-purple-500/20">
									<Cube className="size-5 text-purple-400" />
								</div>
								<div>
									<div class="text-2xl font-medium text-white">{overview.stats.mcp_servers_count}</div>
									<div class="text-xs text-slate-400">MCP Servers</div>
								</div>
							</div>
						</div>
						<div class="bg-slate-900/80 border border-slate-800/50 rounded-xl p-6 shadow-lg shadow-black/20 hover:shadow-xl hover:shadow-black/30 hover:bg-slate-800/80 hover:border-indigo-500/50 hover:-translate-y-1 transition-all duration-300">
							<div class="flex items-center gap-3">
								<div class="p-2 rounded-lg bg-emerald-500/20">
									<svg class="size-5 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
										<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20.25 6.375c0 2.278-3.694 4.125-8.25 4.125S3.75 8.653 3.75 6.375m16.5 0c0-2.278-3.694-4.125-8.25-4.125S3.75 4.097 3.75 6.375m16.5 0v11.25c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125V6.375" />
									</svg>
								</div>
								<div>
									<div class="text-2xl font-medium text-white">{overview.stats.datacloud_count ?? 0}</div>
									<div class="text-xs text-slate-400">Data Cloud</div>
								</div>
							</div>
						</div>
						<div class="bg-slate-900/80 border border-slate-800/50 rounded-xl p-6 shadow-lg shadow-black/20 hover:shadow-xl hover:shadow-black/30 hover:bg-slate-800/80 hover:border-indigo-500/50 hover:-translate-y-1 transition-all duration-300">
							<div class="flex items-center gap-3">
								<div class="p-2 rounded-lg bg-emerald-500/20">
									<Check className="size-5 text-emerald-400" />
								</div>
								<div>
									<div class="text-2xl font-medium text-white">{overview.stats.active_mcp_count}</div>
									<div class="text-xs text-slate-400">Active MCP</div>
								</div>
							</div>
						</div>
						<div class="bg-slate-900/80 border border-slate-800/50 rounded-xl p-6 shadow-lg shadow-black/20 hover:shadow-xl hover:shadow-black/30 hover:bg-slate-800/80 hover:border-indigo-500/50 hover:-translate-y-1 transition-all duration-300">
							<div class="flex items-center gap-3">
								<div class="p-2 rounded-lg bg-amber-500/20">
									<LockClosed className="size-5 text-amber-400" />
								</div>
								<div>
									<div class="text-2xl font-medium text-white">{overview.stats.consumers_count}</div>
									<div class="text-xs text-slate-400">API Keys</div>
								</div>
							</div>
						</div>
					</div>

					<!-- 4 Column Layout -->
					<div class="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-4 gap-6">
						<!-- Kong Services -->
						<div class="bg-slate-900/80 border border-slate-800/50 rounded-xl shadow-lg shadow-black/20 overflow-hidden">
							<div class="px-4 py-3 bg-slate-800/50 border-b border-slate-700/50 flex items-center justify-between">
								<h3 class="font-medium text-white flex items-center gap-2">
									<GlobeAlt className="size-4 text-indigo-400" />
									Kong Services
								</h3>
								<span class="text-xs text-slate-400">{overview.services.length}개</span>
							</div>
							<div class="max-h-[400px] overflow-y-auto">
								{#if overview.services.length === 0}
									<div class="p-4 text-center text-slate-400 text-sm">
										등록된 서비스가 없습니다
									</div>
								{:else}
									{#each overview.services as service}
										<div class="px-4 py-3 border-b border-slate-800/50 last:border-b-0 hover:bg-slate-800/80 hover:border-indigo-500/50 transition-all duration-200">
											<div class="flex items-start justify-between">
												<div class="flex-1 min-w-0">
													<div class="font-medium text-white truncate">{service.name}</div>
													<div class="text-xs text-slate-400 truncate mt-0.5">
														{service.host || service.url || '-'}
													</div>
													{#if service.plugins && service.plugins.length > 0}
														<div class="flex flex-wrap gap-1 mt-1.5">
															{#each service.plugins as plugin}
																<span class="inline-flex items-center px-1.5 py-0.5 rounded text-xs bg-indigo-500/20 text-indigo-400 border border-indigo-500/30">
																	{plugin}
																</span>
															{/each}
														</div>
													{/if}
												</div>
												<ChevronRight className="size-4 text-slate-400 flex-shrink-0 ml-2" />
											</div>
										</div>
									{/each}
								{/if}
							</div>
						</div>

						<!-- MCP Servers -->
						<div class="bg-slate-900/80 border border-slate-800/50 rounded-xl shadow-lg shadow-black/20 overflow-hidden">
							<div class="px-4 py-3 bg-slate-800/50 border-b border-slate-700/50 flex items-center justify-between">
								<h3 class="font-medium text-white flex items-center gap-2">
									<Cube className="size-4 text-purple-400" />
									MCP Servers
								</h3>
								<a href="/build/mcp" class="text-xs text-indigo-400 hover:text-indigo-300 hover:underline">관리</a>
							</div>
							<div class="max-h-[400px] overflow-y-auto">
								{#if overview.mcp_servers.length === 0}
									<div class="p-4 text-center text-slate-400 text-sm">
										등록된 MCP 서버가 없습니다
									</div>
								{:else}
									{#each overview.mcp_servers as server}
										<div class="px-4 py-3 border-b border-slate-800/50 last:border-b-0 hover:bg-slate-800/80 hover:border-indigo-500/50 transition-all duration-200">
											<div class="flex items-start justify-between">
												<div class="flex-1 min-w-0">
													<div class="flex items-center gap-2">
														<span class="font-medium text-white truncate">{server.name}</span>
														{#if server.enabled}
															<span class="inline-flex items-center px-1.5 py-0.5 rounded text-xs bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
																활성
															</span>
														{:else}
															<span class="inline-flex items-center px-1.5 py-0.5 rounded text-xs bg-slate-500/20 text-slate-400 border border-slate-500/30">
																비활성
															</span>
														{/if}
													</div>
													<div class="text-xs text-slate-400 truncate mt-0.5">
														{server.endpoint_url}
													</div>
													<div class="flex items-center gap-2 mt-1.5">
														<span class="inline-flex items-center gap-1 text-xs text-slate-400">
															<Calendar className="size-3" />
															{formatDate(server.created_at)}
														</span>
													</div>
												</div>
												<div class="flex items-center gap-1 flex-shrink-0 ml-2">
													{#if server.health_status === 'healthy'}
														<span class="w-2 h-2 rounded-full bg-emerald-500"></span>
													{:else if server.health_status === 'unhealthy'}
														<span class="w-2 h-2 rounded-full bg-red-500"></span>
													{:else}
														<span class="w-2 h-2 rounded-full bg-slate-500"></span>
													{/if}
												</div>
											</div>
										</div>
									{/each}
								{/if}
							</div>
						</div>

						<!-- API Keys (Consumers) -->
						<div class="bg-slate-900/80 border border-slate-800/50 rounded-xl shadow-lg shadow-black/20 overflow-hidden">
							<div class="px-4 py-3 bg-slate-800/50 border-b border-slate-700/50 flex items-center justify-between">
								<h3 class="font-medium text-white flex items-center gap-2">
									<LockClosed className="size-4 text-amber-400" />
									API Keys
								</h3>
								<span class="text-xs text-slate-400">{overview.consumers.length}개</span>
							</div>
							<div class="max-h-[400px] overflow-y-auto">
								{#if overview.consumers.length === 0}
									<div class="p-4 text-center text-slate-400 text-sm">
										등록된 API Key가 없습니다
									</div>
								{:else}
									{#each overview.consumers as consumer}
										<div class="px-4 py-3 border-b border-slate-800/50 last:border-b-0 hover:bg-slate-800/80 hover:border-indigo-500/50 transition-all duration-200">
											<div class="flex items-start justify-between">
												<div class="flex-1 min-w-0">
													<div class="font-medium text-white truncate">{consumer.username}</div>
													{#if consumer.api_keys && consumer.api_keys.length > 0}
														{#each consumer.api_keys as apiKey}
															<div class="flex items-center gap-2 mt-1.5">
																<code class="text-xs font-mono bg-slate-800/50 border border-slate-700/50 px-2 py-0.5 rounded text-slate-300">
																	{apiKey.key_masked}
																</code>
															</div>
														{/each}
													{:else}
														<div class="text-xs text-slate-400 mt-0.5">
															API Key 없음
														</div>
													{/if}
													{#if consumer.tags && consumer.tags.length > 0}
														<div class="flex flex-wrap gap-1 mt-1.5">
															{#each consumer.tags as tag}
																<span class="inline-flex items-center px-1.5 py-0.5 rounded text-xs bg-amber-500/20 text-amber-400 border border-amber-500/30">
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

						<!-- Data Cloud Connections -->
						<div class="bg-slate-900/80 border border-slate-800/50 rounded-xl shadow-lg shadow-black/20 overflow-hidden">
							<div class="px-4 py-3 bg-slate-800/50 border-b border-slate-700/50 flex items-center justify-between">
								<h3 class="font-medium text-white flex items-center gap-2">
									<svg class="size-4 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
										<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20.25 6.375c0 2.278-3.694 4.125-8.25 4.125S3.75 8.653 3.75 6.375m16.5 0c0-2.278-3.694-4.125-8.25-4.125S3.75 4.097 3.75 6.375m16.5 0v11.25c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125V6.375" />
									</svg>
									Data Cloud
								</h3>
								<a href="/build/datacloud" class="text-xs text-indigo-400 hover:text-indigo-300 hover:underline">관리</a>
							</div>
							<div class="max-h-[400px] overflow-y-auto">
								{#if !overview.datacloud_connections || overview.datacloud_connections.length === 0}
									<div class="p-4 text-center text-slate-400 text-sm">
										등록된 DB 연결이 없습니다
									</div>
								{:else}
									{#each overview.datacloud_connections as conn}
										<div class="px-4 py-3 border-b border-slate-800/50 last:border-b-0 hover:bg-slate-800/80 hover:border-indigo-500/50 transition-all duration-200">
											<div class="flex items-start justify-between">
												<div class="flex-1 min-w-0">
													<div class="flex items-center gap-2">
														<span class="font-medium text-white truncate">{conn.name}</span>
														<span class="inline-flex items-center px-1.5 py-0.5 rounded text-xs bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">
															{conn.db_type}
														</span>
													</div>
													<div class="text-xs text-slate-400 truncate mt-0.5">
														{conn.host}:{conn.port} / {conn.database_name}
													</div>
												</div>
												<div class="flex items-center gap-1 flex-shrink-0 ml-2">
													{#if conn.health_status === 'healthy'}
														<span class="w-2 h-2 rounded-full bg-emerald-500" title="정상"></span>
													{:else if conn.health_status === 'unhealthy'}
														<span class="w-2 h-2 rounded-full bg-red-500" title="오류"></span>
													{:else}
														<span class="w-2 h-2 rounded-full bg-slate-500" title="미확인"></span>
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
								<div class="loading loading-spinner loading-lg text-indigo-400"></div>
								<p class="text-sm text-slate-400">Loading Kong Admin UI...</p>
							</div>
						</div>
					{/if}

					{#if error}
						<div class="absolute inset-0 flex items-center justify-center">
							<div class="text-center p-4">
								<p class="text-red-400 mb-2">{error}</p>
								<p class="text-sm text-slate-400">
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
