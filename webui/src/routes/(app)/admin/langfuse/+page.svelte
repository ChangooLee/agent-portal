<script lang="ts">
	import { onMount } from 'svelte';
	import Star from '$lib/components/icons/Star.svelte';

	let loading = true;
	let iframeReady = false;

	onMount(() => {
		// Set loading to false after a short delay
		setTimeout(() => {
			loading = false;
		}, 1000);
	});

	function handleIframeLoad() {
		iframeReady = true;
	}
</script>

<svelte:head>
	<title>Langfuse - Quality Management | Agent Portal</title>
</svelte:head>

<div class="flex flex-col w-full h-full min-h-screen">
	<!-- Hero Section -->
	<div
		class="relative mb-6 overflow-hidden rounded-2xl bg-gradient-to-br from-amber-500/10 via-orange-500/10 to-yellow-500/10 dark:from-amber-400/5 dark:via-orange-400/5 dark:to-yellow-400/5"
	>
		<div class="absolute inset-0 bg-white/40 dark:bg-gray-900/40 backdrop-blur-xl"></div>

		<div class="relative px-8 py-8">
			<!-- Badge -->
			<div
				class="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-amber-500/10 dark:bg-amber-400/10 text-amber-600 dark:text-amber-400 text-sm font-medium mb-3 backdrop-blur-sm border border-amber-500/20 dark:border-amber-400/20"
			>
				<Star className="size-4" />
				<span>Agent Quality Management</span>
			</div>

			<!-- Title -->
			<h1 class="text-3xl font-bold text-gray-900 dark:text-white mb-3">
				Langfuse
			</h1>

			<!-- Description -->
			<p class="text-base text-gray-600 dark:text-gray-300 max-w-3xl">
				LLM 트레이싱, 프롬프트 관리, 평가 및 품질 모니터링 도구입니다.
			</p>
		</div>
	</div>

	<!-- Langfuse iframe Container -->
	<div class="relative flex-1 w-full overflow-hidden rounded-2xl bg-white/60 dark:bg-gray-800/60 backdrop-blur-sm border border-white/20 dark:border-gray-700/20 shadow-xl">
		{#if loading && !iframeReady}
			<!-- Loading State -->
			<div class="absolute inset-0 flex items-center justify-center bg-white/80 dark:bg-gray-900/80 backdrop-blur-sm">
				<div class="text-center">
					<div class="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-amber-500 dark:border-amber-400 mb-4"></div>
					<p class="text-gray-600 dark:text-gray-300">Loading Langfuse...</p>
				</div>
			</div>
		{/if}

		<!-- iframe -->
		<iframe
			src="/api/proxy/langfuse/"
			title="Langfuse Quality Management"
			class="w-full h-full min-h-[800px]"
			on:load={handleIframeLoad}
			frameborder="0"
			allow="clipboard-read; clipboard-write"
		></iframe>
	</div>
</div>

