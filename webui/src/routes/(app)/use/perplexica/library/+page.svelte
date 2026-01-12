<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { toast } from 'svelte-sonner';
	
	interface Chat {
		id: string;
		title: string;
		createdAt: string;
		updatedAt: string;
		sources: string[];
		files: Array<{ fileId: string; name: string }>;
	}
	
	let chats: Chat[] = [];
	let loading = true;
	let searchQuery = '';
	
	// 시간 차이 포맷팅
	function formatTimeDifference(now: Date, date: string): string {
		const diff = now.getTime() - new Date(date).getTime();
		const seconds = Math.floor(diff / 1000);
		const minutes = Math.floor(seconds / 60);
		const hours = Math.floor(minutes / 60);
		const days = Math.floor(hours / 24);
		
		if (days > 0) return `${days} ${days === 1 ? 'day' : 'days'}`;
		if (hours > 0) return `${hours} ${hours === 1 ? 'hour' : 'hours'}`;
		if (minutes > 0) return `${minutes} ${minutes === 1 ? 'minute' : 'minutes'}`;
		return 'Just now';
	}
	
	// 채팅 목록 로드
	async function loadChats() {
		loading = true;
		try {
			const response = await fetch('/api/perplexica/chats');
			if (response.ok) {
				const data = await response.json();
				chats = (data.chats || []).map((chat: any) => ({
					id: chat.id,
					title: chat.title || 'Untitled',
					createdAt: chat.createdAt,
					updatedAt: chat.updatedAt || chat.createdAt,
					sources: chat.sources || [],
					files: chat.files || []
				}));
			} else {
				throw new Error(`Failed to load chats: ${response.status}`);
			}
		} catch (e) {
			console.error('Failed to load chats:', e);
			toast.error('채팅 목록을 불러오는데 실패했습니다.');
		} finally {
			loading = false;
		}
	}
	
	// 채팅 삭제
	async function deleteChat(chatId: string) {
		try {
			const response = await fetch(`/api/perplexica/chats/${chatId}`, {
				method: 'DELETE'
			});
			if (response.ok) {
				chats = chats.filter(c => c.id !== chatId);
				toast.success('채팅이 삭제되었습니다.');
			} else {
				throw new Error(`Failed to delete chat: ${response.status}`);
			}
		} catch (e) {
			console.error('Failed to delete chat:', e);
			toast.error('채팅 삭제에 실패했습니다.');
		}
	}
	
	// 채팅 열기
	function openChat(chatId: string) {
		goto(`/use/perplexica?chatId=${chatId}`);
	}
	
	// 필터된 채팅 목록
	$: filteredChats = chats.filter(chat => 
		searchQuery === '' || 
		chat.title.toLowerCase().includes(searchQuery.toLowerCase())
	);
	
	onMount(() => {
		loadChats();
	});
</script>

<svelte:head>
	<title>Library | AI Agent Portal</title>
</svelte:head>

