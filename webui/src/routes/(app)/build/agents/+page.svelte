<script lang="ts">
    import { goto } from '$app/navigation';
</script>

<svelte:head>
    <title>에이전트 빌더 | SFN AI Portal</title>
</svelte:head>

<div class="min-h-full bg-gray-950 text-slate-50">
    <!-- Hero Section -->
    <div class="relative overflow-hidden border-b border-slate-800/50">
        <div class="absolute inset-0 bg-gradient-to-br from-blue-600/5 via-transparent to-purple-600/5"></div>
        <div class="absolute inset-0 bg-[linear-gradient(rgba(59,130,246,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(59,130,246,0.03)_1px,transparent_1px)] bg-[size:64px_64px]"></div>
        
        <div class="relative px-6 py-8 text-center">
            <h1 class="text-3xl md:text-4xl font-bold mb-3 text-white">
                에이전트 빌더
            </h1>
            <p class="text-base text-blue-200/80">
                시각적 에이전트 빌더를 통해 맞춤형 AI 에이전트를 생성하세요.
            </p>
        </div>
    </div>

    <div class="px-6 py-12">
        <!-- Coming Soon Card -->
        <div class="bg-slate-900/80 border border-slate-800/50 rounded-2xl p-10 text-center shadow-xl shadow-black/20 max-w-2xl mx-auto">
            <div class="w-20 h-20 mx-auto mb-6 rounded-2xl bg-gradient-to-br from-blue-500/20 to-blue-600/10 border border-blue-500/20 flex items-center justify-center">
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-10 h-10 text-blue-400">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M11.42 15.17L17.25 21A2.652 2.652 0 0021 17.25l-5.877-5.877M11.42 15.17l2.496-3.03c.317-.384.74-.626 1.208-.766M11.42 15.17l-4.655 5.653a2.548 2.548 0 11-3.586-3.586l6.837-5.63m5.108-.233c.55-.164 1.163-.188 1.743-.14a4.5 4.5 0 004.486-6.336l-3.276 3.277a3.004 3.004 0 01-2.25-2.25l3.276-3.276a4.5 4.5 0 00-6.336 4.486c.091 1.076-.071 2.264-.904 2.95l-.102.085m-1.745 1.437L5.909 7.5H4.5L2.25 3.75l1.5-1.5L7.5 4.5v1.409l4.26 4.26m-1.745 1.437l1.745-1.437m6.615 8.206L15.75 15.75M4.867 19.125h.008v.008h-.008v-.008z" />
                </svg>
            </div>
            <span class="inline-block px-4 py-1.5 bg-amber-500/20 text-amber-400 text-sm font-medium rounded-full mb-4 border border-amber-500/30">
                Coming Soon
            </span>
            <h2 class="text-2xl font-semibold text-white mb-3">에이전트 빌더 개발 중</h2>
            <p class="text-slate-400 mb-8 max-w-lg mx-auto leading-relaxed">
                시각적 에이전트 빌더를 통해 맞춤형 AI 에이전트를 생성할 수 있습니다.
                현재 개발 중이며 곧 출시될 예정입니다.
            </p>
            <div class="flex justify-center gap-4">
                <button
                    class="px-5 py-2.5 bg-slate-800/80 hover:bg-slate-700/80 text-slate-300 hover:text-white rounded-xl transition-all duration-300 border border-slate-700/50 hover:border-slate-600/50"
                    on:click={() => goto('/use/agents')}
                >
                    에이전트 사용하기
                </button>
            </div>
        </div>
    </div>
</div>
