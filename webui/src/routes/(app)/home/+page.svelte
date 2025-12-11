<script lang="ts">
    import { onMount } from 'svelte';
    import { goto } from '$app/navigation';
    import { user } from '$lib/stores';
    import { WEBUI_BASE_URL } from '$lib/constants';

    interface Agent {
        id: string;
        name: string;
        description: string;
        icon: string;
        href: string;
        color: string;
        status: 'active' | 'coming-soon';
    }

    interface NewsItem {
        id: string;
        title: string;
        summary: string;
        source: string;
        date: string;
        category: string;
    }

    const agents: Agent[] = [
        {
            id: 'chat',
            name: 'AI Chat',
            description: '다양한 LLM과 대화하고 질문에 답변을 받으세요.',
            icon: '💬',
            href: '/c',
            color: 'from-blue-500 to-blue-600',
            status: 'active'
        },
        {
            id: 'text2sql',
            name: 'Text-to-SQL',
            description: '자연어로 데이터베이스를 질의하고 SQL을 생성합니다.',
            icon: '🗃️',
            href: '/use/datacloud',
            color: 'from-emerald-500 to-emerald-600',
            status: 'active'
        },
        {
            id: 'dart',
            name: '기업공시분석',
            description: 'DART 전자공시 데이터를 분석하고 리포트를 생성합니다.',
            icon: '📊',
            href: '/dart',
            color: 'from-purple-500 to-purple-600',
            status: 'active'
        },
        {
            id: 'report',
            name: '리포트 생성',
            description: '데이터 분석 결과를 시각화하고 보고서를 생성합니다.',
            icon: '📄',
            href: '/report',
            color: 'from-amber-500 to-amber-600',
            status: 'coming-soon'
        }
    ];

    let news: NewsItem[] = [];
    let loadingNews = true;

    onMount(async () => {
        try {
            const response = await fetch('/api/news/articles?limit=6');
            if (response.ok) {
                const data = await response.json();
                news = data.articles || [];
            }
        } catch (e) {
            console.error('Failed to load news:', e);
        } finally {
            loadingNews = false;
        }
    });

    function handleAgentClick(agent: Agent) {
        if (agent.status === 'coming-soon') return;
        goto(agent.href);
    }
</script>

<svelte:head>
    <title>Home | SFN AI Portal</title>
</svelte:head>

