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
<header class="sticky top-0 z-50 w-full bg-gray-950 border-b border-gray-800">
    <!-- Main Nav Row: Logo + Role Tabs + User -->
    <div class="flex items-center justify-between h-14 px-4">
        <!-- Logo -->
        <a href="/" class="flex items-center gap-2 text-white font-semibold text-lg">
            <img src="{WEBUI_BASE_URL}/static/splash.png" alt="logo" class="w-8 h-8 rounded-lg" />
            <span class="hidden sm:inline">SFN AI Portal</span>
        </a>

        <!-- Role Tabs (Center) -->
        <nav class="flex items-center gap-1 bg-gray-900/50 rounded-lg p-1">
            {#each tabs as tab}
                <button
                    class="px-4 py-1.5 rounded-md text-sm font-medium transition-all duration-200
                        {$selectedRole === tab.id 
                            ? 'bg-blue-600 text-white shadow-sm' 
                            : 'text-gray-400 hover:text-white hover:bg-gray-800'}"
                    on:click={() => handleTabClick(tab)}
                >
                    {tab.name}
                </button>
            {/each}
        </nav>

        <!-- User Menu -->
        <div class="flex items-center gap-3">
            {#if $user}
                <button class="flex items-center gap-2 px-2 py-1 rounded-lg hover:bg-gray-800 transition-colors">
                    <img 
                        src={$user.profile_image_url ?? `${WEBUI_BASE_URL}/static/favicon.png`}
                        alt="User"
                        class="w-8 h-8 rounded-full object-cover"
                    />
                    <span class="hidden sm:inline text-sm text-gray-300">{$user.name}</span>
                </button>
            {/if}
        </div>
    </div>

    <!-- Sub Menu Row (only show when not on home page) -->
    {#if !isHomePage}
        <div class="flex items-center gap-1 px-4 py-2 bg-gray-900/30 border-t border-gray-800/50 overflow-x-auto">
            {#each menuItems as item}
                <button
                    class="flex items-center gap-2 px-3 py-1.5 rounded-md text-sm whitespace-nowrap transition-all duration-200
                        {isMenuActive(item.href)
                            ? 'bg-blue-600/20 text-blue-400 border border-blue-500/30'
                            : item.status === 'coming-soon'
                                ? 'text-gray-500 cursor-not-allowed'
                                : 'text-gray-400 hover:text-white hover:bg-gray-800'}"
                    on:click={() => handleMenuClick(item)}
                    disabled={item.status === 'coming-soon'}
                >
                    <span>{item.name}</span>
                    {#if item.status === 'coming-soon'}
                        <span class="text-xs bg-gray-700 px-1.5 py-0.5 rounded text-gray-400">Soon</span>
                    {/if}
                </button>
            {/each}
        </div>
    {/if}
</header>
