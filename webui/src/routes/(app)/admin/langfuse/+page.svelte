<script lang="ts">
	import { onMount } from 'svelte';

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

<!-- Page Container -->
<div class="flex w-full flex-col min-h-full px-3 py-4 @md:px-6 @md:py-6">
	<div class="mx-auto flex w-full max-w-[1200px] flex-col gap-6">
		
		<!-- Hero Section -->
		<section class="relative overflow-hidden rounded-3xl border border-white/20 
						bg-white/60 p-6 shadow-2xl shadow-primary/10 backdrop-blur-2xl 
						dark:border-gray-700/30 dark:bg-gray-900/60">
			<!-- Gradient overlay -->
			<div class="absolute inset-0 bg-gradient-to-br from-primary/20 via-secondary/10 
						to-accent/20 opacity-60" />
			<!-- Glow effect -->
			<div class="pointer-events-none absolute -right-10 -top-12 h-40 w-40 rounded-full 
						bg-gradient-to-br from-primary/40 to-secondary/30 blur-3xl" />
			
			<div class="relative flex flex-col gap-5">
				<!-- Header Row: Badge + Title -->
				<div class="flex flex-wrap items-center gap-3">
					<!-- Badge -->
					<span class="inline-flex items-center gap-2 rounded-full bg-white/90 px-3 py-1 
								 text-xs font-medium text-gray-600 shadow-sm 
								 dark:bg-gray-800/80 dark:text-gray-200">
						<span class="h-1.5 w-1.5 rounded-full bg-gradient-to-r from-primary 
									 via-secondary to-accent" />
						Agent Quality Management
					</span>
					<!-- Title -->
					<h1 class="text-2xl font-semibold tracking-tight text-gray-900 dark:text-gray-100">
						Langfuse
					</h1>
				</div>
				
				<!-- Description -->
				<p class="max-w-3xl text-sm text-gray-600 dark:text-gray-300">
					LLM 트레이싱, 프롬프트 관리, 평가 및 품질 모니터링 도구입니다.
				</p>
			</div>
		</section>

		<!-- Langfuse iframe Container -->
		<div class="relative flex-1 w-full overflow-hidden rounded-2xl bg-white/60 dark:bg-gray-800/60 
					backdrop-blur-sm border border-white/20 dark:border-gray-700/20 shadow-xl min-h-[800px]">
			{#if loading && !iframeReady}
				<!-- Loading State -->
				<div class="absolute inset-0 flex items-center justify-center bg-white/80 dark:bg-gray-900/80 backdrop-blur-sm">
					<div class="text-center">
						<div class="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-primary dark:border-primary mb-4"></div>
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
</div>
