<script lang="ts">
    import { page } from '$app/stores';
    import { goto } from '$app/navigation';
    import { selectedRole, roleMenus, type MenuItem } from '$lib/stores/role';
    import { user, showSidebar, mobile } from '$lib/stores';
    import { WEBUI_BASE_URL } from '$lib/constants';
    import UserMenu from './Sidebar/UserMenu.svelte';
    import RoleTabs from './RoleTabs.svelte';

    export let className = '';

    $: menuItems = roleMenus[$selectedRole];

    function isActive(href: string): boolean {
        const path = $page?.url?.pathname || '';
        if (href === '/') {
            return path === '/' || path === '/today';
        }
        if (href === '/c') {
            return path.startsWith('/c/') || path === '/c';
        }
        return path.startsWith(href);
    }

    function handleMenuClick(item: MenuItem) {
        if (item.status === 'coming-soon') {
            // Don't navigate, show coming soon
            return;
        }
        goto(item.href);
        if ($mobile) {
            showSidebar.set(false);
        }
    }

    function getIcon(iconName: string): string {
        return iconName;
    }
</script>

{#if $showSidebar}
    <div
        class="fixed md:hidden z-40 top-0 right-0 left-0 bottom-0 bg-black/60 w-full min-h-screen h-screen"
        on:mousedown={() => showSidebar.set(false)}
        on:keydown={(e) => e.key === 'Escape' && showSidebar.set(false)}
        role="button"
        tabindex="0"
    />
{/if}

<nav
    class="h-screen max-h-[100dvh] min-h-screen select-none 
        {$showSidebar ? 'md:relative w-[260px] max-w-[260px]' : '-translate-x-[260px] w-[0px]'}
        transition-all duration-200 ease-in-out shrink-0
        bg-gray-950 text-gray-100 text-sm
        fixed z-50 top-0 left-0 overflow-hidden
        border-r border-gray-800/50
        {className}"
    data-state={$showSidebar}
>
    <div class="flex flex-col h-full w-[260px] {$showSidebar ? '' : 'invisible'}">
        <!-- Header: Logo + Toggle -->
        <div class="flex items-center gap-2 px-3 py-4 border-b border-gray-800/50">
            <button
                class="p-2 rounded-lg hover:bg-gray-800 transition-colors"
                on:click={() => showSidebar.set(!$showSidebar)}
            >
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" class="w-5 h-5">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25H12" />
                </svg>
            </button>
            <a href="/" class="flex items-center gap-2 flex-1">
                <img
                    crossorigin="anonymous"
                    src="{WEBUI_BASE_URL}/static/favicon.png"
                    class="size-7 rounded-lg"
                    alt="logo"
                />
                <span class="text-base font-bold text-white">AI Agent Portal</span>
            </a>
        </div>

        <!-- Role Tabs -->
        <div class="px-3 py-3 border-b border-gray-800/50">
            <RoleTabs />
        </div>

        <!-- Menu Items -->
        <div class="flex-1 overflow-y-auto px-3 py-4">
            <div class="space-y-1">
                {#each menuItems as item (item.id)}
                    <button
                        class="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-left transition-all duration-150
                            {isActive(item.href) 
                                ? 'bg-blue-600/20 text-blue-400 border border-blue-500/30' 
                                : item.status === 'coming-soon'
                                    ? 'text-gray-500 cursor-not-allowed'
                                    : 'text-gray-300 hover:bg-gray-800/50 hover:text-white'}"
                        on:click={() => handleMenuClick(item)}
                        disabled={item.status === 'coming-soon'}
                    >
                        <!-- Icon -->
                        <div class="w-5 h-5 flex items-center justify-center">
                            {#if item.icon === 'home'}
                                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-5 h-5">
                                    <path fill-rule="evenodd" d="M9.293 2.293a1 1 0 011.414 0l7 7A1 1 0 0117 11h-1v6a1 1 0 01-1 1h-2a1 1 0 01-1-1v-3a1 1 0 00-1-1H9a1 1 0 00-1 1v3a1 1 0 01-1 1H5a1 1 0 01-1-1v-6H3a1 1 0 01-.707-1.707l7-7z" clip-rule="evenodd" />
                                </svg>
                            {:else if item.icon === 'chat'}
                                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-5 h-5">
                                    <path fill-rule="evenodd" d="M3.43 2.524A41.29 41.29 0 0110 2c2.236 0 4.43.18 6.57.524 1.437.231 2.43 1.49 2.43 2.902v5.148c0 1.413-.993 2.67-2.43 2.902a41.202 41.202 0 01-5.183.501.78.78 0 00-.528.224l-3.579 3.58A.75.75 0 016 17.25v-3.443a41.033 41.033 0 01-2.57-.33C1.993 13.244 1 11.986 1 10.574V5.426c0-1.413.993-2.67 2.43-2.902z" clip-rule="evenodd" />
                                </svg>
                            {:else if item.icon === 'cube'}
                                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-5 h-5">
                                    <path d="M10.362 1.093a.75.75 0 00-.724 0L2.523 5.018 10 9.143l7.477-4.125-7.115-3.925zM18 6.443l-7.25 4v8.25l6.862-3.786A.75.75 0 0018 14.25V6.443zM9.25 18.693v-8.25l-7.25-4v7.807a.75.75 0 00.388.657l6.862 3.786z" />
                                </svg>
                            {:else if item.icon === 'database'}
                                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-5 h-5">
                                    <path fill-rule="evenodd" d="M10 1c3.866 0 7 1.79 7 4s-3.134 4-7 4-7-1.79-7-4 3.134-4 7-4zm5.694 8.13c.464-.264.91-.583 1.306-.952V10c0 2.21-3.134 4-7 4s-7-1.79-7-4V8.178c.396.37.842.688 1.306.953C5.838 10.006 7.854 10.5 10 10.5s4.162-.494 5.694-1.37zM3 13.179V15c0 2.21 3.134 4 7 4s7-1.79 7-4v-1.822c-.396.37-.842.688-1.306.953-1.532.875-3.548 1.369-5.694 1.369s-4.162-.494-5.694-1.37A7.009 7.009 0 013 13.179z" clip-rule="evenodd" />
                                </svg>
                            {:else if item.icon === 'workflow'}
                                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-5 h-5">
                                    <path fill-rule="evenodd" d="M4 2a2 2 0 00-2 2v11a3 3 0 106 0V4a2 2 0 00-2-2H4zm1 14a1 1 0 100-2 1 1 0 000 2zm5-14a2 2 0 00-2 2v11a3 3 0 106 0V4a2 2 0 00-2-2h-2zm1 14a1 1 0 100-2 1 1 0 000 2zm5-14a2 2 0 00-2 2v11a3 3 0 106 0V4a2 2 0 00-2-2h-2zm1 14a1 1 0 100-2 1 1 0 000 2z" clip-rule="evenodd" />
                                </svg>
                            {:else if item.icon === 'server'}
                                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-5 h-5">
                                    <path d="M4.632 3.533A2 2 0 016.577 2h6.846a2 2 0 011.945 1.533l1.976 8.234A3.489 3.489 0 0016 11.5H4c-.476 0-.93.095-1.344.267l1.976-8.234z" />
                                    <path fill-rule="evenodd" d="M4 13a2 2 0 100 4h12a2 2 0 100-4H4zm11.24 2a.75.75 0 01.75-.75H16a.75.75 0 01.75.75v.01a.75.75 0 01-.75.75h-.01a.75.75 0 01-.75-.75V15zm-2.25-.75a.75.75 0 00-.75.75v.01c0 .414.336.75.75.75H13a.75.75 0 00.75-.75V15a.75.75 0 00-.75-.75h-.01z" clip-rule="evenodd" />
                                </svg>
                            {:else if item.icon === 'document'}
                                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-5 h-5">
                                    <path fill-rule="evenodd" d="M4.5 2A1.5 1.5 0 003 3.5v13A1.5 1.5 0 004.5 18h11a1.5 1.5 0 001.5-1.5V7.621a1.5 1.5 0 00-.44-1.06l-4.12-4.122A1.5 1.5 0 0011.378 2H4.5zm2.25 8.5a.75.75 0 000 1.5h6.5a.75.75 0 000-1.5h-6.5zm0 3a.75.75 0 000 1.5h6.5a.75.75 0 000-1.5h-6.5z" clip-rule="evenodd" />
                                </svg>
                            {:else if item.icon === 'book'}
                                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-5 h-5">
                                    <path d="M10.75 16.82A7.462 7.462 0 0115 15.5c.71 0 1.396.098 2.046.282A.75.75 0 0018 15.06v-11a.75.75 0 00-.546-.721A9.006 9.006 0 0015 3a8.963 8.963 0 00-4.25 1.065V16.82zM9.25 4.065A8.963 8.963 0 005 3c-.85 0-1.673.118-2.454.339A.75.75 0 002 4.06v11a.75.75 0 00.954.721A7.506 7.506 0 015 15.5c1.579 0 3.042.487 4.25 1.32V4.065z" />
                                </svg>
                            {:else if item.icon === 'shield'}
                                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-5 h-5">
                                    <path fill-rule="evenodd" d="M9.661 2.237a.531.531 0 01.678 0 11.947 11.947 0 007.078 2.749.5.5 0 01.479.425c.069.52.104 1.05.104 1.589 0 5.162-3.26 9.563-7.834 11.256a.48.48 0 01-.332 0C5.26 16.564 2 12.163 2 7c0-.538.035-1.069.104-1.589a.5.5 0 01.48-.425 11.947 11.947 0 007.077-2.75z" clip-rule="evenodd" />
                                </svg>
                            {:else if item.icon === 'chart'}
                                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-5 h-5">
                                    <path fill-rule="evenodd" d="M1 2.75A.75.75 0 011.75 2h16.5a.75.75 0 010 1.5H18v8.75A2.75 2.75 0 0115.25 15h-1.072l.798 3.06a.75.75 0 01-1.452.38L12.66 15H7.34l-.864 3.44a.75.75 0 11-1.453-.38l.798-3.06H4.75A2.75 2.75 0 012 12.25V3.5h-.25A.75.75 0 011 2.75zM7.373 13.5l.266-1.5h4.722l.265 1.5H7.373zm6.877-3H5.75a.75.75 0 010-1.5h8.5a.75.75 0 010 1.5zm0-3H5.75a.75.75 0 010-1.5h8.5a.75.75 0 010 1.5z" clip-rule="evenodd" />
                                </svg>
                            {:else if item.icon === 'chart-bar'}
                                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-5 h-5">
                                    <path d="M15.5 2A1.5 1.5 0 0014 3.5v13a1.5 1.5 0 001.5 1.5h1a1.5 1.5 0 001.5-1.5v-13A1.5 1.5 0 0016.5 2h-1zM9.5 6A1.5 1.5 0 008 7.5v9A1.5 1.5 0 009.5 18h1a1.5 1.5 0 001.5-1.5v-9A1.5 1.5 0 0010.5 6h-1zM3.5 10A1.5 1.5 0 002 11.5v5A1.5 1.5 0 003.5 18h1A1.5 1.5 0 006 16.5v-5A1.5 1.5 0 004.5 10h-1z" />
                                </svg>
                            {:else if item.icon === 'cpu'}
                                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-5 h-5">
                                    <path d="M14 6H6v8h8V6z" />
                                    <path fill-rule="evenodd" d="M9.25 3V1.75a.75.75 0 011.5 0V3h1.5V1.75a.75.75 0 011.5 0V3h.5A2.75 2.75 0 0117 5.75v.5h1.25a.75.75 0 010 1.5H17v1.5h1.25a.75.75 0 010 1.5H17v1.5h1.25a.75.75 0 010 1.5H17v.5A2.75 2.75 0 0114.25 17h-.5v1.25a.75.75 0 01-1.5 0V17h-1.5v1.25a.75.75 0 01-1.5 0V17h-1.5v1.25a.75.75 0 01-1.5 0V17h-.5A2.75 2.75 0 013 14.25v-.5H1.75a.75.75 0 010-1.5H3v-1.5H1.75a.75.75 0 010-1.5H3v-1.5H1.75a.75.75 0 010-1.5H3v-.5A2.75 2.75 0 015.75 3h.5V1.75a.75.75 0 011.5 0V3h1.5zM4.5 5.75c0-.69.56-1.25 1.25-1.25h8.5c.69 0 1.25.56 1.25 1.25v8.5c0 .69-.56 1.25-1.25 1.25h-8.5c-.69 0-1.25-.56-1.25-1.25v-8.5z" clip-rule="evenodd" />
                                </svg>
                            {:else if item.icon === 'globe'}
                                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-5 h-5">
                                    <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-1.5 0a6.5 6.5 0 11-11-4.69v.447a3.5 3.5 0 001.025 2.475L8.293 10 8 10.293a1 1 0 000 1.414l1.06 1.06a1.5 1.5 0 01.44 1.061v.363a1 1 0 00.553.894l.276.139a1 1 0 001.342-.448l1.454-2.908a1.5 1.5 0 00-.281-1.731l-.772-.772a1 1 0 01-.293-.707v-.363a1 1 0 00-.553-.894l-1.66-.83a1 1 0 01-.553-.894v-.6a1 1 0 01.447-.894l.553-.369a6.5 6.5 0 016.032 5.677z" clip-rule="evenodd" />
                                </svg>
                            {:else if item.icon === 'users'}
                                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-5 h-5">
                                    <path d="M7 8a3 3 0 100-6 3 3 0 000 6zM14.5 9a2.5 2.5 0 100-5 2.5 2.5 0 000 5zM1.615 16.428a1.224 1.224 0 01-.569-1.175 6.002 6.002 0 0111.908 0c.058.467-.172.92-.57 1.174A9.953 9.953 0 017 18a9.953 9.953 0 01-5.385-1.572zM14.5 16h-.106c.07-.297.088-.611.048-.933a7.47 7.47 0 00-1.588-3.755 4.502 4.502 0 015.874 2.636.818.818 0 01-.36.98A7.465 7.465 0 0114.5 16z" />
                                </svg>
                            {:else if item.icon === 'cog'}
                                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-5 h-5">
                                    <path fill-rule="evenodd" d="M7.84 1.804A1 1 0 018.82 1h2.36a1 1 0 01.98.804l.331 1.652a6.993 6.993 0 011.929 1.115l1.598-.54a1 1 0 011.186.447l1.18 2.044a1 1 0 01-.205 1.251l-1.267 1.113a7.047 7.047 0 010 2.228l1.267 1.113a1 1 0 01.206 1.25l-1.18 2.045a1 1 0 01-1.187.447l-1.598-.54a6.993 6.993 0 01-1.929 1.115l-.33 1.652a1 1 0 01-.98.804H8.82a1 1 0 01-.98-.804l-.331-1.652a6.993 6.993 0 01-1.929-1.115l-1.598.54a1 1 0 01-1.186-.447l-1.18-2.044a1 1 0 01.205-1.251l1.267-1.114a7.05 7.05 0 010-2.227L1.821 7.773a1 1 0 01-.206-1.25l1.18-2.045a1 1 0 011.187-.447l1.598.54A6.993 6.993 0 017.51 3.456l.33-1.652zM10 13a3 3 0 100-6 3 3 0 000 6z" clip-rule="evenodd" />
                                </svg>
                            {:else}
                                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-5 h-5">
                                    <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-11a1 1 0 10-2 0v2H7a1 1 0 100 2h2v2a1 1 0 102 0v-2h2a1 1 0 100-2h-2V7z" clip-rule="evenodd" />
                                </svg>
                            {/if}
                        </div>
                        
                        <!-- Label -->
                        <span class="flex-1 text-sm font-medium">{item.name}</span>
                        
                        <!-- Coming Soon Badge -->
                        {#if item.status === 'coming-soon'}
                            <span class="text-[10px] px-1.5 py-0.5 rounded-full bg-gray-700 text-gray-400">
                                Soon
                            </span>
                        {/if}
                    </button>
                {/each}
            </div>
        </div>

        <!-- User Section -->
        <div class="px-3 py-3 border-t border-gray-800/50">
            {#if $user}
                <UserMenu role={$user?.role}>
                    <button class="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg hover:bg-gray-800/50 transition-colors">
                        <img
                            src={$user?.profile_image_url}
                            class="w-8 h-8 rounded-full object-cover"
                            alt="User profile"
                        />
                        <div class="flex-1 text-left">
                            <div class="text-sm font-medium text-white">{$user?.name}</div>
                            <div class="text-xs text-gray-400">{$user?.role}</div>
                        </div>
                    </button>
                </UserMenu>
            {/if}
        </div>
    </div>
</nav>

