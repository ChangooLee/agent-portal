<script lang="ts">
	import { getContext } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';
	import {
		WEBUI_NAME,
		showSidebar,
		user,
		chatId,
		models
	} from '$lib/stores';
	import { selectedRole, roleMenus, getRoleFromPath, type UserRole, type MenuItem } from '$lib/stores/role';

	import Tooltip from '../common/Tooltip.svelte';
	import UserMenu from './Sidebar/UserMenu.svelte';
	import MenuLines from '../icons/MenuLines.svelte';
	import PencilSquare from '../icons/PencilSquare.svelte';

	const i18n = getContext('i18n');

	// Role tabs configuration
	const roleTabs: { id: UserRole; name: string; icon: string; defaultPath: string }[] = [
		{ id: 'use', name: 'Use', icon: 'play', defaultPath: '/' },
		{ id: 'build', name: 'Build', icon: 'hammer', defaultPath: '/build/llm' },
		{ id: 'operate', name: 'Operate', icon: 'chart-bar', defaultPath: '/operate/monitoring' }
	];

	// Get current menu items based on selected role
	$: currentMenuItems = roleMenus[$selectedRole] || [];

	// Update selected role based on current path
	$: if ($page?.url?.pathname) {
		const roleFromPath = getRoleFromPath($page.url.pathname);
		if (roleFromPath !== $selectedRole) {
			selectedRole.set(roleFromPath);
		}
	}

	function handleRoleTabClick(tab: typeof roleTabs[0]) {
		selectedRole.set(tab.id);
		goto(tab.defaultPath);
	}

	function isMenuActive(item: MenuItem): boolean {
		const pathname = $page.url.pathname;
		if (item.href === '/') {
			return pathname === '/' || pathname === '/home';
		}
		if (item.href === '/c') {
			return pathname.startsWith('/c');
		}
		// Exact match for admin paths
		if (item.href.startsWith('/admin/')) {
			return pathname === item.href || pathname.startsWith(item.href + '/');
		}
		// For other paths, use startsWith
		return pathname.startsWith(item.href);
	}

	const initNewChat = async () => {
		chatId.set('');
		await goto('/', { replaceState: false, noScroll: false, keepFocus: false, invalidateAll: true });
	};

	// Icon components for menu items
	function getMenuIcon(iconName: string): string {
		const icons: Record<string, string> = {
			'home': 'M10.707 2.293a1 1 0 00-1.414 0l-7 7a1 1 0 001.414 1.414L4 10.414V17a1 1 0 001 1h2a1 1 0 001-1v-2a1 1 0 011-1h2a1 1 0 011 1v2a1 1 0 001 1h2a1 1 0 001-1v-6.586l.293.293a1 1 0 001.414-1.414l-7-7z',
			'chat': 'M2 5a2 2 0 012-2h7a2 2 0 012 2v4a2 2 0 01-2 2H9l-3 3v-3H4a2 2 0 01-2-2V5z M15 7v2a4 4 0 01-4 4H9.828l-1.766 1.767c.28.149.599.233.938.233h2l3 3v-3h2a2 2 0 002-2V9a2 2 0 00-2-2h-1z',
			'cube': 'M11.3 1.046A1 1 0 0112 2v5h4a1 1 0 01.82 1.573l-7 10A1 1 0 018 18v-5H4a1 1 0 01-.82-1.573l7-10a1 1 0 011.12-.38z',
			'database': 'M3 12v3c0 1.657 3.134 3 7 3s7-1.343 7-3v-3c0 1.657-3.134 3-7 3s-7-1.343-7-3z M3 7v3c0 1.657 3.134 3 7 3s7-1.343 7-3V7c0 1.657-3.134 3-7 3S3 8.657 3 7z M17 5c0 1.657-3.134 3-7 3S3 6.657 3 5s3.134-3 7-3 7 1.343 7 3z',
			'workflow': 'M5 3a2 2 0 00-2 2v2a2 2 0 002 2h2a2 2 0 002-2V5a2 2 0 00-2-2H5zM5 11a2 2 0 00-2 2v2a2 2 0 002 2h2a2 2 0 002-2v-2a2 2 0 00-2-2H5zM11 5a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V5zM14 11a1 1 0 011 1v1h1a1 1 0 110 2h-1v1a1 1 0 11-2 0v-1h-1a1 1 0 110-2h1v-1a1 1 0 011-1z',
			'server': 'M2 5a2 2 0 012-2h12a2 2 0 012 2v2a2 2 0 01-2 2H4a2 2 0 01-2-2V5zm14 1a1 1 0 11-2 0 1 1 0 012 0zM2 13a2 2 0 012-2h12a2 2 0 012 2v2a2 2 0 01-2 2H4a2 2 0 01-2-2v-2zm14 1a1 1 0 11-2 0 1 1 0 012 0z',
			'document': 'M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4zm2 6a1 1 0 011-1h6a1 1 0 110 2H7a1 1 0 01-1-1zm1 3a1 1 0 100 2h6a1 1 0 100-2H7z',
			'book': 'M9 4.804A7.968 7.968 0 005.5 4c-1.255 0-2.443.29-3.5.804v10A7.969 7.969 0 015.5 14c1.669 0 3.218.51 4.5 1.385A7.962 7.962 0 0114.5 14c1.255 0 2.443.29 3.5.804v-10A7.968 7.968 0 0014.5 4c-1.255 0-2.443.29-3.5.804V12a1 1 0 11-2 0V4.804z',
			'shield': 'M2.166 4.999A11.954 11.954 0 0010 1.944 11.954 11.954 0 0017.834 5c.11.65.166 1.32.166 2.001 0 5.225-3.34 9.67-8 11.317C5.34 16.67 2 12.225 2 7c0-.682.057-1.35.166-2.001zm11.541 3.708a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z',
			'chart': 'M2 11a1 1 0 011-1h2a1 1 0 011 1v5a1 1 0 01-1 1H3a1 1 0 01-1-1v-5zM8 7a1 1 0 011-1h2a1 1 0 011 1v9a1 1 0 01-1 1H9a1 1 0 01-1-1V7zM14 4a1 1 0 011-1h2a1 1 0 011 1v12a1 1 0 01-1 1h-2a1 1 0 01-1-1V4z',
			'chart-bar': 'M15.5 2A1.5 1.5 0 0014 3.5v13a1.5 1.5 0 001.5 1.5h1a1.5 1.5 0 001.5-1.5v-13A1.5 1.5 0 0016.5 2h-1zM9.5 6A1.5 1.5 0 008 7.5v9A1.5 1.5 0 009.5 18h1a1.5 1.5 0 001.5-1.5v-9A1.5 1.5 0 0010.5 6h-1zM3.5 10A1.5 1.5 0 002 11.5v5A1.5 1.5 0 003.5 18h1A1.5 1.5 0 006 16.5v-5A1.5 1.5 0 004.5 10h-1z',
			'cpu': 'M14 6a2 2 0 012-2h4a2 2 0 012 2v4a2 2 0 01-2 2h-4a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h4a2 2 0 012 2v4a2 2 0 01-2 2H6a2 2 0 01-2-2v-4zM14 16a2 2 0 012-2h4a2 2 0 012 2v4a2 2 0 01-2 2h-4a2 2 0 01-2-2v-4zM4 6a2 2 0 012-2h4a2 2 0 012 2v4a2 2 0 01-2 2H6a2 2 0 01-2-2V6z',
			'globe': 'M10 18a8 8 0 100-16 8 8 0 000 16zM4.332 8.027a6.012 6.012 0 011.912-2.706C6.512 5.73 6.974 6 7.5 6A1.5 1.5 0 019 7.5V8a2 2 0 004 0 2 2 0 011.523-1.943A5.977 5.977 0 0116 10c0 .34-.028.675-.083 1H15a2 2 0 00-2 2v2.197A5.973 5.973 0 0110 16v-2a2 2 0 00-2-2 2 2 0 01-2-2 2 2 0 00-1.668-1.973z',
			'users': 'M9 6a3 3 0 11-6 0 3 3 0 016 0zM17 6a3 3 0 11-6 0 3 3 0 016 0zM12.93 17c.046-.327.07-.66.07-1a6.97 6.97 0 00-1.5-4.33A5 5 0 0119 16v1h-6.07zM6 11a5 5 0 015 5v1H1v-1a5 5 0 015-5z',
			'cog': 'M11.49 3.17c-.38-1.56-2.6-1.56-2.98 0a1.532 1.532 0 01-2.286.948c-1.372-.836-2.942.734-2.106 2.106.54.886.061 2.042-.947 2.287-1.561.379-1.561 2.6 0 2.978a1.532 1.532 0 01.947 2.287c-.836 1.372.734 2.942 2.106 2.106a1.532 1.532 0 012.287.947c.379 1.561 2.6 1.561 2.978 0a1.533 1.533 0 012.287-.947c1.372.836 2.942-.734 2.106-2.106a1.533 1.533 0 01.947-2.287c1.561-.379 1.561-2.6 0-2.978a1.532 1.532 0 01-.947-2.287c.836-1.372-.734-2.942-2.106-2.106a1.532 1.532 0 01-2.287-.947zM10 13a3 3 0 100-6 3 3 0 000 6z',
		};
		return icons[iconName] || icons['cube'];
	}
