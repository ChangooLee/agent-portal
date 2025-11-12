<script lang="ts">
	import { getContext } from 'svelte';
	import { user, WEBUI_NAME } from '$lib/stores';
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import Cube from '$lib/components/icons/Cube.svelte';

	const i18n = getContext('i18n');

	const heroStats = [
		{ label: '지원 프로토콜', value: 'MCP 1.0', hint: 'Model Context Protocol' },
		{ label: '연결된 서버', value: '0개', hint: '준비 중' },
		{ label: '상태', value: '개발 예정', hint: '향후 버전 출시' }
	];

	onMount(async () => {
		if ($user?.role !== 'admin') {
			await goto('/');
		}
	});
</script>

<svelte:head>
	<title>MCP | {$WEBUI_NAME}</title>
</svelte:head>

{#if $user?.role !== 'admin'}
	<div class="text-red-500">
		{$i18n.t('Access Denied: Only administrators can view this page.')}
	</div>
{:else}
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
							SFN AI MCP Manager
						</span>
						<h1 class="text-2xl font-semibold tracking-tight text-gray-900 dark:text-gray-100">
							Model Context Protocol로 AI 기능을 확장하세요
						</h1>
					</div>

					<p class="max-w-3xl text-sm text-gray-600 dark:text-gray-300">
						MCP 서버를 연결하여 AI 모델에 실시간 데이터 접근, 도구 사용, 외부 시스템 통합 기능을 제공합니다.
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
				<div class="mb-4 inline-flex p-4 rounded-2xl bg-gradient-to-br from-purple-500 to-purple-600 shadow-lg">
					<Cube className="size-16 text-white" />
				</div>
				<h2 class="text-xl font-semibold mb-2 text-gray-900 dark:text-gray-100">준비 중입니다</h2>
				<p class="text-gray-600 dark:text-gray-300 mb-4">
					MCP 관리 기능은 향후 버전에서 구현될 예정입니다.
				</p>
				<p class="text-sm text-gray-500 dark:text-gray-400">
					MCP 서버 연결, 도구 관리, 권한 설정 등의 기능이 제공됩니다.
				</p>
			</div>
		</div>
	</div>
{/if}

