<script lang="ts">
</script>

<svelte:head>
    <title>워크플로우 | SFN AI Portal</title>
</svelte:head>

<div class="min-h-full bg-gray-950 text-slate-50">
    <!-- Hero Section -->
    <div class="relative overflow-hidden border-b border-slate-800/50">
        <div class="absolute inset-0 bg-gradient-to-br from-purple-600/5 via-transparent to-blue-600/5"></div>
        <div class="absolute inset-0 bg-[linear-gradient(rgba(147,51,234,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(147,51,234,0.03)_1px,transparent_1px)] bg-[size:64px_64px]"></div>
        
        <div class="relative px-6 py-8 text-center">
            <h1 class="text-3xl md:text-4xl font-bold mb-3 text-white">
                워크플로우
            </h1>
            <p class="text-base text-purple-200/80">
                AI 에이전트 워크플로우를 시각적으로 설계하세요.
            </p>
        </div>
    </div>

    <div class="px-6 py-12">
        <!-- Coming Soon Card -->
        <div class="bg-slate-900/80 border border-slate-800/50 rounded-2xl p-10 text-center shadow-xl shadow-black/20 max-w-3xl mx-auto">
            <div class="w-20 h-20 mx-auto mb-6 rounded-2xl bg-gradient-to-br from-purple-500/20 to-purple-600/10 border border-purple-500/20 flex items-center justify-center">
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-10 h-10 text-purple-400">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M3.75 6A2.25 2.25 0 016 3.75h2.25A2.25 2.25 0 0110.5 6v2.25a2.25 2.25 0 01-2.25 2.25H6a2.25 2.25 0 01-2.25-2.25V6zM3.75 15.75A2.25 2.25 0 016 13.5h2.25a2.25 2.25 0 012.25 2.25V18a2.25 2.25 0 01-2.25 2.25H6A2.25 2.25 0 013.75 18v-2.25zM13.5 6a2.25 2.25 0 012.25-2.25H18A2.25 2.25 0 0120.25 6v2.25A2.25 2.25 0 0118 10.5h-2.25a2.25 2.25 0 01-2.25-2.25V6zM13.5 15.75a2.25 2.25 0 012.25-2.25H18a2.25 2.25 0 012.25 2.25V18A2.25 2.25 0 0118 20.25h-2.25A2.25 2.25 0 0113.5 18v-2.25z" />
                </svg>
            </div>
            <span class="inline-block px-4 py-1.5 bg-amber-500/20 text-amber-400 text-sm font-medium rounded-full mb-4 border border-amber-500/30">
                Coming Soon
            </span>
            <h2 class="text-2xl font-semibold text-white mb-3">워크플로우 빌더</h2>
            <p class="text-slate-400 mb-8 max-w-lg mx-auto leading-relaxed">
                드래그 앤 드롭으로 복잡한 AI 파이프라인을 설계하세요.
                LangGraph 기반의 강력한 워크플로우 엔진을 제공합니다.
            </p>
            <div class="grid grid-cols-1 sm:grid-cols-3 gap-4 max-w-xl mx-auto text-left">
                <div class="bg-slate-800/50 border border-slate-700/50 rounded-xl p-4 hover:border-purple-500/30 transition-colors duration-300">
                    <div class="text-sm font-medium text-white mb-1">노드 기반</div>
                    <div class="text-xs text-slate-500">시각적 그래프 편집</div>
                </div>
                <div class="bg-slate-800/50 border border-slate-700/50 rounded-xl p-4 hover:border-purple-500/30 transition-colors duration-300">
                    <div class="text-sm font-medium text-white mb-1">조건 분기</div>
                    <div class="text-xs text-slate-500">복잡한 로직 처리</div>
                </div>
                <div class="bg-slate-800/50 border border-slate-700/50 rounded-xl p-4 hover:border-purple-500/30 transition-colors duration-300">
                    <div class="text-sm font-medium text-white mb-1">병렬 실행</div>
                    <div class="text-xs text-slate-500">동시 작업 처리</div>
                </div>
            </div>
        </div>
    </div>
</div>
