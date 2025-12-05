<script lang="ts">
</script>

<svelte:head>
    <title>워크플로우 | SFN AI Portal</title>
</svelte:head>

<div class="h-full bg-gray-950 text-white p-6 overflow-auto">
    <div class="max-w-6xl mx-auto">
        <!-- Header -->
        <div class="mb-8">
            <h1 class="text-3xl font-bold text-white mb-2">워크플로우</h1>
            <p class="text-gray-400">AI 에이전트 워크플로우를 시각적으로 설계합니다.</p>
        </div>

        <!-- Coming Soon Card -->
        <div class="bg-gray-900 border border-gray-800 rounded-xl p-8 text-center">
            <div class="w-16 h-16 mx-auto mb-4 rounded-xl bg-purple-600/20 flex items-center justify-center">
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-8 h-8 text-purple-400">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M3.75 6A2.25 2.25 0 016 3.75h2.25A2.25 2.25 0 0110.5 6v2.25a2.25 2.25 0 01-2.25 2.25H6a2.25 2.25 0 01-2.25-2.25V6zM3.75 15.75A2.25 2.25 0 016 13.5h2.25a2.25 2.25 0 012.25 2.25V18a2.25 2.25 0 01-2.25 2.25H6A2.25 2.25 0 013.75 18v-2.25zM13.5 6a2.25 2.25 0 012.25-2.25H18A2.25 2.25 0 0120.25 6v2.25A2.25 2.25 0 0118 10.5h-2.25a2.25 2.25 0 01-2.25-2.25V6zM13.5 15.75a2.25 2.25 0 012.25-2.25H18a2.25 2.25 0 012.25 2.25V18A2.25 2.25 0 0118 20.25h-2.25A2.25 2.25 0 0113.5 18v-2.25z" />
                </svg>
            </div>
            <span class="inline-block px-3 py-1 bg-yellow-600/20 text-yellow-400 text-sm font-medium rounded-full mb-4">
                Coming Soon
            </span>
            <h2 class="text-xl font-semibold text-white mb-2">워크플로우 빌더</h2>
            <p class="text-gray-400 mb-6">
                드래그 앤 드롭으로 복잡한 AI 파이프라인을 설계하세요.<br />
                LangGraph 기반의 강력한 워크플로우 엔진을 제공합니다.
            </p>
            <div class="grid grid-cols-3 gap-4 max-w-md mx-auto text-left">
                <div class="bg-gray-800/50 rounded-lg p-3">
                    <div class="text-sm font-medium text-white mb-1">노드 기반</div>
                    <div class="text-xs text-gray-400">시각적 그래프 편집</div>
                </div>
                <div class="bg-gray-800/50 rounded-lg p-3">
                    <div class="text-sm font-medium text-white mb-1">조건 분기</div>
                    <div class="text-xs text-gray-400">복잡한 로직 처리</div>
                </div>
                <div class="bg-gray-800/50 rounded-lg p-3">
                    <div class="text-sm font-medium text-white mb-1">병렬 실행</div>
                    <div class="text-xs text-gray-400">동시 작업 처리</div>
                </div>
            </div>
        </div>
    </div>
</div>

