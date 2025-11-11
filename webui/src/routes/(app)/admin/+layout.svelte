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
	<div
		class=" flex flex-col w-full h-screen max-h-[100dvh] transition-width duration-200 ease-in-out {$showSidebar
			? 'md:max-w-[calc(100%-260px)]'
			: ''} max-w-full"
	>
		<nav class="sticky top-0 z-30 w-full py-2 flex flex-col items-center drag-region bg-white/80 backdrop-blur-md shadow-sm border-b border-gray-200">
			<div class="flex items-center w-full px-1.5">
				<div class="{$showSidebar ? 'md:hidden' : ''} mr-1 self-start flex flex-none items-center text-gray-600">
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

				<div class="flex-1 overflow-hidden max-w-full py-0.5">
					<div class="flex items-center gap-2 overflow-x-auto scrollbar-none">
						<a
							href="/admin/users"
							class="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 ease-in-out {['/admin', '/admin/users'].includes($page.url.pathname)
								? 'bg-[#0072CE] text-white shadow-sm'
								: 'text-gray-600 hover:bg-gray-50'}"
							title="사용자관리"
						>
							<span>사용자관리</span>
						</a>

						<a
							href="/admin/monitoring"
							class="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 ease-in-out {$page.url.pathname.includes('/admin/monitoring')
								? 'bg-[#0072CE] text-white shadow-sm'
								: 'text-gray-600 hover:bg-gray-50'}"
							title="사용량"
						>
							<span>사용량</span>
						</a>

						<a
							href="/admin/mcp"
							class="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 ease-in-out {$page.url.pathname.includes('/admin/mcp')
								? 'bg-[#0072CE] text-white shadow-sm'
								: 'text-gray-600 hover:bg-gray-50'}"
							title="MCP"
						>
							<span>MCP</span>
						</a>

						<a
							href="/admin/gateway"
							class="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 ease-in-out {$page.url.pathname.includes('/admin/gateway')
								? 'bg-[#0072CE] text-white shadow-sm'
								: 'text-gray-600 hover:bg-gray-50'}"
							title="Gateway"
						>
							<span>Gateway</span>
						</a>

						<a
							href="/admin/guardrails"
							class="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 ease-in-out {$page.url.pathname.includes('/admin/guardrails')
								? 'bg-[#0072CE] text-white shadow-sm'
								: 'text-gray-600 hover:bg-gray-50'}"
							title="가드레일"
						>
							<span>가드레일</span>
						</a>

						<a
							href="/admin/evaluations"
							class="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 ease-in-out {$page.url.pathname.includes('/admin/evaluations')
								? 'bg-[#0072CE] text-white shadow-sm'
								: 'text-gray-600 hover:bg-gray-50'}"
							title="리더보드"
						>
							<span>리더보드</span>
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
