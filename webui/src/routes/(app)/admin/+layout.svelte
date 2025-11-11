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
		<nav class="   px-2.5 pt-1 backdrop-blur-xl drag-region bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-800">
			<div class=" flex items-center gap-1">
				<div class="{$showSidebar ? 'md:hidden' : ''} flex flex-none items-center self-end">
					<button
						id="sidebar-toggle-button"
						class="cursor-pointer p-1.5 flex rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
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

				<div class=" flex w-full">
					<div
						class="flex gap-1 scrollbar-none overflow-x-auto w-fit text-center text-sm font-medium rounded-full bg-transparent pt-1"
					>
						<a
							class="min-w-fit rounded-lg px-3 py-1.5 text-sm font-medium {['/admin/users'].includes($page.url.pathname)
								? 'text-white'
								: 'text-gray-600 dark:text-gray-400 dark:hover:text-gray-300 hover:bg-blue-50 dark:hover:bg-gray-800'} transition-colors"
							style={['/admin/users'].includes($page.url.pathname) ? 'background-color: #0066CC !important;' : ''}
							href="/admin">{$i18n.t('Users')}</a
						>

						<a
							class="min-w-fit rounded-lg px-3 py-1.5 text-sm font-medium {$page.url.pathname.includes('/admin/evaluations')
								? 'text-white'
								: 'text-gray-600 dark:text-gray-400 dark:hover:text-gray-300 hover:bg-blue-50 dark:hover:bg-gray-800'} transition-colors"
							style={$page.url.pathname.includes('/admin/evaluations') ? 'background-color: #0066CC !important;' : ''}
							href="/admin/evaluations">{$i18n.t('Evaluations')}</a
						>

					<a
						class="min-w-fit rounded-lg px-3 py-1.5 text-sm font-medium {$page.url.pathname.includes('/admin/functions')
							? 'text-white'
							: 'text-gray-600 dark:text-gray-400 dark:hover:text-gray-300 hover:bg-blue-50 dark:hover:bg-gray-800'} transition-colors"
						style={$page.url.pathname.includes('/admin/functions') ? 'background-color: #0066CC !important;' : ''}
						href="/admin/functions">{$i18n.t('Functions')}</a
					>

					<a
						class="min-w-fit rounded-lg px-3 py-1.5 text-sm font-medium {$page.url.pathname.includes('/admin/monitoring')
							? 'text-white'
							: 'text-gray-600 dark:text-gray-400 dark:hover:text-gray-300 hover:bg-blue-50 dark:hover:bg-gray-800'} transition-colors"
						style={$page.url.pathname.includes('/admin/monitoring') ? 'background-color: #0066CC !important;' : ''}
						href="/admin/monitoring">{$i18n.t('Monitoring')}</a
					>

					<a
						class="min-w-fit rounded-lg px-3 py-1.5 text-sm font-medium {$page.url.pathname.includes('/admin/settings')
							? 'text-white'
							: 'text-gray-600 dark:text-gray-400 dark:hover:text-gray-300 hover:bg-blue-50 dark:hover:bg-gray-800'} transition-colors"
						style={$page.url.pathname.includes('/admin/settings') ? 'background-color: #0066CC !important;' : ''}
						href="/admin/settings">{$i18n.t('Settings')}</a
					>

					<a
						class="min-w-fit rounded-lg px-3 py-1.5 text-sm font-medium {$page.url.pathname.includes('/admin/gateway')
							? 'text-white'
							: 'text-gray-600 dark:text-gray-400 dark:hover:text-gray-300 hover:bg-blue-50 dark:hover:bg-gray-800'} transition-colors"
						style={$page.url.pathname.includes('/admin/gateway') ? 'background-color: #0066CC !important;' : ''}
						href="/admin/gateway">{$i18n.t('Gateway')}</a
					>
				</div>
				</div>
			</div>
		</nav>

		<div class=" pb-1 px-[16px] flex-1 max-h-full overflow-y-auto">
			<slot />
		</div>
	</div>
{/if}
