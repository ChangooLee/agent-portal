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
	
	interface AnalysisReport {
		title: string | null;
		summary: string;
		sections: Array<{
			title: string;
			content: string;
		}>;
		toolsUsed: string[];
		tokens: { prompt: number; completion: number; total: number };
		latency_ms: number;
		timestamp: Date;
	}
	
	let messages: Message[] = [];
	let inputValue = '';
	let isLoading = false;
	let currentToolCall: string | null = null;
	let messagesContainer: HTMLDivElement;
	let reportContainer: HTMLDivElement;
	
	// 히스토리 기능
	interface ChatHistory {
		id: string;
		title: string;
		model_tab: string;
		created_at: string;
		updated_at: string;
	}
	
	let showHistorySidebar = false;
	let histories: ChatHistory[] = [];
	let historySearchQuery = '';
	let currentHistoryId: string | null = null;
	let loadingHistory = false;
	
	async function loadHistories() {
		try {
			const response = await fetch('/api/legislation/history');
			if (response.ok) {
				const data = await response.json();
				histories = data.histories || [];
			}
		} catch (e) {
			console.error('Failed to load histories:', e);
		}
	}
	
	async function searchHistories() {
		if (!historySearchQuery.trim()) {
			await loadHistories();
			return;
		}
		try {
			const response = await fetch(`/api/legislation/history/search?query=${encodeURIComponent(historySearchQuery)}`);
			if (response.ok) {
				const data = await response.json();
				histories = data.histories || [];
			}
		} catch (e) {
			console.error('Failed to search histories:', e);
		}
	}
	
	async function saveHistory() {
		if (messages.length <= 1) return;
		
		const userMessages = messages.filter(m => m.role === 'user');
		if (userMessages.length === 0) return;
		
		const title = userMessages[0].content.slice(0, 50) + (userMessages[0].content.length > 50 ? '...' : '');
		
		const historyData = { 
			messages,
			selected_model: selectedModel,
			report: report ? {
				title: report.title,
				summary: report.summary,
				sections: report.sections,
				toolsUsed: report.toolsUsed,
				tokens: report.tokens,
				latency_ms: report.latency_ms
			} : null
		};
		
		try {
			if (currentHistoryId) {
				await fetch(`/api/legislation/history/${currentHistoryId}`, {
					method: 'PUT',
					headers: { 'Content-Type': 'application/json' },
					body: JSON.stringify(historyData)
				});
			} else {
				const response = await fetch('/api/legislation/history', {
					method: 'POST',
					headers: { 'Content-Type': 'application/json' },
					body: JSON.stringify({ title, model_tab: 'single', ...historyData })
				});
				if (response.ok) {
					const data = await response.json();
					currentHistoryId = data.history?.id;
				}
			}
			await loadHistories();
		} catch (e) {
			console.error('Failed to save history:', e);
		}
	}
	
	async function loadHistory(historyId: string) {
		loadingHistory = true;
		try {
			const response = await fetch(`/api/legislation/history/${historyId}`);
			if (response.ok) {
				const data = await response.json();
				messages = data.history?.messages || [];
				currentHistoryId = historyId;
				
				if (data.history?.selected_model) {
					selectedModel = data.history.selected_model;
				}
				
				if (data.history?.report) {
					report = {
						...data.history.report,
						timestamp: new Date()
					};
				} else {
					report = null;
				}
				
				showHistorySidebar = false;
			}
		} catch (e) {
			console.error('Failed to load history:', e);
		} finally {
			loadingHistory = false;
		}
	}
	
	async function deleteHistory(historyId: string) {
		try {
			await fetch(`/api/legislation/history/${historyId}`, { method: 'DELETE' });
			await loadHistories();
			if (currentHistoryId === historyId) {
				currentHistoryId = null;
				startNewChat();
			}
		} catch (e) {
			console.error('Failed to delete history:', e);
		}
	}
	
	// LLM 모델 선택
	interface LLMModel {
		model_name: string;
		model: string;
		provider?: string;
	}
	let availableModels: LLMModel[] = [];
	let selectedModel: string = 'claude-opus-4.5';
	let loadingModels = false;
	
	// 모델 목록 로드
	async function loadModels() {
		loadingModels = true;
		try {
			const response = await fetch('/api/llm/models');
			if (response.ok) {
				const data = await response.json();
				availableModels = data.models || [];
				if (availableModels.length > 0 && !availableModels.find(m => m.model_name === selectedModel)) {
					selectedModel = availableModels[0].model_name;
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
			content: '안녕하세요! 법률 정보 분석 에이전트입니다.\n법령, 판례, 법령해석 등에 대해 질문해 주세요.',
			timestamp: new Date()
		}];
		report = null;
		currentHistoryId = null;
	}
	
	// 분석 레포트
	let report: AnalysisReport | null = null;
	let reportStreaming = false;
	
	// 헬스체크
	let mcpStatus: 'checking' | 'connected' | 'degraded' | 'error' = 'checking';
	let mcpToolCount = 0;
	
	async function checkHealth() {
		try {
			const response = await fetch('/api/legislation/health');
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
		loadHistories();
	});
	
	function scrollToBottom() {
		if (messagesContainer) {
			messagesContainer.scrollTop = messagesContainer.scrollHeight;
		}
	}
	
	function generateId() {
		return 'msg-' + Date.now() + '-' + Math.random().toString(36).substr(2, 9);
	}
	
	// Markdown을 섹션으로 파싱
	function parseMarkdownToSections(content: string): Array<{ title: string; content: string }> {
		const sections: Array<{ title: string; content: string }> = [];
		const lines = content.split('\n');
		let currentSection: { title: string; content: string } | null = null;
		
		for (const line of lines) {
			if (line.startsWith('## ')) {
				if (currentSection) {
					sections.push(currentSection);
				}
				currentSection = { title: line.replace('## ', '').trim(), content: '' };
			} else if (line.startsWith('# ')) {
				if (currentSection) {
					sections.push(currentSection);
				}
				currentSection = { title: line.replace('# ', '').trim(), content: '' };
			} else if (currentSection) {
				currentSection.content += line + '\n';
			} else if (line.trim()) {
				if (!currentSection) {
					currentSection = { title: '요약', content: line + '\n' };
				}
			}
		}
		
		if (currentSection) {
			sections.push(currentSection);
		}
		
		if (sections.length === 0 && content.trim()) {
			sections.push({ title: '분석 결과', content: content });
		}
		
		return sections;
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
		
		// 레포트 초기화
		report = {
			title: null,
			summary: '',
			sections: [],
			toolsUsed: [],
			tokens: { prompt: 0, completion: 0, total: 0 },
			latency_ms: 0,
			timestamp: new Date()
		};
		
		setTimeout(scrollToBottom, 50);
		
		try {
			abortController = new AbortController();
			
			const response = await fetch('/api/legislation/chat/single', {
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
						const eventType = data.event || data.type;
						
						// 기술적 이벤트 → 사용자 친화적 메시지 매핑
						const technicalToFriendly: Record<string, string> = {
							'mcp_call_start': '🔧 데이터 조회 중...',
							'mcp_call_complete': '✅ 데이터 조회 완료',
							'llm_call_start': '🤖 AI 분석 중...',
							'llm_call_complete': '✅ AI 분석 완료',
							'tool_call_start': '🔧 도구 실행 중...',
							'tool_call_complete': '✅ 도구 실행 완료'
						};
						
						const transformProgressMessage = (msg: string): string => {
							for (const [tech, friendly] of Object.entries(technicalToFriendly)) {
								if (msg.includes(tech)) {
									return friendly;
								}
							}
							if (msg.includes('_start') || msg.includes('_complete') || msg.includes('_end')) {
								return '⏳ 처리 중...';
							}
							return msg;
						};
						
						switch (eventType) {
							case 'start':
								messages = [...messages, {
									id: generateId(),
									role: 'assistant',
									content: '⚖️ 법률 정보를 분석합니다...',
									timestamp: new Date()
								}];
								break;
								
							case 'intent_classified':
								if (data.reasoning || data.analysis_reasoning) {
									messages = [...messages, {
										id: generateId(),
										role: 'assistant',
										content: `🔍 **분석 의도**: ${data.reasoning || data.analysis_reasoning}`,
										timestamp: new Date()
									}];
								}
								break;
								
							case 'analyzing':
							case 'progress':
							case 'iteration':
								const progressMsg = data.message || data.content || '분석 진행 중...';
								currentToolCall = transformProgressMessage(progressMsg);
								break;
								
							case 'tool_start':
							case 'tool_call':
								currentToolCall = `🔧 ${data.tool_name || data.tool || '도구'} 실행 중...`;
								break;
								
							case 'tool_end':
							case 'tool_result':
								if (data.tool_name || data.tool) {
									if (report) {
										report.toolsUsed = [...report.toolsUsed, data.tool_name || data.tool];
									}
								}
								currentToolCall = null;
								break;
								
							case 'content':
							case 'stream_chunk':
							case 'analysis':
								if (report && data.content) {
									report.summary += data.content;
									report.sections = parseMarkdownToSections(report.summary);
								}
								break;
								
							case 'answer':
							case 'agent_response':
								if (report && data.content) {
									report.summary = data.content;
									report.sections = parseMarkdownToSections(data.content);
								}
								if (data.tool_calls) {
									report!.toolsUsed = [...report!.toolsUsed, ...data.tool_calls.map((t: any) => t.name || t.tool)];
								}
								break;
								
							case 'error':
								messages = [...messages, {
									id: generateId(),
									role: 'assistant',
									content: `❌ 오류: ${data.error || data.message || '알 수 없는 오류'}`,
									timestamp: new Date()
								}];
								reportStreaming = false;
								break;
								
							case 'done':
								if (report) {
									report.summary = data.answer || report.summary;
									report.sections = parseMarkdownToSections(data.answer || report.summary);
									report.tokens = data.tokens || report.tokens;
									report.latency_ms = data.total_latency_ms || 0;
								}
								reportStreaming = false;
								currentToolCall = null;
								break;
								
							case 'complete':
								if (report && report.summary) {
									messages = [...messages, {
										id: generateId(),
										role: 'assistant',
										content: '✨ 분석이 완료되었습니다. 우측 레포트를 확인해주세요.',
										timestamp: new Date()
									}];
								}
								if (data.total_latency_ms && report) {
									report.latency_ms = data.total_latency_ms;
								}
								reportStreaming = false;
								currentToolCall = null;
								break;
							
							case 'end':
							case 'final':
								if (report) {
									const finalContent = data.final_answer || data.response;
									if (finalContent) {
										report.summary = finalContent;
										report.sections = parseMarkdownToSections(finalContent);
									}
								}
								reportStreaming = false;
								currentToolCall = null;
								break;
							
							default:
								if (data.content || data.message) {
									currentToolCall = data.content || data.message;
								}
								break;
						}
						
						setTimeout(scrollToBottom, 50);
						
					} catch (e) {
						console.error('SSE parse error:', e);
					}
				}
			}
			
		} catch (error) {
			console.error('Stream error:', error);
			toast.error('분석 중 오류가 발생했습니다');
			messages = [...messages, {
				id: generateId(),
				role: 'assistant',
				content: '죄송합니다. 분석 중 오류가 발생했습니다.',
				timestamp: new Date()
			}];
			reportStreaming = false;
		} finally {
			isLoading = false;
			currentToolCall = null;
			abortController = null;
			saveHistory();
		}
	}
	
	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Enter' && !e.shiftKey) {
			e.preventDefault();
			sendMessage();
		}
	}
	
	// 예시 질문
	const exampleQuestions = [
		'민법 상속 규정 검색',
		'근로기준법 휴가 관련 조항',
		'최근 상법 판례 조회',
		'임대차보호법 요약'
	];
