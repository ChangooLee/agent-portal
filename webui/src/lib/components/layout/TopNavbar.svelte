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

	const i18n = getContext('i18n');

	// 메인 채팅 페이지에서 사용할 selectedModels (기본값)
	let selectedModels = $models.length > 0 ? [$models[0].id] : [''];
	
	$: if ($models.length > 0 && selectedModels.length === 0) {
		selectedModels = [$models[0].id];
	}

	const initNewChat = () => {
		chatId.set('');
		window.location.href = '/';
	};
</script>

<nav class="sticky top-0 z-50 w-full py-2 flex flex-col items-center drag-region bg-white/80 backdrop-blur-md shadow-sm">
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
						class="cursor-pointer px-3 py-2 flex rounded-lg hover:bg-gray-100 transition-all duration-200 ease-in-out text-gray-600"
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
						<div class="flex-shrink-0">
							<ModelSelector bind:selectedModels showSetDefault={false} />
						</div>
						
						<!-- Navigation Menu Buttons -->
						<a
							href="/report"
							class="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 ease-in-out {$page.url.pathname.startsWith('/report')
								? 'bg-[#0072CE] text-white shadow-sm'
								: 'text-gray-600 hover:bg-gray-50'}"
							title="보고서"
						>
							<DocumentChartBar className="size-4" />
							<span class="hidden sm:inline">보고서</span>
						</a>
						
						<a
							href="/agent"
							class="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 ease-in-out {$page.url.pathname.startsWith('/agent')
								? 'bg-[#0072CE] text-white shadow-sm'
								: 'text-gray-600 hover:bg-gray-50'}"
							title="에이전트"
						>
							<Cube className="size-4" />
							<span class="hidden sm:inline">에이전트</span>
						</a>
						
						<a
							href="/notebook"
							class="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 ease-in-out {$page.url.pathname.startsWith('/notebook')
								? 'bg-[#0072CE] text-white shadow-sm'
								: 'text-gray-600 hover:bg-gray-50'}"
							title="노트북"
						>
							<BookOpen className="size-4" />
							<span class="hidden sm:inline">노트북</span>
						</a>
						
						<a
							href="/search"
							class="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 ease-in-out {$page.url.pathname.startsWith('/search')
								? 'bg-[#0072CE] text-white shadow-sm'
								: 'text-gray-600 hover:bg-gray-50'}"
							title="검색"
						>
							<Search className="size-4" />
							<span class="hidden sm:inline">검색</span>
						</a>
						
						{#if $user?.role === 'admin'}
							<a
								href="/usage"
								class="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 ease-in-out {$page.url.pathname.startsWith('/usage')
									? 'bg-[#0072CE] text-white shadow-sm'
									: 'text-gray-600 hover:bg-gray-50'}"
								title="사용량"
							>
								<ChartBar className="size-4" />
								<span class="hidden sm:inline">사용량</span>
							</a>
						{/if}
						
						<a
							href="/schedule"
							class="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 ease-in-out {$page.url.pathname.startsWith('/schedule')
								? 'bg-[#0072CE] text-white shadow-sm'
								: 'text-gray-600 hover:bg-gray-50'}"
							title="일정관리"
						>
							<Calendar className="size-4" />
							<span class="hidden sm:inline">일정관리</span>
						</a>
						
						{#if $user?.role === 'admin'}
							<a
								href="/admin"
								class="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 ease-in-out {$page.url.pathname.startsWith('/admin')
									? 'bg-[#0072CE] text-white shadow-sm'
									: 'text-gray-600 hover:bg-gray-50'}"
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
								: ''} cursor-pointer px-3 py-2 rounded-lg text-gray-600 hover:bg-gray-100 transition-all duration-200 ease-in-out"
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
								class="select-none flex rounded-lg p-1.5 w-full hover:bg-gray-100 transition-all duration-200 ease-in-out"
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