<div class="h-screen bg-gray-950 text-slate-50 overflow-hidden flex">
	<!-- 좌측 사이드바 (메인 페이지와 동일) -->
	<div class="hidden lg:fixed lg:inset-y-0 lg:z-50 lg:flex lg:w-[72px] lg:flex-col border-r border-gray-800/50">
		<div class="flex grow flex-col items-center justify-between gap-y-5 overflow-y-auto bg-gray-900/80 backdrop-blur-sm px-2 py-8 shadow-sm">
			<!-- 새 채팅 버튼 (Home) -->
			<a
				href="/use/perplexica"
				class="p-2.5 rounded-full bg-gray-800/60 text-gray-300 hover:opacity-70 hover:scale-105 transition duration-200"
			>
				<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-5 h-5">
					<path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
				</svg>
			</a>
			
			<!-- 네비게이션 링크 -->
			<div class="flex flex-col items-center w-full space-y-4">
				<!-- Home -->
				<a
					href="/use/perplexica"
					class="relative flex flex-col items-center justify-center space-y-0.5 cursor-pointer w-full py-2 rounded-lg hover:bg-gray-800/60 transition duration-200"
				>
					<div class="rounded-lg p-1.5">
						<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-6 h-6 text-gray-300">
							<path stroke-linecap="round" stroke-linejoin="round" d="m2.25 12 8.954-8.955c.44-.439 1.152-.439 1.591 0L21.75 12M4.5 9.75v10.125c0 .621.504 1.125 1.125 1.125H9.75v-4.875c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125V21h4.125c.621 0 1.125-.504 1.125-1.125V9.75M8.25 21h8.25" />
						</svg>
					</div>
					<p class="text-[10px] text-gray-400">Home</p>
				</a>
				
				<!-- Library (활성) -->
				<a
					href="/use/perplexica/library"
					class="relative flex flex-col items-center justify-center space-y-0.5 cursor-pointer w-full py-2 rounded-lg bg-gray-800/60 transition duration-200"
				>
					<div class="rounded-lg p-1.5">
						<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-6 h-6 text-gray-300">
							<path stroke-linecap="round" stroke-linejoin="round" d="M12 6.042A8.967 8.967 0 0 0 6 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 0 1 6 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 0 1 6-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0 0 18 18a8.967 8.967 0 0 0-6 2.292m0-14.25v14.25" />
						</svg>
					</div>
					<p class="text-[10px] text-gray-400">Library</p>
				</a>
			</div>
			
			<!-- Settings 버튼 -->
			<button
				type="button"
				class="p-2.5 rounded-full bg-gray-800/60 text-gray-300 hover:opacity-70 hover:scale-105 transition duration-200"
			>
				<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-5 h-5">
					<path stroke-linecap="round" stroke-linejoin="round" d="M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.324.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 0 1 1.37.49l1.296 2.247a1.125 1.125 0 0 1-.26 1.431l-1.003.827c-.293.24-.438.613-.431.992a6.759 6.759 0 0 1 0 .255c-.007.378.138.75.43.99l1.005.828c.424.35.534.954.26 1.43l-1.298 2.247a1.125 1.125 0 0 1-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.57 6.57 0 0 1-.22.128c-.331.183-.581.495-.644.869l-.213 1.28c-.09.543-.56.941-1.11.941h-2.594c-.55 0-1.02-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 0 1-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 0 1-1.369-.49l-1.297-2.247a1.125 1.125 0 0 1 .26-1.431l1.004-.827c.292-.24.437-.613.43-.992a6.932 6.932 0 0 1 0-.255c.007-.378-.138-.75-.43-.99l-1.004-.828a1.125 1.125 0 0 1-.26-1.43l1.297-2.247a1.125 1.125 0 0 1 1.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.087.22-.128.332-.183.582-.495.644-.869l.214-1.281Z" />
					<path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z" />
				</svg>
			</button>
		</div>
	</div>
	
	<!-- 모바일 하단 네비게이션 -->
	<div class="fixed bottom-0 w-full z-50 flex flex-row items-center gap-x-6 bg-gray-900/95 backdrop-blur-sm px-4 py-4 shadow-sm lg:hidden border-t border-gray-800/50">
		<a
			href="/use/perplexica"
			class="relative flex flex-col items-center space-y-1 text-center w-full text-gray-300"
		>
			<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-5 h-5">
				<path stroke-linecap="round" stroke-linejoin="round" d="m2.25 12 8.954-8.955c.44-.439 1.152-.439 1.591 0L21.75 12M4.5 9.75v10.125c0 .621.504 1.125 1.125 1.125H9.75v-4.875c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125V21h4.125c.621 0 1.125-.504 1.125-1.125V9.75M8.25 21h8.25" />
			</svg>
			<p class="text-xs">Home</p>
		</a>
		<a
			href="/use/perplexica/library"
			class="relative flex flex-col items-center space-y-1 text-center w-full text-gray-300"
		>
			<div class="absolute top-0 -mt-4 h-1 w-full rounded-b-lg bg-gray-300" />
			<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-5 h-5">
				<path stroke-linecap="round" stroke-linejoin="round" d="M12 6.042A8.967 8.967 0 0 0 6 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 0 1 6 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 0 1 6-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0 0 18 18a8.967 8.967 0 0 0-6 2.292m0-14.25v14.25" />
			</svg>
			<p class="text-xs">Library</p>
		</a>
		<button
			type="button"
			class="relative flex flex-col items-center space-y-1 text-center w-full text-gray-300"
		>
			<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-5 h-5">
				<path stroke-linecap="round" stroke-linejoin="round" d="M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.324.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 0 1 1.37.49l1.296 2.247a1.125 1.125 0 0 1-.26 1.431l-1.003.827c-.293.24-.438.613-.431.992a6.759 6.759 0 0 1 0 .255c-.007.378.138.75.43.99l1.005.828c.424.35.534.954.26 1.43l-1.298 2.247a1.125 1.125 0 0 1-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.57 6.57 0 0 1-.22.128c-.331.183-.581.495-.644.869l-.213 1.28c-.09.543-.56.941-1.11.941h-2.594c-.55 0-1.02-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 0 1-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 0 1-1.369-.49l-1.297-2.247a1.125 1.125 0 0 1 .26-1.431l1.004-.827c.292-.24.437-.613.43-.992a6.932 6.932 0 0 1 0-.255c.007-.378-.138-.75-.43-.99l-1.004-.828a1.125 1.125 0 0 1-.26-1.43l1.297-2.247a1.125 1.125 0 0 1 1.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.087.22-.128.332-.183.582-.495.644-.869l.214-1.281Z" />
				<path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z" />
			</svg>
			<p class="text-xs">Settings</p>
		</button>
	</div>
	
	<!-- 메인 컨텐츠 -->
	<main class="flex-1 lg:pl-20 bg-gray-950 min-h-screen">
		<div class="max-w-screen-lg lg:mx-auto px-4 sm:px-4 md:px-8">
			<!-- 헤더 -->
			<div class="flex flex-col pt-10 border-b border-gray-800/50 pb-6">
				<div class="flex flex-col lg:flex-row lg:items-end lg:justify-between gap-3">
					<div class="flex items-center justify-center lg:justify-start">
						<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-11 h-11 text-gray-300 mb-2.5">
							<path stroke-linecap="round" stroke-linejoin="round" d="M12 6.042A8.967 8.967 0 0 0 6 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 0 1 6 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 0 1 6-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0 0 18 18a8.967 8.967 0 0 0-6 2.292m0-14.25v14.25" />
						</svg>
						<div class="flex flex-col">
							<h1 class="text-5xl font-normal p-2 pb-0 text-white">
								Library
							</h1>
							<div class="px-2 text-sm text-gray-400 text-center lg:text-left">
								Past chats, sources, and uploads.
							</div>
						</div>
					</div>
					
					<div class="flex items-center justify-center lg:justify-end gap-2 text-xs text-gray-400">
						<span class="inline-flex items-center gap-1 rounded-full border border-gray-700/50 px-2 py-0.5">
							<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-3.5 h-3.5">
								<path stroke-linecap="round" stroke-linejoin="round" d="M12 6.042A8.967 8.967 0 0 0 6 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 0 1 6 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 0 1 6-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0 0 18 18a8.967 8.967 0 0 0-6 2.292m0-14.25v14.25" />
							</svg>
							{loading ? 'Loading…' : `${chats.length} ${chats.length === 1 ? 'chat' : 'chats'}`}
						</span>
					</div>
				</div>
			</div>
			
			<!-- 검색 -->
			<div class="pt-6 pb-4">
				<div class="relative">
					<input
						type="text"
						bind:value={searchQuery}
						placeholder="Search chats..."
						class="w-full px-4 py-2 bg-gray-800/60 border border-gray-700/50 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-1 focus:ring-blue-500/50"
					/>
					<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-5 h-5 absolute right-3 top-1/2 -translate-y-1/2 text-gray-500">
						<path stroke-linecap="round" stroke-linejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" />
					</svg>
				</div>
			</div>
			
			<!-- 채팅 목록 -->
			{#if loading}
				<div class="flex flex-row items-center justify-center min-h-[60vh]">
					<svg
						aria-hidden="true"
						class="w-8 h-8 text-gray-400 animate-spin"
						viewBox="0 0 100 101"
						fill="none"
						xmlns="http://www.w3.org/2000/svg"
					>
						<path
							d="M100 50.5908C100.003 78.2051 78.1951 100.003 50.5908 100C22.9765 99.9972 0.997224 78.018 1 50.4037C1.00281 22.7993 22.8108 0.997224 50.4251 1C78.0395 1.00281 100.018 22.8108 100 50.4251ZM9.08164 50.594C9.06312 73.3997 27.7909 92.1272 50.5966 92.1457C73.4023 92.1642 92.1298 73.4365 92.1483 50.6308C92.1669 27.8251 73.4392 9.0973 50.6335 9.07878C27.8278 9.06026 9.10003 27.787 9.08164 50.594Z"
							fill="currentColor"
						/>
						<path
							d="M93.9676 39.0409C96.393 38.4037 97.8624 35.9116 96.9801 33.5533C95.1945 28.8227 92.871 24.3692 90.0681 20.348C85.6237 14.1775 79.4473 9.36872 72.0454 6.45794C64.6435 3.54717 56.3134 2.65431 48.3133 3.89319C45.869 4.27179 44.3768 6.77534 45.014 9.20079C45.6512 11.6262 48.1343 13.0956 50.5786 12.717C56.5073 11.8281 62.5542 12.5399 68.0406 14.7911C73.527 17.0422 78.2187 20.7487 81.5841 25.4923C83.7976 28.5886 85.4467 32.059 86.4416 35.7474C87.1273 38.1189 89.5423 39.6781 91.9676 39.0409Z"
							fill="currentFill"
						/>
					</svg>
				</div>
			{:else if filteredChats.length === 0}
				<div class="flex flex-col items-center justify-center min-h-[70vh] text-center">
					<div class="flex items-center justify-center w-12 h-12 rounded-2xl border border-gray-700/50 bg-gray-800/60">
						<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-6 h-6 text-gray-400">
							<path stroke-linecap="round" stroke-linejoin="round" d="M12 6.042A8.967 8.967 0 0 0 6 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 0 1 6 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 0 1 6-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0 0 18 18a8.967 8.967 0 0 0-6 2.292m0-14.25v14.25" />
						</svg>
					</div>
					<p class="mt-2 text-gray-400 text-sm">
						No chats found.
					</p>
					<p class="mt-1 text-gray-400 text-sm">
						<a href="/use/perplexica" class="text-blue-400 hover:text-blue-300">
							Start a new chat
						</a>{' '}
						to see it listed here.
					</p>
				</div>
			{:else}
				<div class="pt-6 pb-28">
					<div class="rounded-2xl border border-gray-800/50 overflow-hidden bg-gray-900/60">
						{#each filteredChats as chat, index (chat.id)}
							{@const sourcesLabel = chat.sources.length === 0
								? null
								: chat.sources.length <= 2
									? chat.sources.map(s => s.charAt(0).toUpperCase() + s.slice(1)).join(', ')
									: `${chat.sources.slice(0, 2).map(s => s.charAt(0).toUpperCase() + s.slice(1)).join(', ')} + ${chat.sources.length - 2}`}
							<div
								class="group flex flex-col gap-2 p-4 hover:bg-gray-800/60 transition-colors duration-200 {index !== filteredChats.length - 1 ? 'border-b border-gray-800/50' : ''}"
							>
								<div class="flex items-start justify-between gap-3">
									<button
										on:click={() => openChat(chat.id)}
										class="flex-1 text-left text-white text-base lg:text-lg font-medium leading-snug line-clamp-2 group-hover:text-blue-400 transition duration-200"
										title={chat.title}
									>
										{chat.title}
									</button>
									<button
										type="button"
										on:click={() => deleteChat(chat.id)}
										class="pt-0.5 shrink-0 p-1 rounded-lg hover:bg-gray-700/60 text-gray-400 hover:text-red-400 transition-colors"
									>
										<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-4 h-4">
											<path stroke-linecap="round" stroke-linejoin="round" d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0" />
										</svg>
									</button>
								</div>
								
								<div class="flex flex-wrap items-center gap-2 text-gray-400">
									<span class="inline-flex items-center gap-1 text-xs">
										<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-3.5 h-3.5">
											<path stroke-linecap="round" stroke-linejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
										</svg>
										{formatTimeDifference(new Date(), chat.updatedAt)} Ago
									</span>
									
									{#if sourcesLabel}
										<span class="inline-flex items-center gap-1 text-xs border border-gray-700/50 rounded-full px-2 py-0.5">
											<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-3.5 h-3.5">
												<path stroke-linecap="round" stroke-linejoin="round" d="M12 21a9.004 9.004 0 0 0 8.716-6.747M12 21a9.004 9.004 0 0 1-8.716-6.747M12 21c2.485 0 4.5-4.03 4.5-9S14.485 3 12 3m0 18c-2.485 0-4.5-4.03-4.5-9S9.515 3 12 3m0 0a8.997 8.997 0 0 1 7.843 4.582M12 3a8.997 8.997 0 0 0-7.843 4.582m15.686 0A11.953 11.953 0 0 1 12 10.5c-2.998 0-5.74-1.1-7.843-2.918m15.686 0A8.959 8.959 0 0 1 21 12c0 .778-.099 1.533-.284 2.253m0 0A17.919 17.919 0 0 1 12 16.5c-3.162 0-6.133-.815-8.716-2.247m0 0A9.015 9.015 0 0 1 3 12c0-1.605.42-3.113 1.157-4.418" />
											</svg>
											{sourcesLabel}
										</span>
									{/if}
									{#if chat.files.length > 0}
										<span class="inline-flex items-center gap-1 text-xs border border-gray-700/50 rounded-full px-2 py-0.5">
											<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-3.5 h-3.5">
												<path stroke-linecap="round" stroke-linejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z" />
											</svg>
											{chat.files.length} {chat.files.length === 1 ? 'file' : 'files'}
										</span>
									{/if}
								</div>
							</div>
						{/each}
					</div>
				</div>
			{/if}
		</div>
	</main>
</div>
