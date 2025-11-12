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

	const builders = [
		{
			id: 'langflow',
			name: 'Langflow',
			description: '노코드 에이전트 빌더 - LangGraph 친화적',
			icon: Cube,
			path: '/builder/langflow',
			color: 'bg-blue-500'
		},
		{
			id: 'flowise',
			name: 'Flowise',
			description: '노코드 에이전트 빌더 - 위젯/임베드 용이',
			icon: Cube,
			path: '/builder/flowise',
			color: 'bg-green-500'
		},
		{
			id: 'autogen',
			name: 'AutoGen Studio',
			description: '대화형 워크플로 설계 - 그룹챗/멀티에이전트',
			icon: Cube,
			path: '/builder/autogen',
			color: 'bg-purple-500'
		}
	];
</script>

<svelte:head>
	<title>에이전트 빌더 | {$WEBUI_NAME}</title>
</svelte:head>

{#if loaded}
	<div class="flex flex-col w-full min-h-full">
		<div class="flex-1 overflow-y-auto p-8">
			<div class="w-full">
				<h1 class="text-3xl font-bold mb-2">에이전트 빌더</h1>
				<p class="text-gray-600 mb-8">원하는 방식으로 AI 에이전트를 만들어보세요.</p>

				<div class="grid grid-cols-1 md:grid-cols-3 gap-6">
					{#each builders as builder}
						<button
							class="bg-white rounded-xl border border-gray-200 p-6 hover:border-blue-500 hover:shadow-lg transition-all text-left group"
							on:click={() => {
								// 향후 /builder/* 경로 연결
								// goto(builder.path);
							}}
						>
							<div class="flex items-center gap-4 mb-4">
								<div class="p-3 rounded-lg {builder.color} text-white">
									<builder.icon className="size-6" />
								</div>
								<h2 class="text-xl font-semibold">{builder.name}</h2>
							</div>
							<p class="text-gray-600 text-sm">{builder.description}</p>
							<div class="mt-4 text-blue-600 text-sm font-medium opacity-0 group-hover:opacity-100 transition-opacity">
								선택하기 →
							</div>
						</button>
					{/each}
				</div>

				<div class="mt-8 p-4 bg-blue-50 rounded-lg text-sm text-gray-700">
					<p class="font-medium mb-1">준비 중입니다</p>
					<p>에이전트 빌더 기능은 Stage 3에서 구현될 예정입니다.</p>
				</div>
			</div>
		</div>
	</div>
{/if}

