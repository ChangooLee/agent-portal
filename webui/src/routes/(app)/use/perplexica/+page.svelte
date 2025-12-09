<script lang="ts">
    import { onMount } from 'svelte';

    interface PerplexicaFeature {
        id: string;
        name: string;
        description: string;
        icon: string;
        color: string;
        status: 'active' | 'coming-soon';
    }

    const features: PerplexicaFeature[] = [
        {
            id: 'web-search',
            name: '웹 검색',
            description: '인터넷을 깊이 검색하고 출처가 인용된 답변을 받으세요.',
            icon: 'search',
            color: 'blue',
            status: 'coming-soon'
        },
        {
            id: 'academic-search',
            name: '학술 검색',
            description: 'arXiv, Google Scholar, PubMed에서 학술 논문을 검색합니다.',
            icon: 'book',
            color: 'emerald',
            status: 'coming-soon'
        },
        {
            id: 'youtube-search',
            name: 'YouTube 검색',
            description: 'YouTube에서 관련 동영상을 검색하고 요약합니다.',
            icon: 'video',
            color: 'red',
            status: 'coming-soon'
        },
        {
            id: 'image-search',
            name: '이미지 검색',
            description: '웹에서 이미지를 검색하고 분석합니다.',
            icon: 'image',
            color: 'purple',
            status: 'coming-soon'
        }
    ];

    function getColorClasses(color: string) {
        const colors: Record<string, { bg: string; border: string; icon: string }> = {
            blue: {
                bg: 'from-blue-500/20 to-blue-600/10',
                border: 'hover:border-blue-500/50',
                icon: 'text-blue-400'
            },
            emerald: {
                bg: 'from-emerald-500/20 to-emerald-600/10',
                border: 'hover:border-emerald-500/50',
                icon: 'text-emerald-400'
            },
            red: {
                bg: 'from-red-500/20 to-red-600/10',
                border: 'hover:border-red-500/50',
                icon: 'text-red-400'
            },
            purple: {
                bg: 'from-purple-500/20 to-purple-600/10',
                border: 'hover:border-purple-500/50',
                icon: 'text-purple-400'
            }
        };
        return colors[color] || colors.blue;
    }
</script>

<svelte:head>
    <title>AI 검색 | SFN AI Portal</title>
</svelte:head>

