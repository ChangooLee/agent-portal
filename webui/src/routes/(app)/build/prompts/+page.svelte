<script lang="ts">
</script>

<svelte:head>
    <title>프롬프트 | SFN AI Portal</title>
</svelte:head>

<div class="min-h-full bg-gray-950 text-slate-50 p-6 overflow-y-auto">
    <!-- Header -->
    <div class="mb-8">
        <h1 class="text-3xl font-bold mb-3">
            <span class="bg-gradient-to-r from-white to-slate-400 bg-clip-text text-transparent">
                프롬프트 라이브러리
            </span>
        </h1>
        <p class="text-slate-400">프롬프트 템플릿을 관리하고 버전을 추적합니다.</p>
    </div>

    <!-- Coming Soon Card -->
    <div class="bg-slate-900/80 border border-slate-800/50 rounded-2xl p-10 text-center shadow-xl shadow-black/20">
        <div class="w-20 h-20 mx-auto mb-6 rounded-2xl bg-gradient-to-br from-amber-500/20 to-amber-600/10 border border-amber-500/20 flex items-center justify-center">
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-10 h-10 text-amber-400">
                <path stroke-linecap="round" stroke-linejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
            </svg>
        </div>
        <span class="inline-block px-4 py-1.5 bg-amber-500/20 text-amber-400 text-sm font-medium rounded-full mb-4 border border-amber-500/30">
            Coming Soon
        </span>
        <h2 class="text-2xl font-semibold text-white mb-3">프롬프트 관리 시스템</h2>
        <p class="text-slate-400 mb-8 max-w-lg mx-auto leading-relaxed">
            프롬프트 버전 관리, A/B 테스트, 성능 분석을 지원합니다.
            팀과 함께 프롬프트를 협업하고 개선하세요.
        </p>
        <div class="grid grid-cols-1 sm:grid-cols-3 gap-4 max-w-xl mx-auto text-left">
            <div class="bg-slate-800/50 border border-slate-700/50 rounded-xl p-4 hover:border-amber-500/30 transition-colors duration-300">
                <div class="text-sm font-medium text-white mb-1">버전 관리</div>
                <div class="text-xs text-slate-500">변경 이력 추적</div>
            </div>
            <div class="bg-slate-800/50 border border-slate-700/50 rounded-xl p-4 hover:border-amber-500/30 transition-colors duration-300">
                <div class="text-sm font-medium text-white mb-1">A/B 테스트</div>
                <div class="text-xs text-slate-500">성능 비교 분석</div>
            </div>
            <div class="bg-slate-800/50 border border-slate-700/50 rounded-xl p-4 hover:border-amber-500/30 transition-colors duration-300">
                <div class="text-sm font-medium text-white mb-1">템플릿</div>
                <div class="text-xs text-slate-500">재사용 가능</div>
            </div>
        </div>
    </div>
</div>
