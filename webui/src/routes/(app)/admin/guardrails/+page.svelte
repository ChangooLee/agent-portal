<script lang="ts">
	import { getContext } from 'svelte';
	import { user, WEBUI_NAME } from '$lib/stores';
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import LockClosed from '$lib/components/icons/LockClosed.svelte';

	const i18n = getContext('i18n');

	const heroStats = [
		{ label: '정책 규칙', value: '준비 중', hint: 'AI 응답 필터링' },
		{ label: '모니터링', value: '실시간', hint: '위험 탐지 시스템' },
		{ label: '자동 차단', value: '활성화', hint: '위험 콘텐츠 방지' }
	];

	onMount(async () => {
		if ($user?.role !== 'admin') {
			await goto('/');
		}
	});
</script>

<svelte:head>
	<title>가드레일 | {$WEBUI_NAME}</title>
</svelte:head>

{#if $user?.role !== 'admin'}
	<div class="text-red-500">
		{$i18n.t('Access Denied: Only administrators can view this page.')}
	</div>
{:else}
	<div class="flex w-full flex-col px-3 py-4 @md:px-6 @md:py-6">
		<div class="flex w-full flex-col gap-6">
			<!-- Hero Section -->
			<section class="relative overflow-hidden rounded-3xl border border-white/20 bg-white/60 p-6 shadow-2xl shadow-primary/10 backdrop-blur-2xl dark:border-gray-700/30 dark:bg-gray-900/60">
				<div class="absolute inset-0 bg-gradient-to-br from-primary/20 via-secondary/10 to-accent/20 opacity-60" />
				<div class="pointer-events-none absolute -right-10 -top-12 h-40 w-40 rounded-full bg-gradient-to-br from-primary/40 to-secondary/30 blur-3xl" />
				<div class="relative flex flex-col gap-5">
					<div class="flex flex-wrap items-center gap-3">
						<span class="inline-flex items-center gap-2 rounded-full bg-white/90 px-3 py-1 text-xs font-medium text-gray-600 shadow-sm dark:bg-gray-800/80 dark:text-gray-200">
							<span class="h-1.5 w-1.5 rounded-full bg-gradient-to-r from-primary via-secondary to-accent" />
							SFN AI Guardrails
						</span>
						<h1 class="text-2xl font-semibold tracking-tight text-gray-900 dark:text-gray-100">
							안전하고 책임감 있는 AI 응답을 보장하세요
						</h1>
					</div>

					<p class="max-w-3xl text-sm text-gray-600 dark:text-gray-300">
						AI 응답 가드레일을 설정하여 부적절한 콘텐츠를 필터링하고, 윤리적 기준을 준수하며, 기업 정책을 적용합니다.
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
				<div class="mb-4 inline-flex p-4 rounded-2xl bg-gradient-to-br from-red-500 to-red-600 shadow-lg">
					<LockClosed className="size-16 text-white" strokeWidth="1.75" />
				</div>
				<h2 class="text-xl font-semibold mb-2 text-gray-900 dark:text-gray-100">준비 중입니다</h2>
				<p class="text-gray-600 dark:text-gray-300 mb-4">
					가드레일 관리 기능은 향후 버전에서 구현될 예정입니다.
				</p>
				<p class="text-sm text-gray-500 dark:text-gray-400">
					콘텐츠 필터링, 정책 설정, 위험 탐지, 감사 로그 등의 기능이 제공됩니다.
				</p>
			</div>
		</div>
	</div>
{/if}

