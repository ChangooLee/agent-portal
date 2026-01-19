<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { slideStudioStore } from './stores/slideStudioStore';
	import TopBar from './components/TopBar.svelte';
	import SlideList from './components/SlideList.svelte';
	import Canvas from './components/Canvas.svelte';
	import Inspector from './components/Inspector.svelte';
	import ChatInput from './components/ChatInput.svelte';
	import ChatHistory from './components/ChatHistory.svelte';
	
	let store = slideStudioStore.get();
	let sseConnection: EventSource | null = null;
	
	const unsubscribe = slideStudioStore.subscribe((s) => {
		const prevDeckId = store.deck_id;
		store = s;
		// Switch to editor mode when deck_id is created (only if it's new)
		if (s.deck_id && !prevDeckId && s.viewMode === 'chat') {
			// Use setTimeout to avoid updating during subscription
			setTimeout(() => {
				slideStudioStore.update(currentStore => ({
					...currentStore,
					viewMode: 'editor'
				}));
			}, 0);
		}
	});
	
	onMount(() => {
		// Cleanup on unmount
		return () => {
			if (sseConnection) {
				sseConnection.close();
			}
		};
	});
	
	onDestroy(() => {
		if (sseConnection) {
			sseConnection.close();
		}
		unsubscribe();
	});
	
	async function handleGenerate(data: {
		prompt: string;
		goal?: string;
		audience?: string;
		tone?: string;
		slide_count: number;
		options?: {
			include_images?: boolean;
			use_playwright?: boolean;
		};
	}) {
		try {
			// Add assistant message for generation start
			slideStudioStore.addMessage({
				id: `msg-${Date.now()}-assistant`,
				role: 'assistant',
				content: '슬라이드 생성을 시작합니다...',
				timestamp: new Date().toISOString()
			});

			// Check if we have an existing deck_id for follow-up request
			const existingDeckId = store.deck_id;
			const url = existingDeckId 
				? `/api/slides/${existingDeckId}/add-slides`
				: '/api/slides/generate';

			const response = await fetch(url, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify(data)
			});
			
			if (!response.ok) {
				throw new Error('Failed to generate deck');
			}
			
			const result = await response.json();
			const deckId = result.deck_id || existingDeckId;
			
			if (!deckId) {
				throw new Error('No deck_id returned');
			}

			// Update store with deck_id
			slideStudioStore.update(s => ({
				...s,
				deck_id: deckId
			}));
			
			// Connect to SSE stream
			connectSSE(deckId);
		} catch (error) {
			console.error('Generate error:', error);
			// Add error message
			slideStudioStore.addMessage({
				id: `msg-${Date.now()}-error`,
				role: 'assistant',
				content: `오류가 발생했습니다: ${error}`,
				timestamp: new Date().toISOString()
			});
		}
	}
	
	function connectSSE(deckId: string) {
		// Close existing connection
		if (sseConnection) {
			sseConnection.close();
		}
		
		// Create new SSE connection
		const eventSource = new EventSource(`/api/slides/${deckId}/events`);
		sseConnection = eventSource;
		
		eventSource.onmessage = (event) => {
			try {
				const data = JSON.parse(event.data);
				const eventType = event.type || data.event;
				slideStudioStore.handleSSEEvent(eventType, data);
			} catch (error) {
				console.error('SSE parse error:', error);
			}
		};
		
		eventSource.addEventListener('deck.created', (e: any) => {
			const data = JSON.parse(e.data);
			slideStudioStore.handleSSEEvent('deck.created', data);
			// Add chat message
			slideStudioStore.addMessage({
				id: `msg-${Date.now()}-deck-created`,
				role: 'assistant',
				content: '덱이 생성되었습니다. 슬라이드 계획을 수립 중입니다...',
				timestamp: new Date().toISOString(),
				metadata: { deck_id: data.deck_id }
			});
		});
		
		eventSource.addEventListener('deck.plan.created', (e: any) => {
			const data = JSON.parse(e.data);
			slideStudioStore.handleSSEEvent('deck.plan.created', data);
			// Add chat message
			slideStudioStore.addMessage({
				id: `msg-${Date.now()}-plan-created`,
				role: 'assistant',
				content: `${data.slides?.length || 0}개의 슬라이드를 생성하기 시작합니다.`,
				timestamp: new Date().toISOString(),
				metadata: { deck_id: data.deck_id, slide_count: data.slides?.length || 0 }
			});
		});
		
		eventSource.addEventListener('slide.stage', (e: any) => {
			const data = JSON.parse(e.data);
			slideStudioStore.handleSSEEvent('slide.stage', data);
		});
		
		eventSource.addEventListener('slide.preview.updated', (e: any) => {
			const data = JSON.parse(e.data);
			slideStudioStore.handleSSEEvent('slide.preview.updated', data);
		});
		
		eventSource.addEventListener('slide.issues', (e: any) => {
			const data = JSON.parse(e.data);
			slideStudioStore.handleSSEEvent('slide.issues', data);
		});
		
		eventSource.addEventListener('slide.finalized', (e: any) => {
			const data = JSON.parse(e.data);
			slideStudioStore.handleSSEEvent('slide.finalized', data);
			// Add chat message for finalized slide
			const slide = store.slides.find(s => s.slide_id === data.slide_id);
			if (slide) {
				const finalizedCount = store.slides.filter(s => 
					s.stage === 'FINAL' || s.stage === 'FINAL_WITH_WARNINGS'
				).length;
				const totalCount = store.slides.length;
				if (finalizedCount === totalCount) {
					slideStudioStore.addMessage({
						id: `msg-${Date.now()}-all-finalized`,
						role: 'assistant',
						content: `모든 슬라이드 생성이 완료되었습니다! (${totalCount}개)`,
						timestamp: new Date().toISOString(),
						metadata: { deck_id: data.deck_id }
					});
				}
			}
		});
		
		eventSource.addEventListener('export.started', (e: any) => {
			const data = JSON.parse(e.data);
			slideStudioStore.handleSSEEvent('export.started', data);
			slideStudioStore.addMessage({
				id: `msg-${Date.now()}-export-started`,
				role: 'assistant',
				content: '파일 내보내기를 시작합니다...',
				timestamp: new Date().toISOString()
			});
		});
		
		eventSource.addEventListener('export.finished', (e: any) => {
			const data = JSON.parse(e.data);
			slideStudioStore.handleSSEEvent('export.finished', data);
			slideStudioStore.addMessage({
				id: `msg-${Date.now()}-export-finished`,
				role: 'assistant',
				content: '파일 내보내기가 완료되었습니다.',
				timestamp: new Date().toISOString()
			});
		});
		
		eventSource.addEventListener('job.error', (e: any) => {
			const data = JSON.parse(e.data);
			slideStudioStore.handleSSEEvent('job.error', data);
			slideStudioStore.addMessage({
				id: `msg-${Date.now()}-error`,
				role: 'assistant',
				content: `오류가 발생했습니다: ${data.error || data.message || 'Unknown error'}`,
				timestamp: new Date().toISOString()
			});
		});
		
		eventSource.addEventListener('job.stopped', (e: any) => {
			const data = JSON.parse(e.data);
			slideStudioStore.handleSSEEvent('job.stopped', data);
			slideStudioStore.addMessage({
				id: `msg-${Date.now()}-stopped`,
				role: 'assistant',
				content: '생성이 중지되었습니다.',
				timestamp: new Date().toISOString()
			});
		});
		
		eventSource.onerror = (error) => {
			console.error('SSE error:', error);
			eventSource.close();
		};
	}
	
	function handleStop() {
		if (store.deck_id) {
			fetch(`/api/slides/${store.deck_id}/stop`, {
				method: 'POST'
			}).catch(console.error);
			// Add user message
			slideStudioStore.addMessage({
				id: `msg-${Date.now()}-stop`,
				role: 'user',
				content: '생성 중지',
				timestamp: new Date().toISOString()
			});
		}
	}
	
	function handleExport() {
		// TODO: Implement export
		console.log('Export clicked');
	}
	
	async function handleSave() {
		if (!store.deck_id) return;
		
		const label = window.prompt('Version label (optional):');
		
		try {
			const response = await fetch(`/api/slides/${store.deck_id}/save`, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify({
					label: label || undefined
				})
			});
			
			if (!response.ok) {
				throw new Error('Save failed');
			}
			
			const data = await response.json();
			alert(`Saved ${data.label}`);
		} catch (error) {
			console.error('Save error:', error);
			alert('Failed to save: ' + error);
		}
	}
	
	let showRestoreModal = false;
	let versions: Array<{version_id: string; label: string; created_at: string}> = [];
	
	async function loadVersions() {
		if (!store.deck_id) return;
		
		try {
			const response = await fetch(`/api/slides/${store.deck_id}/versions`);
			if (response.ok) {
				const data = await response.json();
				versions = data.versions || [];
			}
		} catch (error) {
			console.error('Failed to load versions:', error);
		}
	}
	
	function handleRestore() {
		showRestoreModal = true;
		loadVersions();
	}
	
	async function restoreVersion(versionId: string) {
		if (!store.deck_id) return;
		
		try {
			const response = await fetch(`/api/slides/${store.deck_id}/restore/${versionId}`, {
				method: 'POST'
			});
			
			if (!response.ok) {
				throw new Error('Restore failed');
			}
			
			showRestoreModal = false;
			alert('Version restored');
			// Reload page or refresh state
			location.reload();
		} catch (error) {
			console.error('Restore error:', error);
			alert('Failed to restore: ' + error);
		}
	}
	
	function handleSlideSelect(slideId: string, multi: boolean) {
		if (multi) {
			slideStudioStore.update(s => {
				const selected = [...s.selectedSlideIds];
				const index = selected.indexOf(slideId);
				if (index === -1) {
					selected.push(slideId);
				} else {
					selected.splice(index, 1);
				}
				return { selectedSlideIds: selected };
			});
		} else {
			slideStudioStore.update(s => ({
				selectedSlideIds: [slideId]
			}));
		}
	}
