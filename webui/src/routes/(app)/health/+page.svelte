<script lang="ts">
	import { onMount } from 'svelte';
	import { fly, fade } from 'svelte/transition';
	import { toast } from 'svelte-sonner';
	import Markdown from '$lib/components/chat/Messages/Markdown.svelte';
	
	// 메시지 타입 정의
	interface Message {
		id: string;
		role: 'user' | 'assistant' | 'system' | 'tool';
		content: string;
		timestamp: Date;
		toolName?: string;
	}
	
	let messages: Message[] = [];
	let inputValue = '';
	let isLoading = false;
	let currentToolCall: string | null = null;
	let messagesContainer: HTMLDivElement;
	
	// LLM 모델 선택
	interface LLMModel {
		id: string;
		name: string;
		default?: boolean;
	}
	let availableModels: LLMModel[] = [];
	let selectedModel: string = 'claude-opus-4.5';
	let loadingModels = false;
	
	// 모델 목록 로드
	async function loadModels() {
		loadingModels = true;
		try {
			const response = await fetch('/api/health-agent/models');
			if (response.ok) {
				const data = await response.json();
				availableModels = data.models || [];
				const defaultModel = availableModels.find(m => m.default);
				if (defaultModel) {
					selectedModel = defaultModel.id;
				}
			}
		} catch (e) {
			console.error('Failed to load models:', e);
		} finally {
			loadingModels = false;
		}
	}
	
	// SSE 연결 중단용 AbortController
	let abortController: AbortController | null = null;
	
	// 새 채팅 시작
	function startNewChat() {
		messages = [{
			id: 'system-welcome',
			role: 'system',
			content: '안녕하세요! 건강/의료 분석 에이전트입니다.\n병원, 약국, 의약품, 질병 정보 등에 대해 질문해 주세요.',
			timestamp: new Date()
		}];
	}
	
	// 분석 결과
	let reportContent = '';
	let reportStreaming = false;
	
	// 헬스체크
	let mcpStatus: 'checking' | 'connected' | 'degraded' | 'error' = 'checking';
	let mcpToolCount = 0;
	
	async function checkHealth() {
		try {
			const response = await fetch('/api/health-agent/status');
			const data = await response.json();
			
			mcpToolCount = data.mcp_tools || 0;

			if (data.status === 'ok' && data.mcp_connected) {
				mcpStatus = 'connected';
				return;
			}

			if (data.mcp_connected) {
				mcpStatus = 'degraded';
				return;
			}

			mcpStatus = 'error';
		} catch (error) {
			mcpStatus = 'error';
			mcpToolCount = 0;
		}
	}
	
	onMount(() => {
		checkHealth();
		loadModels();
		startNewChat();
	});
	
	function scrollToBottom() {
		if (messagesContainer) {
			messagesContainer.scrollTop = messagesContainer.scrollHeight;
		}
	}
	
	function generateId() {
		return 'msg-' + Date.now() + '-' + Math.random().toString(36).substr(2, 9);
	}
	
	async function sendMessage() {
		if (!inputValue.trim() || isLoading) return;
		
		const userMessage: Message = {
			id: generateId(),
			role: 'user',
			content: inputValue.trim(),
			timestamp: new Date()
		};
		
		messages = [...messages, userMessage];
		const question = inputValue.trim();
		inputValue = '';
		isLoading = true;
		currentToolCall = null;
		reportStreaming = true;
		reportContent = '';
		
		setTimeout(scrollToBottom, 50);
		
		try {
			abortController = new AbortController();
			
			const response = await fetch('/api/health-agent/chat/single', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ question, model: selectedModel }),
				signal: abortController.signal
			});
			
			if (!response.ok) {
				throw new Error('API 요청 실패');
			}
			
			const reader = response.body?.getReader();
			const decoder = new TextDecoder();
			
			if (!reader) {
				throw new Error('스트림을 읽을 수 없습니다');
			}
			
			let buffer = '';
			
			while (true) {
				const { done, value } = await reader.read();
				if (done) break;
				
				buffer += decoder.decode(value, { stream: true });
				const lines = buffer.split('\n\n');
				buffer = lines.pop() || '';
				
				for (const line of lines) {
					if (!line.startsWith('data: ')) continue;
					
					try {
						const data = JSON.parse(line.slice(6));
						const eventType = data.event;
						
						switch (eventType) {
							case 'start':
								messages = [...messages, {
									id: generateId(),
									role: 'assistant',
									content: data.message || '🏥 의료 정보를 검색합니다...',
									timestamp: new Date()
								}];
								break;
								
							case 'iteration':
								currentToolCall = `🔄 반복 ${data.iteration}/${data.max_iterations}`;
								break;
								
							case 'tool_start':
								currentToolCall = `🔧 ${data.display_name || data.tool || '도구'} 실행 중...`;
								break;
								
							case 'tool_result':
								currentToolCall = `✅ ${data.display_name || data.tool || '도구'} 완료`;
								break;
								
							case 'content':
								reportContent = data.content || '';
								break;
								
							case 'complete':
								currentToolCall = null;
								reportStreaming = false;
								if (reportContent) {
									messages = [...messages, {
										id: generateId(),
										role: 'assistant',
										content: reportContent,
										timestamp: new Date()
									}];
								}
								break;
								
							case 'error':
								toast.error(data.message || '검색 중 오류가 발생했습니다.');
								currentToolCall = null;
								reportStreaming = false;
								break;
								
							case 'done':
								break;
						}
						
						scrollToBottom();
					} catch (e) {
						console.error('Parse error:', e);
					}
				}
			}
			
		} catch (error: any) {
			if (error.name !== 'AbortError') {
				console.error('Stream error:', error);
				toast.error('검색 중 오류가 발생했습니다.');
			}
		} finally {
			isLoading = false;
			currentToolCall = null;
			abortController = null;
		}
	}
	
	function handleKeyPress(e: KeyboardEvent) {
		if (e.key === 'Enter' && !e.shiftKey) {
			e.preventDefault();
			sendMessage();
		}
	}
