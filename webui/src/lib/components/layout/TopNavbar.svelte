<script lang="ts">
    import { page } from '$app/stores';
    import { goto } from '$app/navigation';
    import { selectedRole, roleMenus, getRoleFromPath, type UserRole, type MenuItem } from '$lib/stores/role';
    import { user } from '$lib/stores';
    import { WEBUI_BASE_URL } from '$lib/constants';

    const tabs: { id: UserRole; name: string; defaultPath: string }[] = [
        { id: 'use', name: 'Use', defaultPath: '/' },
        { id: 'build', name: 'Build', defaultPath: '/build/agents' },
        { id: 'operate', name: 'Operate', defaultPath: '/operate/monitoring' }
    ];

    $: menuItems = roleMenus[$selectedRole];
    $: currentPath = $page?.url?.pathname || '/';

    // Update selected role based on current path
    $: if (currentPath) {
        const roleFromPath = getRoleFromPath(currentPath);
        if (roleFromPath !== $selectedRole) {
            selectedRole.set(roleFromPath);
        }
    }

    function handleTabClick(tab: typeof tabs[0]) {
        selectedRole.set(tab.id);
        goto(tab.defaultPath);
    }

    function handleMenuClick(item: MenuItem) {
        if (item.status === 'coming-soon') return;
        goto(item.href);
    }

    function isMenuActive(href: string): boolean {
        if (href === '/') {
            return currentPath === '/' || currentPath === '/today';
        }
        if (href === '/c') {
            return currentPath.startsWith('/c/') || currentPath === '/c';
        }
        return currentPath.startsWith(href);
    }

    // Check if we're on home page (show different layout)
    $: isHomePage = currentPath === '/' || currentPath === '/today';
</script>

<!-- Top Navigation Bar -->
<header class="sticky top-0 z-50 w-full bg-gradient-to-b from-slate-900 to-gray-950 border-b border-slate-800/50 shadow-lg shadow-black/20">
    <!-- Main Nav Row: Logo + Role Tabs + User -->
    <div class="flex items-center justify-between h-14 px-6">
        <!-- Logo -->
        <a href="/" class="flex items-center gap-3 group">
            <div class="relative">
                <img src="{WEBUI_BASE_URL}/static/splash.png" alt="logo" class="w-9 h-9 rounded-xl shadow-lg shadow-blue-500/10 transition-transform duration-300 group-hover:scale-105" />
                <div class="absolute inset-0 rounded-xl bg-blue-500/20 opacity-0 group-hover:opacity-100 transition-opacity duration-300"></div>
            </div>
            <span class="hidden sm:inline text-lg font-semibold bg-gradient-to-r from-white to-slate-300 bg-clip-text text-transparent">SFN AI Portal</span>
        </a>

        <!-- Role Tabs (Center) -->
        <nav class="flex items-center gap-1 bg-slate-900/80 rounded-xl p-1 border border-slate-800/50">
            {#each tabs as tab}
                <button
                    class="px-5 py-2 rounded-lg text-sm font-medium transition-all duration-300 ease-out
                        {$selectedRole === tab.id 
                            ? 'bg-blue-600 text-white shadow-lg shadow-blue-500/25' 
                            : 'text-slate-400 hover:text-white hover:bg-slate-800/80'}"
                    on:click={() => handleTabClick(tab)}
                >
                    {tab.name}
                </button>
            {/each}
        </nav>

        <!-- User Menu -->
        <div class="flex items-center gap-3">
            {#if $user}
                <button class="flex items-center gap-3 px-3 py-1.5 rounded-xl hover:bg-slate-800/80 border border-transparent hover:border-slate-700/50 transition-all duration-300">
                    <img 
                        src={$user.profile_image_url ?? `${WEBUI_BASE_URL}/static/favicon.png`}
                        alt="User"
                        class="w-8 h-8 rounded-full object-cover ring-2 ring-slate-700/50"
                    />
                    <span class="hidden sm:inline text-sm text-slate-300">{$user.name}</span>
                </button>
            {/if}
        </div>
    </div>

    <!-- Sub Menu Row (only show when not on home page) -->
    {#if !isHomePage}
        <div class="flex items-center justify-center gap-2 py-2 bg-slate-900/50 border-t border-slate-800/50 overflow-x-auto">
            {#each menuItems as item}
                <button
                    class="flex items-center gap-2 px-4 py-1.5 rounded-lg text-sm whitespace-nowrap transition-all duration-300 ease-out
                        {isMenuActive(item.href)
                            ? 'bg-blue-600 text-white shadow-lg shadow-blue-500/20'
                            : item.status === 'coming-soon'
                                ? 'text-slate-600 cursor-not-allowed'
                                : 'text-slate-400 hover:text-white hover:bg-slate-800'}"
                    on:click={() => handleMenuClick(item)}
                    disabled={item.status === 'coming-soon'}
                >
                    <span>{item.name}</span>
                    {#if item.status === 'coming-soon'}
                        <span class="text-xs bg-slate-700 px-1.5 py-0.5 rounded text-slate-500">Soon</span>
                    {/if}
                </button>
            {/each}
        </div>
    {/if}
</header>
