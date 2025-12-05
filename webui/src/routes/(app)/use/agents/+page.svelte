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
        status: 'active' | 'coming-soon';
    }

    const agents: Agent[] = [
        {
            id: 'text2sql',
            name: 'Text-to-SQL',
            description: '자연어로 데이터베이스를 질의하고 SQL을 생성합니다.',
            icon: 'database',
            href: '/use/datacloud',
            status: 'active'
        },
        {
            id: 'dart',
            name: '기업공시분석',
            description: 'DART 전자공시 데이터를 분석하고 리포트를 생성합니다.',
            icon: 'document',
            href: '/dart',
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
</script>

<svelte:head>
    <title>에이전트 | SFN AI Portal</title>
</svelte:head>

<div class="h-full bg-gray-950 text-white p-6 overflow-auto">
    <div class="max-w-6xl mx-auto">
        <!-- Header -->
        <div class="mb-8">
            <h1 class="text-3xl font-bold text-white mb-2">에이전트</h1>
            <p class="text-gray-400">AI 에이전트를 선택하여 실행하세요.</p>
        </div>

        <!-- Agent Grid -->
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {#each agents as agent (agent.id)}
                <button
                    class="group relative bg-gray-900 border border-gray-800 rounded-xl p-6 text-left transition-all duration-200
                        {agent.status === 'coming-soon' 
                            ? 'opacity-50 cursor-not-allowed' 
                            : 'hover:border-blue-500/50 hover:bg-gray-800/50 cursor-pointer'}"
                    on:click={() => handleAgentClick(agent)}
                    disabled={agent.status === 'coming-soon'}
                >
                    <!-- Icon -->
                    <div class="w-12 h-12 rounded-xl bg-blue-600/20 flex items-center justify-center mb-4">
                        {#if agent.icon === 'database'}
                            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-6 h-6 text-blue-400">
                                <path fill-rule="evenodd" d="M10 1c3.866 0 7 1.79 7 4s-3.134 4-7 4-7-1.79-7-4 3.134-4 7-4zm5.694 8.13c.464-.264.91-.583 1.306-.952V10c0 2.21-3.134 4-7 4s-7-1.79-7-4V8.178c.396.37.842.688 1.306.953C5.838 10.006 7.854 10.5 10 10.5s4.162-.494 5.694-1.37zM3 13.179V15c0 2.21 3.134 4 7 4s7-1.79 7-4v-1.822c-.396.37-.842.688-1.306.953-1.532.875-3.548 1.369-5.694 1.369s-4.162-.494-5.694-1.37A7.009 7.009 0 013 13.179z" clip-rule="evenodd" />
                            </svg>
                        {:else if agent.icon === 'document'}
                            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-6 h-6 text-emerald-400">
                                <path fill-rule="evenodd" d="M4.5 2A1.5 1.5 0 003 3.5v13A1.5 1.5 0 004.5 18h11a1.5 1.5 0 001.5-1.5V7.621a1.5 1.5 0 00-.44-1.06l-4.12-4.122A1.5 1.5 0 0011.378 2H4.5zm2.25 8.5a.75.75 0 000 1.5h6.5a.75.75 0 000-1.5h-6.5zm0 3a.75.75 0 000 1.5h6.5a.75.75 0 000-1.5h-6.5z" clip-rule="evenodd" />
                            </svg>
                        {:else}
                            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-6 h-6 text-blue-400">
                                <path d="M10.362 1.093a.75.75 0 00-.724 0L2.523 5.018 10 9.143l7.477-4.125-7.115-3.925zM18 6.443l-7.25 4v8.25l6.862-3.786A.75.75 0 0018 14.25V6.443zM9.25 18.693v-8.25l-7.25-4v7.807a.75.75 0 00.388.657l6.862 3.786z" />
                            </svg>
                        {/if}
                    </div>

                    <!-- Content -->
                    <h3 class="text-lg font-semibold text-white mb-2">{agent.name}</h3>
                    <p class="text-sm text-gray-400">{agent.description}</p>

                    <!-- Status Badge -->
                    {#if agent.status === 'coming-soon'}
                        <span class="absolute top-4 right-4 text-xs px-2 py-1 rounded-full bg-gray-700 text-gray-400">
                            Coming Soon
                        </span>
                    {:else}
                        <div class="absolute top-4 right-4 w-2 h-2 rounded-full bg-green-500"></div>
                    {/if}

                    <!-- Arrow -->
                    {#if agent.status !== 'coming-soon'}
                        <div class="absolute bottom-4 right-4 opacity-0 group-hover:opacity-100 transition-opacity">
                            <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-5 h-5 text-blue-400">
                                <path fill-rule="evenodd" d="M3 10a.75.75 0 01.75-.75h10.638L10.23 5.29a.75.75 0 111.04-1.08l5.5 5.25a.75.75 0 010 1.08l-5.5 5.25a.75.75 0 11-1.04-1.08l4.158-3.96H3.75A.75.75 0 013 10z" clip-rule="evenodd" />
                            </svg>
                        </div>
                    {/if}
                </button>
            {/each}
        </div>
    </div>
</div>