</script>

<svelte:head>
	<title>건강/의료 분석 | Agent Portal</title>
</svelte:head>

<div class="flex h-full bg-gradient-to-br from-gray-50 via-white to-gray-100 dark:from-gray-900 dark:via-gray-850 dark:to-gray-900">
	<!-- 메인 채팅 영역 -->
	<div class="flex-1 flex flex-col">
		<!-- 헤더 -->
		<div class="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700 bg-white/80 dark:bg-gray-800/80 backdrop-blur-sm">
			<div class="flex items-center gap-3">
				<div class="p-2 rounded-xl bg-gradient-to-br from-rose-500 to-pink-600 shadow-lg">
					<svg class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
					</svg>
				</div>
				<div>
					<h1 class="text-xl font-semibold text-gray-900 dark:text-white">건강/의료 분석</h1>
					<p class="text-sm text-gray-500 dark:text-gray-400">병원, 약국, 의약품, 질병 정보 검색</p>
				</div>
			</div>
			
			<div class="flex items-center gap-4">
				<!-- MCP 상태 -->
				<div class="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-gray-100 dark:bg-gray-700">
					{#if mcpStatus === 'checking'}
						<div class="w-2 h-2 rounded-full bg-yellow-400 animate-pulse"></div>
						<span class="text-xs text-gray-500">연결 확인 중...</span>
					{:else if mcpStatus === 'connected'}
						<div class="w-2 h-2 rounded-full bg-green-400"></div>
						<span class="text-xs text-gray-600 dark:text-gray-300">MCP 연결됨 ({mcpToolCount} 도구)</span>
					{:else if mcpStatus === 'degraded'}
						<div class="w-2 h-2 rounded-full bg-yellow-400"></div>
						<span class="text-xs text-yellow-600 dark:text-yellow-400">제한된 연결</span>
					{:else}
						<div class="w-2 h-2 rounded-full bg-red-400"></div>
						<span class="text-xs text-red-600 dark:text-red-400">연결 오류</span>
					{/if}
				</div>
				
				<!-- 모델 선택 -->
				<select 
					bind:value={selectedModel}
					class="px-3 py-1.5 text-sm rounded-lg border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-200 focus:outline-none focus:ring-2 focus:ring-rose-500"
					disabled={loadingModels}
				>
					{#each availableModels as model}
						<option value={model.id}>{model.name}</option>
					{/each}
				</select>
				
				<!-- 새 채팅 -->
				<button
					on:click={startNewChat}
					class="px-3 py-1.5 text-sm font-medium rounded-lg bg-rose-100 dark:bg-rose-900/30 text-rose-700 dark:text-rose-300 hover:bg-rose-200 dark:hover:bg-rose-900/50 transition-colors"
				>
					새 채팅
				</button>
			</div>
		</div>
		
		<!-- 메시지 영역 -->
		<div 
			bind:this={messagesContainer}
			class="flex-1 overflow-y-auto p-6 space-y-4"
		>
			{#each messages as message (message.id)}
				<div 
					class="flex {message.role === 'user' ? 'justify-end' : 'justify-start'}"
					in:fly={{ y: 20, duration: 300 }}
				>
					{#if message.role === 'system'}
						<div class="max-w-3xl p-4 rounded-2xl bg-gradient-to-r from-rose-50 to-pink-50 dark:from-rose-900/20 dark:to-pink-900/20 border border-rose-200 dark:border-rose-800">
							<p class="text-gray-700 dark:text-gray-300 whitespace-pre-line">{message.content}</p>
						</div>
					{:else if message.role === 'user'}
						<div class="max-w-2xl p-4 rounded-2xl bg-rose-600 text-white shadow-lg">
							<p class="whitespace-pre-line">{message.content}</p>
						</div>
					{:else}
						<div class="max-w-4xl p-4 rounded-2xl bg-white dark:bg-gray-800 shadow-md border border-gray-100 dark:border-gray-700">
							<Markdown content={message.content} />
						</div>
					{/if}
				</div>
			{/each}
			
			<!-- 도구 호출 스피너 -->
			{#if currentToolCall}
				<div class="flex justify-start" in:fade={{ duration: 200 }}>
					<div class="px-4 py-2 rounded-xl bg-rose-50 dark:bg-rose-900/20 border border-rose-200 dark:border-rose-800">
						<div class="flex items-center gap-2">
							<div class="w-4 h-4 border-2 border-rose-500 border-t-transparent rounded-full animate-spin"></div>
							<span class="text-sm text-rose-700 dark:text-rose-300">{currentToolCall}</span>
						</div>
					</div>
				</div>
			{/if}
		</div>
		
		<!-- 입력 영역 -->
		<div class="p-4 border-t border-gray-200 dark:border-gray-700 bg-white/80 dark:bg-gray-800/80 backdrop-blur-sm">
			<div class="max-w-4xl mx-auto flex gap-3">
				<input
					bind:value={inputValue}
					on:keypress={handleKeyPress}
					placeholder="건강/의료 정보를 질문해 주세요... (예: 강남역 근처 내과)"
					class="flex-1 px-4 py-3 rounded-xl border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-rose-500"
					disabled={isLoading}
				/>
				<button
					on:click={sendMessage}
					disabled={isLoading || !inputValue.trim()}
					class="px-6 py-3 rounded-xl bg-gradient-to-r from-rose-500 to-pink-600 text-white font-medium shadow-lg hover:shadow-xl transition-all disabled:opacity-50 disabled:cursor-not-allowed"
				>
					{#if isLoading}
						<div class="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
					{:else}
						검색
					{/if}
				</button>
			</div>
			<p class="mt-2 text-xs text-center text-gray-400 dark:text-gray-500">
				⚠️ 의료 정보는 참고용입니다. 실제 진료는 전문 의료인과 상담하세요.
			</p>
		</div>
	</div>
</div>