<div class="min-h-screen bg-gray-950 text-white">
    <!-- Hero Section -->
    <div class="relative overflow-hidden">
        <div class="absolute inset-0 bg-gradient-to-br from-blue-600/20 via-purple-600/10 to-transparent"></div>
        <div class="relative px-6 py-16 text-center">
            <h1 class="text-4xl md:text-5xl font-bold mb-4">
                안녕하세요, <span class="text-blue-400">{$user?.name || '사용자'}</span>님
            </h1>
            <p class="text-xl text-gray-400 max-w-2xl mx-auto">
                AI 에이전트를 활용하여 업무를 자동화하고 인사이트를 얻으세요.
            </p>
        </div>
    </div>

    <div class="px-6 pb-16 space-y-12">
        <!-- Agents Section -->
        <section>
            <div class="flex items-center justify-between mb-6">
                <h2 class="text-2xl font-bold text-white">🤖 AI 에이전트</h2>
                <a href="/use/agents" class="text-blue-400 hover:text-blue-300 text-sm">
                    모두 보기 →
                </a>
            </div>
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                {#each agents as agent}
                    <button
                        class="group relative p-6 rounded-2xl bg-gray-900 border border-gray-800 
                            hover:border-gray-700 transition-all duration-300 text-left
                            {agent.status === 'coming-soon' ? 'opacity-60 cursor-not-allowed' : 'hover:scale-[1.02] cursor-pointer'}"
                        on:click={() => handleAgentClick(agent)}
                        disabled={agent.status === 'coming-soon'}
                    >
                        <!-- Gradient Background -->
                        <div class="absolute inset-0 rounded-2xl bg-gradient-to-br {agent.color} opacity-0 
                            group-hover:opacity-10 transition-opacity duration-300"></div>
                        
                        <div class="relative">
                            <div class="text-4xl mb-4">{agent.icon}</div>
                            <h3 class="text-lg font-semibold text-white mb-2 flex items-center gap-2">
                                {agent.name}
                                {#if agent.status === 'coming-soon'}
                                    <span class="text-xs bg-gray-700 px-2 py-0.5 rounded text-gray-400">Soon</span>
                                {/if}
                            </h3>
                            <p class="text-sm text-gray-400 line-clamp-2">{agent.description}</p>
                        </div>
                    </button>
                {/each}
            </div>
        </section>

        <!-- News Section -->
        <section>
            <div class="flex items-center justify-between mb-6">
                <h2 class="text-2xl font-bold text-white">📰 최신 뉴스</h2>
                <a href="/today" class="text-blue-400 hover:text-blue-300 text-sm">
                    모두 보기 →
                </a>
            </div>
            
            {#if loadingNews}
                <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {#each Array(6) as _}
                        <div class="p-5 rounded-xl bg-gray-900 border border-gray-800 animate-pulse">
                            <div class="h-4 bg-gray-800 rounded w-3/4 mb-3"></div>
                            <div class="h-3 bg-gray-800 rounded w-full mb-2"></div>
                            <div class="h-3 bg-gray-800 rounded w-2/3"></div>
                        </div>
                    {/each}
                </div>
            {:else if news.length === 0}
                <div class="text-center py-12 text-gray-500">
                    <p>뉴스를 불러올 수 없습니다.</p>
                </div>
            {:else}
                <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                    {#each news as item}
                        <a 
                            href="/today"
                            class="block p-5 rounded-xl bg-gray-900 border border-gray-800 
                                hover:border-gray-700 hover:bg-gray-900/80 transition-all duration-200"
                        >
                            <div class="flex items-center gap-2 mb-2">
                                <span class="text-xs px-2 py-0.5 rounded bg-blue-600/20 text-blue-400">
                                    {item.category || '뉴스'}
                                </span>
                                <span class="text-xs text-gray-500">{item.source}</span>
                            </div>
                            <h3 class="text-sm font-medium text-white mb-2 line-clamp-2">{item.title}</h3>
                            <p class="text-xs text-gray-500 line-clamp-2">{item.summary}</p>
                        </a>
                    {/each}
                </div>
            {/if}
        </section>

        <!-- Quick Links -->
        <section>
            <h2 class="text-2xl font-bold text-white mb-6">⚡ 빠른 접근</h2>
            <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
                <a href="/build/mcp" class="p-4 rounded-xl bg-gray-900 border border-gray-800 hover:border-gray-700 transition-all text-center">
                    <div class="text-2xl mb-2">🔌</div>
                    <span class="text-sm text-gray-300">MCP 서버</span>
                </a>
                <a href="/operate/monitoring" class="p-4 rounded-xl bg-gray-900 border border-gray-800 hover:border-gray-700 transition-all text-center">
                    <div class="text-2xl mb-2">📈</div>
                    <span class="text-sm text-gray-300">Monitoring</span>
                </a>
                <a href="/build/llm" class="p-4 rounded-xl bg-gray-900 border border-gray-800 hover:border-gray-700 transition-all text-center">
                    <div class="text-2xl mb-2">🧠</div>
                    <span class="text-sm text-gray-300">LLM 관리</span>
                </a>
                <a href="/operate/settings" class="p-4 rounded-xl bg-gray-900 border border-gray-800 hover:border-gray-700 transition-all text-center">
                    <div class="text-2xl mb-2">⚙️</div>
                    <span class="text-sm text-gray-300">설정</span>
                </a>
            </div>
        </section>
    </div>
</div>

