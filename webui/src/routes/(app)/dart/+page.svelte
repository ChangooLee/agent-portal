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
		intent?: {
			domain: string;
			company_name?: string;
		};
	}
	
	interface AnalysisReport {
		company_name: string | null;
		domain: string;
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
	
	// 탭 상태
	type ModelTab = 'qwen-235b' | 'opus-single' | 'opus-multi';
	let activeTab: ModelTab = 'qwen-235b';
	
	// 탭별 엔드포인트 매핑
	function getEndpointForTab(tab: ModelTab): string {
		switch (tab) {
			case 'qwen-235b': return '/api/dart/chat/stream';
			case 'opus-single': return '/api/dart/chat/single';
			case 'opus-multi': return '/api/dart/chat/multi-opus';
		}
	}
	
	// 히스토리 사이드바 상태
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
	
	// 히스토리 목록 로드
	async function loadHistories() {
		try {
			const response = await fetch('/api/dart/history');
			if (response.ok) {
				const data = await response.json();
				histories = data.histories || [];
			}
		} catch (e) {
			console.error('Failed to load histories:', e);
		}
	}
	
	// 히스토리 검색
	async function searchHistories() {
		if (!historySearchQuery.trim()) {
			await loadHistories();
			return;
		}
		try {
			const response = await fetch(`/api/dart/history/search?query=${encodeURIComponent(historySearchQuery)}`);
			if (response.ok) {
				const data = await response.json();
				histories = data.histories || [];
			}
		} catch (e) {
			console.error('Failed to search histories:', e);
		}
	}
	
	// 히스토리 저장
	async function saveHistory() {
		if (messages.length <= 1) return; // 시스템 메시지만 있으면 저장 안함
		
		const userMessages = messages.filter(m => m.role === 'user');
		if (userMessages.length === 0) return;
		
		const title = userMessages[0].content.slice(0, 50) + (userMessages[0].content.length > 50 ? '...' : '');
		
		try {
			if (currentHistoryId) {
				// 기존 히스토리 업데이트
				await fetch(`/api/dart/history/${currentHistoryId}`, {
					method: 'PUT',
					headers: { 'Content-Type': 'application/json' },
					body: JSON.stringify({ messages })
				});
			} else {
				// 새 히스토리 생성
				const response = await fetch('/api/dart/history', {
					method: 'POST',
					headers: { 'Content-Type': 'application/json' },
					body: JSON.stringify({ title, messages, model_tab: activeTab })
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
	
	// 히스토리 불러오기
	async function loadHistory(historyId: string) {
		loadingHistory = true;
		try {
			const response = await fetch(`/api/dart/history/${historyId}`);
			if (response.ok) {
				const data = await response.json();
				messages = data.history?.messages || [];
				currentHistoryId = historyId;
				activeTab = data.history?.model_tab || 'qwen-235b';
				showHistorySidebar = false;
			}
		} catch (e) {
			console.error('Failed to load history:', e);
		} finally {
			loadingHistory = false;
		}
	}
	
	// 히스토리 삭제
	async function deleteHistory(historyId: string) {
		if (!confirm('이 대화 기록을 삭제하시겠습니까?')) return;
		
		try {
			await fetch(`/api/dart/history/${historyId}`, { method: 'DELETE' });
			histories = histories.filter(h => h.id !== historyId);
			if (currentHistoryId === historyId) {
				currentHistoryId = null;
				startNewChat();
			}
		} catch (e) {
			console.error('Failed to delete history:', e);
		}
	}
	
	// 새 채팅 시작
	function startNewChat() {
		currentHistoryId = null;
		messages = [{
			id: 'system-welcome',
			role: 'system',
			content: '안녕하세요! DART 기업공시 분석 에이전트입니다.\n기업의 공시 정보, 재무제표, 지배구조 등에 대해 질문해 주세요.',
			timestamp: new Date()
		}];
		report = null;
	}
	
	// 분석 레포트
	let report: AnalysisReport | null = null;
	let reportStreaming = false;
	
	// 헬스체크
	let mcpStatus: 'checking' | 'connected' | 'degraded' | 'error' = 'checking';
	let mcpToolCount = 0;
	let mcpToolsCallable = false;
	let mcpHealthError = '';
	
	async function checkHealth() {
		try {
			const response = await fetch('/api/dart/health');
			const data = await response.json();
			
			mcpToolCount = data.mcp_tools || 0;
			mcpToolsCallable = Boolean(data.mcp_tools_callable);
			mcpHealthError = data.mcp_error || '';

			if (data.status === 'ok' && data.mcp_connected && mcpToolsCallable) {
				mcpStatus = 'connected';
				return;
			}

			if (data.mcp_connected) {
				// Connected but not callable -> degraded
				mcpStatus = 'degraded';
				return;
			}

			mcpStatus = 'error';
		} catch (error) {
			mcpStatus = 'error';
			mcpToolCount = 0;
			mcpToolsCallable = false;
			mcpHealthError = '';
		}
	}
	
	onMount(() => {
		checkHealth();
		loadHistories();
		
		// 시스템 메시지 추가
		messages = [{
			id: 'system-welcome',
			role: 'system',
			content: '안녕하세요! DART 기업공시 분석 에이전트입니다.\n기업의 공시 정보, 재무제표, 지배구조 등에 대해 질문해 주세요.',
			timestamp: new Date()
		}];
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
				// 첫 번째 섹션 전의 내용
				if (!currentSection) {
					currentSection = { title: '요약', content: line + '\n' };
				}
			}
		}
		
		if (currentSection) {
			sections.push(currentSection);
		}
		
		// 섹션이 없으면 전체 내용을 하나의 섹션으로
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
			company_name: null,
			domain: '',
			summary: '',
			sections: [],
			toolsUsed: [],
			tokens: { prompt: 0, completion: 0, total: 0 },
			latency_ms: 0,
			timestamp: new Date()
		};
		
		setTimeout(scrollToBottom, 50);
		
		try {
			// #region agent log
			fetch('http://127.0.0.1:7242/ingest/2a63104a-f45f-4098-b5e6-fe6cbc3b98a1',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'dart/+page.svelte:158',message:'Starting SSE fetch',data:{question_length:question.length},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'F'})}).catch(()=>{});
			// #endregion
			
			// SSE 스트리밍 (탭에 따른 엔드포인트)
			const endpoint = getEndpointForTab(activeTab);
			const response = await fetch(endpoint, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ question })
			});
			
			// #region agent log
			fetch('http://127.0.0.1:7242/ingest/2a63104a-f45f-4098-b5e6-fe6cbc3b98a1',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'dart/+page.svelte:166',message:'Fetch response received',data:{ok:response.ok,status:response.status,contentType:response.headers.get('content-type')},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'F'})}).catch(()=>{});
			// #endregion
			
			if (!response.ok) {
				throw new Error('API 요청 실패');
			}
			
			const reader = response.body?.getReader();
			const decoder = new TextDecoder();
			
			if (!reader) {
				throw new Error('스트림을 읽을 수 없습니다');
			}
			
			// #region agent log
			fetch('http://127.0.0.1:7242/ingest/2a63104a-f45f-4098-b5e6-fe6cbc3b98a1',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'dart/+page.svelte:175',message:'Starting to read stream',data:{},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'D'})}).catch(()=>{});
			// #endregion
			
			let buffer = '';
			let chunk_count = 0;
			
			while (true) {
				const { done, value } = await reader.read();
				if (done) break;
				
				chunk_count++;
				buffer += decoder.decode(value, { stream: true });
				const lines = buffer.split('\n\n');
				buffer = lines.pop() || '';
				
				// #region agent log
				if (chunk_count <= 3) {
					fetch('http://127.0.0.1:7242/ingest/2a63104a-f45f-4098-b5e6-fe6cbc3b98a1',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'dart/+page.svelte:185',message:'Chunk received',data:{chunk_count,lines_count:lines.length,buffer_length:buffer.length},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'D'})}).catch(()=>{});
				}
				// #endregion
				
				for (const line of lines) {
					if (!line.startsWith('data: ')) continue;
					
					// #region agent log
					fetch('http://127.0.0.1:7242/ingest/2a63104a-f45f-4098-b5e6-fe6cbc3b98a1',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'dart/+page.svelte:192',message:'Parsing SSE line',data:{line_length:line.length,line_preview:line.substring(0,100)},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'D'})}).catch(()=>{});
					// #endregion
					
					try {
						const data = JSON.parse(line.slice(6));
						
						// #region agent log
						fetch('http://127.0.0.1:7242/ingest/2a63104a-f45f-4098-b5e6-fe6cbc3b98a1',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'dart/+page.svelte:196',message:'SSE data parsed',data:{event:data.event},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'D'})}).catch(()=>{});
						// #endregion
						
						switch (data.event) {
							case 'start':
								messages = [...messages, {
									id: generateId(),
									role: 'assistant',
									content: data.content || '🔍 분석을 시작합니다...',
									timestamp: new Date()
								}];
								break;
								
							case 'analyzing':
								currentToolCall = data.message || '분석 중...';
								break;
								
							case 'intent_classified':
								if (report) {
									report.domain = data.domain;
									report.company_name = data.company_name;
								}
								messages = [...messages, {
									id: generateId(),
									role: 'assistant',
									content: `📋 의도 분류 완료: ${getDomainLabel(data.domain)}${data.company_name ? ` (${data.company_name})` : ''}`,
									timestamp: new Date(),
									intent: { domain: data.domain, company_name: data.company_name }
								}];
								break;
								
							case 'iteration':
								currentToolCall = `반복 ${data.iteration}...`;
								break;
								
							case 'tool_start':
								currentToolCall = `🔧 ${data.tool} 실행 중...`;
								messages = [...messages, {
									id: generateId(),
									role: 'tool',
									content: `${data.tool} 도구 호출 중...`,
									toolName: data.tool,
									timestamp: new Date()
								}];
								break;
								
							case 'tool_end':
								if (report && data.tool) {
									report.toolsUsed = [...report.toolsUsed, data.tool];
								}
								// 마지막 tool 메시지 업데이트
								messages = messages.map((m, i) => {
									if (i === messages.length - 1 && m.role === 'tool') {
										return { ...m, content: `✅ ${data.tool}: ${data.result?.substring(0, 100)}...` };
									}
									return m;
								});
								break;
								
							case 'content':
								// 스트리밍 콘텐츠 - 레포트에 누적
								if (report && data.content) {
									report.summary = (report.summary || '') + data.content;
									report.sections = parseMarkdownToSections(report.summary);
								}
								break;
								
							case 'answer':
								// 최종 답변 - 레포트에 추가
								if (report) {
									report.summary = data.content;
									report.sections = parseMarkdownToSections(data.content);
								}
								messages = [...messages, {
									id: generateId(),
									role: 'assistant',
									content: '✨ 분석이 완료되었습니다. 우측 레포트를 확인해주세요.',
									timestamp: new Date()
								}];
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
								// 분석 완료 - 레포트 표시
								if (report && report.summary) {
									// 레포트가 이미 채워져 있으면 완료 메시지 추가
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
								
							case 'error':
								toast.error(data.error || '오류가 발생했습니다');
								messages = [...messages, {
									id: generateId(),
									role: 'assistant',
									content: `❌ 오류: ${data.error}`,
									timestamp: new Date()
								}];
								reportStreaming = false;
								currentToolCall = null;
								break;
						}
						
						setTimeout(scrollToBottom, 50);
						
					} catch (e) {
						console.error('SSE parse error:', e);
						// #region agent log
						fetch('http://127.0.0.1:7242/ingest/2a63104a-f45f-4098-b5e6-fe6cbc3b98a1',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'dart/+page.svelte:293',message:'SSE parse error',data:{error:String(e),line_preview:line.substring(0,100)},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'D'})}).catch(()=>{});
						// #endregion
					}
				}
			}
			
		} catch (error) {
			console.error('Stream error:', error);
			// #region agent log
			fetch('http://127.0.0.1:7242/ingest/2a63104a-f45f-4098-b5e6-fe6cbc3b98a1',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'dart/+page.svelte:298',message:'Stream error caught',data:{error_type:error?.constructor?.name,error_message:String(error)},timestamp:Date.now(),sessionId:'debug-session',runId:'run1',hypothesisId:'E'})}).catch(()=>{});
			// #endregion
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
			// 히스토리 저장
			saveHistory();
		}
	}
	
	function handleKeydown(e: KeyboardEvent) {
		if (e.key === 'Enter' && !e.shiftKey) {
			e.preventDefault();
			sendMessage();
		}
	}
	
	function getDomainLabel(domain: string): string {
		const labels: Record<string, string> = {
			'financial': '재무 분석',
			'governance': '지배구조',
			'business_structure': '사업구조',
			'capital_change': '자본변동',
			'debt_funding': '부채/자금조달',
			'overseas_business': '해외사업',
			'legal_compliance': '법률/규정',
			'executive_audit': '임원/감사',
			'document_analysis': '문서분석',
			'general': '일반 질문'
		};
		return labels[domain] || domain;
	}
	
	// 예시 질문
	const exampleQuestions = [
		'삼성전자 최근 공시 분석해줘',
		'현대자동차 재무제표 요약',
		'네이버 지배구조 현황',
		'SK하이닉스 자본변동 분석'
	];
