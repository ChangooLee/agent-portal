<script lang="ts">
    import { page } from '$app/stores';
    import { goto } from '$app/navigation';
    import { selectedRole, roleMenus, getRoleFromPath, type UserRole } from '$lib/stores/role';
    import { user } from '$lib/stores';

    const tabs: { id: UserRole; name: string; icon: string; defaultPath: string }[] = [
        { id: 'use', name: 'Use', icon: 'play', defaultPath: '/' },
        { id: 'build', name: 'Build', icon: 'hammer', defaultPath: '/build/agents' },
        { id: 'operate', name: 'Operate', icon: 'chart-bar', defaultPath: '/admin/monitoring' }
    ];

    function handleTabClick(tab: typeof tabs[0]) {
        selectedRole.set(tab.id);
        goto(tab.defaultPath);
    }

    // Update selected role based on current path
    $: if ($page?.url?.pathname) {
        const roleFromPath = getRoleFromPath($page.url.pathname);
        if (roleFromPath !== $selectedRole) {
            selectedRole.set(roleFromPath);
        }
    }
</script>

<div class="role-tabs flex items-center gap-1 bg-gray-900/80 backdrop-blur-xl rounded-xl p-1 border border-gray-700/50">
    {#each tabs as tab}
        <!-- Only show Operate tab to admin users -->
        {#if tab.id !== 'operate' || $user?.role === 'admin'}
            <button
                class="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200
                    {$selectedRole === tab.id 
                        ? 'bg-blue-600 text-white shadow-lg shadow-blue-600/25' 
                        : 'text-gray-400 hover:text-white hover:bg-gray-800/50'}"
                on:click={() => handleTabClick(tab)}
            >
                {#if tab.icon === 'play'}
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-4 h-4">
                        <path fill-rule="evenodd" d="M4.5 5.653c0-1.426 1.529-2.33 2.779-1.643l11.54 6.348c1.295.712 1.295 2.573 0 3.285L7.28 19.991c-1.25.687-2.779-.217-2.779-1.643V5.653z" clip-rule="evenodd" />
                    </svg>
                {:else if tab.icon === 'hammer'}
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-4 h-4">
                        <path fill-rule="evenodd" d="M13.5 4.938a7 7 0 11-9.006 1.737c.202-.257.59-.218.793.039.278.352.594.672.943.954.332.269.786-.049.773-.476a5.977 5.977 0 01.572-2.759 6.026 6.026 0 012.486-2.665c.247-.14.55-.016.677.238A6.967 6.967 0 0013.5 4.938zM14 12a4 4 0 01-4 4c-1.913 0-3.52-1.398-3.91-3.182-.093-.429.44-.643.814-.413a4.043 4.043 0 001.601.564c.303.038.531-.24.51-.544a5.975 5.975 0 011.315-4.192.447.447 0 01.431-.16A4.001 4.001 0 0114 12z" clip-rule="evenodd" />
                    </svg>
                {:else if tab.icon === 'chart-bar'}
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-4 h-4">
                        <path d="M15.5 2A1.5 1.5 0 0014 3.5v13a1.5 1.5 0 001.5 1.5h1a1.5 1.5 0 001.5-1.5v-13A1.5 1.5 0 0016.5 2h-1zM9.5 6A1.5 1.5 0 008 7.5v9A1.5 1.5 0 009.5 18h1a1.5 1.5 0 001.5-1.5v-9A1.5 1.5 0 0010.5 6h-1zM3.5 10A1.5 1.5 0 002 11.5v5A1.5 1.5 0 003.5 18h1A1.5 1.5 0 006 16.5v-5A1.5 1.5 0 004.5 10h-1z" />
                    </svg>
                {/if}
                <span>{tab.name}</span>
            </button>
        {/if}
    {/each}
</div>