<div class="min-h-full bg-gray-950 text-slate-50">
    <!-- Hero Section -->
    <div class="relative overflow-hidden border-b border-slate-800/50">
        <div class="absolute inset-0 bg-gradient-to-br from-blue-600/5 via-transparent to-purple-600/5"></div>
        <div class="absolute inset-0 bg-[linear-gradient(rgba(59,130,246,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(59,130,246,0.03)_1px,transparent_1px)] bg-[size:64px_64px]"></div>
        
        <div class="relative px-6 py-8 text-center">
            <h1 class="text-3xl md:text-4xl font-bold mb-3 text-white">
                🔍 AI 검색
            </h1>
            <p class="text-base text-blue-200/80">
                Perplexica를 사용하여 인터넷을 깊이 검색하고 출처가 인용된 답변을 받으세요.
            </p>
        </div>
    </div>

    <div class="px-6 py-12">
        <!-- Coming Soon Message -->
        <div class="mb-8">
            <div class="bg-slate-900/80 border border-slate-800/50 rounded-2xl p-6 text-center max-w-3xl mx-auto">
                <div class="mb-4">
                    <svg class="w-16 h-16 mx-auto text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                    </svg>
                </div>
                <h2 class="text-2xl font-bold text-white mb-3">
                    Perplexica 서비스 준비 중
                </h2>
                <p class="text-slate-300 mb-4">
                    Perplexica 검색 서비스가 곧 제공될 예정입니다.
                </p>
                <div class="bg-slate-800/50 border border-slate-700/50 rounded-lg p-4 text-left max-w-2xl mx-auto">
                    <p class="text-sm text-slate-400 mb-2">활성화 방법:</p>
                    <code class="text-xs text-slate-300 block">
                        docker-compose.yml에서 perplexica 서비스의<br />
                        profiles: ["disabled"] 제거 후 재시작
                    </code>
                </div>
            </div>
        </div>

        <!-- Features Grid -->
        <div class="mb-6">
            <h2 class="text-2xl font-bold text-white mb-6 text-center">
                제공 예정 기능
            </h2>
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
                {#each features as feature (feature.id)}
                    {@const colorClasses = getColorClasses(feature.color)}
                    <div
                        class="group relative bg-slate-900/80 border border-slate-800/50 rounded-2xl p-6 text-left 
                            shadow-lg shadow-black/20 transition-all duration-300
                            opacity-50 cursor-not-allowed"
                    >
                        <!-- Gradient Background on hover -->
                        <div class="absolute inset-0 rounded-2xl bg-gradient-to-br {colorClasses.bg} opacity-0 
                            group-hover:opacity-100 transition-opacity duration-300"></div>
                        
                        <div class="relative">
                            <!-- Icon -->
                            <div class="w-14 h-14 rounded-xl bg-gradient-to-br {colorClasses.bg} border border-slate-700/50 flex items-center justify-center mb-4 group-hover:scale-110 transition-transform duration-300">
                                {#if feature.icon === 'search'}
                                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-7 h-7 {colorClasses.icon}">
                                        <path fill-rule="evenodd" d="M9 3.5a5.5 5.5 0 100 11 5.5 5.5 0 000-11zM2 9a7 7 0 1112.452 4.391l3.328 3.329a.75.75 0 11-1.06 1.06l-3.329-3.328A7 7 0 012 9z" clip-rule="evenodd" />
                                    </svg>
                                {:else if feature.icon === 'book'}
                                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-7 h-7 {colorClasses.icon}">
                                        <path d="M10.75 16.82A7.462 7.462 0 0115 15.5c.71 0 1.396.098 2.046.282A.75.75 0 0018 15.06v-11a.75.75 0 00-.546-.721A9.006 9.006 0 0015 3a8.963 8.963 0 00-4.25 1.065V16.82zM9.25 4.065A8.963 8.963 0 005 3c-.85 0-1.673.118-2.454.339A.75.75 0 002 4.06v11a.75.75 0 00.954.721A7.506 7.506 0 015 15.5c1.579 0 3.042.487 4.25 1.32V4.065z" />
                                    </svg>
                                {:else if feature.icon === 'video'}
                                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-7 h-7 {colorClasses.icon}">
                                        <path d="M2 6a2 2 0 012-2h6a2 2 0 012 2v8a2 2 0 01-2 2H4a2 2 0 01-2-2V6zM14.553 7.106A1 1 0 0014 8v4a1 1 0 00.553.894l2 1A1 1 0 0018 13V7a1 1 0 00-1.447-.894l-2 1z" />
                                    </svg>
                                {:else if feature.icon === 'image'}
                                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-7 h-7 {colorClasses.icon}">
                                        <path fill-rule="evenodd" d="M1 5.25A2.25 2.25 0 013.25 3h13.5A2.25 2.25 0 0119 5.25v9.5A2.25 2.25 0 0116.75 17H3.25A2.25 2.25 0 011 14.75v-9.5zm1.5 5.81v3.69c0 .414.336.75.75.75h13.5a.75.75 0 00.75-.75v-2.69l-2.22-2.22a.75.75 0 00-1.06 0l-1.91 1.91-2.78-2.78a.75.75 0 00-1.06 0l-3.5 3.5a.75.75 0 00-.22.53zm15 2.25a.75.75 0 01-.75.75H3.25a.75.75 0 01-.75-.75v-9.5a.75.75 0 01.75-.75h13.5a.75.75 0 01.75.75v9.5z" clip-rule="evenodd" />
                                    </svg>
                                {:else}
                                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-7 h-7 {colorClasses.icon}">
                                        <path d="M10.362 1.093a.75.75 0 00-.724 0L2.523 5.018 10 9.143l7.477-4.125-7.115-3.925zM18 6.443l-7.25 4v8.25l6.862-3.786A.75.75 0 0018 14.25V6.443zM9.25 18.693v-8.25l-7.25-4v7.807a.75.75 0 00.388.657l6.862 3.786z" />
                                    </svg>
                                {/if}
                            </div>

                            <!-- Content -->
                            <h3 class="text-lg font-semibold text-white mb-2">{feature.name}</h3>
                            <p class="text-sm text-slate-400 group-hover:text-slate-300 transition-colors duration-200">{feature.description}</p>

                            <!-- Status Badge -->
                            <span class="absolute top-4 right-4 text-xs px-2.5 py-1 rounded-full bg-slate-700 text-slate-400 border border-slate-600/50">
                                Coming Soon
                            </span>
                        </div>
                    </div>
                {/each}
            </div>
        </div>
    </div>
</div>
