<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { WEBUI_NAME } from '$lib/stores';
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
	<div class="min-h-full bg-gray-950 text-slate-50">
		<!-- Hero Section -->
		<div class="relative overflow-hidden border-b border-slate-800/50">
			<div class="absolute inset-0 bg-gradient-to-br from-amber-600/5 via-transparent to-orange-600/5"></div>
			<div class="absolute inset-0 bg-[linear-gradient(rgba(251,191,36,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(251,191,36,0.03)_1px,transparent_1px)] bg-[size:64px_64px]"></div>
			
			<div class="relative px-6 py-8">
				<div class="text-center mb-6">
					<h1 class="text-3xl md:text-4xl font-medium text-white mb-3">
						Notebook
					</h1>
					<p class="text-base text-amber-200/80 mb-6">
						노트 중심 인터페이스와 광범위한 모델 프로바이더 지원으로 연구 워크플로를 최적화합니다.
					</p>
					
					<!-- Stats Grid -->
					<div class="grid grid-cols-1 md:grid-cols-3 gap-4 max-w-4xl mx-auto mt-8">
						{#each heroStats as stat}
							<div class="bg-slate-900/80 border border-slate-800/50 rounded-xl p-4 text-center">
								<div class="text-xs font-medium uppercase tracking-wide text-amber-400/80 mb-1">
									{stat.label}
								</div>
								<div class="text-2xl font-medium text-white mb-1">
									{stat.value}
								</div>
								<div class="text-xs text-slate-400">{stat.hint}</div>
							</div>
						{/each}
					</div>
				</div>
			</div>
		</div>

		<!-- Content Section -->
		<div class="px-6 py-8">
			<div class="bg-slate-900/80 border border-slate-800/50 rounded-2xl shadow-xl shadow-black/20 p-8 text-center">
				<div class="mb-6 inline-flex p-4 rounded-2xl bg-gradient-to-br from-amber-500 to-orange-600 shadow-lg shadow-amber-500/25">
					<BookOpen className="size-16 text-white" />
				</div>
				<h2 class="text-2xl font-semibold mb-3 text-white">준비 중입니다</h2>
				<p class="text-slate-300 mb-4 max-w-2xl mx-auto">
					Open-Notebook 기능은 Stage 8에서 구현될 예정입니다.
				</p>
				<p class="text-sm text-slate-400 max-w-2xl mx-auto">
					향후 iframe으로 임베드되어 포털 Apps 탭에서 사용할 수 있습니다.
				</p>
			</div>
		</div>
	</div>
{/if}

