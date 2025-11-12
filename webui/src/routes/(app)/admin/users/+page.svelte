<script lang="ts">
	import Users from '$lib/components/admin/Users.svelte';

	const heroStats = [
		{ label: '역할 기반 접근', value: 'Admin · Manager · Viewer', hint: '세분화된 권한 제어' },
		{ label: '상태 모니터링', value: '실시간', hint: '활성/비활성 사용자 추적' },
		{ label: '프로비저닝', value: '자동화 준비', hint: 'Stage 3에서 워크플로 연동' }
	];
</script>

<div class="flex w-full flex-col min-h-full px-3 py-4 @md:px-6 @md:py-6">
	<div class="mx-auto flex w-full max-w-[1200px] flex-col gap-6">
		<section class="relative overflow-hidden rounded-3xl border border-white/20 bg-white/60 p-6 shadow-2xl shadow-primary/10 backdrop-blur-2xl dark:border-gray-700/30 dark:bg-gray-900/60">
			<div class="absolute inset-0 bg-gradient-to-br from-primary/20 via-secondary/10 to-accent/20 opacity-60" />
			<div class="pointer-events-none absolute -right-10 -top-12 h-40 w-40 rounded-full bg-gradient-to-br from-primary/40 to-secondary/30 blur-3xl" />
			<div class="relative flex flex-col gap-5">
				<div class="flex flex-wrap items-center gap-3">
					<span class="inline-flex items-center gap-2 rounded-full bg-white/90 px-3 py-1 text-xs font-medium text-gray-600 shadow-sm dark:bg-gray-800/80 dark:text-gray-200">
						<span class="h-1.5 w-1.5 rounded-full bg-gradient-to-r from-primary via-secondary to-accent" />
						SFN 사용자관리
					</span>
					<h1 class="text-2xl font-semibold tracking-tight text-gray-900 dark:text-gray-100">
						조직 구성원과 권한을 한 곳에서 관리하세요
					</h1>
				</div>

				<p class="max-w-3xl text-sm text-gray-600 dark:text-gray-300">
					역할 기반 접근 제어와 초대, 감사 로그 기능을 통합하여 사용자 라이프사이클을 효율적으로 운영할 수 있도록 준비하고 있습니다.
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
			<Users />
		</div>
	</div>
</div>
