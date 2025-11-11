<script lang="ts">
	import { onMount } from 'svelte';
	import { getContext } from 'svelte';
	import { page } from '$app/stores';
	
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
	<title>{$i18n.t('Gateway')} | Admin Panel</title>
</svelte:head>

<div class="flex flex-col w-full h-full">
	<div class="flex gap-2 mb-4 border-b border-gray-200 dark:border-gray-800">
		<button
			class="px-4 py-2 text-sm font-medium transition {activeTab === 'kong-admin'
				? 'border-b-2 border-blue-500 text-blue-600 dark:text-blue-400'
				: 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'}"
			on:click={() => {
				activeTab = 'kong-admin';
			}}
		>
			Kong Admin
		</button>
		<button
			class="px-4 py-2 text-sm font-medium transition {activeTab === 'security'
				? 'border-b-2 border-blue-500 text-blue-600 dark:text-blue-400'
				: 'text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-300'}"
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

<style>
	iframe {
		min-height: 90vh;
	}
</style>


