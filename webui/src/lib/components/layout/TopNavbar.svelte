<script lang="ts">
	import { getContext } from 'svelte';
	import {
		WEBUI_NAME,
		showSidebar,
		user,
		chatId,
		models
	} from '$lib/stores';

	import { page } from '$app/stores';
	import { goto } from '$app/navigation';

	import ModelSelector from '../chat/ModelSelector.svelte';
	import Tooltip from '../common/Tooltip.svelte';
	import UserMenu from './Sidebar/UserMenu.svelte';
	import MenuLines from '../icons/MenuLines.svelte';
	import PencilSquare from '../icons/PencilSquare.svelte';
	import DocumentChartBar from '../icons/DocumentChartBar.svelte';
	import Cube from '../icons/Cube.svelte';
	import BookOpen from '../icons/BookOpen.svelte';
	import Search from '../icons/Search.svelte';
	import ChartBar from '../icons/ChartBar.svelte';
	import Calendar from '../icons/Calendar.svelte';
	import Cog6Solid from '../icons/Cog6Solid.svelte';
	import Newspaper from '../icons/Newspaper.svelte';

	const i18n = getContext('i18n');

	// 메인 채팅 페이지에서 사용할 selectedModels (기본값)
	let selectedModels = $models.length > 0 ? [$models[0].id] : [''];
	
	$: if ($models.length > 0 && selectedModels.length === 0) {
		selectedModels = [$models[0].id];
	}

	const initNewChat = async () => {
		chatId.set('');
		await goto('/', { replaceState: false, noScroll: false, keepFocus: false, invalidateAll: true });
	};
</script>