</script>

<svelte:head>
	<title>슬라이드 | AI Agent Portal</title>
</svelte:head>

<div class="h-full min-h-full bg-gray-950 text-slate-50 flex flex-col">
	{#if store.viewMode === 'chat'}
		<!-- Chat Mode: Initial screen -->
		<div class="flex-1 flex flex-col min-h-0">
			<!-- Chat History -->
			<ChatHistory />
			
			<!-- Chat Input -->
			<div class="flex-shrink-0 border-t border-gray-800/50">
				<ChatInput onGenerate={handleGenerate} />
			</div>
		</div>
	{:else}
		<!-- Editor Mode: 3-panel layout -->
		<!-- Top Bar -->
		<TopBar
			onGenerate={() => {
				// Switch back to chat mode for new generation
				slideStudioStore.update(s => ({ ...s, viewMode: 'chat' }));
			}}
			onStop={handleStop}
			onExport={handleExport}
			onSave={handleSave}
			onRestore={handleRestore}
		/>
		
		<!-- Main Content (3-panel layout) -->
		<div class="flex-1 flex min-h-0 overflow-hidden">
			<!-- Left Panel: Slide List -->
			<div class="w-64 shrink-0 overflow-y-auto border-r border-gray-800/50">
				<SlideList onSlideSelect={handleSlideSelect} />
			</div>
			
			<!-- Center Panel: Canvas -->
			<div class="flex-1 min-w-0 overflow-hidden">
				<Canvas />
			</div>
			
			<!-- Right Panel: Inspector -->
			<div class="w-80 shrink-0 overflow-y-auto border-l border-gray-800/50">
				<Inspector />
			</div>
		</div>
	{/if}
	
	<!-- Restore Modal -->
	{#if showRestoreModal}
		<div
			class="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4"
			on:click={() => showRestoreModal = false}
		>
			<div
				class="bg-gray-800 rounded-2xl shadow-xl max-w-2xl w-full max-h-[90vh] overflow-hidden"
				on:click|stopPropagation
			>
				<div class="px-6 py-4 border-b border-gray-700 flex items-center justify-between">
					<h2 class="text-lg font-semibold text-white">Restore Version</h2>
					<button
						on:click={() => showRestoreModal = false}
						class="p-1 hover:bg-gray-700 rounded-lg"
					>
						<svg class="w-5 h-5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
						</svg>
					</button>
				</div>
				
				<div class="p-6 overflow-y-auto max-h-[calc(90vh-140px)]">
					<div class="space-y-2">
						{#each versions as version (version.version_id)}
							<button
								on:click={() => restoreVersion(version.version_id)}
								class="w-full p-3 rounded-lg bg-gray-700 hover:bg-gray-600 text-left transition-colors"
							>
								<div class="font-medium text-white">{version.label}</div>
								<div class="text-xs text-gray-400 mt-1">
									{new Date(version.created_at).toLocaleString()}
								</div>
							</button>
						{/each}
					</div>
				</div>
			</div>
		</div>
	{/if}
</div>
