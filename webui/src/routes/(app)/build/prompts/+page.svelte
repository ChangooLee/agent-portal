<script lang="ts">
</script>

<svelte:head>
    <title>프롬프트 | SFN AI Portal</title>
</svelte:head>

<div class="h-full bg-gray-950 text-white p-6 overflow-auto">
    <div class="max-w-6xl mx-auto">
        <!-- Header -->
        <div class="mb-8">
            <h1 class="text-3xl font-bold text-white mb-2">프롬프트 라이브러리</h1>
            <p class="text-gray-400">프롬프트 템플릿을 관리하고 버전을 추적합니다.</p>
        </div>

        <!-- Coming Soon Card -->
        <div class="bg-gray-900 border border-gray-800 rounded-xl p-8 text-center">
            <div class="w-16 h-16 mx-auto mb-4 rounded-xl bg-amber-600/20 flex items-center justify-center">
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-8 h-8 text-amber-400">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
                </svg>
            </div>
            <span class="inline-block px-3 py-1 bg-yellow-600/20 text-yellow-400 text-sm font-medium rounded-full mb-4">
                Coming Soon
            </span>
            <h2 class="text-xl font-semibold text-white mb-2">프롬프트 관리 시스템</h2>
            <p class="text-gray-400 mb-6">
                프롬프트 버전 관리, A/B 테스트, 성능 분석을 지원합니다.<br />
                팀과 함께 프롬프트를 협업하고 개선하세요.
            </p>
            <div class="grid grid-cols-3 gap-4 max-w-md mx-auto text-left">
                <div class="bg-gray-800/50 rounded-lg p-3">
                    <div class="text-sm font-medium text-white mb-1">버전 관리</div>
                    <div class="text-xs text-gray-400">변경 이력 추적</div>
                </div>
                <div class="bg-gray-800/50 rounded-lg p-3">
                    <div class="text-sm font-medium text-white mb-1">A/B 테스트</div>
                    <div class="text-xs text-gray-400">성능 비교 분석</div>
                </div>
                <div class="bg-gray-800/50 rounded-lg p-3">
                    <div class="text-sm font-medium text-white mb-1">템플릿</div>
                    <div class="text-xs text-gray-400">재사용 가능</div>
                </div>
            </div>
        </div>
    </div>
</div>

