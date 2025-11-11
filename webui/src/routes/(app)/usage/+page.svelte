<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { goto } from '$app/navigation';
	import { WEBUI_NAME, showSidebar, user } from '$lib/stores';

	const i18n = getContext('i18n');

	onMount(async () => {
		if ($user?.role === 'admin') {
			await goto('/admin/monitoring');
		} else {
			await goto('/');
		}
	});
</script>

<svelte:head>
	<title>사용량 | {$WEBUI_NAME}</title>
</svelte:head>

<div
	class="flex flex-col w-full h-screen max-h-[100dvh] transition-width duration-200 ease-in-out {$showSidebar
		? 'md:max-w-[calc(100%-260px)]'
		: ''} max-w-full"
>
	<div class="flex-1 overflow-y-auto p-8">
		<div class="max-w-4xl mx-auto text-center">
			<p class="text-gray-600">리다이렉트 중...</p>
		</div>
	</div>
</div>

