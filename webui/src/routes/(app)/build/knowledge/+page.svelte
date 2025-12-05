<script lang="ts">
</script>

<svelte:head>
    <title>Knowledge | SFN AI Portal</title>
</svelte:head>

<div class="h-full bg-gray-950 text-white p-6 overflow-auto">
    <div class="max-w-6xl mx-auto">
        <!-- Header -->
        <div class="mb-8">
            <h1 class="text-3xl font-bold text-white mb-2">Knowledge Base</h1>
            <p class="text-gray-400">RAG를 위한 지식 베이스를 구축하고 관리합니다.</p>
        </div>

        <!-- Coming Soon Card -->
        <div class="bg-gray-900 border border-gray-800 rounded-xl p-8 text-center">
            <div class="w-16 h-16 mx-auto mb-4 rounded-xl bg-emerald-600/20 flex items-center justify-center">
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-8 h-8 text-emerald-400">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M12 6.042A8.967 8.967 0 006 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 016 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 016-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0018 18a8.967 8.967 0 00-6 2.292m0-14.25v14.25" />
                </svg>
            </div>
            <span class="inline-block px-3 py-1 bg-yellow-600/20 text-yellow-400 text-sm font-medium rounded-full mb-4">
                Coming Soon
            </span>
            <h2 class="text-xl font-semibold text-white mb-2">지식 베이스 관리</h2>
            <p class="text-gray-400 mb-6">
                문서, 웹페이지, 데이터베이스에서 지식을 수집하고 벡터화합니다.<br />
                AI 에이전트가 참조할 수 있는 신뢰할 수 있는 정보원을 구축하세요.
            </p>
            <div class="grid grid-cols-3 gap-4 max-w-md mx-auto text-left">
                <div class="bg-gray-800/50 rounded-lg p-3">
                    <div class="text-sm font-medium text-white mb-1">문서 업로드</div>
                    <div class="text-xs text-gray-400">PDF, DOCX 지원</div>
                </div>
                <div class="bg-gray-800/50 rounded-lg p-3">
                    <div class="text-sm font-medium text-white mb-1">벡터 검색</div>
                    <div class="text-xs text-gray-400">의미 기반 검색</div>
                </div>
                <div class="bg-gray-800/50 rounded-lg p-3">
                    <div class="text-sm font-medium text-white mb-1">자동 동기화</div>
                    <div class="text-xs text-gray-400">최신 상태 유지</div>
                </div>
            </div>
        </div>
    </div>
</div>