</script>

<nav class="sticky top-0 z-50 w-full bg-gray-950 border-b border-gray-800/50">
	<!-- Top Row: Role Tabs (Use/Build/Operate) + User Actions -->
	<div class="flex items-center justify-between px-4 py-1.5">
		<!-- Left: Portal Name with Logo -->
		<div class="flex items-center gap-3">
			<a href="/" class="flex items-center gap-2">
				<img
					crossorigin="anonymous"
					src="/static/favicon.png"
					class="size-7 rounded-lg"
					alt="logo"
					draggable="false"
				/>
				<span class="text-base font-bold text-white" style="font-family: 'Samsung Gothic', sans-serif;">
					SFN AI Portal
				</span>
			</a>
		</div>

		<!-- Center: Role Tabs -->
		<div class="flex items-center gap-1 bg-gray-900/80 backdrop-blur-xl rounded-xl p-1 border border-gray-700/50">
			{#each roleTabs as tab}
				{#if tab.id !== 'operate' || $user?.role === 'admin'}
					<button
						class="flex items-center gap-2 px-4 py-1.5 rounded-lg text-sm font-medium transition-all duration-200
							{$selectedRole === tab.id 
								? 'bg-gradient-to-r from-blue-600 to-indigo-600 text-white shadow-lg shadow-blue-600/25' 
								: 'text-gray-400 hover:text-white hover:bg-gray-800/50'}"
						on:click={() => handleRoleTabClick(tab)}
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

		<!-- Right: Actions -->
		<div class="flex items-center gap-2">
			<Tooltip content="New Chat">
				<button
					id="new-chat-button"
					class="p-2 rounded-lg text-gray-400 hover:text-white hover:bg-gray-800/50 transition-all duration-200"
					on:click={() => initNewChat()}
					aria-label="New Chat"
				>
					<PencilSquare className="size-5" strokeWidth="2" />
				</button>
			</Tooltip>

			{#if $user !== undefined && $user !== null}
				<UserMenu
					className="max-w-[200px]"
					role={$user?.role}
					on:show={(e) => {}}
				>
					<button
						class="flex rounded-lg p-1 hover:bg-gray-800/50 transition-all duration-200"
						aria-label="User Menu"
					>
						<img
							src={$user?.profile_image_url}
							class="size-8 object-cover rounded-lg ring-2 ring-gray-700"
							alt="User profile"
							draggable="false"
						/>
					</button>
				</UserMenu>
			{/if}
		</div>
	</div>

	<!-- Bottom Row: Sub-menu (centered) -->
	<div class="flex items-center justify-center px-4 py-1.5 border-t border-gray-800/30">
		<div class="flex items-center gap-1">
			{#each currentMenuItems as item}
				<a
					href={item.href}
					class="flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-all duration-200
						{isMenuActive(item)
							? 'bg-gray-800 text-white' 
							: 'text-gray-400 hover:text-white hover:bg-gray-800/50'}
						{item.status === 'coming-soon' ? 'opacity-60' : ''}"
					title={item.description}
				>
					<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" class="w-4 h-4">
						<path fill-rule="evenodd" d={getMenuIcon(item.icon)} clip-rule="evenodd" />
					</svg>
					<span>{item.name}</span>
					{#if item.status === 'coming-soon'}
						<span class="text-[10px] px-1.5 py-0.5 rounded-full bg-gray-700 text-gray-400">Soon</span>
					{/if}
				</a>
			{/each}
		</div>
	</div>
</nav>
