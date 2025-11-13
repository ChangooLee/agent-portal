<script lang="ts">
	import { onMount } from 'svelte';
	import { WEBUI_NAME } from '$lib/stores';
	
	interface Article {
		id: number;
		title: string;
		highlight: string;
		importance_score: number;
		tags?: string[];
		link: string;
	}
	
	interface NewsData {
		date: string;
		total_articles: number;
		total_pages: number;
		items_per_page: number;
		featured_articles: Article[];
	}
	
	interface ArticleDetail extends Article {
		content: string;
		pub_date: string;
		original_link: string;
	}
	
	let newsData: NewsData | null = null;
	let allArticles: Article[] = [];
	let selectedArticle: ArticleDetail | null = null;
	let loading = true;
	let loadingMore = false;
	let error = '';
	let showModal = false;
	let hasMore = true;
	let offset = 0;
	let observerTarget: HTMLDivElement;
	
	const formatDate = (dateStr: string) => {
		if (!dateStr) return '';
		const year = dateStr.substring(0, 4);
		const month = dateStr.substring(4, 6);
		const day = dateStr.substring(6, 8);
		return `${year}년 ${month}월 ${day}일`;
	};
	
	const getScoreBadgeColor = (score: number) => {
		if (score >= 10) return 'bg-gradient-to-r from-red-500 to-pink-500 text-white';
		if (score >= 5) return 'bg-gradient-to-r from-orange-500 to-yellow-500 text-white';
		return '';
	};
	
	const getScoreLabel = (score: number) => {
		if (score >= 10) return '🔥 HOT';
		if (score >= 5) return '⭐ 주요';
		return '';
	};
	
	const getTagColor = (index: number) => {
		const colors = [
			'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-300',
			'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300',
			'bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-300',
			'bg-pink-100 text-pink-800 dark:bg-pink-900/30 dark:text-pink-300',
			'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300'
		];
		return colors[index % colors.length];
	};
	
	const fetchTodayNews = async () => {
		try {
			loading = true;
			error = '';
			const response = await fetch('/api/news/today');
			if (!response.ok) {
				throw new Error(`Failed to fetch news: ${response.statusText}`);
			}
			newsData = await response.json();
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load news';
			console.error('Error fetching news:', e);
		} finally {
			loading = false;
		}
	};
	
	const fetchMoreArticles = async () => {
		if (loadingMore || !hasMore) return;
		
		try {
			loadingMore = true;
			const response = await fetch(`/api/news/articles?offset=${offset}&limit=20`);
			if (!response.ok) {
				throw new Error(`Failed to fetch articles: ${response.statusText}`);
			}
			const data = await response.json();
			allArticles = [...allArticles, ...data.articles];
			offset += data.articles.length;
			hasMore = data.has_more;
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load more articles';
			console.error('Error fetching more articles:', e);
		} finally {
			loadingMore = false;
		}
	};
	
	const fetchArticleDetail = async (articleId: number) => {
		try {
			const response = await fetch(`/api/news/article/${articleId}`);
			if (!response.ok) {
				throw new Error(`Failed to fetch article: ${response.statusText}`);
			}
			selectedArticle = await response.json();
			showModal = true;
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load article';
			console.error('Error fetching article:', e);
		}
	};
	
	const closeModal = () => {
		showModal = false;
		selectedArticle = null;
	};
	
	onMount(() => {
		fetchTodayNews();
		fetchMoreArticles();
		
		// Intersection Observer for infinite scroll
		const observer = new IntersectionObserver(
			(entries) => {
				if (entries[0].isIntersecting && hasMore && !loadingMore) {
					fetchMoreArticles();
				}
			},
			{ threshold: 0.1 }
		);
		
		if (observerTarget) {
			observer.observe(observerTarget);
		}
		
		return () => {
			if (observerTarget) {
				observer.unobserve(observerTarget);
			}
		};
	});
</script>

<svelte:head>
	<title>투데이 | {$WEBUI_NAME}</title>
</svelte:head>