<nav class="sticky top-0 z-50 w-full py-2 flex flex-col items-center drag-region bg-white/70 dark:bg-gray-900/70 backdrop-blur-xl shadow-lg border-b border-white/20 dark:border-gray-700/20">
	<div class="flex items-center w-full px-1.5">
		<div class=" flex max-w-full w-full mx-auto px-1 pt-0.5 bg-transparent">
			<div class="flex items-center w-full max-w-full">
				<div
					class="{$showSidebar
						? 'md:hidden'
						: ''} mr-1 self-start flex flex-none items-center text-gray-600"
				>
				<button
					id="sidebar-toggle-button"
					class="cursor-pointer px-3 py-2 flex rounded-xl bg-white/50 dark:bg-gray-800/50 hover:bg-white/70 dark:hover:bg-gray-800/70 backdrop-blur-md border border-gray-200/30 dark:border-gray-700/30 shadow-md hover:shadow-lg transform hover:scale-105 transition-all duration-300 ease-out text-gray-600 dark:text-gray-200"
					on:click={() => {
						showSidebar.set(!$showSidebar);
					}}
					aria-label="Toggle Sidebar"
				>
						<div class=" m-auto self-center">
							<MenuLines />
						</div>
					</button>
				</div>

				<div
					class="flex-1 overflow-hidden max-w-full py-0.5
			{$showSidebar ? 'ml-1' : ''}
			"
				>
					<div class="flex items-center gap-2 overflow-x-auto scrollbar-none">
						<!-- <div class="flex-shrink-0">
							<ModelSelector bind:selectedModels showSetDefault={false} />
						</div> -->
						
					<!-- Navigation Menu Buttons -->
					<a
						href="/today"
						class="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium transition-all duration-300 ease-out {$page.url.pathname.startsWith('/today')
							? 'bg-gradient-to-br from-primary/90 via-secondary/90 to-accent/90 dark:from-primary-light/80 dark:via-secondary-light/80 dark:to-accent-light/80 text-white backdrop-blur-md shadow-lg shadow-primary/30 dark:shadow-primary-light/20 border border-white/20 dark:border-gray-700/20 transform scale-105'
							: 'bg-white/40 dark:bg-gray-800/40 text-gray-700 dark:text-gray-200 backdrop-blur-sm hover:bg-white/60 dark:hover:bg-gray-800/60 border border-gray-200/30 dark:border-gray-700/30 hover:shadow-md hover:scale-105'}"
						title="투데이"
					>
						<Newspaper className="size-4" />
						<span class="hidden sm:inline">투데이</span>
					</a>
					
					<a
						href="/report"
						class="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium transition-all duration-300 ease-out {$page.url.pathname.startsWith('/report')
							? 'bg-gradient-to-br from-primary/90 via-secondary/90 to-accent/90 dark:from-primary-light/80 dark:via-secondary-light/80 dark:to-accent-light/80 text-white backdrop-blur-md shadow-lg shadow-primary/30 dark:shadow-primary-light/20 border border-white/20 dark:border-gray-700/20 transform scale-105'
							: 'bg-white/40 dark:bg-gray-800/40 text-gray-700 dark:text-gray-200 backdrop-blur-sm hover:bg-white/60 dark:hover:bg-gray-800/60 border border-gray-200/30 dark:border-gray-700/30 hover:shadow-md hover:scale-105'}"
						title="보고서"
					>
						<DocumentChartBar className="size-4" />
						<span class="hidden sm:inline">보고서</span>
					</a>
					
					<a
						href="/agent"
						class="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium transition-all duration-300 ease-out {$page.url.pathname.startsWith('/agent')
							? 'bg-gradient-to-br from-primary/90 via-secondary/90 to-accent/90 dark:from-primary-light/80 dark:via-secondary-light/80 dark:to-accent-light/80 text-white backdrop-blur-md shadow-lg shadow-primary/30 dark:shadow-primary-light/20 border border-white/20 dark:border-gray-700/20 transform scale-105'
							: 'bg-white/40 dark:bg-gray-800/40 text-gray-700 dark:text-gray-200 backdrop-blur-sm hover:bg-white/60 dark:hover:bg-gray-800/60 border border-gray-200/30 dark:border-gray-700/30 hover:shadow-md hover:scale-105'}"
						title="에이전트"
					>
						<Cube className="size-4" />
						<span class="hidden sm:inline">에이전트</span>
					</a>
					
					<a
						href="/notebook"
						class="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium transition-all duration-300 ease-out {$page.url.pathname.startsWith('/notebook')
							? 'bg-gradient-to-br from-primary/90 via-secondary/90 to-accent/90 dark:from-primary-light/80 dark:via-secondary-light/80 dark:to-accent-light/80 text-white backdrop-blur-md shadow-lg shadow-primary/30 dark:shadow-primary-light/20 border border-white/20 dark:border-gray-700/20 transform scale-105'
							: 'bg-white/40 dark:bg-gray-800/40 text-gray-700 dark:text-gray-200 backdrop-blur-sm hover:bg-white/60 dark:hover:bg-gray-800/60 border border-gray-200/30 dark:border-gray-700/30 hover:shadow-md hover:scale-105'}"
						title="노트북"
					>
						<BookOpen className="size-4" />
						<span class="hidden sm:inline">노트북</span>
					</a>
					
					<a
						href="/search"
						class="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium transition-all duration-300 ease-out {$page.url.pathname.startsWith('/search')
							? 'bg-gradient-to-br from-primary/90 via-secondary/90 to-accent/90 dark:from-primary-light/80 dark:via-secondary-light/80 dark:to-accent-light/80 text-white backdrop-blur-md shadow-lg shadow-primary/30 dark:shadow-primary-light/20 border border-white/20 dark:border-gray-700/20 transform scale-105'
							: 'bg-white/40 dark:bg-gray-800/40 text-gray-700 dark:text-gray-200 backdrop-blur-sm hover:bg-white/60 dark:hover:bg-gray-800/60 border border-gray-200/30 dark:border-gray-700/30 hover:shadow-md hover:scale-105'}"
						title="검색"
					>
						<Search className="size-4" />
						<span class="hidden sm:inline">검색</span>
					</a>
					
					{#if $user?.role === 'admin'}
						<a
							href="/usage"
							class="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium transition-all duration-300 ease-out {$page.url.pathname.startsWith('/usage')
								? 'bg-gradient-to-br from-primary/90 via-secondary/90 to-accent/90 dark:from-primary-light/80 dark:via-secondary-light/80 dark:to-accent-light/80 text-white backdrop-blur-md shadow-lg shadow-primary/30 dark:shadow-primary-light/20 border border-white/20 dark:border-gray-700/20 transform scale-105'
								: 'bg-white/40 dark:bg-gray-800/40 text-gray-700 dark:text-gray-200 backdrop-blur-sm hover:bg-white/60 dark:hover:bg-gray-800/60 border border-gray-200/30 dark:border-gray-700/30 hover:shadow-md hover:scale-105'}"
							title="사용량"
						>
							<ChartBar className="size-4" />
							<span class="hidden sm:inline">사용량</span>
						</a>
					{/if}
					
					<a
						href="/schedule"
						class="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium transition-all duration-300 ease-out {$page.url.pathname.startsWith('/schedule')
							? 'bg-gradient-to-br from-primary/90 via-secondary/90 to-accent/90 dark:from-primary-light/80 dark:via-secondary-light/80 dark:to-accent-light/80 text-white backdrop-blur-md shadow-lg shadow-primary/30 dark:shadow-primary-light/20 border border-white/20 dark:border-gray-700/20 transform scale-105'
							: 'bg-white/40 dark:bg-gray-800/40 text-gray-700 dark:text-gray-200 backdrop-blur-sm hover:bg-white/60 dark:hover:bg-gray-800/60 border border-gray-200/30 dark:border-gray-700/30 hover:shadow-md hover:scale-105'}"
						title="일정관리"
					>
						<Calendar className="size-4" />
						<span class="hidden sm:inline">일정관리</span>
					</a>
					
					{#if $user?.role === 'admin'}
						<a
							href="/admin"
							class="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium transition-all duration-300 ease-out {$page.url.pathname.startsWith('/admin')
								? 'bg-gradient-to-br from-primary/90 via-secondary/90 to-accent/90 dark:from-primary-light/80 dark:via-secondary-light/80 dark:to-accent-light/80 text-white backdrop-blur-md shadow-lg shadow-primary/30 dark:shadow-primary-light/20 border border-white/20 dark:border-gray-700/20 transform scale-105'
								: 'bg-white/40 dark:bg-gray-800/40 text-gray-700 dark:text-gray-200 backdrop-blur-sm hover:bg-white/60 dark:hover:bg-gray-800/60 border border-gray-200/30 dark:border-gray-700/30 hover:shadow-md hover:scale-105'}"
							title="관리자"
						>
							<Cog6Solid className="size-4" />
							<span class="hidden sm:inline">관리자</span>
						</a>
					{/if}
					</div>
				</div>

				<div class="self-start flex flex-none items-center text-gray-600">
				<Tooltip content="New Chat">
					<button
						id="new-chat-button"
						class=" flex {$showSidebar
							? 'md:hidden'
							: ''} cursor-pointer px-3 py-2 rounded-xl bg-white/50 dark:bg-gray-800/50 hover:bg-white/70 dark:hover:bg-gray-800/70 backdrop-blur-md border border-gray-200/30 dark:border-gray-700/30 shadow-md hover:shadow-lg transform hover:scale-105 transition-all duration-300 ease-out text-gray-600 dark:text-gray-200"
						on:click={() => {
							initNewChat();
						}}
						aria-label="New Chat"
					>
							<div class=" m-auto self-center">
								<PencilSquare className=" size-5" strokeWidth="2" />
							</div>
						</button>
					</Tooltip>

					{#if $user !== undefined && $user !== null}
						<UserMenu
							className="max-w-[200px]"
							role={$user?.role}
							on:show={(e) => {
								// Handle menu actions if needed
							}}
						>
						<button
							class="select-none flex rounded-xl p-1.5 w-full bg-white/50 dark:bg-gray-800/50 hover:bg-white/70 dark:hover:bg-gray-800/70 backdrop-blur-md border border-gray-200/30 dark:border-gray-700/30 shadow-md hover:shadow-lg transform hover:scale-105 transition-all duration-300 ease-out"
							aria-label="User Menu"
						>
								<div class=" self-center">
									<img
										src={$user?.profile_image_url}
										class="size-6 object-cover rounded-full"
										alt="User profile"
										draggable="false"
									/>
								</div>
							</button>
						</UserMenu>
					{/if}
				</div>
			</div>
		</div>
	</div>
</nav>

