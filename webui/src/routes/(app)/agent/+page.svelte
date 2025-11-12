<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { goto } from '$app/navigation';
	import { WEBUI_NAME, showSidebar } from '$lib/stores';
	import Cube from '$lib/components/icons/Cube.svelte';

	const i18n = getContext('i18n');

	let loaded = false;

	onMount(async () => {
		loaded = true;
	});

	const heroStats = [
		{ label: '지원 빌더', value: '3개', hint: 'Langflow · Flowise · AutoGen' },
		{ label: '평균 구축 시간', value: '15분', hint: '노코드 비주얼 설계' },
		{ label: 'LangGraph 변환', value: '자동', hint: '프로덕션 배포 지원' }
	];

	const builders = [
		{
			id: 'langflow',
			name: 'Langflow',
			description: '노코드 에이전트 빌더 - LangGraph 친화적',
			icon: Cube,
			path: '/builder/langflow',
			gradientFrom: 'from-blue-500',
			gradientTo: 'to-blue-600'
		},
		{
			id: 'flowise',
			name: 'Flowise',
			description: '노코드 에이전트 빌더 - 위젯/임베드 용이',
			icon: Cube,
			path: '/builder/flowise',
			gradientFrom: 'from-green-500',
			gradientTo: 'to-green-600'
		},
		{
			id: 'autogen',
			name: 'AutoGen Studio',
			description: '대화형 워크플로 설계 - 그룹챗/멀티에이전트',
			icon: Cube,
			path: '/builder/autogen',
			gradientFrom: 'from-purple-500',
			gradientTo: 'to-purple-600'
		}
	];
</script>

<svelte:head>
	<title>에이전트 빌더 | {$WEBUI_NAME}</title>
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
							SFN AI Agent Builder
						</span>
						<h1 class="text-2xl font-semibold tracking-tight text-gray-900 dark:text-gray-100">
							원하는 방식으로 AI 에이전트를 만들어보세요
						</h1>
					</div>

					<p class="max-w-3xl text-sm text-gray-600 dark:text-gray-300">
						노코드 빌더로 에이전트를 시각적으로 설계하고, LangGraph로 자동 변환하여 프로덕션 배포까지 한 번에 완성하세요.
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

			<!-- Builder Cards -->
			<div class="grid grid-cols-1 md:grid-cols-3 gap-6">
				{#each builders as builder}
					<button
						class="relative flex flex-col p-6 rounded-xl bg-white/60 dark:bg-gray-900/50 backdrop-blur-xl border border-white/20 dark:border-gray-700/20 shadow-xl hover:shadow-2xl transform hover:-translate-y-1 hover:scale-[1.01] transition-all duration-300 ease-out text-left"
						on:click={() => {
							// 향후 /builder/* 경로 연결
							// goto(builder.path);
						}}
					>
						<div class="flex items-center gap-4 mb-4">
							<div class="p-3 rounded-lg bg-gradient-to-br {builder.gradientFrom} {builder.gradientTo} text-white shadow-lg">
								<builder.icon className="size-6" />
							</div>
							<h2 class="text-xl font-semibold text-gray-900 dark:text-gray-100">{builder.name}</h2>
						</div>
						<p class="text-sm text-gray-600 dark:text-gray-300 mb-4 flex-1">{builder.description}</p>
						<div class="text-sm font-medium bg-gradient-to-r from-primary via-secondary to-accent bg-clip-text text-transparent">
							선택하기 →
						</div>
					</button>
				{/each}
			</div>

			<!-- Status Notice -->
			<div class="p-4 bg-white/50 dark:bg-gray-900/50 backdrop-blur-md rounded-xl border border-white/20 dark:border-gray-700/20 shadow-lg text-sm">
				<p class="font-medium mb-1 text-gray-900 dark:text-gray-100">준비 중입니다</p>
				<p class="text-gray-600 dark:text-gray-300">에이전트 빌더 기능은 Stage 3에서 구현될 예정입니다.</p>
			</div>
		</div>
	</div>
{/if}