</script>

<svelte:head>
	<title>법률 정보 분석 | Legislation Agent</title>
</svelte:head>

<div class="h-[calc(100vh-120px)] bg-gray-950 text-slate-50 overflow-hidden flex flex-col">
	<!-- Hero Section -->
	<div class="relative overflow-hidden border-b border-slate-800/50 flex-shrink-0">
		<div class="absolute inset-0 bg-gradient-to-br from-indigo-600/5 via-transparent to-violet-600/5"></div>
		<div class="absolute inset-0 bg-[linear-gradient(rgba(99,102,241,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(99,102,241,0.03)_1px,transparent_1px)] bg-[size:64px_64px]"></div>
		
		<div class="relative px-6 py-6">
			<div class="flex items-center justify-between">
				<div class="flex items-center gap-3">
					<div class="w-12 h-12 rounded-xl bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center shadow-lg shadow-indigo-500/20">
						<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-6 h-6 text-white">
							<path stroke-linecap="round" stroke-linejoin="round" d="M12 3v17.25m0 0c-1.472 0-2.882.265-4.185.75M12 20.25c1.472 0 2.882.265 4.185.75M18.75 4.97A48.416 48.416 0 0 0 12 4.5c-2.291 0-4.545.16-6.75.47m13.5 0c1.01.143 2.01.317 3 .52m-3-.52 2.62 10.726c.122.499-.106 1.028-.589 1.202a5.988 5.988 0 0 1-2.031.352 5.988 5.988 0 0 1-2.031-.352c-.483-.174-.711-.703-.59-1.202L18.75 4.97Zm-16.5.52c.99-.203 1.99-.377 3-.52m0 0 2.62 10.726c.122.499-.106 1.028-.589 1.202a5.989 5.989 0 0 1-2.031.352 5.989 5.989 0 0 1-2.031-.352c-.483-.174-.711-.703-.59-1.202L5.25 4.97Z" />
						</svg>
					</div>
					<div>
						<h1 class="text-2xl font-bold text-white">⚖️ 법률 정보 분석</h1>
						<p class="text-sm text-indigo-200/80">Legislation AI Agent</p>
					</div>
				</div>
				
				<!-- MCP 상태 & 새 채팅 & 히스토리 -->
				<div class="flex items-center gap-4">
					<!-- 히스토리 버튼 -->
					<button 
						class="flex items-center gap-2 text-xs px-3 py-1.5 rounded-full transition-all {showHistorySidebar ? 'bg-indigo-500/20 text-indigo-300 border border-indigo-500/30' : 'text-gray-400 hover:text-gray-200 hover:bg-gray-800/50 border border-gray-700/50'}"
						on:click={() => showHistorySidebar = !showHistorySidebar}
					>
						<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-4 h-4">
							<path stroke-linecap="round" stroke-linejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
						</svg>
						<span>히스토리</span>
					</button>
					
					<button 
						class="flex items-center gap-2 text-xs px-3 py-1.5 rounded-full text-gray-400 hover:text-gray-200 hover:bg-gray-800/50 border border-gray-700/50 transition-all"
						on:click={startNewChat}
					>
						<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-4 h-4">
							<path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
						</svg>
						<span>새 채팅</span>
					</button>
					
					{#if mcpStatus === 'checking'}
						<div class="flex items-center gap-2 text-xs text-gray-400 px-3 py-1.5 rounded-full bg-gray-800/60 border border-gray-700/50">
							<div class="w-2 h-2 rounded-full bg-yellow-400 animate-pulse"></div>
							<span>연결 확인 중...</span>
						</div>
					{:else if mcpStatus === 'connected'}
						<div class="flex items-center gap-2 text-xs text-indigo-400 px-3 py-1.5 rounded-full bg-indigo-500/20 border border-indigo-500/30">
							<div class="w-2 h-2 rounded-full bg-indigo-500"></div>
							<span>MCP 연결됨 ({mcpToolCount} tools)</span>
						</div>
					{:else if mcpStatus === 'degraded'}
						<div class="flex items-center gap-2 text-xs text-amber-300 px-3 py-1.5 rounded-full bg-amber-500/15 border border-amber-500/30">
							<div class="w-2 h-2 rounded-full bg-amber-400"></div>
							<span>MCP 부분 장애 ({mcpToolCount} tools)</span>
						</div>
					{:else}
						<div class="flex items-center gap-2 text-xs text-amber-400 px-3 py-1.5 rounded-full bg-amber-500/20 border border-amber-500/30">
							<div class="w-2 h-2 rounded-full bg-amber-500"></div>
							<span>MCP 오프라인</span>
						</div>
					{/if}
				</div>
			</div>
		</div>
	</div>
	
	<!-- 모델 선택 -->
	<div class="px-6 py-2 border-b border-gray-800/50 bg-gray-900/40 flex-shrink-0">
		<div class="flex items-center justify-end gap-2">
			<span class="text-xs text-gray-400">Model:</span>
			<select 
				bind:value={selectedModel}
				disabled={isLoading || loadingModels}
				class="px-3 py-1.5 text-sm rounded-lg bg-gray-800/60 border border-gray-700/50 text-white focus:outline-none focus:ring-1 focus:ring-indigo-500/50 disabled:opacity-50"
			>
				{#if loadingModels}
					<option value="">로딩 중...</option>
				{:else if availableModels.length === 0}
					<option value="claude-opus-4.5">claude-opus-4.5</option>
				{:else}
					{#each availableModels as model}
						<option value={model.model_name}>
							{model.model_name}
						</option>
					{/each}
				{/if}
			</select>
		</div>
	</div>
	
	<!-- 메인 콘텐츠 (좌우 분할 + 히스토리 사이드바) -->
	<div class="flex relative flex-1 overflow-hidden">
		<!-- 히스토리 사이드바 -->
		{#if showHistorySidebar}
			<div class="w-72 border-r border-gray-800/50 bg-gray-900/80 backdrop-blur-sm flex flex-col h-full">
				<div class="px-4 py-3 border-b border-gray-800/50 flex items-center justify-between">
					<h3 class="text-sm font-medium text-gray-300">채팅 기록</h3>
					<button 
						class="p-1 rounded hover:bg-gray-800/50 text-gray-400 hover:text-white transition-colors"
						on:click={() => showHistorySidebar = false}
					>
						<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-4 h-4">
							<path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
						</svg>
					</button>
				</div>
				<div class="px-3 py-2 border-b border-gray-800/50">
					<input
						type="text"
						placeholder="검색..."
						bind:value={historySearchQuery}
						on:input={() => searchHistories()}
						class="w-full px-3 py-1.5 text-sm rounded-lg bg-gray-800/60 border border-gray-700/50 text-white placeholder-gray-500 focus:outline-none focus:ring-1 focus:ring-indigo-500/50"
					/>
				</div>
				<div class="flex-1 overflow-y-auto">
					{#if histories.length === 0}
						<div class="p-4 text-center text-gray-500 text-sm">채팅 기록이 없습니다</div>
					{:else}
						{#each histories as history}
							<div 
								class="group px-3 py-2 border-b border-gray-800/30 hover:bg-gray-800/40 cursor-pointer transition-colors {currentHistoryId === history.id ? 'bg-indigo-500/10 border-l-2 border-l-indigo-500' : ''}"
								on:click={() => loadHistory(history.id)}
								on:keypress={(e) => e.key === 'Enter' && loadHistory(history.id)}
								role="button"
								tabindex="0"
							>
								<div class="flex items-start justify-between gap-2">
									<div class="flex-1 min-w-0">
										<p class="text-sm text-gray-200 truncate">{history.title}</p>
										<p class="text-xs text-gray-500 mt-1">{new Date(history.updated_at).toLocaleDateString('ko-KR')}</p>
									</div>
									<button
										class="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-red-500/20 text-gray-500 hover:text-red-400 transition-all"
										on:click|stopPropagation={() => deleteHistory(history.id)}
									>
										<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-3.5 h-3.5">
											<path stroke-linecap="round" stroke-linejoin="round" d="m14.74 9-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 0 1-2.244 2.077H8.084a2.25 2.25 0 0 1-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 0 0-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 0 1 3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 0 0-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 0 0-7.5 0" />
										</svg>
									</button>
								</div>
							</div>
						{/each}
					{/if}
				</div>
			</div>
		{/if}
		
		<!-- 좌측: 채팅 영역 -->
		<div class="flex-1 flex flex-col border-r border-gray-800/50 h-full relative" style="max-width: {showHistorySidebar ? 'calc(50% - 144px)' : '50%'}">
			<!-- 채팅 헤더 -->
			<div class="px-4 py-3 border-b border-gray-800/50 bg-gray-900/60 backdrop-blur-sm">
				<div class="flex items-center gap-2 text-sm text-gray-300">
					<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-4 h-4">
						<path stroke-linecap="round" stroke-linejoin="round" d="M8.625 12a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0H8.25m4.125 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0H12m4.125 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0h-.375M21 12c0 4.556-4.03 8.25-9 8.25a9.764 9.764 0 0 1-2.555-.337A5.972 5.972 0 0 1 5.41 20.97a5.969 5.969 0 0 1-.474-.065 4.48 4.48 0 0 0 .978-2.025c.09-.457-.133-.901-.467-1.226C3.93 16.178 3 14.189 3 12c0-4.556 4.03-8.25 9-8.25s9 3.694 9 8.25Z" />
					</svg>
					<span class="font-medium">에이전트 로그</span>
					{#if isLoading}
						<span class="ml-auto flex items-center gap-1.5 text-indigo-400">
							<span class="relative flex h-2 w-2">
								<span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-indigo-400 opacity-75"></span>
								<span class="relative inline-flex rounded-full h-2 w-2 bg-indigo-500"></span>
							</span>
							분석 중...
						</span>
					{/if}
				</div>
			</div>
			
			<!-- 메시지 목록 -->
			<div bind:this={messagesContainer} class="flex-1 overflow-y-auto px-4 py-4 pb-40 space-y-3 bg-gray-950">
				{#each messages as message (message.id)}
					<div 
						class="flex {message.role === 'user' ? 'justify-end' : 'justify-start'}"
						in:fly={{ y: 10, duration: 200 }}
					>
						{#if message.role === 'system'}
							<div class="max-w-[90%] p-3 rounded-xl bg-gray-800/60 backdrop-blur-sm border border-gray-700/50 text-sm">
								<p class="text-gray-300 whitespace-pre-wrap">{message.content}</p>
							</div>
						{:else if message.role === 'user'}
							<div class="max-w-[85%] px-4 py-2.5 rounded-2xl bg-gradient-to-r from-indigo-500 to-violet-500 text-white text-sm shadow-md shadow-indigo-500/20">
								<p class="whitespace-pre-wrap">{message.content}</p>
							</div>
						{:else if message.role === 'tool'}
							<div class="max-w-[90%] px-3 py-2 rounded-lg bg-purple-500/20 border border-purple-500/30 text-sm">
								<div class="flex items-center gap-2 text-purple-300">
									<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-4 h-4">
										<path stroke-linecap="round" stroke-linejoin="round" d="M11.42 15.17 17.25 21A2.652 2.652 0 0 0 21 17.25l-5.877-5.877M11.42 15.17l2.496-3.03c.317-.384.74-.626 1.208-.766M11.42 15.17l-4.655 5.653a2.548 2.548 0 1 1-3.586-3.586l6.837-5.63m5.108-.233c.55-.164 1.163-.188 1.743-.14a4.5 4.5 0 0 0 4.486-6.336l-3.276 3.277a3.004 3.004 0 0 1-2.25-2.25l3.276-3.276a4.5 4.5 0 0 0-6.336 4.486c.091 1.076-.071 2.264-.904 2.95l-.102.085m-1.745 1.437L5.909 7.5H4.5L2.25 3.75l1.5-1.5L7.5 4.5v1.409l4.26 4.26m-1.745 1.437 1.745-1.437m6.615 8.206L15.75 15.75M4.867 19.125h.008v.008h-.008v-.008Z" />
									</svg>
									<span class="truncate">{message.content}</span>
								</div>
							</div>
						{:else}
							<div class="max-w-[90%] px-3 py-2 rounded-xl bg-gray-800/60 backdrop-blur-sm border border-gray-700/50 shadow-sm text-sm">
								<Markdown id={message.id} content={message.content} />
							</div>
						{/if}
					</div>
				{/each}
				
				{#if currentToolCall}
					<div class="flex justify-start" in:fade={{ duration: 150 }}>
						<div class="px-3 py-2 rounded-lg bg-amber-500/20 border border-amber-500/30 text-sm">
							<div class="flex items-center gap-2 text-amber-300">
								<svg class="animate-spin w-4 h-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
									<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
									<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
								</svg>
								<span>{currentToolCall}</span>
							</div>
						</div>
					</div>
				{/if}
			</div>
			
			<!-- 입력 영역 -->
			<div class="absolute bottom-0 left-0 right-0 border-t border-gray-800/50 bg-gray-900/95 backdrop-blur-md p-4">
				{#if messages.length <= 1}
					<div class="mb-3 flex flex-wrap gap-2">
						{#each exampleQuestions as q}
							<button
								class="px-2.5 py-1 rounded-lg text-xs bg-gray-800/60 hover:bg-gray-700/60 text-gray-300 transition-colors border border-gray-700/50"
								on:click={() => { inputValue = q; sendMessage(); }}
							>
								{q}
							</button>
						{/each}
					</div>
				{/if}
				
				<form on:submit|preventDefault={sendMessage} class="flex items-end gap-2">
					<div class="flex-1 relative">
						<textarea
							bind:value={inputValue}
							on:keydown={handleKeydown}
							placeholder="법률 정보에 대해 질문하세요..."
							rows="1"
							disabled={isLoading}
							class="w-full resize-none rounded-xl border border-gray-700/50 bg-gray-800/60 backdrop-blur-sm px-4 py-2.5 text-sm text-white placeholder-gray-400 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 transition-all disabled:opacity-50"
							style="min-height: 42px; max-height: 120px;"
						></textarea>
					</div>
					
					<button
						type="submit"
						disabled={!inputValue.trim() || isLoading}
						class="flex-shrink-0 p-2.5 rounded-xl bg-gradient-to-r from-indigo-500 to-violet-500 text-white shadow-md shadow-indigo-500/20 hover:shadow-lg disabled:opacity-50 disabled:cursor-not-allowed transition-all"
					>
						{#if isLoading}
							<svg class="animate-spin w-5 h-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
								<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
								<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
							</svg>
						{:else}
							<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2" stroke="currentColor" class="w-5 h-5">
								<path stroke-linecap="round" stroke-linejoin="round" d="M6 12 3.269 3.125A59.769 59.769 0 0 1 21.485 12 59.768 59.768 0 0 1 3.27 20.875L5.999 12Zm0 0h7.5" />
							</svg>
						{/if}
					</button>
				</form>
			</div>
		</div>
		
		<!-- 우측: 분석 레포트 -->
		<div class="w-1/2 flex flex-col bg-gray-950 h-full overflow-hidden">
			<!-- 레포트 헤더 -->
			<div class="px-6 py-3 border-b border-gray-800/50 bg-gray-900/60 backdrop-blur-sm">
				<div class="flex items-center justify-between">
					<div class="flex items-center gap-2 text-sm text-gray-300">
						<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-4 h-4">
							<path stroke-linecap="round" stroke-linejoin="round" d="M9 12h3.75M9 15h3.75M9 18h3.75m3 .75H18a2.25 2.25 0 0 0 2.25-2.25V6.108c0-1.135-.845-2.098-1.976-2.192a48.424 48.424 0 0 0-1.123-.08m-5.801 0c-.065.21-.1.433-.1.664 0 .414.336.75.75.75h4.5a.75.75 0 0 0 .75-.75 2.25 2.25 0 0 0-.1-.664m-5.8 0A2.251 2.251 0 0 1 13.5 2.25H15c1.012 0 1.867.668 2.15 1.586m-5.8 0c-.376.023-.75.05-1.124.08C9.095 4.01 8.25 4.973 8.25 6.108V8.25m0 0H4.875c-.621 0-1.125.504-1.125 1.125v11.25c0 .621.504 1.125 1.125 1.125h9.75c.621 0 1.125-.504 1.125-1.125V9.375c0-.621-.504-1.125-1.125-1.125H8.25ZM6.75 12h.008v.008H6.75V12Zm0 3h.008v.008H6.75V15Zm0 3h.008v.008H6.75V18Z" />
						</svg>
						<span class="font-medium">분석 레포트</span>
					</div>
					
					{#if report && report.latency_ms > 0}
						<div class="flex items-center gap-3 text-xs text-gray-400">
							<span>{report.tokens.total.toLocaleString()} tokens</span>
							<span>{(report.latency_ms / 1000).toFixed(1)}s</span>
						</div>
					{/if}
				</div>
			</div>
			
			<!-- 레포트 내용 -->
			<div bind:this={reportContainer} class="flex-1 overflow-y-auto bg-gray-950">
				{#if report && (report.summary || report.sections.length > 0)}
					<div class="p-6 space-y-6" in:fade={{ duration: 300 }}>
						<!-- 헤더 -->
						<div class="flex items-center gap-3 pb-4 border-b border-gray-800/50">
							<div class="w-12 h-12 rounded-xl bg-gradient-to-br from-indigo-500 to-violet-600 flex items-center justify-center shadow-lg shadow-indigo-500/20">
								<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-6 h-6 text-white">
									<path stroke-linecap="round" stroke-linejoin="round" d="M12 3v17.25m0 0c-1.472 0-2.882.265-4.185.75M12 20.25c1.472 0 2.882.265 4.185.75M18.75 4.97A48.416 48.416 0 0 0 12 4.5c-2.291 0-4.545.16-6.75.47m13.5 0c1.01.143 2.01.317 3 .52m-3-.52 2.62 10.726c.122.499-.106 1.028-.589 1.202a5.988 5.988 0 0 1-2.031.352 5.988 5.988 0 0 1-2.031-.352c-.483-.174-.711-.703-.59-1.202L18.75 4.97Zm-16.5.52c.99-.203 1.99-.377 3-.52m0 0 2.62 10.726c.122.499-.106 1.028-.589 1.202a5.989 5.989 0 0 1-2.031.352 5.989 5.989 0 0 1-2.031-.352c-.483-.174-.711-.703-.59-1.202L5.25 4.97Z" />
								</svg>
							</div>
							<div>
								<h2 class="text-xl font-bold text-white">
									{report.title || '법률 정보 분석 결과'}
								</h2>
								<p class="text-sm text-gray-400">Legislation Analysis Report</p>
							</div>
						</div>
						
						<!-- 사용된 도구 -->
						{#if report.toolsUsed.length > 0}
							<div class="flex flex-wrap gap-2">
								{#each [...new Set(report.toolsUsed)] as tool}
									<span class="px-2 py-1 text-xs rounded-md bg-purple-500/20 text-purple-300 border border-purple-500/30">
										{tool}
									</span>
								{/each}
							</div>
						{/if}
						
						<!-- 섹션들 -->
						{#each report.sections as section, i}
							<div class="space-y-3" in:fly={{ y: 20, duration: 300, delay: i * 100 }}>
								<h3 class="flex items-center gap-2 text-lg font-semibold text-white">
									<span class="w-6 h-6 rounded-md bg-indigo-500/20 text-indigo-400 flex items-center justify-center text-sm font-bold border border-indigo-500/30">
										{i + 1}
									</span>
									{section.title}
								</h3>
								<div class="pl-8">
									<article class="prose prose-sm max-w-none prose-invert prose-headings:text-white prose-p:text-slate-300 prose-strong:text-white prose-code:text-slate-300 prose-pre:text-slate-200 prose-blockquote:text-slate-300 prose-li:text-slate-300 prose-a:text-indigo-400 
									prose-table:text-slate-200
									prose-thead:bg-gray-800 prose-thead:text-white
									prose-th:border prose-th:border-gray-600 prose-th:px-3 prose-th:py-2 prose-th:text-left prose-th:font-semibold
									prose-td:border prose-td:border-gray-700 prose-td:px-3 prose-td:py-2
									prose-tr:bg-gray-900/50 prose-tr:even:bg-gray-800/50">
										<Markdown id={`legislation-report-${i}`} content={section.content.trim()} />
									</article>
								</div>
							</div>
						{/each}
						
						<!-- 스트리밍 중 표시 -->
						{#if reportStreaming}
							<div class="flex items-center gap-2 text-sm text-indigo-400 pl-8" in:fade>
								<div class="flex space-x-1">
									<div class="w-2 h-2 rounded-full bg-indigo-500 animate-bounce" style="animation-delay: 0ms"></div>
									<div class="w-2 h-2 rounded-full bg-indigo-500 animate-bounce" style="animation-delay: 150ms"></div>
									<div class="w-2 h-2 rounded-full bg-indigo-500 animate-bounce" style="animation-delay: 300ms"></div>
								</div>
								<span>레포트 생성 중...</span>
							</div>
						{/if}
					</div>
				{:else}
					<!-- 빈 상태 -->
					<div class="flex-1 flex items-center justify-center h-full">
						<div class="text-center px-6 py-12">
							<div class="w-20 h-20 mx-auto mb-6 rounded-2xl bg-gray-800/60 backdrop-blur-sm border border-gray-700/50 flex items-center justify-center">
								<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1" stroke="currentColor" class="w-10 h-10 text-gray-500">
									<path stroke-linecap="round" stroke-linejoin="round" d="M12 3v17.25m0 0c-1.472 0-2.882.265-4.185.75M12 20.25c1.472 0 2.882.265 4.185.75M18.75 4.97A48.416 48.416 0 0 0 12 4.5c-2.291 0-4.545.16-6.75.47m13.5 0c1.01.143 2.01.317 3 .52m-3-.52 2.62 10.726c.122.499-.106 1.028-.589 1.202a5.988 5.988 0 0 1-2.031.352 5.988 5.988 0 0 1-2.031-.352c-.483-.174-.711-.703-.59-1.202L18.75 4.97Zm-16.5.52c.99-.203 1.99-.377 3-.52m0 0 2.62 10.726c.122.499-.106 1.028-.589 1.202a5.989 5.989 0 0 1-2.031.352 5.989 5.989 0 0 1-2.031-.352c-.483-.174-.711-.703-.59-1.202L5.25 4.97Z" />
								</svg>
							</div>
							<h3 class="text-lg font-semibold text-gray-300 mb-2">
								분석 레포트가 여기에 표시됩니다
							</h3>
							<p class="text-sm text-gray-400 max-w-sm mx-auto">
								좌측에서 법률 정보에 대해 질문하시면, AI가 분석한 결과가 구조화된 레포트로 나타납니다.
							</p>
						</div>
					</div>
				{/if}
			</div>
		</div>
	</div>
</div>