</script>

<svelte:head>
	<title>기업공시분석 | DART Agent</title>
</svelte:head>

<div class="min-h-screen bg-gray-950 text-slate-50">
	<!-- Hero Section -->
	<div class="relative overflow-hidden border-b border-slate-800/50">
		<div class="absolute inset-0 bg-gradient-to-br from-emerald-600/5 via-transparent to-teal-600/5"></div>
		<div class="absolute inset-0 bg-[linear-gradient(rgba(16,185,129,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(16,185,129,0.03)_1px,transparent_1px)] bg-[size:64px_64px]"></div>
		
		<div class="relative px-6 py-6">
			<div class="flex items-center justify-between">
				<div class="flex items-center gap-3">
					<div class="w-12 h-12 rounded-xl bg-gradient-to-br from-emerald-500 to-teal-600 flex items-center justify-center shadow-lg shadow-emerald-500/20">
						<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-6 h-6 text-white">
							<path stroke-linecap="round" stroke-linejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z" />
						</svg>
					</div>
					<div>
						<h1 class="text-2xl font-bold text-white">📊 기업공시분석</h1>
						<p class="text-sm text-emerald-200/80">DART AI Agent</p>
					</div>
				</div>
				
				<!-- 히스토리 & MCP 상태 -->
				<div class="flex items-center gap-4">
					<!-- 히스토리 토글 버튼 -->
					<button 
						class="flex items-center gap-2 text-xs px-3 py-1.5 rounded-full transition-all {showHistorySidebar ? 'bg-blue-500/20 text-blue-300 border border-blue-500/30' : 'text-gray-400 hover:text-gray-200 hover:bg-gray-800/50 border border-gray-700/50'}"
						on:click={() => showHistorySidebar = !showHistorySidebar}
					>
						<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-4 h-4">
							<path stroke-linecap="round" stroke-linejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
						</svg>
						<span>기록</span>
						{#if histories.length > 0}
							<span class="bg-gray-700/50 px-1.5 py-0.5 rounded text-[10px]">{histories.length}</span>
						{/if}
					</button>
					
					<!-- 새 채팅 버튼 -->
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
						<div class="flex items-center gap-2 text-xs text-emerald-400 px-3 py-1.5 rounded-full bg-emerald-500/20 border border-emerald-500/30">
							<div class="w-2 h-2 rounded-full bg-emerald-500"></div>
							<span>MCP 연결됨 ({mcpToolCount} tools)</span>
						</div>
					{:else if mcpStatus === 'degraded'}
						<div
							class="flex items-center gap-2 text-xs text-amber-300 px-3 py-1.5 rounded-full bg-amber-500/15 border border-amber-500/30"
							title={mcpHealthError || 'MCP는 연결되었지만 tools/call 실행이 실패했습니다.'}
						>
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
	
	<!-- 탭 UI -->
	<div class="px-6 py-2 border-b border-gray-800/50 bg-gray-900/40">
		<div class="flex items-center gap-1">
			<button 
				class="px-4 py-2 text-sm rounded-lg transition-all {activeTab === 'qwen-235b' ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30' : 'text-gray-400 hover:text-gray-200 hover:bg-gray-800/50'}"
				on:click={() => activeTab = 'qwen-235b'}
			>
				Qwen 235B
			</button>
			<button 
				class="px-4 py-2 text-sm rounded-lg transition-all {activeTab === 'opus-single' ? 'bg-purple-500/20 text-purple-300 border border-purple-500/30' : 'text-gray-400 hover:text-gray-200 hover:bg-gray-800/50'}"
				on:click={() => activeTab = 'opus-single'}
			>
				Opus 4.5 Single
			</button>
			<button 
				class="px-4 py-2 text-sm rounded-lg transition-all {activeTab === 'opus-multi' ? 'bg-blue-500/20 text-blue-300 border border-blue-500/30' : 'text-gray-400 hover:text-gray-200 hover:bg-gray-800/50'}"
				on:click={() => activeTab = 'opus-multi'}
			>
				Opus 4.5 Multi
			</button>
		</div>
	</div>
	
	<!-- 메인 콘텐츠 (좌우 분할 + 사이드바) -->
	<div class="flex relative h-[calc(100vh-160px)]">
		<!-- 히스토리 사이드바 -->
		{#if showHistorySidebar}
			<div class="w-72 border-r border-gray-800/50 bg-gray-900/80 backdrop-blur-sm flex flex-col h-[calc(100vh-160px)]">
				<!-- 사이드바 헤더 -->
				<div class="p-3 border-b border-gray-800/50">
					<div class="flex items-center justify-between mb-2">
						<span class="text-sm font-medium text-gray-200">대화 기록</span>
						<button 
							class="p-1 rounded hover:bg-gray-800/50 text-gray-400 hover:text-white transition-colors"
							on:click={() => showHistorySidebar = false}
						>
							<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-4 h-4">
								<path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
							</svg>
						</button>
					</div>
					<!-- 검색 -->
					<div class="relative">
						<input 
							type="text" 
							placeholder="검색..." 
							bind:value={historySearchQuery}
							on:input={searchHistories}
							class="w-full px-3 py-1.5 text-sm bg-gray-800/50 border border-gray-700/50 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:ring-1 focus:ring-emerald-500/50"
						/>
						<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-4 h-4 absolute right-3 top-1/2 -translate-y-1/2 text-gray-500">
							<path stroke-linecap="round" stroke-linejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" />
						</svg>
					</div>
				</div>
				
				<!-- 히스토리 목록 -->
				<div class="flex-1 overflow-y-auto">
					{#if histories.length === 0}
						<div class="p-4 text-center text-gray-500 text-sm">
							저장된 대화가 없습니다
						</div>
					{:else}
						{#each histories as history (history.id)}
							<div 
								class="group px-3 py-2 border-b border-gray-800/30 hover:bg-gray-800/40 cursor-pointer transition-colors {currentHistoryId === history.id ? 'bg-emerald-500/10 border-l-2 border-l-emerald-500' : ''}"
								on:click={() => loadHistory(history.id)}
								on:keypress={(e) => e.key === 'Enter' && loadHistory(history.id)}
								role="button"
								tabindex="0"
							>
								<div class="flex items-start justify-between gap-2">
									<div class="flex-1 min-w-0">
										<div class="text-sm text-gray-200 truncate">{history.title}</div>
										<div class="flex items-center gap-2 mt-1">
											<span class="text-[10px] px-1.5 py-0.5 rounded bg-gray-700/50 text-gray-400">{history.model_tab}</span>
											<span class="text-[10px] text-gray-500">
												{new Date(history.updated_at).toLocaleDateString('ko-KR', { month: 'short', day: 'numeric' })}
											</span>
										</div>
									</div>
									<button 
										class="opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-red-500/20 text-gray-400 hover:text-red-400 transition-all"
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
		<div class="flex-1 flex flex-col border-r border-gray-800/50 h-full overflow-hidden relative" style="max-width: {showHistorySidebar ? 'calc(50% - 144px)' : '50%'}">
			<!-- 채팅 헤더 -->
			<div class="px-4 py-3 border-b border-gray-800/50 bg-gray-900/60 backdrop-blur-sm">
				<div class="flex items-center gap-2 text-sm text-gray-300">
					<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-4 h-4">
						<path stroke-linecap="round" stroke-linejoin="round" d="M8.625 12a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0H8.25m4.125 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0H12m4.125 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0h-.375M21 12c0 4.556-4.03 8.25-9 8.25a9.764 9.764 0 0 1-2.555-.337A5.972 5.972 0 0 1 5.41 20.97a5.969 5.969 0 0 1-.474-.065 4.48 4.48 0 0 0 .978-2.025c.09-.457-.133-.901-.467-1.226C3.93 16.178 3 14.189 3 12c0-4.556 4.03-8.25 9-8.25s9 3.694 9 8.25Z" />
					</svg>
					<span class="font-medium">에이전트 로그</span>
					{#if isLoading}
						<span class="ml-auto flex items-center gap-1.5 text-emerald-400">
							<span class="relative flex h-2 w-2">
								<span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
								<span class="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
							</span>
							분석 중...
						</span>
					{/if}
				</div>
			</div>
			
			<!-- 메시지 목록 -->
			<div bind:this={messagesContainer} class="flex-1 overflow-y-auto px-4 py-4 pb-32 space-y-3 bg-gray-950">
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
							<div class="max-w-[85%] px-4 py-2.5 rounded-2xl bg-gradient-to-r from-emerald-500 to-teal-500 text-white text-sm shadow-md shadow-emerald-500/20">
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
								<p class="text-gray-300 whitespace-pre-wrap">{message.content}</p>
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
			
			<!-- 입력 영역 (최하단 고정) -->
			<div class="sticky bottom-0 z-10 border-t border-gray-800/50 bg-gray-900/60 backdrop-blur-sm p-4">
				<!-- 예시 질문 -->
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
				
				<!-- 입력 폼 -->
				<form on:submit|preventDefault={sendMessage} class="flex items-end gap-2">
					<div class="flex-1 relative">
						<textarea
							bind:value={inputValue}
							on:keydown={handleKeydown}
							placeholder="기업 공시에 대해 질문하세요..."
							rows="1"
							disabled={isLoading}
							class="w-full resize-none rounded-xl border border-gray-700/50 bg-gray-800/60 backdrop-blur-sm px-4 py-2.5 text-sm text-white placeholder-gray-400 focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/20 transition-all disabled:opacity-50"
							style="min-height: 42px; max-height: 120px;"
						></textarea>
					</div>
					
					<button
						type="submit"
						disabled={!inputValue.trim() || isLoading}
						class="flex-shrink-0 p-2.5 rounded-xl bg-gradient-to-r from-emerald-500 to-teal-500 text-white shadow-md shadow-emerald-500/20 hover:shadow-lg disabled:opacity-50 disabled:cursor-not-allowed transition-all"
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
						<!-- 회사 정보 헤더 -->
						{#if report.company_name || report.domain}
							<div class="flex items-center gap-3 pb-4 border-b border-gray-800/50">
								<div class="w-12 h-12 rounded-xl bg-gradient-to-br from-emerald-500 to-teal-600 flex items-center justify-center shadow-lg shadow-emerald-500/20">
									<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-6 h-6 text-white">
										<path stroke-linecap="round" stroke-linejoin="round" d="M2.25 21h19.5m-18-18v18m10.5-18v18m6-13.5V21M6.75 6.75h.75m-.75 3h.75m-.75 3h.75m3-6h.75m-.75 3h.75m-.75 3h.75M6.75 21v-3.375c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125V21M3 3h12m-.75 4.5H21m-3.75 3.75h.008v.008h-.008v-.008Zm0 3h.008v.008h-.008v-.008Zm0 3h.008v.008h-.008v-.008Z" />
									</svg>
								</div>
								<div>
									<h2 class="text-xl font-bold text-white">
										{report.company_name || '분석 결과'}
									</h2>
									<p class="text-sm text-gray-400">
										{getDomainLabel(report.domain)} 분석 레포트
									</p>
								</div>
							</div>
						{/if}
						
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
									<span class="w-6 h-6 rounded-md bg-emerald-500/20 text-emerald-400 flex items-center justify-center text-sm font-bold border border-emerald-500/30">
										{i + 1}
									</span>
									{section.title}
								</h3>
								<div class="pl-8">
									<article class="prose prose-sm max-w-none prose-invert prose-headings:text-white prose-p:text-slate-300 prose-strong:text-white prose-code:text-slate-300 prose-pre:text-slate-200 prose-blockquote:text-slate-300 prose-li:text-slate-300 prose-a:text-emerald-400 prose-table:text-slate-300">
										<Markdown id={`dart-report-${i}`} content={section.content.trim()} />
									</article>
								</div>
							</div>
						{/each}
						
						<!-- 스트리밍 중 표시 -->
						{#if reportStreaming}
							<div class="flex items-center gap-2 text-sm text-emerald-400 pl-8" in:fade>
								<div class="flex space-x-1">
									<div class="w-2 h-2 rounded-full bg-emerald-500 animate-bounce" style="animation-delay: 0ms"></div>
									<div class="w-2 h-2 rounded-full bg-emerald-500 animate-bounce" style="animation-delay: 150ms"></div>
									<div class="w-2 h-2 rounded-full bg-emerald-500 animate-bounce" style="animation-delay: 300ms"></div>
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
									<path stroke-linecap="round" stroke-linejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z" />
								</svg>
							</div>
							<h3 class="text-lg font-semibold text-gray-300 mb-2">
								분석 레포트가 여기에 표시됩니다
							</h3>
							<p class="text-sm text-gray-400 max-w-sm mx-auto">
								좌측에서 기업 공시에 대해 질문하시면, AI가 분석한 결과가 구조화된 레포트로 나타납니다.
							</p>
						</div>
					</div>
				{/if}
			</div>
		</div>
	</div>
</div>
