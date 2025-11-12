<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { WEBUI_NAME, showSidebar } from '$lib/stores';
	import Calendar from '$lib/components/icons/Calendar.svelte';

	const i18n = getContext('i18n');

	let loaded = false;

	onMount(async () => {
		loaded = true;
	});
</script>

<svelte:head>
	<title>일정관리 | {$WEBUI_NAME}</title>
</svelte:head>

{#if loaded}
	<div class="flex flex-col w-full min-h-full">
		<div class="flex-1 overflow-y-auto p-8">
			<div class="w-full">
				<div class="flex items-center gap-4 mb-6">
					<div class="p-3 rounded-lg bg-orange-500 text-white">
						<Calendar className="size-8" />
					</div>
					<div>
						<h1 class="text-3xl font-bold">일정관리</h1>
						<p class="text-gray-600">일정 관리 및 작업 추적</p>
					</div>
				</div>

				<div class="bg-white rounded-xl border border-gray-200 p-8 text-center">
					<div class="mb-4">
						<Calendar className="size-16 mx-auto text-gray-300" />
					</div>
					<h2 class="text-xl font-semibold mb-2">기능 준비 중</h2>
					<p class="text-gray-600 mb-4">
						일정 관리 기능은 추후 구현될 예정입니다.
					</p>
					<p class="text-sm text-gray-500">
						이 기능에 대한 상세 내용은 README에 추가될 예정입니다.
					</p>
				</div>
			</div>
		</div>
	</div>
{/if}

