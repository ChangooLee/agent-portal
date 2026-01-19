<script lang="ts">
</script>

<svelte:head>
    <title>Knowledge | SFN AI Portal</title>
</svelte:head>

<div class="min-h-full bg-gray-950 text-slate-50">
    <!-- Hero Section -->
    <div class="relative overflow-hidden border-b border-slate-800/50">
        <div class="absolute inset-0 bg-gradient-to-br from-emerald-600/5 via-transparent to-teal-600/5"></div>
        <div class="absolute inset-0 bg-[linear-gradient(rgba(16,185,129,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(16,185,129,0.03)_1px,transparent_1px)] bg-[size:64px_64px]"></div>
        
        <div class="relative px-6 py-8 text-center">
            <h1 class="text-3xl md:text-4xl font-bold mb-3 text-white">
                Knowledge Base
            </h1>
            <p class="text-base text-emerald-200/80">
                RAG를 위한 지식 베이스를 구축하고 관리합니다.
            </p>
        </div>
    </div>

    <div class="px-6 py-12">
        <!-- Coming Soon Card -->
        <div class="bg-slate-900/80 border border-slate-800/50 rounded-2xl p-10 text-center shadow-xl shadow-black/20 max-w-3xl mx-auto">
            <div class="w-20 h-20 mx-auto mb-6 rounded-2xl bg-gradient-to-br from-emerald-500/20 to-emerald-600/10 border border-emerald-500/20 flex items-center justify-center">
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-10 h-10 text-emerald-400">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M12 6.042A8.967 8.967 0 006 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 016 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 016-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0018 18a8.967 8.967 0 00-6 2.292m0-14.25v14.25" />
                </svg>
            </div>
            <span class="inline-block px-4 py-1.5 bg-amber-500/20 text-amber-400 text-sm font-medium rounded-full mb-4 border border-amber-500/30">
                Coming Soon
            </span>
            <h2 class="text-2xl font-semibold text-white mb-3">지식 베이스 관리</h2>
            <p class="text-slate-400 mb-8 max-w-lg mx-auto leading-relaxed">
                문서, 웹페이지, 데이터베이스에서 지식을 수집하고 벡터화합니다.
                AI 에이전트가 참조할 수 있는 신뢰할 수 있는 정보원을 구축하세요.
            </p>
            <div class="grid grid-cols-1 sm:grid-cols-3 gap-4 max-w-xl mx-auto text-left">
                <div class="bg-slate-800/50 border border-slate-700/50 rounded-xl p-4 hover:border-emerald-500/30 transition-colors duration-300">
                    <div class="text-sm font-medium text-white mb-1">문서 업로드</div>
                    <div class="text-xs text-slate-500">PDF, DOCX 지원</div>
                </div>
                <div class="bg-slate-800/50 border border-slate-700/50 rounded-xl p-4 hover:border-emerald-500/30 transition-colors duration-300">
                    <div class="text-sm font-medium text-white mb-1">벡터 검색</div>
                    <div class="text-xs text-slate-500">의미 기반 검색</div>
                </div>
                <div class="bg-slate-800/50 border border-slate-700/50 rounded-xl p-4 hover:border-emerald-500/30 transition-colors duration-300">
                    <div class="text-sm font-medium text-white mb-1">자동 동기화</div>
                    <div class="text-xs text-slate-500">최신 상태 유지</div>
                </div>
            </div>
        </div>
    </div>
</div>
