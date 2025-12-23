<script lang="ts">
	import { onMount, afterUpdate, getContext } from 'svelte';
	import { goto } from '$app/navigation';
	import { WEBUI_NAME, showSidebar } from '$lib/stores';
	import Cube from '$lib/components/icons/Cube.svelte';
	import Fuse from 'fuse.js';

	const i18n = getContext('i18n');

	interface Flow {
		id: string;
		name: string;
		description?: string;
		updated_at?: string;
		user_id?: string;
	}

	let loaded = false;
	let activeTab: 'overview' | 'langflow' | 'flowise' | 'autogen' = 'overview';
	let langflowLoading = true;
	let flowiseLoading = true;
	let autogenLoading = true;

	// Flow list state
	let flows: Flow[] = [];
	let filteredFlows: Flow[] = [];
	let loading = true;
	let loadingMore = false;
	let error = '';
	let hasMore = true;
	let offset = 0;
	let observerTarget: HTMLDivElement;
	let observer: IntersectionObserver | null = null;
	let searchQuery = '';
	let isSearching = false;
	let selectedBuilder: 'all' | 'langflow' | 'flowise' | 'autogen' = 'all';
	let sortBy: 'recent' | 'name' = 'recent';
	let fuse: Fuse<Flow> | null = null;

	onMount(async () => {
		loaded = true;
		await fetchFlows();
	});

	const heroStats = [
		{ label: '지원 빌더', value: '3개', hint: 'Langflow · Flowise · AutoGen' },
		{ label: '평균 구축 시간', value: '15분', hint: '노코드 비주얼 설계' },
		{ label: 'LangGraph 변환', value: '자동', hint: '프로덕션 배포 지원' }
	];

	const builders = [
		{
			id: 'langflow' as const,
			name: 'Langflow',
			description: '노코드 에이전트 빌더 - LangGraph 친화적',
			icon: Cube,
			path: '/builder/langflow',
			gradientFrom: 'from-blue-500',
			gradientTo: 'to-blue-600',
			proxyUrl: 'http://localhost:7861/'
		},
		{
			id: 'flowise' as const,
			name: 'Flowise',
			description: '노코드 에이전트 빌더 - 위젯/임베드 용이',
			icon: Cube,
			path: '/builder/flowise',
			gradientFrom: 'from-green-500',
			gradientTo: 'to-green-600',
			proxyUrl: 'http://localhost:3002/'
		},
		{
			id: 'autogen' as const,
			name: 'AutoGen Studio',
			description: '대화형 워크플로 설계 - 그룹챗/멀티에이전트',
			icon: Cube,
			path: '/builder/autogen',
			gradientFrom: 'from-purple-500',
			gradientTo: 'to-purple-600',
			proxyUrl: 'http://localhost:5050/'
		}
	];

	const fetchFlows = async () => {
		if (loading || loadingMore || !hasMore) return;
		
		try {
			if (offset === 0) {
				loading = true;
			} else {
				loadingMore = true;
			}
			error = '';

			const response = await fetch(`/api/agents/flows?offset=${offset}&limit=20`);
			if (!response.ok) {
				throw new Error(`Failed to fetch flows: ${response.statusText}`);
			}

			const data = await response.json();
			flows = [...flows, ...data.flows];
			offset += data.flows.length;
			hasMore = data.has_more;

			// Initialize Fuse.js for search
			if (!fuse && flows.length > 0) {
				fuse = new Fuse(flows, {
					keys: ['name', 'description'],
					threshold: 0.3,
					includeScore: true
				});
			}
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load flows';
		} finally {
			loading = false;
			loadingMore = false;
		}
	};

	const handleSearch = () => {
		if (!searchQuery.trim()) {
			filteredFlows = [];
			isSearching = false;
			return;
		}

		isSearching = true;
		if (fuse) {
			const results = fuse.search(searchQuery);
			filteredFlows = results.map(result => result.item);
		}
	};

	const clearSearch = () => {
		searchQuery = '';
		filteredFlows = [];
		isSearching = false;
	};

	const handleBuilderFilter = (builder: typeof selectedBuilder) => {
		selectedBuilder = builder;
	};

	const handleSort = (sort: typeof sortBy) => {
		sortBy = sort;
	};

	const getDisplayFlows = (): Flow[] => {
		let displayFlows = isSearching ? filteredFlows : flows;

		// Apply builder filter (currently only Langflow is supported)
		if (selectedBuilder !== 'all') {
			// For now, show all flows since we're only proxying Langflow
			// In Phase 1-B, we can add builder metadata to flows
		}

		// Apply sorting
		if (sortBy === 'recent') {
			displayFlows = [...displayFlows].sort((a, b) => {
				const dateA = new Date(a.updated_at || 0).getTime();
				const dateB = new Date(b.updated_at || 0).getTime();
				return dateB - dateA;
			});
		} else {
			displayFlows = [...displayFlows].sort((a, b) => a.name.localeCompare(b.name));
		}

		return displayFlows;
	};

	const formatDate = (dateStr?: string) => {
		if (!dateStr) return '알 수 없음';
		const date = new Date(dateStr);
		const now = new Date();
		const diff = now.getTime() - date.getTime();
		const days = Math.floor(diff / (1000 * 60 * 60 * 24));

		if (days === 0) return '오늘';
		if (days === 1) return '어제';
		if (days < 7) return `${days}일 전`;
		if (days < 30) return `${Math.floor(days / 7)}주 전`;
		if (days < 365) return `${Math.floor(days / 30)}개월 전`;
		return `${Math.floor(days / 365)}년 전`;
	};

	const openFlowInBuilder = (flowId: string) => {
		// Open flow in Langflow (in new tab or iframe)
		window.open(`http://localhost:7861/flow/${flowId}`, '_blank');
	};

	const deleteFlow = async (flowId: string) => {
		if (!confirm('이 플로우를 삭제하시겠습니까?')) return;

		try {
			const response = await fetch(`/api/agents/flows/${flowId}`, {
				method: 'DELETE'
			});

			if (!response.ok) {
				throw new Error('Failed to delete flow');
			}

			// Remove from local state
			flows = flows.filter(f => f.id !== flowId);
			filteredFlows = filteredFlows.filter(f => f.id !== flowId);
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to delete flow';
		}
	};

	function handleBuilderSelect(builderId: 'langflow' | 'flowise' | 'autogen') {
		activeTab = builderId;
	}

	function handleIframeLoad(builderId: 'langflow' | 'flowise' | 'autogen') {
		if (builderId === 'langflow') {
			langflowLoading = false;
		} else if (builderId === 'flowise') {
			flowiseLoading = false;
		} else if (builderId === 'autogen') {
			autogenLoading = false;
		}
	}

	// Infinite scroll observer
	afterUpdate(() => {
		if (observerTarget && !observer && activeTab === 'overview') {
			observer = new IntersectionObserver(
				(entries) => {
					if (entries[0].isIntersecting && hasMore && !loadingMore) {
						fetchFlows();
					}
				},
				{ threshold: 0.1 }
			);
			observer.observe(observerTarget);
		}
	});

	onMount(() => {
		return () => {
			if (observer) observer.disconnect();
		};
	});
