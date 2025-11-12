<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import {
		WEBUI_NAME,
		showSidebar,
		functions,
		user,
		mobile,
		models,
		prompts,
		knowledge,
		tools
	} from '$lib/stores';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';

	import MenuLines from '$lib/components/icons/MenuLines.svelte';

	const i18n = getContext('i18n');

	let loaded = false;

	onMount(async () => {
		if ($user?.role !== 'admin') {
			if ($page.url.pathname.includes('/models') && !$user?.permissions?.workspace?.models) {
				goto('/');
			} else if (
				$page.url.pathname.includes('/knowledge') &&
				!$user?.permissions?.workspace?.knowledge
			) {
				goto('/');
			} else if (
				$page.url.pathname.includes('/prompts') &&
				!$user?.permissions?.workspace?.prompts
			) {
				goto('/');
			} else if ($page.url.pathname.includes('/tools') && !$user?.permissions?.workspace?.tools) {
				goto('/');
			}
		}

		loaded = true;
	});
</script>

<svelte:head>
	<title>
		{$i18n.t('Workspace')} | {$WEBUI_NAME}
	</title>
</svelte:head>

{#if loaded}
	<div
		class="relative flex flex-col w-full h-screen max-h-[100dvh] transition-all duration-200 ease-in-out {$showSidebar
			? 'md:ml-[260px]'
			: ''}"
	>
		<nav class="   px-2.5 pt-1 backdrop-blur-xl drag-region bg-white dark:bg-gray-900 border-b border-gray-200 dark:border-gray-800">
			<div class=" flex items-center gap-1">
				<div class="{$showSidebar ? 'md:hidden' : ''} self-center flex flex-none items-center">
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

				<div class="">
					<div
						class="flex gap-1 scrollbar-none overflow-x-auto w-fit text-center text-sm font-medium rounded-full bg-transparent py-1 touch-auto pointer-events-auto"
					>
						{#if $user?.role === 'admin' || $user?.permissions?.workspace?.models}
							<a
								class="min-w-fit rounded-lg px-3 py-1.5 text-sm font-medium {$page.url.pathname.includes(
									'/workspace/models'
								)
									? 'text-white'
									: 'text-gray-600 dark:text-gray-400 dark:hover:text-gray-300 hover:bg-blue-50 dark:hover:bg-gray-800'} transition-colors"
								style={$page.url.pathname.includes('/workspace/models') ? 'background-color: #0066CC !important;' : ''}
								href="/workspace/models">{$i18n.t('Models')}</a
							>
						{/if}

						{#if $user?.role === 'admin' || $user?.permissions?.workspace?.knowledge}
							<a
								class="min-w-fit rounded-lg px-3 py-1.5 text-sm font-medium {$page.url.pathname.includes(
									'/workspace/knowledge'
								)
									? 'text-white'
									: 'text-gray-600 dark:text-gray-400 dark:hover:text-gray-300 hover:bg-blue-50 dark:hover:bg-gray-800'} transition-colors"
								style={$page.url.pathname.includes('/workspace/knowledge') ? 'background-color: #0066CC !important;' : ''}
								href="/workspace/knowledge"
							>
								{$i18n.t('Knowledge')}
							</a>
						{/if}

						{#if $user?.role === 'admin' || $user?.permissions?.workspace?.prompts}
							<a
								class="min-w-fit rounded-lg px-3 py-1.5 text-sm font-medium {$page.url.pathname.includes(
									'/workspace/prompts'
								)
									? 'text-white'
									: 'text-gray-600 dark:text-gray-400 dark:hover:text-gray-300 hover:bg-blue-50 dark:hover:bg-gray-800'} transition-colors"
								style={$page.url.pathname.includes('/workspace/prompts') ? 'background-color: #0066CC !important;' : ''}
								href="/workspace/prompts">{$i18n.t('Prompts')}</a
							>
						{/if}

						{#if $user?.role === 'admin' || $user?.permissions?.workspace?.tools}
							<a
								class="min-w-fit rounded-lg px-3 py-1.5 text-sm font-medium {$page.url.pathname.includes('/workspace/tools')
									? 'text-white'
									: 'text-gray-600 dark:text-gray-400 dark:hover:text-gray-300 hover:bg-blue-50 dark:hover:bg-gray-800'} transition-colors"
								style={$page.url.pathname.includes('/workspace/tools') ? 'background-color: #0066CC !important;' : ''}
								href="/workspace/tools"
							>
								{$i18n.t('Tools')}
							</a>
						{/if}
					</div>
				</div>

				<!-- <div class="flex items-center text-xl font-semibold">{$i18n.t('Workspace')}</div> -->
			</div>
		</nav>

		<div class="  pb-1 px-[18px] flex-1 max-h-full overflow-y-auto" id="workspace-container">
			<slot />
		</div>
	</div>
{/if}
