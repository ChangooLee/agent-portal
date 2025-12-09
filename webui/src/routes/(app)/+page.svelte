<script lang="ts">
    import { onMount } from 'svelte';
    import { goto } from '$app/navigation';
    import { user, WEBUI_NAME } from '$lib/stores';
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
        id: number;
        title: string;
        highlight: string;
        link: string;
        pub_date: string;
        category: string;
        tags?: string[];
    }

    const agents: Agent[] = [
        {
            id: 'chat',
            name: 'AI Chat',
            description: '다양한 LLM과 대화하고 질문에 답변을 받으세요.',
            icon: '💬',
            href: '/c',
            color: 'blue',
            status: 'active'
        },
        {
            id: 'text2sql',
            name: 'Text-to-SQL',
            description: '자연어로 데이터베이스를 질의하고 SQL을 생성합니다.',
            icon: '🗃️',
            href: '/use/datacloud',
            color: 'emerald',
            status: 'active'
        },
        {
            id: 'dart',
            name: '기업공시분석',
            description: 'DART 전자공시 데이터를 분석하고 리포트를 생성합니다.',
            icon: '📊',
            href: '/dart',
            color: 'purple',
            status: 'active'
        },
        {
            id: 'report',
            name: '리포트 생성',
            description: '데이터 분석 결과를 시각화하고 보고서를 생성합니다.',
            icon: '📄',
            href: '/report',
            color: 'amber',
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

    function getAgentGradient(color: string) {
        const gradients: Record<string, string> = {
            blue: 'from-blue-500/20 to-blue-600/10',
            emerald: 'from-emerald-500/20 to-emerald-600/10',
            purple: 'from-purple-500/20 to-purple-600/10',
            amber: 'from-amber-500/20 to-amber-600/10'
        };
        return gradients[color] || gradients.blue;
    }

    function getAgentBorder(color: string) {
        const borders: Record<string, string> = {
            blue: 'hover:border-blue-500/50',
            emerald: 'hover:border-emerald-500/50',
            purple: 'hover:border-purple-500/50',
            amber: 'hover:border-amber-500/50'
        };
        return borders[color] || borders.blue;
    }
</script>

<svelte:head>
    <title>Home | {$WEBUI_NAME || 'SFN AI Portal'}</title>
</svelte:head>

<div class="min-h-full bg-gray-950 text-slate-50">
    <!-- Hero Section -->
    <div class="relative overflow-hidden border-b border-slate-800/50">
        <!-- Subtle gradient overlay -->
        <div class="absolute inset-0 bg-gradient-to-br from-blue-600/5 via-transparent to-purple-600/5"></div>
        <!-- Grid pattern -->
        <div class="absolute inset-0 bg-[linear-gradient(rgba(59,130,246,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(59,130,246,0.03)_1px,transparent_1px)] bg-[size:64px_64px]"></div>
        
		<div class="relative px-6 py-8 text-center">
			<h1 class="text-3xl md:text-4xl font-bold mb-3 text-white">
                안녕하세요, {$user?.name || '사용자'}님
            </h1>
            <p class="text-base text-blue-200/80">
                AI 에이전트를 활용하여 업무를 자동화하고 인사이트를 얻으세요.
            </p>
        </div>
    </div>

    <div class="px-6 py-12 space-y-16">
        <!-- Agents Section -->
        <section>
            <div class="flex items-center justify-between mb-8">
                <h2 class="text-2xl font-bold text-white flex items-center gap-3">
                    <span class="text-3xl">🤖</span>
                    AI 에이전트
                </h2>
                <a href="/use/agents" class="text-blue-400 hover:text-blue-300 text-sm font-medium transition-colors duration-200 flex items-center gap-1">
                    모두 보기 
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/>
                    </svg>
                </a>
            </div>
            <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
                {#each agents as agent}
                    <button
                        class="group relative p-6 rounded-2xl bg-slate-900/80 border border-slate-800/50 
                            shadow-lg shadow-black/20 transition-all duration-300 text-left
                            {agent.status === 'coming-soon' 
                                ? 'opacity-50 cursor-not-allowed' 
                                : `cursor-pointer hover:bg-slate-800/80 ${getAgentBorder(agent.color)} hover:shadow-xl hover:shadow-black/30 hover:-translate-y-1`}"
                        on:click={() => handleAgentClick(agent)}
                        disabled={agent.status === 'coming-soon'}
                    >
                        <!-- Gradient Background on hover -->
                        <div class="absolute inset-0 rounded-2xl bg-gradient-to-br {getAgentGradient(agent.color)} opacity-0 
                            group-hover:opacity-100 transition-opacity duration-300"></div>
                        
                        <div class="relative">
                            <div class="text-4xl mb-4 transform group-hover:scale-110 transition-transform duration-300">{agent.icon}</div>
                            <h3 class="text-lg font-semibold text-white mb-2 flex items-center gap-2">
                                {agent.name}
                                {#if agent.status === 'coming-soon'}
                                    <span class="text-xs bg-slate-700 px-2 py-0.5 rounded-full text-slate-400 font-normal">Soon</span>
                                {/if}
                            </h3>
                            <p class="text-sm text-slate-400 line-clamp-2 group-hover:text-slate-300 transition-colors duration-200">{agent.description}</p>
                        </div>
                    </button>
                {/each}
            </div>
        </section>

        <!-- News Section -->
        <section>
            <div class="flex items-center justify-between mb-8">
                <h2 class="text-2xl font-bold text-white flex items-center gap-3">
                    <span class="text-3xl">📰</span>
                    최신 뉴스
                </h2>
                <a href="/today" class="text-blue-400 hover:text-blue-300 text-sm font-medium transition-colors duration-200 flex items-center gap-1">
                    모두 보기
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/>
                    </svg>
                </a>
            </div>
            
            {#if loadingNews}
                <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
                    {#each Array(6) as _}
                        <div class="p-5 rounded-xl bg-slate-900/80 border border-slate-800/50 animate-pulse">
                            <div class="h-4 bg-slate-800 rounded w-3/4 mb-3"></div>
                            <div class="h-3 bg-slate-800 rounded w-full mb-2"></div>
                            <div class="h-3 bg-slate-800 rounded w-2/3"></div>
                        </div>
                    {/each}
                </div>
            {:else if news.length === 0}
                <div class="text-center py-16 bg-slate-900/50 rounded-2xl border border-slate-800/50">
                    <div class="text-4xl mb-4">📭</div>
                    <p class="text-slate-500">뉴스를 불러올 수 없습니다.</p>
                </div>
            {:else}
                <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
                    {#each news as item}
                        <a 
                            href="/today"
                            class="block p-5 rounded-xl bg-slate-900/80 border border-slate-800/50 
                                shadow-lg shadow-black/20 hover:shadow-xl hover:shadow-black/30
                                hover:bg-slate-800/80 hover:border-slate-700/50 
                                transition-all duration-300 hover:-translate-y-1"
                        >
                            <div class="flex items-center gap-2 mb-3">
                                <span class="text-xs px-2.5 py-1 rounded-full bg-blue-500/20 text-blue-400 font-medium border border-blue-500/30">
                                    {item.category || '뉴스'}
                                </span>
                            </div>
                            <h3 class="text-sm font-medium text-white mb-2 line-clamp-2 leading-relaxed">{item.title}</h3>
                            <p class="text-xs text-slate-400 line-clamp-2 leading-relaxed">{item.highlight}</p>
                        </a>
                    {/each}
                </div>
            {/if}
        </section>

        <!-- Quick Links -->
        <section>
            <h2 class="text-2xl font-bold text-white mb-8 flex items-center gap-3">
                <span class="text-3xl">⚡</span>
                빠른 접근
            </h2>
            <div class="grid grid-cols-2 md:grid-cols-4 gap-5">
                <a href="/build/mcp" class="group p-5 rounded-xl bg-slate-900/80 border border-slate-800/50 
                    shadow-lg shadow-black/20 hover:shadow-xl hover:shadow-black/30
                    hover:bg-slate-800/80 hover:border-slate-700/50 
                    transition-all duration-300 text-center hover:-translate-y-1">
                    <div class="text-3xl mb-3 transform group-hover:scale-110 transition-transform duration-300">🔌</div>
                    <span class="text-sm text-slate-300 font-medium group-hover:text-white transition-colors">MCP 서버</span>
                </a>
                <a href="/operate/monitoring" class="group p-5 rounded-xl bg-slate-900/80 border border-slate-800/50 
                    shadow-lg shadow-black/20 hover:shadow-xl hover:shadow-black/30
                    hover:bg-slate-800/80 hover:border-slate-700/50 
                    transition-all duration-300 text-center hover:-translate-y-1">
                    <div class="text-3xl mb-3 transform group-hover:scale-110 transition-transform duration-300">📈</div>
                    <span class="text-sm text-slate-300 font-medium group-hover:text-white transition-colors">Monitoring</span>
                </a>
                <a href="/operate/llm" class="group p-5 rounded-xl bg-slate-900/80 border border-slate-800/50 
                    shadow-lg shadow-black/20 hover:shadow-xl hover:shadow-black/30
                    hover:bg-slate-800/80 hover:border-slate-700/50 
                    transition-all duration-300 text-center hover:-translate-y-1">
                    <div class="text-3xl mb-3 transform group-hover:scale-110 transition-transform duration-300">🧠</div>
                    <span class="text-sm text-slate-300 font-medium group-hover:text-white transition-colors">LLM 관리</span>
                </a>
                <a href="/operate/settings" class="group p-5 rounded-xl bg-slate-900/80 border border-slate-800/50 
                    shadow-lg shadow-black/20 hover:shadow-xl hover:shadow-black/30
                    hover:bg-slate-800/80 hover:border-slate-700/50 
                    transition-all duration-300 text-center hover:-translate-y-1">
                    <div class="text-3xl mb-3 transform group-hover:scale-110 transition-transform duration-300">⚙️</div>
                    <span class="text-sm text-slate-300 font-medium group-hover:text-white transition-colors">설정</span>
                </a>
            </div>
        </section>
    </div>
</div>
