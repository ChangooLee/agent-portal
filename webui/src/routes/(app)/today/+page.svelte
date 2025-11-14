<script lang="ts">
	import { onMount, afterUpdate } from 'svelte';
	import { WEBUI_NAME } from '$lib/stores';
	
	interface Article {
		id: number;
		title: string;
		highlight: string;
		importance_score: number;
		tags?: string[];
		category?: string;
		link: string;
	}
	
	interface CategoryStatistics {
		total_categories: number;
		category_list: string[];
		category_distribution: Record<string, number>;
		top_categories: Array<{ category: string; count: number; percentage: number }>;
	}
	
	interface NewsData {
		date: string;
		total_articles: number;
		total_pages: number;
		items_per_page: number;
		featured_articles: Article[];
		category_statistics?: CategoryStatistics;
	}
	
	interface ArticleDetail extends Article {
		content: string;
		pub_date: string;
		original_link: string;
	}
	
	let newsData: NewsData | null = null;
	let allArticles: Article[] = [];
	let filteredArticles: Article[] = [];
	let selectedArticle: ArticleDetail | null = null;
	let loading = true;
	let loadingMore = false;
	let error = '';
	let showModal = false;
	let hasMore = true;
	let offset = 0;
	let observerTarget: HTMLDivElement;
	let observer: IntersectionObserver | null = null;
	let searchQuery = '';
	let isSearching = false;
	let selectedTags: string[] = [];
	let selectedCategories: string[] = [];
	let topTags: Array<{ tag: string; count: number }> = [];
	let categories: Array<{ category: string; count: number; isActive: boolean }> = [];
	
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
		} finally {
			loading = false;
		}
	};
	
		const fetchMoreArticles = async () => {
		if (loadingMore || !hasMore) {
			return;
		}
		
		try {
			loadingMore = true;
			const response = await fetch(`/api/news/articles?offset=${offset}&limit=20`);
			if (!response.ok) {
				throw new Error(`Failed to fetch articles: ${response.statusText}`);
			}
			const data = await response.json();
			
			// 백엔드에서 이미 featured articles를 제외하고 있으므로 필터링 불필요
			allArticles = [...allArticles, ...data.articles];
			offset += data.articles.length;
			hasMore = data.has_more;
			
			// 태그 및 카테고리 재계산 (새 기사 로드 후)
			calculateTopTags();
			if (newsData || allArticles.length > 0) {
				calculateCategories();
			}
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load more articles';
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
		}
	};
	
	const closeModal = () => {
		showModal = false;
		selectedArticle = null;
	};
	
	const handleSearch = () => {
		if (!searchQuery.trim()) {
			filteredArticles = [];
			isSearching = false;
			selectedTags = []; // 검색 해제 시 태그 필터도 해제
			selectedCategories = []; // 검색 해제 시 카테고리 필터도 해제
			return;
		}
		
		isSearching = true;
		selectedTags = []; // 검색 시 태그 필터 해제
		selectedCategories = []; // 검색 시 카테고리 필터 해제
		const query = searchQuery.toLowerCase().trim();
		
		// Featured articles에서 검색
		const featuredResults = newsData?.featured_articles.filter(article => 
			article.title.toLowerCase().includes(query) || 
			article.highlight.toLowerCase().includes(query) ||
			article.tags?.some(tag => tag.toLowerCase().includes(query))
		) || [];
		
		// All articles에서 검색
		const allResults = allArticles.filter(article => 
			article.title.toLowerCase().includes(query) || 
			article.highlight.toLowerCase().includes(query) ||
			article.tags?.some(tag => tag.toLowerCase().includes(query))
		);
		
		// 중복 제거 (featured articles가 all articles에도 포함될 수 있음)
		const allIds = new Set(allResults.map(a => a.id));
		const uniqueFeatured = featuredResults.filter(a => !allIds.has(a.id));
		
		// 중요도순 정렬
		filteredArticles = [...uniqueFeatured, ...allResults].sort(
			(a, b) => b.importance_score - a.importance_score
		);
	};
	
	const clearSearch = () => {
		searchQuery = '';
		filteredArticles = [];
		isSearching = false;
		selectedTags = []; // 검색 해제 시 태그 필터도 해제
		selectedCategories = []; // 검색 해제 시 카테고리 필터도 해제
	};
	
	// 태그 카운팅 및 상위 10개 선택
	const calculateTopTags = () => {
		const tagCounts = new Map<string, Set<number>>();
		
		// Featured articles의 태그 카운팅 (기사 ID 저장)
		if (newsData?.featured_articles) {
			newsData.featured_articles.forEach(article => {
				article.tags?.forEach(tag => {
					if (!tagCounts.has(tag)) {
						tagCounts.set(tag, new Set());
					}
					tagCounts.get(tag)!.add(article.id);
				});
			});
		}
		
		// All articles의 태그 카운팅 (featured articles와 중복되지 않는 기사만)
		const featuredIds = new Set(newsData?.featured_articles?.map(a => a.id) || []);
		allArticles.forEach(article => {
			// featured articles에 포함되지 않은 기사만 카운팅
			if (!featuredIds.has(article.id)) {
				article.tags?.forEach(tag => {
					if (!tagCounts.has(tag)) {
						tagCounts.set(tag, new Set());
					}
					tagCounts.get(tag)!.add(article.id);
				});
			}
		});
		
		// 상위 10개 태그 선택 (고유 기사 수 기준)
		topTags = Array.from(tagCounts.entries())
			.map(([tag, articleIds]) => ({ tag, count: articleIds.size }))
			.sort((a, b) => b.count - a.count)
			.slice(0, 10);
	};
	
	// 카테고리 카운팅 및 목록 생성 (meta.json 기반)
	const calculateCategories = () => {
		// meta.json에서 전체 카테고리 목록 가져오기
		const metaCategories = newsData?.category_statistics?.top_categories || [];
		
		// 로드된 기사에서 실제로 존재하는 카테고리 추출
		const loadedCategorySet = new Set<string>();
		
		// Featured articles의 카테고리
		if (newsData?.featured_articles) {
			newsData.featured_articles.forEach(article => {
				const cat = (article as Article).category;
				if (cat && cat.trim()) {
					loadedCategorySet.add(cat);
				}
			});
		}
		
		// All articles의 카테고리
		allArticles.forEach(article => {
			const cat = (article as Article).category;
			if (cat && cat.trim()) {
				loadedCategorySet.add(cat);
			}
		});
		
		// 카테고리별 실제 카운팅 (로드된 기사 기준)
		const categoryCounts = new Map<string, Set<number>>();
		
		// Featured articles의 카테고리 카운팅
		if (newsData?.featured_articles) {
			newsData.featured_articles.forEach(article => {
				const cat = (article as Article).category;
				if (cat && cat.trim()) {
					if (!categoryCounts.has(cat)) {
						categoryCounts.set(cat, new Set());
					}
					categoryCounts.get(cat)!.add(article.id);
				}
			});
		}
		
		// All articles의 카테고리 카운팅 (featured articles와 중복되지 않는 기사만)
		const featuredIds = new Set(newsData?.featured_articles?.map(a => a.id) || []);
		allArticles.forEach(article => {
			const cat = (article as Article).category;
			if (cat && cat.trim() && !featuredIds.has(article.id)) {
				if (!categoryCounts.has(cat)) {
					categoryCounts.set(cat, new Set());
				}
				categoryCounts.get(cat)!.add(article.id);
			}
		});
		
		// meta.json의 전체 카테고리 목록을 기반으로 카테고리 목록 생성
		// 로드된 기사에 있는 카테고리는 활성화, 없는 카테고리는 비활성화
		categories = metaCategories.map(metaCat => {
			const loadedCount = categoryCounts.get(metaCat.category)?.size || 0;
			const isActive = loadedCategorySet.has(metaCat.category);
			
			return {
				category: metaCat.category,
				count: loadedCount > 0 ? loadedCount : metaCat.count, // 로드된 기사 수 또는 전체 기사 수
				isActive: isActive
			};
		});
	};
	
	// 태그/카테고리 필터링 적용
	const applyFilters = () => {
		// 검색 중이면 필터링하지 않음
		if (isSearching) {
			return;
		}
		
		// 필터가 없으면 초기화
		if (selectedTags.length === 0 && selectedCategories.length === 0) {
			filteredArticles = [];
			return;
		}
		
		// Featured articles에서 필터링
		const featuredResults = newsData?.featured_articles.filter(article => {
			// 태그 필터 (OR 조건: 선택된 태그 중 하나라도 포함)
			const tagMatch = selectedTags.length === 0 || 
				selectedTags.some(tag => article.tags?.includes(tag));
			
			// 카테고리 필터 (OR 조건: 선택된 카테고리 중 하나라도 일치)
			const categoryMatch = selectedCategories.length === 0 || 
				selectedCategories.includes(article.category || '');
			
			return tagMatch && categoryMatch;
		}) || [];
		
		// All articles에서 필터링
		const allResults = allArticles.filter(article => {
			// 태그 필터 (OR 조건)
			const tagMatch = selectedTags.length === 0 || 
				selectedTags.some(tag => article.tags?.includes(tag));
			
			// 카테고리 필터 (OR 조건)
			const categoryMatch = selectedCategories.length === 0 || 
				selectedCategories.includes(article.category || '');
			
			return tagMatch && categoryMatch;
		});
		
		// 중복 제거
		const allIds = new Set(allResults.map(a => a.id));
		const uniqueFeatured = featuredResults.filter(a => !allIds.has(a.id));
		
		// 중요도순 정렬
		filteredArticles = [...uniqueFeatured, ...allResults].sort(
			(a, b) => b.importance_score - a.importance_score
		);
	};
	
	// 태그 토글 핸들러 (복수 선택)
	const handleTagToggle = (tag: string) => {
		isSearching = false;
		searchQuery = '';
		
		// 태그 토글
		if (selectedTags.includes(tag)) {
			selectedTags = selectedTags.filter(t => t !== tag);
		} else {
			selectedTags = [...selectedTags, tag];
		}
		
		// 필터 적용
		applyFilters();
	};
	
	// 카테고리 토글 핸들러 (복수 선택)
	const handleCategoryToggle = (category: string) => {
		// 비활성화된 카테고리는 클릭 불가
		const categoryData = categories.find(c => c.category === category);
		if (!categoryData || !categoryData.isActive) {
			return;
		}
		
		isSearching = false;
		searchQuery = '';
		
		// 카테고리 토글
		if (selectedCategories.includes(category)) {
			selectedCategories = selectedCategories.filter(c => c !== category);
		} else {
			selectedCategories = [...selectedCategories, category];
		}
		
		// 필터 적용
		applyFilters();
	};
	
	onMount(async () => {
		await fetchTodayNews();
		await fetchMoreArticles();
		// 태그 및 카테고리 계산 (데이터 로드 후)
		calculateTopTags();
		// 카테고리 계산은 데이터가 있을 때만
		if (newsData || allArticles.length > 0) {
			calculateCategories();
		}
	});
	
	// Setup observer after DOM is ready
	afterUpdate(() => {
		if (observerTarget && !observer) {
			observer = new IntersectionObserver(
				(entries) => {
					if (entries[0].isIntersecting && hasMore && !loadingMore) {
						fetchMoreArticles();
					}
				},
				{ threshold: 0.1, rootMargin: '100px' }
			);
			
			observer.observe(observerTarget);
		}
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
		<div class="relative px-6 py-4 text-center">
			<div class="inline-flex items-center justify-center px-6 py-3 mb-2 rounded-full bg-gradient-to-r from-primary/90 to-secondary/90 text-white text-base font-semibold shadow-lg">
				<span>📰 Today's News</span>
			</div>
			
			<p class="text-sm text-gray-600 dark:text-gray-300">
				{#if newsData}
					{formatDate(newsData.date)} · {newsData.total_articles}개 기사
				{:else}
					Loading...
				{/if}
			</p>
		</div>
	</div>
	
	<!-- Content Section -->
	<div class="flex-1 px-6 py-4">
		<div class="max-w-7xl mx-auto">
			<!-- Search Bar -->
			<div class="mb-6">
				<div class="relative max-w-2xl mx-auto">
					<input
						type="text"
						bind:value={searchQuery}
						on:input={handleSearch}
						placeholder="제목, 내용, 태그로 검색..."
						class="w-full px-5 py-3 pl-12 pr-12 rounded-xl bg-white/60 dark:bg-gray-800/60 backdrop-blur-sm border border-gray-200/50 dark:border-gray-700/50 focus:outline-none focus:ring-2 focus:ring-primary/30 focus:border-primary transition-all text-gray-900 dark:text-white placeholder-gray-500 dark:placeholder-gray-400"
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
							aria-label="Clear search"
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
				<!-- Search Results Count -->
				{#if isSearching}
					<p class="text-center mt-3 text-sm text-gray-600 dark:text-gray-400">
						🔍 "{searchQuery}" 검색 결과: {filteredArticles.length}개
					</p>
				{/if}
			</div>
			
			{#if loading}
				<div class="flex items-center justify-center py-20">
					<div class="animate-spin rounded-full h-12 w-12 border-b-2 border-primary"></div>
				</div>
			{:else if error}
				<div class="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-xl p-6 text-center">
					<p class="text-red-800 dark:text-red-300 font-medium">⚠️ {error}</p>
				</div>
			{:else if isSearching}
				<!-- Search Results Section -->
				{#if filteredArticles.length > 0}
					<div>
						<h2 class="text-2xl font-bold text-gray-900 dark:text-white mb-6">🔍 검색 결과 ({filteredArticles.length}개)</h2>
						<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
							{#each filteredArticles as article}
								<button
									class="text-left bg-white/50 dark:bg-gray-800/50 backdrop-blur-sm border border-primary/20 dark:border-primary-light/20 rounded-xl p-6 hover:shadow-xl hover:scale-[1.02] hover:border-primary/40 transition-all duration-300 ease-out cursor-pointer"
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
									
									<!-- Title (highlight search term) -->
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
											{#each article.tags as tag, index}
												<span class="{getTagColor(index)} px-2 py-1 rounded-md text-xs font-medium">
													{tag}
												</span>
											{/each}
										</div>
									{/if}
								</button>
							{/each}
						</div>
					</div>
				{:else}
					<div class="bg-gray-50 dark:bg-gray-800/50 border border-gray-200 dark:border-gray-700 rounded-xl p-12 text-center">
						<p class="text-gray-600 dark:text-gray-400">🔍 "{searchQuery}"에 대한 검색 결과가 없습니다.</p>
					</div>
				{/if}
			{:else}
				<!-- Tags and Categories Filter Section -->
				<div class="mb-8 space-y-6">
					<!-- Tags Section (제목 우측에 태그 배치) -->
					{#if topTags.length > 0}
						<div class="flex items-center gap-4 flex-wrap">
							<h3 class="text-lg font-semibold text-gray-700 dark:text-gray-300 whitespace-nowrap">🏷️ 인기 태그</h3>
							<div class="flex flex-wrap gap-2 flex-1">
								{#each topTags as { tag, count }}
									<button
										on:click={() => handleTagToggle(tag)}
										class="px-3 py-1.5 rounded-full text-xs font-medium backdrop-blur-sm transition-all duration-200 ease-out cursor-pointer {selectedTags.includes(tag)
											? 'bg-gradient-to-r from-primary/90 to-secondary/90 text-white border-2 border-primary shadow-md scale-105' 
											: 'bg-white/70 dark:bg-gray-800/70 text-blue-700 dark:text-blue-300 border border-blue-300/50 dark:border-blue-600/50 hover:bg-blue-50 dark:hover:bg-blue-900/30 hover:border-blue-400 dark:hover:border-blue-500 hover:shadow-md transition-all'}"
									>
										<span>{tag}</span>
										<span class="ml-1.5 text-[10px] opacity-70">({count})</span>
									</button>
								{/each}
							</div>
						</div>
					{/if}
					
					<!-- Categories Section (제목 우측에 카테고리 배치) -->
					<div>
						<!-- 카테고리 설명 (당구장 표시) -->
						<div class="mb-2">
							<p class="text-xs text-gray-500 dark:text-gray-400 border-l-2 border-dashed border-gray-300 dark:border-gray-600 pl-3">
								스크롤하여 더 많은 카테고리 기사를 불러오면 활성화됩니다
							</p>
						</div>
						<div class="flex items-center gap-4 flex-wrap">
							<h3 class="text-lg font-semibold text-gray-700 dark:text-gray-300 whitespace-nowrap">📂 카테고리</h3>
							{#if categories.length > 0}
								<div class="flex flex-wrap gap-2 flex-1">
									{#each categories as { category, count, isActive }}
										<button
											on:click={() => handleCategoryToggle(category)}
											class="px-3 py-1.5 rounded-full text-xs font-medium backdrop-blur-sm transition-all duration-200 ease-out {!isActive 
												? 'opacity-30 cursor-not-allowed bg-gray-100/50 dark:bg-gray-800/30 text-gray-400 dark:text-gray-600 border border-gray-200/50 dark:border-gray-700/50'
												: selectedCategories.includes(category)
													? 'bg-gradient-to-r from-indigo-500 to-purple-500 text-white border-2 border-indigo-400 shadow-md scale-105 cursor-pointer' 
													: 'bg-white/70 dark:bg-gray-800/70 text-indigo-700 dark:text-indigo-300 border border-indigo-300/50 dark:border-indigo-600/50 hover:bg-indigo-50 dark:hover:bg-indigo-900/30 hover:border-indigo-400 dark:hover:border-indigo-500 hover:shadow-md cursor-pointer'}"
										>
											<span>{category}</span>
											<span class="ml-1.5 text-[10px] opacity-70">({count})</span>
										</button>
									{/each}
								</div>
							{:else}
								<p class="text-sm text-gray-500 dark:text-gray-400">카테고리 데이터를 불러오는 중...</p>
							{/if}
						</div>
					</div>
					
					<!-- Selected Filters Display -->
					{#if selectedTags.length > 0 || selectedCategories.length > 0}
						<div class="flex flex-wrap items-center gap-3 text-sm text-gray-600 dark:text-gray-400 bg-gray-50 dark:bg-gray-800/50 rounded-lg px-4 py-3">
							{#if selectedTags.length > 0}
								<div class="flex items-center gap-2">
									<span class="font-medium">태그:</span>
									<div class="flex flex-wrap gap-2">
										{#each selectedTags as tag}
											<span class="px-2 py-1 rounded-md bg-primary/20 text-primary dark:bg-primary-light/20 dark:text-primary-light text-xs font-medium">
												{tag}
											</span>
										{/each}
									</div>
								</div>
							{/if}
							{#if selectedCategories.length > 0}
								<div class="flex items-center gap-2">
									<span class="font-medium">카테고리:</span>
									<div class="flex flex-wrap gap-2">
										{#each selectedCategories as category}
											<span class="px-2 py-1 rounded-md bg-green-500/20 text-green-700 dark:bg-green-500/20 dark:text-green-300 text-xs font-medium">
												{category}
											</span>
										{/each}
									</div>
								</div>
							{/if}
							<span class="ml-auto font-semibold text-primary dark:text-primary-light">
								{filteredArticles.length}개 기사
							</span>
						</div>
					{/if}
				</div>
				
				<!-- Featured Articles Section -->
				{#if newsData && newsData.featured_articles.length > 0 && selectedTags.length === 0 && selectedCategories.length === 0}
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
											{#each article.tags as tag, index}
												<span class="{getTagColor(index)} px-2 py-1 rounded-md text-xs font-medium">
													{tag}
												</span>
											{/each}
										</div>
									{/if}
								</button>
							{/each}
						</div>
					</div>
				{/if}
				
				<!-- Filtered Articles Section -->
				{#if (selectedTags.length > 0 || selectedCategories.length > 0) && filteredArticles.length > 0}
					<div class="mb-12">
						<h2 class="text-2xl font-bold text-gray-900 dark:text-white mb-6">
							필터링된 기사 ({filteredArticles.length}개)
						</h2>
						<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
							{#each filteredArticles as article}
								<button
									class="text-left bg-white/50 dark:bg-gray-800/50 backdrop-blur-sm border border-primary/20 dark:border-primary-light/20 rounded-xl p-6 hover:shadow-xl hover:scale-[1.02] hover:border-primary/40 transition-all duration-300 ease-out cursor-pointer"
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
											{#each article.tags as tag, index}
												<span class="{getTagColor(index)} px-2 py-1 rounded-md text-xs font-medium">
													{tag}
												</span>
											{/each}
										</div>
									{/if}
								</button>
							{/each}
						</div>
					</div>
				{:else if (selectedTags.length > 0 || selectedCategories.length > 0) && filteredArticles.length === 0}
					<div class="bg-gray-50 dark:bg-gray-800/50 border border-gray-200 dark:border-gray-700 rounded-xl p-12 text-center">
						<p class="text-gray-600 dark:text-gray-400">선택한 필터 조건에 맞는 기사가 없습니다.</p>
					</div>
				{/if}
				
				<!-- All Articles Section -->
				{#if allArticles.length > 0 && selectedTags.length === 0 && selectedCategories.length === 0}
					<div>
						<h2 class="text-2xl font-bold text-gray-900 dark:text-white mb-6">
							📰 전체 뉴스 ({allArticles.length}개 / 전체 {newsData?.total_articles || 0}개)
						</h2>
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
									<p class="text-sm text-gray-600 dark:text-gray-300 mb-4 line-clamp-3">
										{article.highlight}
									</p>
									
									<!-- Tags -->
									{#if article.tags && article.tags.length > 0}
										<div class="flex flex-wrap gap-2">
											{#each article.tags as tag, index}
												<span class="{getTagColor(index)} px-2 py-1 rounded-md text-xs font-medium">
													{tag}
												</span>
											{/each}
										</div>
									{/if}
								</button>
							{/each}
						</div>
						
						<!-- Intersection Observer Target (positioned before loading indicator) -->
						{#if hasMore}
							<div bind:this={observerTarget} class="h-20 w-full"></div>
						{/if}
						
						<!-- Loading More Indicator -->
						{#if loadingMore}
							<div class="flex items-center justify-center py-12">
								<div class="animate-spin rounded-full h-10 w-10 border-b-2 border-primary"></div>
								<p class="ml-3 text-gray-600 dark:text-gray-400">더 많은 기사를 불러오는 중...</p>
							</div>
						{/if}
						
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

