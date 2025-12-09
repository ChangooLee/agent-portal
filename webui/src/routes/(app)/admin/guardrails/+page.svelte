<script lang="ts">
	import { getContext } from 'svelte';
	import { user, WEBUI_NAME } from '$lib/stores';
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';

	const i18n = getContext('i18n');

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
	<div class="text-red-500 p-6">
		{$i18n.t('Access Denied: Only administrators can view this page.')}
	</div>
{:else}
	<div class="min-h-full bg-gray-950 text-slate-50">
		<!-- Hero Section -->
		<div class="relative overflow-hidden border-b border-slate-800/50">
			<div class="absolute inset-0 bg-gradient-to-br from-red-600/5 via-transparent to-rose-600/5"></div>
			<div class="absolute inset-0 bg-[linear-gradient(rgba(239,68,68,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(239,68,68,0.03)_1px,transparent_1px)] bg-[size:64px_64px]"></div>
			
		<div class="relative px-6 py-8 text-center">
			<h1 class="text-3xl md:text-4xl font-bold mb-3 text-white">
				🛡️ 가드레일
			</h1>
			<p class="text-base text-red-200/80">
				안전하고 책임감 있는 AI 응답을 보장하세요.
			</p>
		</div>
		</div>

		<div class="px-6 py-12">
			<!-- Coming Soon Card -->
			<div class="bg-slate-900/80 border border-slate-800/50 rounded-2xl p-10 text-center shadow-xl shadow-black/20 max-w-2xl mx-auto">
				<div class="w-20 h-20 mx-auto mb-6 rounded-2xl bg-gradient-to-br from-red-500/20 to-red-600/10 border border-red-500/20 flex items-center justify-center">
					<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-10 h-10 text-red-400">
						<path stroke-linecap="round" stroke-linejoin="round" d="M16.5 10.5V6.75a4.5 4.5 0 1 0-9 0v3.75m-.75 11.25h10.5a2.25 2.25 0 0 0 2.25-2.25v-6.75a2.25 2.25 0 0 0-2.25-2.25H6.75a2.25 2.25 0 0 0-2.25 2.25v6.75a2.25 2.25 0 0 0 2.25 2.25Z" />
					</svg>
				</div>
				<span class="inline-block px-4 py-1.5 bg-amber-500/20 text-amber-400 text-sm font-medium rounded-full mb-4 border border-amber-500/30">
					Coming Soon
				</span>
				<h2 class="text-2xl font-semibold text-white mb-3">준비 중입니다</h2>
				<p class="text-slate-300 mb-8 max-w-lg leading-relaxed">
					가드레일 관리 기능은 향후 버전에서 구현될 예정입니다.
					콘텐츠 필터링, 정책 설정, 위험 탐지, 감사 로그 등의 기능이 제공됩니다.
				</p>
				<div class="grid grid-cols-1 sm:grid-cols-3 gap-4 max-w-xl mx-auto text-left">
					<div class="bg-slate-800/50 border border-slate-700/50 rounded-xl p-4 hover:border-red-500/30 transition-colors duration-300">
						<div class="text-sm font-medium text-white mb-1">정책 규칙</div>
						<div class="text-xs text-slate-500">AI 응답 필터링</div>
					</div>
					<div class="bg-slate-800/50 border border-slate-700/50 rounded-xl p-4 hover:border-red-500/30 transition-colors duration-300">
						<div class="text-sm font-medium text-white mb-1">실시간 모니터링</div>
						<div class="text-xs text-slate-500">위험 탐지 시스템</div>
					</div>
					<div class="bg-slate-800/50 border border-slate-700/50 rounded-xl p-4 hover:border-red-500/30 transition-colors duration-300">
						<div class="text-sm font-medium text-white mb-1">자동 차단</div>
						<div class="text-xs text-slate-500">위험 콘텐츠 방지</div>
					</div>
				</div>
			</div>
		</div>
	</div>
{/if}