<div class="h-full w-full flex flex-col overflow-y-auto">
	<!-- Hero Section -->
	<div class="relative overflow-hidden">
		<!-- Background Gradient -->
		<div class="absolute inset-0 bg-gradient-to-br from-blue-50/30 via-purple-50/20 to-pink-50/30 dark:from-gray-900 dark:via-blue-900/20 dark:to-purple-900/30" />
		
		<!-- Hero Content -->
		<div class="relative px-6 py-12 text-center">
			<div class="inline-flex items-center justify-center px-4 py-2 mb-4 rounded-full bg-gradient-to-r from-primary/90 to-secondary/90 text-white text-sm font-medium shadow-lg">
				<span>📰 Today's News</span>
			</div>
			
			<h1 class="text-4xl md:text-5xl font-bold text-gray-900 dark:text-white mb-4">
				오늘의 뉴스
			</h1>
			
			<p class="text-lg text-gray-600 dark:text-gray-300 max-w-2xl mx-auto">
				{#if newsData}
					{formatDate(newsData.date)} · {newsData.total_articles}개 기사
				{:else}
					Loading...
				{/if}
			</p>
		</div>
	</div>
	
	<!-- Content Section -->
	<div class="flex-1 px-6 py-8">
		<div class="max-w-7xl mx-auto">
			{#if loading}
				<div class="flex items-center justify-center py-20">
					<div class="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
				</div>
			{:else if error}
				<div class="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl p-6 text-center">
					<p class="text-red-800 dark:text-red-300 font-medium">⚠️ {error}</p>
				</div>
			{:else}
				<!-- Featured Articles Section -->
				{#if newsData && newsData.featured_articles.length > 0}
					<div class="mb-12">
						<h2 class="text-2xl font-bold text-gray-900 dark:text-white mb-6">🔥 주요 뉴스</h2>
						<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
							{#each newsData.featured_articles as article}
								<button
									class="text-left bg-gradient-to-br from-white/60 to-white/40 dark:from-gray-800/60 dark:to-gray-800/40 backdrop-blur-sm border border-gray-200/50 dark:border-gray-700/50 rounded-xl p-6 hover:shadow-xl hover:scale-[1.02] hover:border-primary/30 transition-all duration-300 ease-out cursor-pointer"
									on:click={() => fetchArticleDetail(article.id)}
								>
									<!-- Importance Badge -->
									{#if getScoreLabel(article.importance_score)}
										<div class="flex items-center mb-3">
											<span class="{getScoreBadgeColor(article.importance_score)} px-3 py-1 rounded-full text-xs font-semibold shadow-sm">
												{getScoreLabel(article.importance_score)}
											</span>
										</div>
									{/if}
									
									<!-- Title -->
									<h3 class="text-lg font-bold text-gray-900 dark:text-white mb-3 line-clamp-2">
										{article.title}
									</h3>
									
									<!-- Highlight -->
									<p class="text-sm text-gray-600 dark:text-gray-300 mb-4 line-clamp-3">
										{article.highlight}
									</p>
									
									<!-- Tags -->
									{#if article.tags && article.tags.length > 0}
										<div class="flex flex-wrap gap-2">
											{#each article.tags.slice(0, 3) as tag, index}
												<span class="{getTagColor(index)} px-2 py-1 rounded-md text-xs font-medium">
													{tag}
												</span>
											{/each}
											{#if article.tags.length > 3}
												<span class="bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400 px-2 py-1 rounded-md text-xs font-medium">
													+{article.tags.length - 3}
												</span>
											{/if}
										</div>
									{/if}
								</button>
							{/each}
						</div>
					</div>
				{/if}
				
				<!-- All Articles Section -->
				{#if allArticles.length > 0}
					<div>
						<h2 class="text-2xl font-bold text-gray-900 dark:text-white mb-6">📰 전체 뉴스 ({newsData?.total_articles || 0}개)</h2>
						<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
							{#each allArticles as article}
								<button
									class="text-left bg-white/40 dark:bg-gray-800/40 backdrop-blur-sm border border-gray-200/30 dark:border-gray-700/30 rounded-xl p-6 hover:shadow-lg hover:scale-105 transition-all duration-300 ease-out cursor-pointer"
									on:click={() => fetchArticleDetail(article.id)}
								>
									<!-- Importance Badge -->
									{#if getScoreLabel(article.importance_score)}
										<div class="flex items-center mb-3">
											<span class="{getScoreBadgeColor(article.importance_score)} px-3 py-1 rounded-full text-xs font-semibold shadow-sm">
												{getScoreLabel(article.importance_score)}
											</span>
										</div>
									{/if}
									
									<!-- Title -->
									<h3 class="text-lg font-bold text-gray-900 dark:text-white mb-3 line-clamp-2">
										{article.title}
									</h3>
									
									<!-- Highlight -->
									<p class="text-sm text-gray-600 dark:text-gray-300 line-clamp-3">
										{article.highlight}
									</p>
								</button>
							{/each}
						</div>
						
						<!-- Loading More Indicator -->
						{#if loadingMore}
							<div class="flex items-center justify-center py-12">
								<div class="animate-spin rounded-full h-10 w-10 border-b-2 border-primary"></div>
								<p class="ml-3 text-gray-600 dark:text-gray-400">더 많은 기사를 불러오는 중...</p>
							</div>
						{/if}
						
						<!-- Intersection Observer Target -->
						<div bind:this={observerTarget} class="h-4"></div>
						
						<!-- No More Articles -->
						{#if !hasMore && allArticles.length > 0}
							<div class="text-center py-8">
								<p class="text-gray-500 dark:text-gray-400">모든 기사를 불러왔습니다.</p>
							</div>
						{/if}
					</div>
				{/if}
				
				{#if !newsData?.featured_articles?.length && !allArticles.length}
					<div class="bg-gray-50 dark:bg-gray-800/50 border border-gray-200 dark:border-gray-700 rounded-xl p-12 text-center">
						<p class="text-gray-600 dark:text-gray-400">📰 오늘의 뉴스가 없습니다.</p>
					</div>
				{/if}
			{/if}
		</div>
	</div>
</div>

<!-- Modal Overlay -->
{#if showModal && selectedArticle}
	<div
		class="fixed inset-0 z-50 flex items-center justify-center backdrop-blur-md bg-black/30"
		on:click={closeModal}
		on:keydown={(e) => e.key === 'Escape' && closeModal()}
		role="button"
		tabindex="0"
	>
		<div
			class="bg-white dark:bg-gray-900 rounded-2xl shadow-2xl max-w-4xl w-full mx-4 max-h-[80vh] overflow-hidden"
			on:click|stopPropagation
			on:keydown|stopPropagation
			role="dialog"
			tabindex="-1"
		>
			<!-- Modal Header -->
			<div class="sticky top-0 bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-700 px-6 py-4 flex items-center justify-between">
				<div class="flex-1">
					<div class="flex items-center gap-2 mb-2">
						<span class="{getScoreBadgeColor(selectedArticle.importance_score)} px-3 py-1 rounded-full text-xs font-semibold">
							{getScoreLabel(selectedArticle.importance_score)}
						</span>
						{#if selectedArticle.tags && selectedArticle.tags.length > 0}
							{#each selectedArticle.tags.slice(0, 3) as tag, index}
								<span class="{getTagColor(index)} px-2 py-1 rounded-md text-xs font-medium">
									{tag}
								</span>
							{/each}
						{/if}
					</div>
					<h2 class="text-2xl font-bold text-gray-900 dark:text-white">
						{selectedArticle.title}
					</h2>
				</div>
				<button
					class="ml-4 p-2 hover:bg-gray-100 dark:hover:bg-gray-800 rounded-lg transition-colors"
					on:click={closeModal}
					aria-label="Close"
				>
					<svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
					</svg>
				</button>
			</div>
			
			<!-- Modal Content -->
			<div class="overflow-y-auto max-h-[calc(80vh-8rem)] px-6 py-6">
				<!-- Highlight -->
				<div class="bg-blue-50 dark:bg-blue-900/20 border-l-4 border-blue-500 p-4 mb-6">
					<p class="text-sm text-blue-900 dark:text-blue-200 font-medium">
						{selectedArticle.highlight}
					</p>
				</div>
				
				<!-- Content -->
				<div class="prose prose-sm dark:prose-invert max-w-none">
					<div class="text-gray-700 dark:text-gray-300 whitespace-pre-wrap leading-relaxed">
						{selectedArticle.content}
					</div>
				</div>
				
				<!-- Original Link -->
				{#if selectedArticle.original_link}
					<div class="mt-6 pt-6 border-t border-gray-200 dark:border-gray-700">
						<a
							href={selectedArticle.original_link}
							target="_blank"
							rel="noopener noreferrer"
							class="inline-flex items-center gap-2 text-primary hover:text-primary-dark transition-colors"
						>
							<span>원문 보기</span>
							<svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
							</svg>
						</a>
					</div>
				{/if}
			</div>
		</div>
	</div>
{/if}

<style>
	.line-clamp-2 {
		display: -webkit-box;
		-webkit-line-clamp: 2;
		-webkit-box-orient: vertical;
		overflow: hidden;
	}
	
	.line-clamp-3 {
		display: -webkit-box;
		-webkit-line-clamp: 3;
		-webkit-box-orient: vertical;
		overflow: hidden;
	}
</style>

