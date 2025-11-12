<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { WEBUI_NAME, showSidebar } from '$lib/stores';
	import Search from '$lib/components/icons/Search.svelte';

	const i18n = getContext('i18n');

	let loaded = false;

	onMount(async () => {
		loaded = true;
	});
</script>

<svelte:head>
	<title>검색 | {$WEBUI_NAME}</title>
</svelte:head>

{#if loaded}
	<div class="flex flex-col w-full min-h-full">
		<div class="flex-1 overflow-y-auto p-8">
			<div class="w-full">
				<div class="flex items-center gap-4 mb-6">
					<div class="p-3 rounded-lg bg-green-500 text-white">
						<Search className="size-8" />
					</div>
					<div>
						<h1 class="text-3xl font-bold">검색 포털</h1>
						<p class="text-gray-600">대화형 리서치에 특화된 검색 포털</p>
					</div>
				</div>

				<div class="bg-white rounded-xl border border-gray-200 p-8 text-center">
					<div class="mb-4">
						<Search className="size-16 mx-auto text-gray-300" />
					</div>
					<h2 class="text-xl font-semibold mb-2">준비 중입니다</h2>
					<p class="text-gray-600 mb-4">
						Perplexica 검색 포털 기능은 Stage 8에서 구현될 예정입니다.
					</p>
					<p class="text-sm text-gray-500">
						향후 iframe으로 임베드되어 포털 Apps 탭에서 사용할 수 있습니다.
					</p>
				</div>
			</div>
		</div>
	</div>
{/if}

