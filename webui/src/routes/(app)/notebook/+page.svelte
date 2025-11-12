<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { WEBUI_NAME, showSidebar } from '$lib/stores';
	import BookOpen from '$lib/components/icons/BookOpen.svelte';

	const i18n = getContext('i18n');

	let loaded = false;

	onMount(async () => {
		loaded = true;
	});

	const heroStats = [
		{ label: '지원 모델', value: '50+개', hint: 'OpenAI · Anthropic · 로컬' },
		{ label: '마크다운 기반', value: '노트', hint: '코드 실행 지원' },
		{ label: 'Stage 8', value: '출시 예정', hint: 'iframe 임베드' }
	];
</script>

<svelte:head>
	<title>노트북 | {$WEBUI_NAME}</title>
</svelte:head>

{#if loaded}
	<div class="flex w-full flex-col min-h-full px-3 py-4 @md:px-6 @md:py-6">
		<div class="mx-auto flex w-full max-w-[1200px] flex-col gap-6">
			<!-- Hero Section -->
			<section class="relative overflow-hidden rounded-3xl border border-white/20 bg-white/60 p-6 shadow-2xl shadow-primary/10 backdrop-blur-2xl dark:border-gray-700/30 dark:bg-gray-900/60">
				<div class="absolute inset-0 bg-gradient-to-br from-primary/20 via-secondary/10 to-accent/20 opacity-60" />
				<div class="pointer-events-none absolute -right-10 -top-12 h-40 w-40 rounded-full bg-gradient-to-br from-primary/40 to-secondary/30 blur-3xl" />
				<div class="relative flex flex-col gap-5">
					<div class="flex flex-wrap items-center gap-3">
						<span class="inline-flex items-center gap-2 rounded-full bg-white/90 px-3 py-1 text-xs font-medium text-gray-600 shadow-sm dark:bg-gray-800/80 dark:text-gray-200">
							<span class="h-1.5 w-1.5 rounded-full bg-gradient-to-r from-primary via-secondary to-accent" />
							SFN AI Notebook
						</span>
						<h1 class="text-2xl font-semibold tracking-tight text-gray-900 dark:text-gray-100">
							AI 노트북으로 지식을 체계화하세요
						</h1>
					</div>

					<p class="max-w-3xl text-sm text-gray-600 dark:text-gray-300">
						노트 중심 인터페이스와 광범위한 모델 프로바이더 지원으로 연구 워크플로를 최적화합니다.
					</p>

					<div class="grid grid-cols-3 gap-3 @md:grid-cols-4 @lg:grid-cols-6">
						{#each heroStats as stat}
							<div class="rounded-2xl border border-white/30 bg-white/70 px-4 py-3 text-left shadow-md shadow-primary/10 transition dark:border-gray-700/30 dark:bg-gray-900/50">
								<div class="text-[11px] font-medium uppercase tracking-wide text-primary dark:text-primary-light">
									{stat.label}
								</div>
								<div class="text-xl font-semibold text-gray-900 dark:text-gray-100">
									{stat.value}
								</div>
								<div class="pt-1 text-xs text-gray-500 dark:text-gray-400">{stat.hint}</div>
							</div>
						{/each}
					</div>
				</div>
			</section>

			<!-- Coming Soon Card -->
			<div class="bg-white/60 dark:bg-gray-900/50 backdrop-blur-xl rounded-xl border border-white/20 dark:border-gray-700/20 shadow-xl p-8 text-center">
				<div class="mb-4 inline-flex p-4 rounded-2xl bg-gradient-to-br from-blue-500 to-blue-600 shadow-lg">
					<BookOpen className="size-16 text-white" />
				</div>
				<h2 class="text-xl font-semibold mb-2 text-gray-900 dark:text-gray-100">준비 중입니다</h2>
				<p class="text-gray-600 dark:text-gray-300 mb-4">
					Open-Notebook 기능은 Stage 8에서 구현될 예정입니다.
				</p>
				<p class="text-sm text-gray-500 dark:text-gray-400">
					향후 iframe으로 임베드되어 포털 Apps 탭에서 사용할 수 있습니다.
				</p>
			</div>
		</div>
	</div>
{/if}

