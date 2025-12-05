<script lang="ts">
	import { onMount } from 'svelte';
	import { fly, fade } from 'svelte/transition';
	import { toast } from 'svelte-sonner';
	
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
	
	// 분석 레포트
	let report: AnalysisReport | null = null;
	let reportStreaming = false;
	
	// 헬스체크
	let mcpStatus: 'checking' | 'connected' | 'error' = 'checking';
	let mcpToolCount = 0;
	
	async function checkHealth() {
		try {
			const response = await fetch('/api/dart/health');
			const data = await response.json();
			
			if (data.mcp_connected) {
				mcpStatus = 'connected';
				mcpToolCount = data.mcp_tools || 0;
			} else {
				mcpStatus = 'error';
			}
		} catch (error) {
			mcpStatus = 'error';
		}
	}
	
	onMount(() => {
		checkHealth();
		
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
			// SSE 스트리밍
			const response = await fetch('/api/dart/chat/stream', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ question })
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
						
						switch (data.event) {
							case 'start':
								messages = [...messages, {
									id: generateId(),
									role: 'assistant',
									content: '🔍 분석을 시작합니다...',
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

<div class="flex flex-col h-screen bg-gradient-to-br from-slate-50 via-white to-slate-50 dark:from-slate-950 dark:via-slate-900 dark:to-slate-950">
	<!-- 헤더 -->
	<header class="flex-shrink-0 border-b border-slate-200/50 dark:border-slate-800/50 bg-white/80 dark:bg-slate-900/80 backdrop-blur-xl z-10">
		<div class="px-6 py-3 flex items-center justify-between">
			<div class="flex items-center gap-3">
				<div class="w-10 h-10 rounded-xl bg-gradient-to-br from-emerald-500 to-teal-600 flex items-center justify-center shadow-lg shadow-emerald-500/20">
					<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-5 h-5 text-white">
						<path stroke-linecap="round" stroke-linejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z" />
					</svg>
				</div>
				<div>
					<h1 class="text-lg font-bold text-slate-900 dark:text-white">기업공시분석</h1>
					<p class="text-xs text-slate-500 dark:text-slate-400">DART AI Agent</p>
				</div>
			</div>
			
			<!-- MCP 상태 -->
			<div class="flex items-center gap-4">
				{#if mcpStatus === 'checking'}
					<div class="flex items-center gap-2 text-xs text-slate-500 px-3 py-1.5 rounded-full bg-slate-100 dark:bg-slate-800">
						<div class="w-2 h-2 rounded-full bg-yellow-400 animate-pulse"></div>
						<span>연결 확인 중...</span>
					</div>
				{:else if mcpStatus === 'connected'}
					<div class="flex items-center gap-2 text-xs text-emerald-600 dark:text-emerald-400 px-3 py-1.5 rounded-full bg-emerald-50 dark:bg-emerald-900/30">
						<div class="w-2 h-2 rounded-full bg-emerald-500"></div>
						<span>MCP 연결됨 ({mcpToolCount} tools)</span>
					</div>
				{:else}
					<div class="flex items-center gap-2 text-xs text-amber-600 dark:text-amber-400 px-3 py-1.5 rounded-full bg-amber-50 dark:bg-amber-900/30">
						<div class="w-2 h-2 rounded-full bg-amber-500"></div>
						<span>MCP 오프라인</span>
					</div>
				{/if}
			</div>
		</div>
	</header>
	
	<!-- 메인 콘텐츠 (좌우 분할) -->
	<div class="flex-1 flex overflow-hidden">
		<!-- 좌측: 채팅 영역 -->
		<div class="w-1/2 flex flex-col border-r border-slate-200/50 dark:border-slate-700/50">
			<!-- 채팅 헤더 -->
			<div class="px-4 py-2 border-b border-slate-100 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/50">
				<div class="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-400">
					<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-4 h-4">
						<path stroke-linecap="round" stroke-linejoin="round" d="M8.625 12a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0H8.25m4.125 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0H12m4.125 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Zm0 0h-.375M21 12c0 4.556-4.03 8.25-9 8.25a9.764 9.764 0 0 1-2.555-.337A5.972 5.972 0 0 1 5.41 20.97a5.969 5.969 0 0 1-.474-.065 4.48 4.48 0 0 0 .978-2.025c.09-.457-.133-.901-.467-1.226C3.93 16.178 3 14.189 3 12c0-4.556 4.03-8.25 9-8.25s9 3.694 9 8.25Z" />
					</svg>
					<span class="font-medium">에이전트 로그</span>
					{#if isLoading}
						<span class="ml-auto flex items-center gap-1.5 text-emerald-600 dark:text-emerald-400">
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
			<div bind:this={messagesContainer} class="flex-1 overflow-y-auto px-4 py-4 space-y-3">
				{#each messages as message (message.id)}
					<div 
						class="flex {message.role === 'user' ? 'justify-end' : 'justify-start'}"
						in:fly={{ y: 10, duration: 200 }}
					>
						{#if message.role === 'system'}
							<div class="max-w-[90%] p-3 rounded-xl bg-gradient-to-r from-slate-100 to-slate-50 dark:from-slate-800 dark:to-slate-800/50 border border-slate-200/50 dark:border-slate-700/50 text-sm">
								<p class="text-slate-600 dark:text-slate-300 whitespace-pre-wrap">{message.content}</p>
							</div>
						{:else if message.role === 'user'}
							<div class="max-w-[85%] px-4 py-2.5 rounded-2xl bg-gradient-to-r from-emerald-500 to-teal-500 text-white text-sm shadow-md shadow-emerald-500/20">
								<p class="whitespace-pre-wrap">{message.content}</p>
							</div>
						{:else if message.role === 'tool'}
							<div class="max-w-[90%] px-3 py-2 rounded-lg bg-purple-50 dark:bg-purple-900/20 border border-purple-200/50 dark:border-purple-800/50 text-sm">
								<div class="flex items-center gap-2 text-purple-700 dark:text-purple-300">
									<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-4 h-4">
										<path stroke-linecap="round" stroke-linejoin="round" d="M11.42 15.17 17.25 21A2.652 2.652 0 0 0 21 17.25l-5.877-5.877M11.42 15.17l2.496-3.03c.317-.384.74-.626 1.208-.766M11.42 15.17l-4.655 5.653a2.548 2.548 0 1 1-3.586-3.586l6.837-5.63m5.108-.233c.55-.164 1.163-.188 1.743-.14a4.5 4.5 0 0 0 4.486-6.336l-3.276 3.277a3.004 3.004 0 0 1-2.25-2.25l3.276-3.276a4.5 4.5 0 0 0-6.336 4.486c.091 1.076-.071 2.264-.904 2.95l-.102.085m-1.745 1.437L5.909 7.5H4.5L2.25 3.75l1.5-1.5L7.5 4.5v1.409l4.26 4.26m-1.745 1.437 1.745-1.437m6.615 8.206L15.75 15.75M4.867 19.125h.008v.008h-.008v-.008Z" />
									</svg>
									<span class="truncate">{message.content}</span>
								</div>
							</div>
						{:else}
							<div class="max-w-[90%] px-3 py-2 rounded-xl bg-white dark:bg-slate-800 border border-slate-200/50 dark:border-slate-700/50 shadow-sm text-sm">
								<p class="text-slate-700 dark:text-slate-300 whitespace-pre-wrap">{message.content}</p>
							</div>
						{/if}
					</div>
				{/each}
				
				{#if currentToolCall}
					<div class="flex justify-start" in:fade={{ duration: 150 }}>
						<div class="px-3 py-2 rounded-lg bg-amber-50 dark:bg-amber-900/20 border border-amber-200/50 dark:border-amber-800/50 text-sm">
							<div class="flex items-center gap-2 text-amber-700 dark:text-amber-300">
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
			<div class="flex-shrink-0 border-t border-slate-200/50 dark:border-slate-700/50 bg-white/50 dark:bg-slate-900/50 backdrop-blur-sm p-4">
				<!-- 예시 질문 -->
				{#if messages.length <= 1}
					<div class="mb-3 flex flex-wrap gap-2">
						{#each exampleQuestions as q}
							<button
								class="px-2.5 py-1 rounded-lg text-xs bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-600 dark:text-slate-400 transition-colors border border-slate-200/50 dark:border-slate-700/50"
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
							class="w-full resize-none rounded-xl border border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-4 py-2.5 text-sm text-slate-900 dark:text-white placeholder-slate-400 focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/20 transition-all disabled:opacity-50"
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
		<div class="w-1/2 flex flex-col bg-gradient-to-b from-white to-slate-50 dark:from-slate-900 dark:to-slate-950">
			<!-- 레포트 헤더 -->
			<div class="px-6 py-3 border-b border-slate-100 dark:border-slate-800 bg-white/80 dark:bg-slate-900/80 backdrop-blur-sm">
				<div class="flex items-center justify-between">
					<div class="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-400">
						<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-4 h-4">
							<path stroke-linecap="round" stroke-linejoin="round" d="M9 12h3.75M9 15h3.75M9 18h3.75m3 .75H18a2.25 2.25 0 0 0 2.25-2.25V6.108c0-1.135-.845-2.098-1.976-2.192a48.424 48.424 0 0 0-1.123-.08m-5.801 0c-.065.21-.1.433-.1.664 0 .414.336.75.75.75h4.5a.75.75 0 0 0 .75-.75 2.25 2.25 0 0 0-.1-.664m-5.8 0A2.251 2.251 0 0 1 13.5 2.25H15c1.012 0 1.867.668 2.15 1.586m-5.8 0c-.376.023-.75.05-1.124.08C9.095 4.01 8.25 4.973 8.25 6.108V8.25m0 0H4.875c-.621 0-1.125.504-1.125 1.125v11.25c0 .621.504 1.125 1.125 1.125h9.75c.621 0 1.125-.504 1.125-1.125V9.375c0-.621-.504-1.125-1.125-1.125H8.25ZM6.75 12h.008v.008H6.75V12Zm0 3h.008v.008H6.75V15Zm0 3h.008v.008H6.75V18Z" />
						</svg>
						<span class="font-medium">분석 레포트</span>
					</div>
					
					{#if report && report.latency_ms > 0}
						<div class="flex items-center gap-3 text-xs text-slate-500">
							<span>{report.tokens.total.toLocaleString()} tokens</span>
							<span>{(report.latency_ms / 1000).toFixed(1)}s</span>
						</div>
					{/if}
				</div>
			</div>
			
			<!-- 레포트 내용 -->
			<div bind:this={reportContainer} class="flex-1 overflow-y-auto">
				{#if report && (report.summary || report.sections.length > 0)}
					<div class="p-6 space-y-6" in:fade={{ duration: 300 }}>
						<!-- 회사 정보 헤더 -->
						{#if report.company_name || report.domain}
							<div class="flex items-center gap-3 pb-4 border-b border-slate-200 dark:border-slate-700">
								<div class="w-12 h-12 rounded-xl bg-gradient-to-br from-emerald-500 to-teal-600 flex items-center justify-center shadow-lg shadow-emerald-500/20">
									<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-6 h-6 text-white">
										<path stroke-linecap="round" stroke-linejoin="round" d="M2.25 21h19.5m-18-18v18m10.5-18v18m6-13.5V21M6.75 6.75h.75m-.75 3h.75m-.75 3h.75m3-6h.75m-.75 3h.75m-.75 3h.75M6.75 21v-3.375c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125V21M3 3h12m-.75 4.5H21m-3.75 3.75h.008v.008h-.008v-.008Zm0 3h.008v.008h-.008v-.008Zm0 3h.008v.008h-.008v-.008Z" />
									</svg>
								</div>
								<div>
									<h2 class="text-xl font-bold text-slate-900 dark:text-white">
										{report.company_name || '분석 결과'}
									</h2>
									<p class="text-sm text-slate-500 dark:text-slate-400">
										{getDomainLabel(report.domain)} 분석 레포트
									</p>
								</div>
							</div>
						{/if}
						
						<!-- 사용된 도구 -->
						{#if report.toolsUsed.length > 0}
							<div class="flex flex-wrap gap-2">
								{#each [...new Set(report.toolsUsed)] as tool}
									<span class="px-2 py-1 text-xs rounded-md bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300 border border-purple-200/50 dark:border-purple-800/50">
										{tool}
									</span>
								{/each}
							</div>
						{/if}
						
						<!-- 섹션들 -->
						{#each report.sections as section, i}
							<div class="space-y-3" in:fly={{ y: 20, duration: 300, delay: i * 100 }}>
								<h3 class="flex items-center gap-2 text-lg font-semibold text-slate-800 dark:text-slate-200">
									<span class="w-6 h-6 rounded-md bg-emerald-100 dark:bg-emerald-900/30 text-emerald-600 dark:text-emerald-400 flex items-center justify-center text-sm font-bold">
										{i + 1}
									</span>
									{section.title}
								</h3>
								<div class="prose prose-sm prose-slate dark:prose-invert max-w-none pl-8">
									<p class="text-slate-600 dark:text-slate-400 whitespace-pre-wrap leading-relaxed">
										{section.content.trim()}
									</p>
								</div>
							</div>
						{/each}
						
						<!-- 스트리밍 중 표시 -->
						{#if reportStreaming}
							<div class="flex items-center gap-2 text-sm text-emerald-600 dark:text-emerald-400 pl-8" in:fade>
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
							<div class="w-20 h-20 mx-auto mb-6 rounded-2xl bg-gradient-to-br from-slate-100 to-slate-200 dark:from-slate-800 dark:to-slate-700 flex items-center justify-center">
								<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1" stroke="currentColor" class="w-10 h-10 text-slate-400 dark:text-slate-500">
									<path stroke-linecap="round" stroke-linejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z" />
								</svg>
							</div>
							<h3 class="text-lg font-semibold text-slate-700 dark:text-slate-300 mb-2">
								분석 레포트가 여기에 표시됩니다
							</h3>
							<p class="text-sm text-slate-500 dark:text-slate-400 max-w-sm mx-auto">
								좌측에서 기업 공시에 대해 질문하시면, AI가 분석한 결과가 구조화된 레포트로 나타납니다.
							</p>
						</div>
					</div>
				{/if}
			</div>
		</div>
	</div>
</div>
