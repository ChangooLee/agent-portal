<script lang="ts">
	import { getContext } from 'svelte';
	import { toast } from 'svelte-sonner';

	import {
		WEBUI_NAME,
		banners,
		chatId,
		config,
		mobile,
		settings,
		showArchivedChats,
		showControls,
		showSidebar,
		temporaryChatEnabled,
		user
	} from '$lib/stores';

	import { slide } from 'svelte/transition';
	import { page } from '$app/stores';

	import ShareChatModal from '../chat/ShareChatModal.svelte';
	import ModelSelector from '../chat/ModelSelector.svelte';
	import Tooltip from '../common/Tooltip.svelte';
	import Menu from '$lib/components/layout/Navbar/Menu.svelte';
	import UserMenu from '$lib/components/layout/Sidebar/UserMenu.svelte';
	import MenuLines from '../icons/MenuLines.svelte';
	import AdjustmentsHorizontal from '../icons/AdjustmentsHorizontal.svelte';

	import PencilSquare from '../icons/PencilSquare.svelte';
	import Banner from '../common/Banner.svelte';
	import DocumentChartBar from '../icons/DocumentChartBar.svelte';
	import Cube from '../icons/Cube.svelte';
	import BookOpen from '../icons/BookOpen.svelte';
	import Search from '../icons/Search.svelte';
	import ChartBar from '../icons/ChartBar.svelte';
	import Calendar from '../icons/Calendar.svelte';
	import Cog6Solid from '../icons/Cog6Solid.svelte';

	const i18n = getContext('i18n');

	export let initNewChat: Function;
	export let title: string = $WEBUI_NAME;
	export let shareEnabled: boolean = false;

	export let chat;
	export let history;
	export let selectedModels;
	export let showModelSelector = true;

	let showShareChatModal = false;
	let showDownloadChatModal = false;
</script>

<ShareChatModal bind:show={showShareChatModal} chatId={$chatId} />

<nav class="sticky top-0 z-50 w-full py-2 flex flex-col items-center drag-region bg-white/80 backdrop-blur-md shadow-sm">
	<div class="flex items-center w-full px-1.5">
		<div class=" flex max-w-full w-full mx-auto px-1 pt-0.5 bg-transparent">
			<div class="flex items-center w-full max-w-full">
				<div
					class="flex-1 overflow-hidden max-w-full py-0.5"
				>
					<div class="flex items-center gap-2 overflow-x-auto scrollbar-none">
						{#if showModelSelector}
							<div class="flex-shrink-0">
								<ModelSelector bind:selectedModels showSetDefault={false} />
							</div>
						{/if}
						
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
					<!-- <div class="md:hidden flex self-center w-[1px] h-5 mx-2 bg-gray-300 dark:bg-stone-700" /> -->
					{#if shareEnabled && chat && (chat.id || $temporaryChatEnabled)}
						<Menu
							{chat}
							{shareEnabled}
							shareHandler={() => {
								showShareChatModal = !showShareChatModal;
							}}
							downloadHandler={() => {
								showDownloadChatModal = !showDownloadChatModal;
							}}
						>
							<button
								class="flex cursor-pointer px-3 py-2 rounded-lg hover:bg-gray-100 transition-all duration-200 ease-in-out text-gray-600"
								id="chat-context-menu-button"
							>
								<div class=" m-auto self-center">
									<svg
										xmlns="http://www.w3.org/2000/svg"
										fill="none"
										viewBox="0 0 24 24"
										stroke-width="1.5"
										stroke="currentColor"
										class="size-5"
									>
										<path
											stroke-linecap="round"
											stroke-linejoin="round"
											d="M6.75 12a.75.75 0 1 1-1.5 0 .75.75 0 0 1 1.5 0ZM12.75 12a.75.75 0 1 1-1.5 0 .75.75 0 0 1 1.5 0ZM18.75 12a.75.75 0 1 1-1.5 0 .75.75 0 0 1 1.5 0Z"
										/>
									</svg>
								</div>
							</button>
						</Menu>
					{/if}

					<Tooltip content={$i18n.t('Controls')}>
						<button
							class=" flex cursor-pointer px-3 py-2 rounded-lg hover:bg-gray-100 transition-all duration-200 ease-in-out text-gray-600"
							on:click={async () => {
								await showControls.set(!$showControls);
							}}
							aria-label="Controls"
						>
							<div class=" m-auto self-center">
								<AdjustmentsHorizontal className=" size-5" strokeWidth="0.5" />
							</div>
						</button>
					</Tooltip>

					<Tooltip content={$i18n.t('New Chat')}>
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
								if (e.detail === 'archived-chat') {
									showArchivedChats.set(true);
								}
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

	{#if !history.currentId && !$chatId && ($banners.length > 0 || ($config?.license_metadata?.type ?? null) === 'trial' || (($config?.license_metadata?.seats ?? null) !== null && $config?.user_count > $config?.license_metadata?.seats))}
		<div class=" w-full z-30 mt-5">
			<div class=" flex flex-col gap-1 w-full">
				{#if ($config?.license_metadata?.type ?? null) === 'trial'}
					<Banner
						banner={{
							type: 'info',
							title: 'Trial License',
							content: $i18n.t(
								'You are currently using a trial license. Please contact support to upgrade your license.'
							)
						}}
					/>
				{/if}

				{#if ($config?.license_metadata?.seats ?? null) !== null && $config?.user_count > $config?.license_metadata?.seats}
					<Banner
						banner={{
							type: 'error',
							title: 'License Error',
							content: $i18n.t(
								'Exceeded the number of seats in your license. Please contact support to increase the number of seats.'
							)
						}}
					/>
				{/if}

				{#each $banners.filter( (b) => (b.dismissible ? !JSON.parse(localStorage.getItem('dismissedBannerIds') ?? '[]').includes(b.id) : true) ) as banner}
					<Banner
						{banner}
						on:dismiss={(e) => {
							const bannerId = e.detail;

							localStorage.setItem(
								'dismissedBannerIds',
								JSON.stringify(
									[
										bannerId,
										...JSON.parse(localStorage.getItem('dismissedBannerIds') ?? '[]')
									].filter((id) => $banners.find((b) => b.id === id))
								)
							);
						}}
					/>
				{/each}
			</div>
		</div>
	{/if}
</nav>