</script>

<svelte:head>
	<title>에이전트 빌더 | {$WEBUI_NAME}</title>
</svelte:head>

{#if loaded}
	<div class="flex w-full flex-col min-h-full px-3 py-4 @md:px-6 @md:py-6">
		<div class="flex w-full flex-col gap-6">
			<!-- Hero Section -->
			<section class="relative overflow-hidden rounded-3xl border border-white/20 bg-white/60 p-6 shadow-2xl shadow-primary/10 backdrop-blur-2xl dark:border-gray-700/30 dark:bg-gray-900/60">
				<div class="absolute inset-0 bg-gradient-to-br from-primary/20 via-secondary/10 to-accent/20 opacity-60" />
				<div class="pointer-events-none absolute -right-10 -top-12 h-40 w-40 rounded-full bg-gradient-to-br from-primary/40 to-secondary/30 blur-3xl" />
				<div class="relative flex flex-col gap-5">
					<div class="flex flex-wrap items-center gap-3">
						<span class="inline-flex items-center gap-2 rounded-full bg-white/90 px-3 py-1 text-xs font-medium text-gray-600 shadow-sm dark:bg-gray-800/80 dark:text-gray-200">
							<span class="h-1.5 w-1.5 rounded-full bg-gradient-to-r from-primary via-secondary to-accent" />
							SFN AI Agent Builder
						</span>
						<h1 class="text-2xl font-semibold tracking-tight text-gray-900 dark:text-gray-100">
							원하는 방식으로 AI 에이전트를 만들어보세요
						</h1>
					</div>

					<p class="max-w-3xl text-sm text-gray-600 dark:text-gray-300">
						노코드 빌더로 에이전트를 시각적으로 설계하고, LangGraph로 자동 변환하여 프로덕션 배포까지 한 번에 완성하세요.
					</p>

					<div class="grid grid-cols-3 gap-3 @md:grid-cols-4 @lg:grid-cols-6">
						{#each heroStats as stat}
							<div class="group relative overflow-hidden rounded-xl border border-white/20 bg-white/70 p-3 shadow-sm backdrop-blur-sm transition-all duration-300 hover:shadow-md dark:border-gray-700/30 dark:bg-gray-800/70">
								<div class="flex flex-col gap-1">
									<span class="text-xs font-medium text-gray-600 dark:text-gray-400">{stat.label}</span>
									<span class="text-xl font-medium text-gray-900 dark:text-gray-100">{stat.value}</span>
									<span class="text-xs text-gray-500 dark:text-gray-500">{stat.hint}</span>
								</div>
							</div>
						{/each}
					</div>
				</div>
			</section>

			<!-- Tab Navigation -->
			<div class="flex flex-wrap gap-2">
				<button
					on:click={() => (activeTab = 'overview')}
					class="px-4 py-2 rounded-lg {activeTab === 'overview' ? 'bg-[#0072CE] text-white shadow-sm' : 'text-gray-600 hover:bg-gray-50 dark:text-gray-300 dark:hover:bg-gray-800'} transition-all duration-200 text-sm font-medium"
				>
					플로우 목록
				</button>
				{#each builders as builder}
					<button
						on:click={() => handleBuilderSelect(builder.id)}
						class="px-4 py-2 rounded-lg {activeTab === builder.id ? 'bg-[#0072CE] text-white shadow-sm' : 'text-gray-600 hover:bg-gray-50 dark:text-gray-300 dark:hover:bg-gray-800'} transition-all duration-200 text-sm font-medium"
					>
						{builder.name}
					</button>
				{/each}
			</div>

			<!-- Flow List (Overview Tab) -->
			{#if activeTab === 'overview'}
				<div class="flex flex-col gap-6">
					<!-- Search and Filter Bar -->
					<div class="flex flex-col gap-4 @md:flex-row @md:items-center @md:justify-between">
						<!-- Search -->
						<div class="relative flex-1 max-w-2xl">
							<input
								type="text"
								bind:value={searchQuery}
								on:input={handleSearch}
								placeholder="플로우 이름, 설명으로 검색..."
								class="w-full px-5 py-3 pl-12 pr-12 rounded-xl bg-white/60 dark:bg-gray-800/60 backdrop-blur-sm border border-gray-200/50 dark:border-gray-700/50 focus:outline-none focus:ring-2 focus:ring-[#0072CE]/30 focus:border-[#0072CE] transition-all"
							/>

							<!-- Search Icon -->
							<svg
								xmlns="http://www.w3.org/2000/svg"
								class="absolute left-4 top-1/2 -translate-y-1/2 h-5 w-5 text-gray-400"
								fill="none"
								viewBox="0 0 24 24"
								stroke="currentColor"
							>
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									stroke-width="2"
									d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
								/>
							</svg>

							<!-- Clear Button -->
							{#if searchQuery}
								<button
									on:click={clearSearch}
									class="absolute right-4 top-1/2 -translate-y-1/2 p-1 rounded-full hover:bg-gray-200/50 dark:hover:bg-gray-700/50 transition-colors"
								>
									<svg
										xmlns="http://www.w3.org/2000/svg"
										class="h-5 w-5 text-gray-400"
										fill="none"
										viewBox="0 0 24 24"
										stroke="currentColor"
									>
										<path
											stroke-linecap="round"
											stroke-linejoin="round"
											stroke-width="2"
											d="M6 18L18 6M6 6l12 12"
										/>
									</svg>
								</button>
							{/if}
						</div>

						<!-- Filters -->
						<div class="flex gap-2">
							<!-- Builder Filter -->
							<select
								bind:value={selectedBuilder}
								on:change={() => handleBuilderFilter(selectedBuilder)}
								class="px-4 py-2 rounded-lg bg-white/60 dark:bg-gray-800/60 backdrop-blur-sm border border-gray-200/50 dark:border-gray-700/50 focus:outline-none focus:ring-2 focus:ring-[#0072CE]/30 focus:border-[#0072CE] transition-all text-sm"
							>
								<option value="all">모든 빌더</option>
								<option value="langflow">Langflow</option>
								<option value="flowise">Flowise</option>
								<option value="autogen">AutoGen</option>
							</select>

							<!-- Sort -->
							<select
								bind:value={sortBy}
								on:change={() => handleSort(sortBy)}
								class="px-4 py-2 rounded-lg bg-white/60 dark:bg-gray-800/60 backdrop-blur-sm border border-gray-200/50 dark:border-gray-700/50 focus:outline-none focus:ring-2 focus:ring-[#0072CE]/30 focus:border-[#0072CE] transition-all text-sm"
							>
								<option value="recent">최신순</option>
								<option value="name">이름순</option>
							</select>
						</div>
					</div>

					<!-- Search Results Count -->
					{#if isSearching}
						<p class="text-center text-sm text-gray-600 dark:text-gray-400">
							🔍 "{searchQuery}" 검색 결과: {filteredFlows.length}개
						</p>
					{/if}

					<!-- Error Message -->
					{#if error}
						<div class="p-4 rounded-xl bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800">
							<p class="text-sm text-red-600 dark:text-red-400">{error}</p>
						</div>
					{/if}

					<!-- Loading Skeleton -->
					{#if loading}
						<div class="grid grid-cols-1 @md:grid-cols-2 @lg:grid-cols-3 gap-6">
							{#each Array(6) as _}
								<div class="animate-pulse rounded-xl border border-gray-200/50 dark:border-gray-700/50 bg-white/60 dark:bg-gray-800/60 p-6 backdrop-blur-sm">
									<div class="h-6 bg-gray-200 dark:bg-gray-700 rounded w-3/4 mb-3"></div>
									<div class="h-4 bg-gray-200 dark:bg-gray-700 rounded w-full mb-2"></div>
									<div class="h-4 bg-gray-200 dark:bg-gray-700 rounded w-5/6 mb-4"></div>
									<div class="flex gap-2">
										<div class="h-8 bg-gray-200 dark:bg-gray-700 rounded w-20"></div>
										<div class="h-8 bg-gray-200 dark:bg-gray-700 rounded w-20"></div>
									</div>
								</div>
							{/each}
						</div>
					{:else}
						<!-- Flow Cards Grid -->
						<div class="grid grid-cols-1 @md:grid-cols-2 @lg:grid-cols-3 gap-6">
							{#each getDisplayFlows() as flow (flow.id)}
								<div class="group relative overflow-hidden rounded-xl border border-white/20 bg-white/60 p-6 shadow-lg backdrop-blur-2xl transition-all duration-300 hover:shadow-xl hover:scale-[1.02] dark:border-gray-700/30 dark:bg-gray-900/60">
									<!-- Card Content -->
									<div class="flex flex-col gap-4">
										<!-- Header -->
										<div class="flex items-start justify-between">
											<div class="flex-1 min-w-0">
												<h3 class="text-lg font-semibold text-gray-900 dark:text-gray-100 truncate">
													{flow.name}
												</h3>
												<p class="text-xs text-gray-500 dark:text-gray-400 mt-1">
													{formatDate(flow.updated_at)}
												</p>
											</div>
											<div class="ml-2 p-2 rounded-lg bg-gradient-to-br from-blue-500/10 to-blue-600/10">
												<Cube class="w-5 h-5 text-blue-600 dark:text-blue-400" />
											</div>
										</div>

										<!-- Description -->
										{#if flow.description}
											<p class="text-sm text-gray-600 dark:text-gray-400 line-clamp-2">
												{flow.description}
											</p>
										{/if}

										<!-- Actions -->
										<div class="flex gap-2 mt-auto">
											<button
												on:click={() => openFlowInBuilder(flow.id)}
												class="flex-1 px-3 py-2 rounded-lg bg-[#0072CE] text-white text-sm font-medium hover:bg-[#005BA3] transition-all duration-200 shadow-sm"
											>
												열기
											</button>
											<button
												on:click={() => deleteFlow(flow.id)}
												class="px-3 py-2 rounded-lg bg-red-50 text-red-600 text-sm font-medium hover:bg-red-100 transition-all duration-200 dark:bg-red-900/20 dark:text-red-400 dark:hover:bg-red-900/30"
											>
												삭제
											</button>
										</div>
									</div>
								</div>
							{/each}
						</div>

						<!-- Empty State -->
						{#if getDisplayFlows().length === 0 && !loading}
							<div class="flex flex-col items-center justify-center py-16 px-4">
								<Cube class="w-16 h-16 text-gray-400 dark:text-gray-600 mb-4" />
								<h3 class="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2">
									{isSearching ? '검색 결과가 없습니다' : '플로우가 없습니다'}
								</h3>
								<p class="text-sm text-gray-600 dark:text-gray-400 text-center max-w-md">
									{isSearching
										? '다른 검색어를 입력해보세요'
										: 'Langflow, Flowise, AutoGen Studio에서 새로운 플로우를 만들어보세요'}
								</p>
							</div>
						{/if}

						<!-- Infinite Scroll Target -->
						{#if !isSearching && hasMore}
							<div bind:this={observerTarget} class="h-20"></div>
						{/if}

						<!-- Loading More Indicator -->
						{#if loadingMore}
							<div class="flex justify-center py-8">
								<div class="animate-spin rounded-full h-8 w-8 border-b-2 border-[#0072CE]"></div>
							</div>
						{/if}
					{/if}
				</div>
			{/if}

			<!-- Builder iframes (Langflow, Flowise, AutoGen tabs) -->
			{#if activeTab === 'langflow'}
				<div class="relative h-[calc(100vh-16rem)] rounded-xl overflow-hidden border border-gray-200/50 dark:border-gray-700/50 bg-white dark:bg-gray-900">
					{#if langflowLoading}
						<div class="absolute inset-0 flex items-center justify-center bg-white dark:bg-gray-900">
							<div class="flex flex-col items-center gap-4">
								<div class="animate-spin rounded-full h-12 w-12 border-b-2 border-[#0072CE]"></div>
								<p class="text-sm text-gray-600 dark:text-gray-400">Langflow 로딩 중...</p>
							</div>
						</div>
					{/if}
					<iframe
						src={builders[0].proxyUrl}
						title="Langflow"
						class="w-full h-full"
						on:load={() => handleIframeLoad('langflow')}
						sandbox="allow-same-origin allow-scripts allow-forms allow-popups allow-modals"
					></iframe>
				</div>
			{:else if activeTab === 'flowise'}
				<div class="relative h-[calc(100vh-16rem)] rounded-xl overflow-hidden border border-gray-200/50 dark:border-gray-700/50 bg-white dark:bg-gray-900">
					{#if flowiseLoading}
						<div class="absolute inset-0 flex items-center justify-center bg-white dark:bg-gray-900">
							<div class="flex flex-col items-center gap-4">
								<div class="animate-spin rounded-full h-12 w-12 border-b-2 border-[#0072CE]"></div>
								<p class="text-sm text-gray-600 dark:text-gray-400">Flowise 로딩 중...</p>
							</div>
						</div>
					{/if}
					<iframe
						src={builders[1].proxyUrl}
						title="Flowise"
						class="w-full h-full"
						on:load={() => handleIframeLoad('flowise')}
						sandbox="allow-same-origin allow-scripts allow-forms allow-popups allow-modals"
					></iframe>
				</div>
			{:else if activeTab === 'autogen'}
				<div class="relative h-[calc(100vh-16rem)] rounded-xl overflow-hidden border border-gray-200/50 dark:border-gray-700/50 bg-white dark:bg-gray-900">
					{#if autogenLoading}
						<div class="absolute inset-0 flex items-center justify-center bg-white dark:bg-gray-900">
							<div class="flex flex-col items-center gap-4">
								<div class="animate-spin rounded-full h-12 w-12 border-b-2 border-[#0072CE]"></div>
								<p class="text-sm text-gray-600 dark:text-gray-400">AutoGen Studio 로딩 중...</p>
							</div>
						</div>
					{/if}
					<iframe
						src={builders[2].proxyUrl}
						title="AutoGen Studio"
						class="w-full h-full"
						on:load={() => handleIframeLoad('autogen')}
						sandbox="allow-same-origin allow-scripts allow-forms allow-popups allow-modals"
					></iframe>
				</div>
			{/if}
		</div>
	</div>
{/if}
