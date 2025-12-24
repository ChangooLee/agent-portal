<script lang="ts">
    import { onMount } from 'svelte';
    import { goto } from '$app/navigation';
    import { user, mobile, showSidebar } from '$lib/stores';

    interface Agent {
        id: string;
        name: string;
        description: string;
        icon: string;
        href: string;
        color: string;
        status: 'active' | 'coming-soon';
    }

    const agents: Agent[] = [
        {
            id: 'dart',
            name: '기업공시분석',
            description: 'DART 전자공시 데이터를 분석하고 리포트를 생성합니다.',
            icon: 'document',
            href: '/dart',
            color: 'emerald',
            status: 'active'
        },
        {
            id: 'text2sql',
            name: 'Text-to-SQL',
            description: '자연어로 데이터베이스를 질의하고 SQL을 생성합니다.',
            icon: 'database',
            href: '/use/datacloud',
            color: 'blue',
            status: 'active'
        }
    ];

    function handleAgentClick(agent: Agent) {
        if (agent.status !== 'coming-soon') {
            goto(agent.href);
            if ($mobile) {
                showSidebar.set(false);
            }
        }
    }

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
            }
        };
        return colors[color] || colors.blue;
    }
</script>

<svelte:head>
    <title>에이전트 | AI Agent Portal</title>
</svelte:head>

<div class="min-h-full bg-gray-950 text-slate-50">
    <!-- Hero Section -->
    <div class="relative overflow-hidden border-b border-slate-800/50">
        <div class="absolute inset-0 bg-gradient-to-br from-blue-600/5 via-transparent to-purple-600/5"></div>
        <div class="absolute inset-0 bg-[linear-gradient(rgba(59,130,246,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(59,130,246,0.03)_1px,transparent_1px)] bg-[size:64px_64px]"></div>
        
		<div class="relative px-6 py-8 text-center">
			<h1 class="text-3xl md:text-4xl font-medium mb-3 text-white">
                🤖 AI 에이전트
            </h1>
            <p class="text-base text-blue-200/80">
                AI 에이전트를 선택하여 업무를 자동화하고 인사이트를 얻으세요.
            </p>
        </div>
    </div>

    <div class="px-6 py-12">
        <!-- Agent Grid -->
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5">
            {#each agents as agent (agent.id)}
                {@const colorClasses = getColorClasses(agent.color)}
                <button
                    class="group relative bg-slate-900/80 border border-slate-800/50 rounded-2xl p-6 text-left 
                        shadow-lg shadow-black/20 transition-all duration-300
                        {agent.status === 'coming-soon' 
                            ? 'opacity-50 cursor-not-allowed' 
                            : `cursor-pointer hover:bg-slate-800/80 ${colorClasses.border} hover:shadow-xl hover:shadow-black/30 hover:-translate-y-1`}"
                    on:click={() => handleAgentClick(agent)}
                    disabled={agent.status === 'coming-soon'}
                >
                    <!-- Gradient Background on hover -->
                    <div class="absolute inset-0 rounded-2xl bg-gradient-to-br {colorClasses.bg} opacity-0 
                        group-hover:opacity-100 transition-opacity duration-300"></div>
                    
                    <div class="relative">
                        <!-- Icon -->
                        <div class="w-14 h-14 rounded-xl bg-gradient-to-br {colorClasses.bg} border border-slate-700/50 flex items-center justify-center mb-4 group-hover:scale-110 transition-transform duration-300">
                            {#if agent.icon === 'database'}
                                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-7 h-7 {colorClasses.icon}">
                                    <path fill-rule="evenodd" d="M10 1c3.866 0 7 1.79 7 4s-3.134 4-7 4-7-1.79-7-4 3.134-4 7-4zm5.694 8.13c.464-.264.91-.583 1.306-.952V10c0 2.21-3.134 4-7 4s-7-1.79-7-4V8.178c.396.37.842.688 1.306.953C5.838 10.006 7.854 10.5 10 10.5s4.162-.494 5.694-1.37zM3 13.179V15c0 2.21 3.134 4 7 4s7-1.79 7-4v-1.822c-.396.37-.842.688-1.306.953-1.532.875-3.548 1.369-5.694 1.369s-4.162-.494-5.694-1.37A7.009 7.009 0 013 13.179z" clip-rule="evenodd" />
                                </svg>
                            {:else if agent.icon === 'document'}
                                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-7 h-7 {colorClasses.icon}">
                                    <path fill-rule="evenodd" d="M4.5 2A1.5 1.5 0 003 3.5v13A1.5 1.5 0 004.5 18h11a1.5 1.5 0 001.5-1.5V7.621a1.5 1.5 0 00-.44-1.06l-4.12-4.122A1.5 1.5 0 0011.378 2H4.5zm2.25 8.5a.75.75 0 000 1.5h6.5a.75.75 0 000-1.5h-6.5zm0 3a.75.75 0 000 1.5h6.5a.75.75 0 000-1.5h-6.5z" clip-rule="evenodd" />
                                </svg>
                            {:else}
                                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-7 h-7 {colorClasses.icon}">
                                    <path d="M10.362 1.093a.75.75 0 00-.724 0L2.523 5.018 10 9.143l7.477-4.125-7.115-3.925zM18 6.443l-7.25 4v8.25l6.862-3.786A.75.75 0 0018 14.25V6.443zM9.25 18.693v-8.25l-7.25-4v7.807a.75.75 0 00.388.657l6.862 3.786z" />
                                </svg>
                            {/if}
                        </div>

                        <!-- Content -->
                        <h3 class="text-lg font-semibold text-white mb-2">{agent.name}</h3>
                        <p class="text-sm text-slate-400 group-hover:text-slate-300 transition-colors duration-200">{agent.description}</p>

                        <!-- Status Badge -->
                        {#if agent.status === 'coming-soon'}
                            <span class="absolute top-4 right-4 text-xs px-2.5 py-1 rounded-full bg-slate-700 text-slate-400 border border-slate-600/50">
                                Coming Soon
                            </span>
                        {:else}
                            <div class="absolute top-4 right-4 w-2.5 h-2.5 rounded-full bg-emerald-500 shadow-lg shadow-emerald-500/50"></div>
                        {/if}

                        <!-- Arrow -->
                        {#if agent.status !== 'coming-soon'}
                            <div class="absolute bottom-4 right-4 opacity-0 group-hover:opacity-100 transition-all duration-300 transform translate-x-2 group-hover:translate-x-0">
                                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-5 h-5 text-blue-400">
                                    <path fill-rule="evenodd" d="M3 10a.75.75 0 01.75-.75h10.638L10.23 5.29a.75.75 0 111.04-1.08l5.5 5.25a.75.75 0 010 1.08l-5.5 5.25a.75.75 0 11-1.04-1.08l4.158-3.96H3.75A.75.75 0 013 10z" clip-rule="evenodd" />
                                </svg>
                            </div>
                        {/if}
                    </div>
                </button>
            {/each}
        </div>
    </div>
</div>
