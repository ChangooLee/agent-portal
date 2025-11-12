<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { goto } from '$app/navigation';

	import { WEBUI_NAME, showSidebar, user } from '$lib/stores';
	import MenuLines from '$lib/components/icons/MenuLines.svelte';
	import { page } from '$app/stores';

	const i18n = getContext('i18n');

	let loaded = false;

	onMount(async () => {
		if ($user?.role !== 'admin') {
			await goto('/');
		}
		loaded = true;
	});
</script>

<svelte:head>
	<title>
		{$i18n.t('Admin Panel')} | {$WEBUI_NAME}
	</title>
</svelte:head>

{#if loaded}
	<div class="flex flex-col w-full h-screen max-h-[100dvh]">
		<nav class="sticky top-0 z-30 w-full py-2 flex flex-col items-center drag-region bg-white/70 dark:bg-gray-900/70 backdrop-blur-xl shadow-lg border-b border-white/20 dark:border-gray-700/20">
			<div class="flex items-center w-full px-1.5">
				<div class="{$showSidebar ? 'md:hidden' : ''} mr-1 self-start flex flex-none items-center text-gray-600">
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

				<div class="flex-1 overflow-hidden max-w-full py-0.5">
					<div class="flex items-center gap-2 overflow-x-auto scrollbar-none">
						<a
							href="/admin/users"
							class="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium transition-all duration-300 ease-out {['/admin', '/admin/users'].includes($page.url.pathname)
								? 'bg-gradient-to-br from-primary/90 via-secondary/90 to-accent/90 dark:from-primary-light/80 dark:via-secondary-light/80 dark:to-accent-light/80 text-white backdrop-blur-md shadow-lg shadow-primary/30 dark:shadow-primary-light/20 border border-white/20 dark:border-gray-700/20 transform scale-105'
								: 'bg-white/40 dark:bg-gray-800/40 text-gray-700 dark:text-gray-200 backdrop-blur-sm hover:bg-white/60 dark:hover:bg-gray-800/60 border border-gray-200/30 dark:border-gray-700/30 hover:shadow-md hover:scale-105'}"
							title="사용자관리"
						>
							<span>사용자관리</span>
						</a>

						<a
							href="/admin/monitoring"
							class="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium transition-all duration-300 ease-out {$page.url.pathname.includes('/admin/monitoring')
								? 'bg-gradient-to-br from-primary/90 via-secondary/90 to-accent/90 dark:from-primary-light/80 dark:via-secondary-light/80 dark:to-accent-light/80 text-white backdrop-blur-md shadow-lg shadow-primary/30 dark:shadow-primary-light/20 border border-white/20 dark:border-gray-700/20 transform scale-105'
								: 'bg-white/40 dark:bg-gray-800/40 text-gray-700 dark:text-gray-200 backdrop-blur-sm hover:bg-white/60 dark:hover:bg-gray-800/60 border border-gray-200/30 dark:border-gray-700/30 hover:shadow-md hover:scale-105'}"
							title="사용량"
						>
							<span>사용량</span>
						</a>

						<a
							href="/admin/mcp"
							class="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium transition-all duration-300 ease-out {$page.url.pathname.includes('/admin/mcp')
								? 'bg-gradient-to-br from-primary/90 via-secondary/90 to-accent/90 dark:from-primary-light/80 dark:via-secondary-light/80 dark:to-accent-light/80 text-white backdrop-blur-md shadow-lg shadow-primary/30 dark:shadow-primary-light/20 border border-white/20 dark:border-gray-700/20 transform scale-105'
								: 'bg-white/40 dark:bg-gray-800/40 text-gray-700 dark:text-gray-200 backdrop-blur-sm hover:bg-white/60 dark:hover:bg-gray-800/60 border border-gray-200/30 dark:border-gray-700/30 hover:shadow-md hover:scale-105'}"
							title="MCP"
						>
							<span>MCP</span>
						</a>

						<a
							href="/admin/gateway"
							class="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium transition-all duration-300 ease-out {$page.url.pathname.includes('/admin/gateway')
								? 'bg-gradient-to-br from-primary/90 via-secondary/90 to-accent/90 dark:from-primary-light/80 dark:via-secondary-light/80 dark:to-accent-light/80 text-white backdrop-blur-md shadow-lg shadow-primary/30 dark:shadow-primary-light/20 border border-white/20 dark:border-gray-700/20 transform scale-105'
								: 'bg-white/40 dark:bg-gray-800/40 text-gray-700 dark:text-gray-200 backdrop-blur-sm hover:bg-white/60 dark:hover:bg-gray-800/60 border border-gray-200/30 dark:border-gray-700/30 hover:shadow-md hover:scale-105'}"
							title="Gateway"
						>
							<span>Gateway</span>
						</a>

						<a
							href="/admin/guardrails"
							class="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium transition-all duration-300 ease-out {$page.url.pathname.includes('/admin/guardrails')
								? 'bg-gradient-to-br from-primary/90 via-secondary/90 to-accent/90 dark:from-primary-light/80 dark:via-secondary-light/80 dark:to-accent-light/80 text-white backdrop-blur-md shadow-lg shadow-primary/30 dark:shadow-primary-light/20 border border-white/20 dark:border-gray-700/20 transform scale-105'
								: 'bg-white/40 dark:bg-gray-800/40 text-gray-700 dark:text-gray-200 backdrop-blur-sm hover:bg-white/60 dark:hover:bg-gray-800/60 border border-gray-200/30 dark:border-gray-700/30 hover:shadow-md hover:scale-105'}"
							title="가드레일"
						>
							<span>가드레일</span>
						</a>

						<a
							href="/admin/evaluations"
							class="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium transition-all duration-300 ease-out {$page.url.pathname.includes('/admin/evaluations')
								? 'bg-gradient-to-br from-primary/90 via-secondary/90 to-accent/90 dark:from-primary-light/80 dark:via-secondary-light/80 dark:to-accent-light/80 text-white backdrop-blur-md shadow-lg shadow-primary/30 dark:shadow-primary-light/20 border border-white/20 dark:border-gray-700/20 transform scale-105'
								: 'bg-white/40 dark:bg-gray-800/40 text-gray-700 dark:text-gray-200 backdrop-blur-sm hover:bg-white/60 dark:hover:bg-gray-800/60 border border-gray-200/30 dark:border-gray-700/30 hover:shadow-md hover:scale-105'}"
							title="리더보드"
						>
							<span>리더보드</span>
						</a>

						<a
							href="/admin/settings"
							class="flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium transition-all duration-300 ease-out {$page.url.pathname.includes('/admin/settings')
								? 'bg-gradient-to-br from-primary/90 via-secondary/90 to-accent/90 dark:from-primary-light/80 dark:via-secondary-light/80 dark:to-accent-light/80 text-white backdrop-blur-md shadow-lg shadow-primary/30 dark:shadow-primary-light/20 border border-white/20 dark:border-gray-700/20 transform scale-105'
								: 'bg-white/40 dark:bg-gray-800/40 text-gray-700 dark:text-gray-200 backdrop-blur-sm hover:bg-white/60 dark:hover:bg-gray-800/60 border border-gray-200/30 dark:border-gray-700/30 hover:shadow-md hover:scale-105'}"
							title="설정"
						>
							<span>설정</span>
						</a>
					</div>
				</div>
			</div>
		</nav>

		<div class=" pb-1 px-[16px] flex-1 max-h-full overflow-y-auto">
			<slot />
		</div>
	</div>
{/if}
