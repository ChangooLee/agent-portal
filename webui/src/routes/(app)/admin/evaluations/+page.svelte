<script lang="ts">
	import Evaluations from '$lib/components/admin/Evaluations.svelte';

	const heroStats = [
		{ label: '핵심 지표', value: '정확도 · 응답속도', hint: 'Stage 3에서 실데이터 연결' },
		{ label: '랭킹 산출', value: '실시간 업데이트', hint: 'OTEL 기반 분석' },
		{ label: '운영 목표', value: '품질 모니터링', hint: 'SLA 기반 점수화' }
	];
</script>

<div class="flex w-full flex-col px-3 py-4 @md:px-6 @md:py-6">
	<div class="flex w-full flex-col gap-6">
		<section class="relative overflow-hidden rounded-3xl border border-white/20 bg-white/60 p-6 shadow-2xl shadow-primary/10 backdrop-blur-2xl dark:border-gray-700/30 dark:bg-gray-900/60">
			<div class="absolute inset-0 bg-gradient-to-br from-primary/20 via-secondary/10 to-accent/20 opacity-60" />
			<div class="pointer-events-none absolute -right-10 -top-12 h-40 w-40 rounded-full bg-gradient-to-br from-primary/40 to-secondary/30 blur-3xl" />
			<div class="relative flex flex-col gap-5">
				<div class="flex flex-wrap items-center gap-3">
					<span class="inline-flex items-center gap-2 rounded-full bg-white/90 px-3 py-1 text-xs font-medium text-gray-600 shadow-sm dark:bg-gray-800/80 dark:text-gray-200">
						<span class="h-1.5 w-1.5 rounded-full bg-gradient-to-r from-primary via-secondary to-accent" />
						SFN 리더보드
					</span>
					<h1 class="text-2xl font-semibold tracking-tight text-gray-900 dark:text-gray-100">
						모델·에이전트 성능을 한눈에 비교하세요
					</h1>
				</div>

				<p class="max-w-3xl text-sm text-gray-600 dark:text-gray-300">
					사용량, 품질 지표, 피드백 데이터를 조합해 모델과 에이전트의 경쟁력을 시각화합니다. Stage 3에서는 OTEL 기반 트레이스 분석과 연동하여 실시간 랭킹을 제공합니다.
				</p>

				<div class="grid grid-cols-3 gap-3 @md:grid-cols-4 @lg:grid-cols-6">
					{#each heroStats as stat}
						<div class="rounded-2xl border border-white/30 bg-white/70 px-4 py-3 text-left shadow-md shadow-primary/10 transition dark:border-gray-700/30 dark:bg-gray-900/50">
							<div class="text-[11px] font-medium uppercase tracking-wide text-primary dark:text-primary-light">
								{stat.label}
							</div>
							<div class="text-sm font-semibold text-gray-900 dark:text-gray-100">
								{stat.value}
							</div>
							<div class="pt-1 text-xs text-gray-500 dark:text-gray-400">{stat.hint}</div>
						</div>
					{/each}
				</div>
			</div>
		</section>

		<div class="rounded-3xl border border-white/20 bg-white/70 p-4 shadow-xl shadow-primary/10 backdrop-blur-xl dark:border-gray-700/20 dark:bg-gray-900/60 @md:p-6">
			<Evaluations />
		</div>
	</div>
</div>
