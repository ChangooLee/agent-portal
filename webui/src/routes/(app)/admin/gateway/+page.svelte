<script lang="ts">
	import { onMount } from 'svelte';
	import { getContext } from 'svelte';
	import { page } from '$app/stores';
	import { WEBUI_NAME } from '$lib/stores';
	
	const i18n = getContext('i18n');

	let loading = true;
	let error: string | null = null;
	let activeTab = 'kong-admin';

	const BFF_BASE_URL = import.meta.env.VITE_BFF_BASE_URL || 'http://localhost:8000';
	const kongAdminUrl = `${BFF_BASE_URL}/embed/kong-admin/`;

	onMount(() => {
		// Check if Konga is accessible
		loading = false;
	});

	function handleIframeLoad() {
		loading = false;
		error = null;
	}

	function handleIframeError() {
		loading = false;
		error = 'Failed to load Kong Admin UI. Please ensure the backend service is running.';
	}
</script>

<svelte:head>
	<title>{$i18n.t('Gateway')} | {$WEBUI_NAME}</title>
</svelte:head>

<div class="flex w-full flex-col min-h-full px-3 py-4 @md:px-6 @md:py-6">
	<div class="mx-auto flex w-full max-w-[1400px] flex-col gap-6">
		<!-- Hero Section -->
		<section class="relative overflow-hidden rounded-3xl border border-white/20 bg-white/60 p-4 shadow-xl shadow-primary/10 backdrop-blur-2xl dark:border-gray-700/30 dark:bg-gray-900/60">
			<div class="absolute inset-0 bg-gradient-to-br from-primary/20 via-secondary/10 to-accent/20 opacity-60" />
			<div class="relative flex items-center gap-3">
				<span class="inline-flex items-center gap-2 rounded-full bg-white/90 px-3 py-1 text-xs font-medium text-gray-600 shadow-sm dark:bg-gray-800/80 dark:text-gray-200">
					<span class="h-1.5 w-1.5 rounded-full bg-gradient-to-r from-primary via-secondary to-accent" />
					SFN AI Gateway
				</span>
				<h1 class="text-xl font-semibold tracking-tight text-gray-900 dark:text-gray-100">
					API 게이트웨이 관리 및 보안 설정
				</h1>
			</div>
		</section>

		<!-- Tab Navigation -->
		<div class="flex gap-2">
			<button
				class="px-4 py-2 rounded-xl text-sm font-medium transition-all duration-300 ease-out {activeTab === 'kong-admin'
					? 'bg-gradient-to-br from-primary/90 via-secondary/90 to-accent/90 text-white backdrop-blur-md shadow-lg shadow-primary/30'
					: 'bg-white/40 dark:bg-gray-800/40 text-gray-700 dark:text-gray-200 backdrop-blur-sm hover:bg-white/60 dark:hover:bg-gray-800/60 border border-gray-200/30 dark:border-gray-700/30 hover:shadow-md hover:scale-105'}"
				on:click={() => {
					activeTab = 'kong-admin';
				}}
			>
				Kong Admin
			</button>
			<button
				class="px-4 py-2 rounded-xl text-sm font-medium transition-all duration-300 ease-out {activeTab === 'security'
					? 'bg-gradient-to-br from-primary/90 via-secondary/90 to-accent/90 text-white backdrop-blur-md shadow-lg shadow-primary/30'
					: 'bg-white/40 dark:bg-gray-800/40 text-gray-700 dark:text-gray-200 backdrop-blur-sm hover:bg-white/60 dark:hover:bg-gray-800/60 border border-gray-200/30 dark:border-gray-700/30 hover:shadow-md hover:scale-105'}"
				on:click={() => {
					activeTab = 'security';
				}}
			>
				Security Metrics
			</button>
		</div>

		<div class="flex-1 relative min-h-[90vh]">
		{#if loading}
			<div class="absolute inset-0 flex items-center justify-center">
				<div class="flex flex-col items-center gap-2">
					<div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
					<p class="text-sm text-gray-500 dark:text-gray-400">Loading Kong Admin UI...</p>
				</div>
			</div>
		{/if}

		{#if error}
			<div class="absolute inset-0 flex items-center justify-center">
				<div class="text-center p-4">
					<p class="text-red-500 dark:text-red-400 mb-2">{error}</p>
					<p class="text-sm text-gray-500 dark:text-gray-400">
						Please check if the backend service is running and accessible.
					</p>
				</div>
			</div>
		{/if}

		{#if activeTab === 'kong-admin'}
			<iframe
				src={kongAdminUrl}
				class="w-full h-full border-0 {loading ? 'opacity-0' : 'opacity-100'} transition-opacity"
				title="Kong Admin UI"
				on:load={handleIframeLoad}
				on:error={handleIframeError}
				sandbox="allow-same-origin allow-scripts allow-forms allow-popups allow-modals"
			/>
	{:else if activeTab === 'security'}
		<div class="flex items-center justify-center h-full text-gray-500 dark:text-gray-400">
			<p>Security Metrics dashboard will be available here.</p>
		</div>
	{/if}
</div>
	</div>
</div>

<style>
	iframe {
		min-height: 90vh;
	}
</style>


