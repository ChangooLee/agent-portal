<script lang="ts">
	import { getContext } from 'svelte';
	import { user } from '$lib/stores';
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

<div class="flex flex-col w-full h-full">
	{#if $user?.role !== 'admin'}
		<div class="text-red-500">
			{$i18n.t('Access Denied: Only administrators can view this page.')}
		</div>
	{:else}
		<div class="p-6">
			<h1 class="text-2xl font-semibold text-gray-800 mb-4">가드레일 관리</h1>
			<p class="text-gray-600">AI 응답 가드레일 설정 및 관리 페이지입니다.</p>
			<!-- 가드레일 관리 기능은 추후 구현 예정 -->
		</div>
	{/if}
</div>

