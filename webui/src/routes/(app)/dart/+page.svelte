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
	
	// 탭 상태 (Single Agent / Multi Agent)
	type AgentTab = 'single' | 'multi';
	let activeTab: AgentTab = 'multi';
	
	// LLM 모델 선택
	interface LLMModel {
		model_name: string;
		model: string;
		provider?: string;
	}
	let availableModels: LLMModel[] = [];
	let selectedModel: string = 'qwen-235b'; // 기본값
	let loadingModels = false;
	
	// 모델 목록 로드
	async function loadModels() {
		loadingModels = true;
		try {
			const response = await fetch('/api/llm/models');
			if (response.ok) {
				const data = await response.json();
				availableModels = data.models || [];
				// 기본 모델이 목록에 있는지 확인
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
	
	// 탭 변경 확인 모달 상태
	let showTabChangeConfirm = false;
	let pendingTab: AgentTab | null = null;
	
	// 워크플로우 다이어그램 모달 상태
	let showWorkflowModal = false;
	let workflowModalType: AgentTab = 'single';
	
	// SSE 연결 중단용 AbortController
	let abortController: AbortController | null = null;
	
	// 탭별 엔드포인트 매핑
	function getEndpointForTab(tab: AgentTab): string {
		switch (tab) {
			case 'single': return '/api/dart/chat/single';
			case 'multi': return '/api/dart/chat/stream';
		}
	}
	
	// 탭 변경 처리 (분석 중이면 확인 모달 표시)
	function handleTabChange(newTab: AgentTab) {
		if (activeTab === newTab) return;
		
		if (isLoading) {
			// 분석 중이면 확인 모달 표시
			pendingTab = newTab;
			showTabChangeConfirm = true;
		} else {
			// 분석 중이 아니면 바로 변경
			activeTab = newTab;
			startNewChat();
		}
	}
	
	// 탭 변경 확인 (분석 중단)
	function confirmTabChange() {
		// SSE 연결 중단
		if (abortController) {
			abortController.abort();
			abortController = null;
		}
		
		// 상태 초기화
		isLoading = false;
		currentToolCall = null;
		
		// 탭 변경
		if (pendingTab) {
			activeTab = pendingTab;
			pendingTab = null;
		}
		showTabChangeConfirm = false;
		startNewChat();
		
		toast.info('분석이 중단되었습니다.');
	}
	
	// 탭 변경 취소
	function cancelTabChange() {
		pendingTab = null;
		showTabChangeConfirm = false;
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
	
	// 히스토리 저장 (레포트 포함)
	async function saveHistory() {
		if (messages.length <= 1) return; // 시스템 메시지만 있으면 저장 안함
		
		const userMessages = messages.filter(m => m.role === 'user');
		if (userMessages.length === 0) return;
		
		const title = userMessages[0].content.slice(0, 50) + (userMessages[0].content.length > 50 ? '...' : '');
		
		// 레포트도 함께 저장
		const historyData = { 
			messages,
			selected_model: selectedModel,
			report: report ? {
				company_name: report.company_name,
				domain: report.domain,
				summary: report.summary,
				sections: report.sections,
				toolsUsed: report.toolsUsed,
				tokens: report.tokens,
				latency_ms: report.latency_ms
			} : null
		};
		
		try {
			if (currentHistoryId) {
				// 기존 히스토리 업데이트
				await fetch(`/api/dart/history/${currentHistoryId}`, {
					method: 'PUT',
					headers: { 'Content-Type': 'application/json' },
					body: JSON.stringify(historyData)
				});
			} else {
				// 새 히스토리 생성
				const response = await fetch('/api/dart/history', {
					method: 'POST',
					headers: { 'Content-Type': 'application/json' },
					body: JSON.stringify({ title, model_tab: activeTab, ...historyData })
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
	
	// 히스토리 불러오기 (레포트 포함)
	async function loadHistory(historyId: string) {
		loadingHistory = true;
		try {
			const response = await fetch(`/api/dart/history/${historyId}`);
			if (response.ok) {
				const data = await response.json();
				messages = data.history?.messages || [];
				currentHistoryId = historyId;
				
				// 기존 탭 형식을 새 형식으로 변환
				const savedTab = data.history?.model_tab || 'multi';
				if (savedTab === 'qwen-235b' || savedTab === 'opus-multi') {
					activeTab = 'multi';
				} else if (savedTab === 'opus-single') {
					activeTab = 'single';
				} else {
					activeTab = savedTab as AgentTab;
				}
				
				// 저장된 모델 복원
				if (data.history?.selected_model) {
					selectedModel = data.history.selected_model;
				}
				
				// 저장된 레포트 복원
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
		loadModels(); // LLM 모델 목록 로드
		
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
			
			// AbortController 생성 (탭 변경 시 중단용)
			abortController = new AbortController();
			
			// SSE 스트리밍 (탭에 따른 엔드포인트)
			const endpoint = getEndpointForTab(activeTab);
			const response = await fetch(endpoint, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ question, model: selectedModel }),
				signal: abortController.signal
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
						
						// ========================================
						// 이벤트 타입별 표시 전략
						// ========================================
						// 1. message: 화면 메시지에 표시
						// 2. spinner: 스피너에만 표시 (도구 호출 등)
						// 3. report: 레포트에만 반영 (스트리밍 콘텐츠)
						// 4. silent: 상태 업데이트만 (완료 이벤트 등)
						// ========================================
						
						const eventType = data.event || data.type;
						
						// 이벤트 타입별 표시 전략 정의
						const DISPLAY_MESSAGE = ['start', 'answer', 'agent_response', 'error', 'intent_classified'];
						const DISPLAY_SPINNER = ['analyzing', 'progress', 'iteration', 'tool_start', 'tool_end', 'tool_result'];
						const DISPLAY_REPORT = ['content', 'stream_chunk', 'analysis'];
						const DISPLAY_SILENT = ['complete', 'done', 'end', 'final', 'agent_results'];
						
						// 기술적 이벤트 이름 → 사용자 친화적 메시지 매핑
						const technicalToFriendly: Record<string, string> = {
							'intent_classification_start': '질문 분석 중...',
							'intent_classification_complete': '질문 분석 완료',
							'mcp_call_start': '데이터 조회 중...',
							'mcp_call_complete': '데이터 조회 완료',
							'llm_call_start': 'AI 분석 중...',
							'llm_call_complete': 'AI 분석 완료',
							'tool_call_start': '도구 실행 중...',
							'tool_call_complete': '도구 실행 완료',
							'mcp_start': 'MCP 도구 호출 중...',
							'mcp_complete': 'MCP 도구 호출 완료'
						};
						
						// progress 이벤트 메시지 변환
						const transformProgressMessage = (msg: string): string => {
							// 기술적 이벤트 이름이 포함되어 있으면 친화적 메시지로 변환
							for (const [tech, friendly] of Object.entries(technicalToFriendly)) {
								if (msg.includes(tech)) {
									return friendly;
								}
							}
							// 기술적 이벤트 패턴 감지
							if (msg.includes('_start') || msg.includes('_complete') || msg.includes('_end')) {
								return '처리 중...';
							}
							return msg;
						};
						
						// 스피너 메시지 생성 헬퍼
						const getSpinnerMessage = (event: string, eventData: any): string => {
							switch (event) {
								case 'analyzing':
									return eventData.message || '분석 중...';
							case 'progress': {
								// finish_reason이 있으면 백엔드에서 이미 친화적 메시지로 변환되어 있음
								// 없으면 기본 메시지 사용
								const rawMsg = eventData.message || eventData.content || '처리 중...';
								return transformProgressMessage(rawMsg);
							}
								case 'intent_classified':
									return `${eventData.company_name || '기업'} 분석 준비 중...`;
								case 'iteration':
									return `반복 ${eventData.iteration}...`;
								case 'tool_start':
									return `${eventData.tool || eventData.display_name || '도구'} 실행 중...`;
								case 'tool_end':
									return `${eventData.tool || '도구'} 완료`;
								case 'tool_result':
									return `${eventData.display_name || eventData.tool_name || eventData.tool || '도구'} 완료`;
								default:
									return '처리 중...';
							}
						};
						
						switch (eventType) {
							// ========================================
							// 1. 화면 메시지로 표시하는 이벤트
							// ========================================
							case 'start':
								messages = [...messages, {
									id: generateId(),
									role: 'assistant',
									content: data.content || '분석을 시작합니다...',
									timestamp: new Date()
								}];
								break;
								
							case 'agent_response':
								// 서브 에이전트 응답 - 화면에 표시
								const agentName = data.agent_name || '에이전트';
								currentToolCall = `${agentName} 분석 완료`;
								messages = [...messages, {
									id: generateId(),
									role: 'assistant',
									content: `${agentName} 분석이 완료되었습니다.`,
									timestamp: new Date()
								}];
								// 에이전트 응답을 레포트에도 추가
								if (report && data.content) {
									report.summary = (report.summary || '') + '\n\n' + data.content;
									report.sections = parseMarkdownToSections(report.summary);
								}
								break;
							
							case 'error':
								toast.error(data.error || '오류가 발생했습니다');
								messages = [...messages, {
									id: generateId(),
									role: 'assistant',
									content: `오류: ${data.error || '알 수 없는 오류'}`,
									timestamp: new Date()
								}];
								reportStreaming = false;
								currentToolCall = null;
								break;
							
							// ========================================
							// 2. 스피너에만 표시하는 이벤트 (도구 호출 등)
							// ========================================
							case 'analyzing':
							case 'progress':
							case 'iteration':
							case 'tool_start':
							case 'tool_end':
							case 'tool_result':
								// 스피너만 업데이트 (화면 메시지 추가 안함)
								currentToolCall = getSpinnerMessage(eventType, data);
								// 도구 사용 기록
								if (report) {
									const toolName = data.tool_name || data.tool;
									if (toolName && (eventType === 'tool_end' || eventType === 'tool_result')) {
										if (!report.toolsUsed.includes(toolName)) {
											report.toolsUsed = [...report.toolsUsed, toolName];
										}
									}
								}
								break;
							
							case 'intent_classified':
								// 의도 분류 - 화면에 reasoning 표시 + 레포트 상태 업데이트
								if (report) {
									report.domain = data.domain;
									report.company_name = data.company_name;
								}
								
								// reasoning과 analysis_reasoning을 화면에 표시
								const intentContent: string[] = [];
								if (data.reasoning) {
									intentContent.push(data.reasoning);
								}
								if (data.analysis_reasoning) {
									intentContent.push(data.analysis_reasoning);
								}
								
								if (intentContent.length > 0) {
									messages = [...messages, {
										id: generateId(),
										role: 'assistant',
										content: intentContent.join('\n\n'),
										timestamp: new Date()
									}];
								}
								
								// 스피너도 업데이트
								currentToolCall = getSpinnerMessage(eventType, data);
								break;
								
							// ========================================
							// 3. 레포트에만 반영하는 이벤트 (스트리밍 콘텐츠)
							// ========================================
							case 'content':
							case 'stream_chunk':
							case 'analysis':
								// 레포트에 콘텐츠 누적 (화면 메시지 추가 안함)
								if (report && data.content) {
									report.summary = (report.summary || '') + data.content;
									report.sections = parseMarkdownToSections(report.summary);
								}
								break;
							
							// ========================================
							// 4. 완료 이벤트 (상태 업데이트 + 완료 메시지)
							// ========================================
							case 'answer':
								// 최종 답변 - 레포트 + 완료 메시지
								if (report) {
									report.summary = data.content;
									report.sections = parseMarkdownToSections(data.content);
								}
								messages = [...messages, {
									id: generateId(),
									role: 'assistant',
									content: '분석이 완료되었습니다. 우측 레포트를 확인해주세요.',
									timestamp: new Date()
								}];
								reportStreaming = false;
								currentToolCall = null;
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
								// 분석 완료 - 레포트가 있으면 완료 메시지 추가
								if (report && report.summary) {
									messages = [...messages, {
										id: generateId(),
										role: 'assistant',
										content: '분석이 완료되었습니다. 우측 레포트를 확인해주세요.',
										timestamp: new Date()
									}];
								}
								if (data.total_latency_ms && report) {
									report.latency_ms = data.total_latency_ms;
								}
								reportStreaming = false;
								currentToolCall = null;
								break;
							
							case 'agent_results':
								// 에이전트 결과 수신 - 스피너만 업데이트
								const resultsCount = data.results?.length || 0;
								if (resultsCount > 0) {
									currentToolCall = `📊 ${resultsCount}개 에이전트 분석 완료`;
								}
								break;
							
							case 'end':
							case 'final':
								// 분석 종료
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
								// 알 수 없는 이벤트 - 진행 표시로 처리
								if (data.content || data.message) {
									currentToolCall = data.content || data.message;
								}
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
			abortController = null;
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
		'현대자동차 최근 공시 분석해줘',
		'현대자동차 재무제표 요약',
		'네이버 지배구조 현황',
		'SK하이닉스 자본변동 분석'
	];
</script>

<svelte:head>
	<title>기업공시분석 | DART Agent</title>
</svelte:head>

<div class="h-[calc(100vh-120px)] bg-gray-950 text-slate-50 overflow-hidden flex flex-col">
	<!-- Hero Section -->
	<div class="relative overflow-hidden border-b border-slate-800/50 flex-shrink-0">
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
						<h1 class="text-2xl font-bold text-white">기업공시분석</h1>
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
	
	<!-- 탭 UI + 모델 선택 -->
	<div class="px-6 py-2 border-b border-gray-800/50 bg-gray-900/40 flex-shrink-0">
		<div class="flex items-center justify-between">
			<!-- 탭 버튼 -->
			<div class="flex items-center gap-1">
				<!-- Single Agent 탭 -->
				<div class="flex items-center">
					<button 
						class="px-4 py-2 text-sm rounded-l-lg transition-all {activeTab === 'single' ? 'bg-purple-500/20 text-purple-300 border border-purple-500/30' : 'text-gray-400 hover:text-gray-200 hover:bg-gray-800/50 border border-gray-700/30'}"
						on:click={() => handleTabChange('single')}
					>
						<span class="flex items-center gap-2">
							<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-4 h-4">
								<path stroke-linecap="round" stroke-linejoin="round" d="M15.75 6a3.75 3.75 0 1 1-7.5 0 3.75 3.75 0 0 1 7.5 0ZM4.501 20.118a7.5 7.5 0 0 1 14.998 0A17.933 17.933 0 0 1 12 21.75c-2.676 0-5.216-.584-7.499-1.632Z" />
							</svg>
							Single Agent
						</span>
					</button>
					<button
						class="px-2 py-2 text-sm rounded-r-lg transition-all border-l-0 {activeTab === 'single' ? 'bg-purple-500/10 text-purple-300 border border-purple-500/30 hover:bg-purple-500/20' : 'text-gray-500 hover:text-gray-300 hover:bg-gray-800/50 border border-gray-700/30'}"
						on:click={() => { workflowModalType = 'single'; showWorkflowModal = true; }}
						title="Single Agent 워크플로우 보기"
					>
						<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-4 h-4">
							<path stroke-linecap="round" stroke-linejoin="round" d="M3.75 6A2.25 2.25 0 0 1 6 3.75h2.25A2.25 2.25 0 0 1 10.5 6v2.25a2.25 2.25 0 0 1-2.25 2.25H6a2.25 2.25 0 0 1-2.25-2.25V6ZM3.75 15.75A2.25 2.25 0 0 1 6 13.5h2.25a2.25 2.25 0 0 1 2.25 2.25V18a2.25 2.25 0 0 1-2.25 2.25H6A2.25 2.25 0 0 1 3.75 18v-2.25ZM13.5 6a2.25 2.25 0 0 1 2.25-2.25H18A2.25 2.25 0 0 1 20.25 6v2.25A2.25 2.25 0 0 1 18 10.5h-2.25a2.25 2.25 0 0 1-2.25-2.25V6ZM13.5 15.75a2.25 2.25 0 0 1 2.25-2.25H18a2.25 2.25 0 0 1 2.25 2.25V18A2.25 2.25 0 0 1 18 20.25h-2.25A2.25 2.25 0 0 1 13.5 18v-2.25Z" />
						</svg>
					</button>
				</div>
				
				<!-- Multi Agent 탭 -->
				<div class="flex items-center ml-1">
					<button 
						class="px-4 py-2 text-sm rounded-l-lg transition-all {activeTab === 'multi' ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30' : 'text-gray-400 hover:text-gray-200 hover:bg-gray-800/50 border border-gray-700/30'}"
						on:click={() => handleTabChange('multi')}
					>
						<span class="flex items-center gap-2">
							<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-4 h-4">
								<path stroke-linecap="round" stroke-linejoin="round" d="M18 18.72a9.094 9.094 0 0 0 3.741-.479 3 3 0 0 0-4.682-2.72m.94 3.198.001.031c0 .225-.012.447-.037.666A11.944 11.944 0 0 1 12 21c-2.17 0-4.207-.576-5.963-1.584A6.062 6.062 0 0 1 6 18.719m12 0a5.971 5.971 0 0 0-.941-3.197m0 0A5.995 5.995 0 0 0 12 12.75a5.995 5.995 0 0 0-5.058 2.772m0 0a3 3 0 0 0-4.681 2.72 8.986 8.986 0 0 0 3.74.477m.94-3.197a5.971 5.971 0 0 0-.94 3.197M15 6.75a3 3 0 1 1-6 0 3 3 0 0 1 6 0Zm6 3a2.25 2.25 0 1 1-4.5 0 2.25 2.25 0 0 1 4.5 0Zm-13.5 0a2.25 2.25 0 1 1-4.5 0 2.25 2.25 0 0 1 4.5 0Z" />
							</svg>
							Multi Agent
						</span>
					</button>
					<button
						class="px-2 py-2 text-sm rounded-r-lg transition-all border-l-0 {activeTab === 'multi' ? 'bg-emerald-500/10 text-emerald-300 border border-emerald-500/30 hover:bg-emerald-500/20' : 'text-gray-500 hover:text-gray-300 hover:bg-gray-800/50 border border-gray-700/30'}"
						on:click={() => { workflowModalType = 'multi'; showWorkflowModal = true; }}
						title="Multi Agent 워크플로우 보기"
					>
						<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-4 h-4">
							<path stroke-linecap="round" stroke-linejoin="round" d="M3.75 6A2.25 2.25 0 0 1 6 3.75h2.25A2.25 2.25 0 0 1 10.5 6v2.25a2.25 2.25 0 0 1-2.25 2.25H6a2.25 2.25 0 0 1-2.25-2.25V6ZM3.75 15.75A2.25 2.25 0 0 1 6 13.5h2.25a2.25 2.25 0 0 1 2.25 2.25V18a2.25 2.25 0 0 1-2.25 2.25H6A2.25 2.25 0 0 1 3.75 18v-2.25ZM13.5 6a2.25 2.25 0 0 1 2.25-2.25H18A2.25 2.25 0 0 1 20.25 6v2.25A2.25 2.25 0 0 1 18 10.5h-2.25a2.25 2.25 0 0 1-2.25-2.25V6ZM13.5 15.75a2.25 2.25 0 0 1 2.25-2.25H18a2.25 2.25 0 0 1 2.25 2.25V18A2.25 2.25 0 0 1 18 20.25h-2.25A2.25 2.25 0 0 1 13.5 18v-2.25Z" />
						</svg>
					</button>
				</div>
			</div>
			
			<!-- 모델 선택 드롭다운 -->
			<div class="flex items-center gap-2">
				<span class="text-xs text-gray-400">Model:</span>
				<select 
					bind:value={selectedModel}
					disabled={isLoading || loadingModels}
					class="px-3 py-1.5 text-sm rounded-lg bg-gray-800/60 border border-gray-700/50 text-white focus:outline-none focus:ring-1 focus:ring-emerald-500/50 disabled:opacity-50"
				>
					{#if loadingModels}
						<option value="">로딩 중...</option>
					{:else if availableModels.length === 0}
						<option value="qwen-235b">qwen-235b</option>
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
	</div>
	
	<!-- 메인 콘텐츠 (좌우 분할 + 사이드바) -->
	<div class="flex relative flex-1 overflow-hidden">
		<!-- 히스토리 사이드바 -->
		{#if showHistorySidebar}
			<div class="w-72 border-r border-gray-800/50 bg-gray-900/80 backdrop-blur-sm flex flex-col h-full">
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
		<div class="flex-1 flex flex-col border-r border-gray-800/50 h-full relative" style="max-width: {showHistorySidebar ? 'calc(50% - 144px)' : '50%'}">
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
			<div class="absolute bottom-0 left-0 right-0 border-t border-gray-800/50 bg-gray-900/95 backdrop-blur-md p-4">
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
									<article class="prose prose-sm max-w-none prose-invert prose-headings:text-white prose-p:text-slate-300 prose-strong:text-white prose-code:text-slate-300 prose-pre:text-slate-200 prose-blockquote:text-slate-300 prose-li:text-slate-300 prose-a:text-emerald-400 
									prose-table:text-slate-200
									prose-thead:bg-gray-800 prose-thead:text-white
									prose-th:border prose-th:border-gray-600 prose-th:px-3 prose-th:py-2 prose-th:text-left prose-th:font-semibold
									prose-td:border prose-td:border-gray-700 prose-td:px-3 prose-td:py-2
									prose-tr:bg-gray-900/50 prose-tr:even:bg-gray-800/50">
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

<!-- 탭 변경 확인 모달 -->
{#if showTabChangeConfirm}
	<!-- svelte-ignore a11y-no-noninteractive-element-interactions -->
	<div 
		class="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4"
		transition:fade={{ duration: 150 }}
		on:click={cancelTabChange}
		on:keydown={(e) => e.key === 'Escape' && cancelTabChange()}
		role="dialog"
		aria-modal="true"
		aria-labelledby="confirm-title"
	>
		<!-- svelte-ignore a11y-click-events-have-key-events a11y-no-noninteractive-element-interactions -->
		<div 
			class="bg-gray-900 border border-gray-700/50 rounded-2xl shadow-2xl max-w-md w-full p-6"
			role="document"
			on:click|stopPropagation
			in:fly={{ y: 20, duration: 200 }}
		>
			<div class="flex items-center gap-3 mb-4">
				<div class="w-12 h-12 rounded-xl bg-amber-500/20 flex items-center justify-center">
					<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-6 h-6 text-amber-400">
						<path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
					</svg>
				</div>
				<div>
					<h3 id="confirm-title" class="text-lg font-semibold text-white">분석 중단 확인</h3>
					<p class="text-sm text-gray-400">진행 중인 분석이 있습니다</p>
				</div>
			</div>
			
			<p class="text-gray-300 mb-6">
				탭을 변경하면 현재 진행 중인 분석이 중단됩니다. 계속하시겠습니까?
			</p>
			
			<div class="flex gap-3 justify-end">
				<button 
					class="px-4 py-2 text-sm font-medium text-gray-300 hover:text-white bg-gray-800 hover:bg-gray-700 rounded-lg border border-gray-700 transition-colors"
					on:click={cancelTabChange}
				>
					취소
				</button>
				<button 
					class="px-4 py-2 text-sm font-medium text-white bg-amber-600 hover:bg-amber-500 rounded-lg transition-colors"
					on:click={confirmTabChange}
				>
					분석 중단
				</button>
			</div>
		</div>
	</div>
{/if}

<!-- 전역 키보드 이벤트 핸들러 (ESC로 모달 닫기) -->
<svelte:window on:keydown={(e) => {
	if (e.key === 'Escape' && showWorkflowModal) {
		showWorkflowModal = false;
	}
}} />

<!-- 워크플로우 다이어그램 모달 -->
{#if showWorkflowModal}
	<!-- svelte-ignore a11y-no-noninteractive-element-interactions a11y-click-events-have-key-events -->
	<div 
		class="fixed inset-0 bg-black/80 backdrop-blur-sm z-50 flex items-center justify-center p-4 cursor-pointer"
		transition:fade={{ duration: 200 }}
		on:click={() => showWorkflowModal = false}
		role="dialog"
		aria-modal="true"
		aria-labelledby="workflow-title"
	>
		<!-- svelte-ignore a11y-click-events-have-key-events a11y-no-noninteractive-element-interactions -->
		<div 
			class="bg-gray-900 border border-gray-700/50 rounded-2xl shadow-2xl max-w-6xl w-full max-h-[95vh] overflow-hidden"
			role="document"
			on:click={() => showWorkflowModal = false}
			in:fly={{ y: 30, duration: 250 }}
		>
			<!-- 헤더 -->
			<div class="sticky top-0 bg-gray-900 border-b border-gray-800 px-6 py-4 flex items-center justify-between rounded-t-2xl">
				<div class="flex items-center gap-3">
					<div class="w-10 h-10 rounded-xl {workflowModalType === 'single' ? 'bg-purple-500/20' : 'bg-emerald-500/20'} flex items-center justify-center">
						{#if workflowModalType === 'single'}
							<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-5 h-5 text-purple-400">
								<path stroke-linecap="round" stroke-linejoin="round" d="M15.75 6a3.75 3.75 0 1 1-7.5 0 3.75 3.75 0 0 1 7.5 0ZM4.501 20.118a7.5 7.5 0 0 1 14.998 0A17.933 17.933 0 0 1 12 21.75c-2.676 0-5.216-.584-7.499-1.632Z" />
							</svg>
						{:else}
							<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-5 h-5 text-emerald-400">
								<path stroke-linecap="round" stroke-linejoin="round" d="M18 18.72a9.094 9.094 0 0 0 3.741-.479 3 3 0 0 0-4.682-2.72m.94 3.198.001.031c0 .225-.012.447-.037.666A11.944 11.944 0 0 1 12 21c-2.17 0-4.207-.576-5.963-1.584A6.062 6.062 0 0 1 6 18.719m12 0a5.971 5.971 0 0 0-.941-3.197m0 0A5.995 5.995 0 0 0 12 12.75a5.995 5.995 0 0 0-5.058 2.772m0 0a3 3 0 0 0-4.681 2.72 8.986 8.986 0 0 0 3.74.477m.94-3.197a5.971 5.971 0 0 0-.94 3.197M15 6.75a3 3 0 1 1-6 0 3 3 0 0 1 6 0Zm6 3a2.25 2.25 0 1 1-4.5 0 2.25 2.25 0 0 1 4.5 0Zm-13.5 0a2.25 2.25 0 1 1-4.5 0 2.25 2.25 0 0 1 4.5 0Z" />
							</svg>
						{/if}
					</div>
					<div>
						<h3 id="workflow-title" class="text-lg font-semibold text-white">
							{workflowModalType === 'single' ? 'Single Agent' : 'Multi Agent'} 워크플로우
						</h3>
						<p class="text-sm text-gray-400">
							{workflowModalType === 'single' ? 'ReAct 패턴 기반 단일 에이전트' : 'DartMasterAgent 오케스트레이션'}
						</p>
					</div>
				</div>
				<button 
					class="p-2 rounded-lg hover:bg-gray-800 text-gray-400 hover:text-white transition-colors"
					on:click={() => showWorkflowModal = false}
				>
					<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-5 h-5">
						<path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
					</svg>
				</button>
			</div>
			
			<!-- 다이어그램 콘텐츠 (드래그 가능) -->
			<div class="p-6 overflow-auto max-h-[calc(95vh-80px)] cursor-grab active:cursor-grabbing">
				{#if workflowModalType === 'single'}
					<!-- Single Agent 워크플로우 다이어그램 -->
					<svg viewBox="0 0 800 400" class="w-full h-auto" xmlns="http://www.w3.org/2000/svg">
						<!-- 배경 그라디언트 -->
						<defs>
							<linearGradient id="purpleGradient" x1="0%" y1="0%" x2="100%" y2="100%">
								<stop offset="0%" style="stop-color:#7c3aed;stop-opacity:0.2" />
								<stop offset="100%" style="stop-color:#a855f7;stop-opacity:0.1" />
							</linearGradient>
							<linearGradient id="arrowGradient" x1="0%" y1="0%" x2="100%" y2="0%">
								<stop offset="0%" style="stop-color:#a855f7" />
								<stop offset="100%" style="stop-color:#7c3aed" />
							</linearGradient>
							<marker id="arrowHead" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
								<polygon points="0 0, 10 3.5, 0 7" fill="#a855f7" />
							</marker>
							<marker id="arrowHeadReverse" markerWidth="10" markerHeight="7" refX="1" refY="3.5" orient="auto-start-reverse">
								<polygon points="10 0, 0 3.5, 10 7" fill="#a855f7" />
							</marker>
						</defs>
						
						<!-- 사용자 질문 -->
						<g transform="translate(50, 150)">
							<rect x="0" y="0" width="120" height="60" rx="12" fill="#1e1b4b" stroke="#7c3aed" stroke-width="2"/>
							<text x="60" y="25" text-anchor="middle" fill="#c4b5fd" font-size="12" font-weight="600">User</text>
							<text x="60" y="42" text-anchor="middle" fill="#a78bfa" font-size="11">Query</text>
						</g>
						
						<!-- 화살표: User -> LLM -->
						<line x1="170" y1="180" x2="240" y2="180" stroke="url(#arrowGradient)" stroke-width="2" marker-end="url(#arrowHead)"/>
						
						<!-- LLM (ReAct) -->
						<g transform="translate(250, 120)">
							<rect x="0" y="0" width="180" height="120" rx="16" fill="url(#purpleGradient)" stroke="#a855f7" stroke-width="2"/>
							<text x="90" y="30" text-anchor="middle" fill="#e9d5ff" font-size="14" font-weight="700">LLM (ReAct)</text>
							<text x="90" y="50" text-anchor="middle" fill="#c4b5fd" font-size="11">Reasoning + Acting</text>
							<line x1="20" y1="65" x2="160" y2="65" stroke="#7c3aed" stroke-width="1" opacity="0.5"/>
							<text x="90" y="85" text-anchor="middle" fill="#a78bfa" font-size="10">• 질문 분석</text>
							<text x="90" y="100" text-anchor="middle" fill="#a78bfa" font-size="10">• 도구 선택 및 호출</text>
							<text x="90" y="115" text-anchor="middle" fill="#a78bfa" font-size="10">• 결과 종합</text>
						</g>
						
						<!-- ReAct Loop 화살표 -->
						<path d="M 430 150 Q 470 80 410 80 Q 350 80 350 120" fill="none" stroke="#a855f7" stroke-width="2" stroke-dasharray="4,4" marker-end="url(#arrowHead)"/>
						<text x="420" y="65" fill="#c4b5fd" font-size="10" font-style="italic">ReAct Loop</text>
						
						<!-- 화살표: LLM -> MCP Tools -->
						<line x1="430" y1="180" x2="510" y2="180" stroke="url(#arrowGradient)" stroke-width="2" marker-end="url(#arrowHead)"/>
						
						<!-- MCP Tools -->
						<g transform="translate(520, 90)">
							<rect x="0" y="0" width="230" height="180" rx="16" fill="#1e1b4b" stroke="#7c3aed" stroke-width="2"/>
							<text x="115" y="28" text-anchor="middle" fill="#e9d5ff" font-size="13" font-weight="700">MCP Tools (85개)</text>
							<line x1="15" y1="40" x2="215" y2="40" stroke="#7c3aed" stroke-width="1" opacity="0.5"/>
							
							<!-- 도구 그리드 -->
							<g transform="translate(15, 50)">
								<rect x="0" y="0" width="95" height="25" rx="6" fill="#312e81" stroke="#6366f1" stroke-width="1"/>
								<text x="47" y="16" text-anchor="middle" fill="#a5b4fc" font-size="9">get_corp_info</text>
								
								<rect x="105" y="0" width="95" height="25" rx="6" fill="#312e81" stroke="#6366f1" stroke-width="1"/>
								<text x="152" y="16" text-anchor="middle" fill="#a5b4fc" font-size="9">get_single_acnt</text>
								
								<rect x="0" y="32" width="95" height="25" rx="6" fill="#312e81" stroke="#6366f1" stroke-width="1"/>
								<text x="47" y="48" text-anchor="middle" fill="#a5b4fc" font-size="9">get_disclosure</text>
								
								<rect x="105" y="32" width="95" height="25" rx="6" fill="#312e81" stroke="#6366f1" stroke-width="1"/>
								<text x="152" y="48" text-anchor="middle" fill="#a5b4fc" font-size="9">get_single_index</text>
								
								<rect x="0" y="64" width="95" height="25" rx="6" fill="#312e81" stroke="#6366f1" stroke-width="1"/>
								<text x="47" y="80" text-anchor="middle" fill="#a5b4fc" font-size="9">search_notes</text>
								
								<rect x="105" y="64" width="95" height="25" rx="6" fill="#312e81" stroke="#6366f1" stroke-width="1"/>
								<text x="152" y="80" text-anchor="middle" fill="#a5b4fc" font-size="9">get_document</text>
							</g>
							
							<text x="115" y="160" text-anchor="middle" fill="#6366f1" font-size="10">... 외 79개 도구</text>
						</g>
						
						<!-- 화살표: MCP -> LLM (결과 반환) -->
						<line x1="520" y1="200" x2="430" y2="200" stroke="#7c3aed" stroke-width="2" stroke-dasharray="5,3" marker-end="url(#arrowHead)"/>
						<text x="475" y="220" fill="#a78bfa" font-size="9">결과 반환</text>
						
						<!-- 화살표: LLM -> Response -->
						<line x1="340" y1="240" x2="340" y2="300" stroke="url(#arrowGradient)" stroke-width="2" marker-end="url(#arrowHead)"/>
						
						<!-- 최종 응답 -->
						<g transform="translate(280, 310)">
							<rect x="0" y="0" width="120" height="60" rx="12" fill="#1e1b4b" stroke="#22c55e" stroke-width="2"/>
							<text x="60" y="25" text-anchor="middle" fill="#86efac" font-size="12" font-weight="600">Response</text>
							<text x="60" y="42" text-anchor="middle" fill="#4ade80" font-size="11">분석 결과</text>
						</g>
					</svg>
					
					<!-- 설명 -->
					<div class="mt-6 p-4 bg-purple-900/20 border border-purple-700/30 rounded-xl">
						<h4 class="text-sm font-semibold text-purple-300 mb-2">Single Agent 특징</h4>
						<ul class="text-sm text-gray-300 space-y-1">
							<li>• <strong>ReAct 패턴</strong>: LLM이 자율적으로 Reasoning(추론)과 Acting(행동)을 반복</li>
							<li>• <strong>85개 MCP 도구</strong>에 직접 연결되어 필요한 도구를 자유롭게 선택</li>
							<li>• 단일 LLM이 모든 분석을 담당하여 일관된 맥락 유지</li>
							<li>• 복잡한 질문도 도구 호출을 반복하며 단계적으로 해결</li>
						</ul>
					</div>
				{:else}
					<!-- Multi Agent 워크플로우 다이어그램 -->
					<svg viewBox="0 0 950 800" class="w-full min-w-[900px]" xmlns="http://www.w3.org/2000/svg">
						<!-- 배경 그라디언트 -->
						<defs>
							<linearGradient id="emeraldGradient" x1="0%" y1="0%" x2="100%" y2="100%">
								<stop offset="0%" style="stop-color:#059669;stop-opacity:0.2" />
								<stop offset="100%" style="stop-color:#10b981;stop-opacity:0.1" />
							</linearGradient>
							<linearGradient id="emeraldArrow" x1="0%" y1="0%" x2="100%" y2="0%">
								<stop offset="0%" style="stop-color:#10b981" />
								<stop offset="100%" style="stop-color:#059669" />
							</linearGradient>
							<linearGradient id="orangeGradient" x1="0%" y1="0%" x2="100%" y2="100%">
								<stop offset="0%" style="stop-color:#d97706;stop-opacity:0.3" />
								<stop offset="100%" style="stop-color:#f59e0b;stop-opacity:0.15" />
							</linearGradient>
							<marker id="greenArrow" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
								<polygon points="0 0, 10 3.5, 0 7" fill="#10b981" />
							</marker>
							<marker id="orangeArrow" markerWidth="10" markerHeight="7" refX="9" refY="3.5" orient="auto">
								<polygon points="0 0, 10 3.5, 0 7" fill="#f59e0b" />
							</marker>
						</defs>
						
						<!-- 사용자 질문 -->
						<g transform="translate(405, 20)">
							<rect x="0" y="0" width="140" height="50" rx="12" fill="#064e3b" stroke="#10b981" stroke-width="2"/>
							<text x="70" y="22" text-anchor="middle" fill="#a7f3d0" font-size="12" font-weight="600">User Query</text>
							<text x="70" y="38" text-anchor="middle" fill="#6ee7b7" font-size="10">"국내 3대 생보사의 CSM..."</text>
						</g>
						
						<!-- 화살표 -->
						<line x1="475" y1="70" x2="475" y2="95" stroke="url(#emeraldArrow)" stroke-width="2" marker-end="url(#greenArrow)"/>
						
						<!-- DartMasterAgent -->
						<g transform="translate(375, 100)">
							<rect x="0" y="0" width="200" height="70" rx="16" fill="url(#emeraldGradient)" stroke="#10b981" stroke-width="2"/>
							<text x="100" y="28" text-anchor="middle" fill="#ecfdf5" font-size="14" font-weight="700">DartMasterAgent</text>
							<text x="100" y="48" text-anchor="middle" fill="#a7f3d0" font-size="11">마스터 오케스트레이터</text>
							<text x="100" y="62" text-anchor="middle" fill="#6ee7b7" font-size="9">워크플로우 조정 및 결과 통합</text>
						</g>
						
						<!-- 화살표: Master -> Intent -->
						<line x1="475" y1="170" x2="475" y2="195" stroke="url(#emeraldArrow)" stroke-width="2" marker-end="url(#greenArrow)"/>
						
						<!-- IntentClassifierAgent -->
						<g transform="translate(355, 200)">
							<rect x="0" y="0" width="240" height="60" rx="12" fill="#064e3b" stroke="#059669" stroke-width="2"/>
							<text x="120" y="24" text-anchor="middle" fill="#a7f3d0" font-size="12" font-weight="600">IntentClassifierAgent</text>
							<text x="120" y="42" text-anchor="middle" fill="#6ee7b7" font-size="10">의도 분류 + 에이전트 선택 + 기업 식별</text>
						</g>
						
						<!-- 분기 화살표들 -->
						<line x1="475" y1="260" x2="475" y2="290" stroke="url(#emeraldArrow)" stroke-width="2"/>
						<!-- 좌측 분기 -->
						<path d="M 475 290 L 100 290 L 100 330" fill="none" stroke="#10b981" stroke-width="2" marker-end="url(#greenArrow)"/>
						<path d="M 475 290 L 230 290 L 230 330" fill="none" stroke="#10b981" stroke-width="2" marker-end="url(#greenArrow)"/>
						<path d="M 475 290 L 360 290 L 360 330" fill="none" stroke="#10b981" stroke-width="2" marker-end="url(#greenArrow)"/>
						<!-- 중앙 -->
						<path d="M 475 290 L 475 330" fill="none" stroke="#10b981" stroke-width="2" marker-end="url(#greenArrow)"/>
						<!-- 우측 분기 -->
						<path d="M 475 290 L 590 290 L 590 330" fill="none" stroke="#10b981" stroke-width="2" marker-end="url(#greenArrow)"/>
						<path d="M 475 290 L 720 290 L 720 330" fill="none" stroke="#10b981" stroke-width="2" marker-end="url(#greenArrow)"/>
						<path d="M 475 290 L 850 290 L 850 330" fill="none" stroke="#10b981" stroke-width="2" marker-end="url(#greenArrow)"/>
						
						<!-- 전문 에이전트들 (1차 분석) -->
						<!-- Financial -->
						<g transform="translate(30, 335)">
							<rect x="0" y="0" width="140" height="80" rx="10" fill="#064e3b" stroke="#047857" stroke-width="1.5"/>
							<text x="70" y="18" text-anchor="middle" fill="#a7f3d0" font-size="10" font-weight="600">FinancialAgent</text>
							<line x1="10" y1="26" x2="130" y2="26" stroke="#047857" stroke-width="1" opacity="0.5"/>
							<text x="70" y="42" text-anchor="middle" fill="#6ee7b7" font-size="8">• 재무제표 분석</text>
							<text x="70" y="54" text-anchor="middle" fill="#6ee7b7" font-size="8">• CSM/K-ICS 분석</text>
							<text x="70" y="66" text-anchor="middle" fill="#6ee7b7" font-size="8">• 수익성 평가</text>
						</g>
						
						<!-- Governance -->
						<g transform="translate(160, 335)">
							<rect x="0" y="0" width="140" height="80" rx="10" fill="#064e3b" stroke="#047857" stroke-width="1.5"/>
							<text x="70" y="18" text-anchor="middle" fill="#a7f3d0" font-size="10" font-weight="600">GovernanceAgent</text>
							<line x1="10" y1="26" x2="130" y2="26" stroke="#047857" stroke-width="1" opacity="0.5"/>
							<text x="70" y="42" text-anchor="middle" fill="#6ee7b7" font-size="8">• 지배구조 분석</text>
							<text x="70" y="54" text-anchor="middle" fill="#6ee7b7" font-size="8">• 주주 현황</text>
							<text x="70" y="66" text-anchor="middle" fill="#6ee7b7" font-size="8">• 이사회 구성</text>
						</g>
						
						<!-- DocumentAnalysis -->
						<g transform="translate(290, 335)">
							<rect x="0" y="0" width="140" height="80" rx="10" fill="#064e3b" stroke="#047857" stroke-width="1.5"/>
							<text x="70" y="18" text-anchor="middle" fill="#a7f3d0" font-size="10" font-weight="600">DocumentAgent</text>
							<line x1="10" y1="26" x2="130" y2="26" stroke="#047857" stroke-width="1" opacity="0.5"/>
							<text x="70" y="42" text-anchor="middle" fill="#6ee7b7" font-size="8">• 공시 문서 분석</text>
							<text x="70" y="54" text-anchor="middle" fill="#6ee7b7" font-size="8">• 재무제표 주석</text>
							<text x="70" y="66" text-anchor="middle" fill="#6ee7b7" font-size="8">• 사업보고서</text>
						</g>
						
						<!-- CapitalChange -->
						<g transform="translate(405, 335)">
							<rect x="0" y="0" width="140" height="80" rx="10" fill="#064e3b" stroke="#047857" stroke-width="1.5"/>
							<text x="70" y="18" text-anchor="middle" fill="#a7f3d0" font-size="10" font-weight="600">CapitalAgent</text>
							<line x1="10" y1="26" x2="130" y2="26" stroke="#047857" stroke-width="1" opacity="0.5"/>
							<text x="70" y="42" text-anchor="middle" fill="#6ee7b7" font-size="8">• 자본변동 분석</text>
							<text x="70" y="54" text-anchor="middle" fill="#6ee7b7" font-size="8">• 배당 정책</text>
							<text x="70" y="66" text-anchor="middle" fill="#6ee7b7" font-size="8">• 증자/감자</text>
						</g>
						
						<!-- DebtFunding -->
						<g transform="translate(520, 335)">
							<rect x="0" y="0" width="140" height="80" rx="10" fill="#064e3b" stroke="#047857" stroke-width="1.5"/>
							<text x="70" y="18" text-anchor="middle" fill="#a7f3d0" font-size="10" font-weight="600">DebtFundingAgent</text>
							<line x1="10" y1="26" x2="130" y2="26" stroke="#047857" stroke-width="1" opacity="0.5"/>
							<text x="70" y="42" text-anchor="middle" fill="#6ee7b7" font-size="8">• 부채 구조</text>
							<text x="70" y="54" text-anchor="middle" fill="#6ee7b7" font-size="8">• 자금조달</text>
							<text x="70" y="66" text-anchor="middle" fill="#6ee7b7" font-size="8">• 회사채 발행</text>
						</g>
						
						<!-- Business Structure -->
						<g transform="translate(650, 335)">
							<rect x="0" y="0" width="140" height="80" rx="10" fill="#064e3b" stroke="#047857" stroke-width="1.5"/>
							<text x="70" y="18" text-anchor="middle" fill="#a7f3d0" font-size="10" font-weight="600">BusinessAgent</text>
							<line x1="10" y1="26" x2="130" y2="26" stroke="#047857" stroke-width="1" opacity="0.5"/>
							<text x="70" y="42" text-anchor="middle" fill="#6ee7b7" font-size="8">• 사업구조 분석</text>
							<text x="70" y="54" text-anchor="middle" fill="#6ee7b7" font-size="8">• 자회사 현황</text>
							<text x="70" y="66" text-anchor="middle" fill="#6ee7b7" font-size="8">• 사업 부문</text>
						</g>
						
						<!-- Others -->
						<g transform="translate(780, 335)">
							<rect x="0" y="0" width="140" height="80" rx="10" fill="#064e3b" stroke="#047857" stroke-width="1.5"/>
							<text x="70" y="18" text-anchor="middle" fill="#a7f3d0" font-size="10" font-weight="600">기타 에이전트</text>
							<line x1="10" y1="26" x2="130" y2="26" stroke="#047857" stroke-width="1" opacity="0.5"/>
							<text x="70" y="42" text-anchor="middle" fill="#6ee7b7" font-size="8">• OverseasAgent</text>
							<text x="70" y="54" text-anchor="middle" fill="#6ee7b7" font-size="8">• LegalRiskAgent</text>
							<text x="70" y="66" text-anchor="middle" fill="#6ee7b7" font-size="8">• ExecutiveAgent</text>
						</g>
						
						<!-- 1차 결과 수집 화살표들 -->
						<path d="M 100 415 L 100 445 L 475 445" fill="none" stroke="#10b981" stroke-width="1.5"/>
						<path d="M 230 415 L 230 445" fill="none" stroke="#10b981" stroke-width="1.5"/>
						<path d="M 360 415 L 360 445" fill="none" stroke="#10b981" stroke-width="1.5"/>
						<path d="M 475 415 L 475 445" fill="none" stroke="#10b981" stroke-width="1.5"/>
						<path d="M 590 415 L 590 445" fill="none" stroke="#10b981" stroke-width="1.5"/>
						<path d="M 720 415 L 720 445" fill="none" stroke="#10b981" stroke-width="1.5"/>
						<path d="M 850 415 L 850 445 L 475 445" fill="none" stroke="#10b981" stroke-width="1.5"/>
						
						<line x1="475" y1="445" x2="475" y2="475" stroke="url(#emeraldArrow)" stroke-width="2" marker-end="url(#greenArrow)"/>
						
						<!-- 추가 분석 판단 (핵심 추가!) -->
						<g transform="translate(325, 480)">
							<rect x="0" y="0" width="300" height="70" rx="14" fill="url(#orangeGradient)" stroke="#f59e0b" stroke-width="2" stroke-dasharray="5,3"/>
							<text x="150" y="24" text-anchor="middle" fill="#fef3c7" font-size="13" font-weight="700">🔄 추가 분석 판단</text>
							<text x="150" y="42" text-anchor="middle" fill="#fcd34d" font-size="10">_determine_additional_agents()</text>
							<text x="150" y="58" text-anchor="middle" fill="#fbbf24" font-size="9">"더 깊이 분석해봐" → 추가 에이전트 호출</text>
						</g>
						
						<!-- 분기: 추가 분석 필요 여부 -->
						<line x1="475" y1="550" x2="475" y2="570" stroke="#f59e0b" stroke-width="2"/>
						
						<!-- 추가 분석 필요 시 우회 루프 -->
						<path d="M 625 515 Q 750 515 750 400 Q 750 320 680 320" fill="none" stroke="#f59e0b" stroke-width="2" stroke-dasharray="6,3" marker-end="url(#orangeArrow)"/>
						<text x="770" y="420" fill="#fcd34d" font-size="9" transform="rotate(90, 770, 420)">추가 에이전트 호출</text>
						
						<!-- Yes/No 레이블 -->
						<text x="640" y="510" fill="#fcd34d" font-size="9" font-weight="600">YES</text>
						<text x="490" y="590" fill="#6ee7b7" font-size="9" font-weight="600">NO (충분)</text>
						
						<!-- 결과 통합 -->
						<g transform="translate(375, 600)">
							<rect x="0" y="0" width="200" height="55" rx="12" fill="#064e3b" stroke="#10b981" stroke-width="2"/>
							<text x="100" y="22" text-anchor="middle" fill="#a7f3d0" font-size="12" font-weight="600">Result Merge</text>
							<text x="100" y="38" text-anchor="middle" fill="#6ee7b7" font-size="10">분석 결과 통합</text>
							<text x="100" y="50" text-anchor="middle" fill="#6ee7b7" font-size="9">+ 최종 보고서 생성</text>
						</g>
						
						<!-- 최종 응답 -->
						<line x1="475" y1="655" x2="475" y2="685" stroke="url(#emeraldArrow)" stroke-width="2" marker-end="url(#greenArrow)"/>
						<g transform="translate(405, 690)">
							<rect x="0" y="0" width="140" height="45" rx="10" fill="#064e3b" stroke="#22c55e" stroke-width="2"/>
							<text x="70" y="20" text-anchor="middle" fill="#86efac" font-size="12" font-weight="600">Final Report</text>
							<text x="70" y="36" text-anchor="middle" fill="#4ade80" font-size="9">종합 분석 보고서</text>
						</g>
						
						<!-- 범례 -->
						<g transform="translate(30, 720)">
							<rect x="0" y="0" width="200" height="65" rx="8" fill="#1f2937" stroke="#374151" stroke-width="1"/>
							<text x="10" y="18" fill="#9ca3af" font-size="10" font-weight="600">범례</text>
							<line x1="10" y1="25" x2="50" y2="25" stroke="#10b981" stroke-width="2"/>
							<text x="55" y="28" fill="#6ee7b7" font-size="9">정상 흐름</text>
							<line x1="10" y1="40" x2="50" y2="40" stroke="#f59e0b" stroke-width="2" stroke-dasharray="5,3"/>
							<text x="55" y="43" fill="#fcd34d" font-size="9">추가 분석 루프</text>
							<text x="10" y="58" fill="#9ca3af" font-size="8">needs_deep_analysis=true 시 발동</text>
						</g>
					</svg>
					
					<!-- 설명 -->
					<div class="mt-6 p-4 bg-emerald-900/20 border border-emerald-700/30 rounded-xl">
						<h4 class="text-sm font-semibold text-emerald-300 mb-2">Multi Agent 특징</h4>
						<ul class="text-sm text-gray-300 space-y-1.5">
							<li>• <strong>DartMasterAgent</strong>: 전체 워크플로우를 조정하는 마스터 오케스트레이터</li>
							<li>• <strong>IntentClassifierAgent</strong>: 사용자 의도 분석, 필요 에이전트 선택, 대상 기업 식별</li>
							<li>• <strong>9개 전문 에이전트</strong>: 각 도메인(재무, 지배구조, 문서 등)을 전문적으로 분석</li>
							<li>• <strong class="text-amber-300">추가 분석 판단</strong>: 1차 분석 결과가 불충분하면 LLM이 추가 에이전트를 호출하여 심층 분석</li>
							<li>• 복잡한 멀티-기업 비교 분석도 병렬 처리로 효율적 수행</li>
							<li>• 각 에이전트의 분석 결과를 통합하여 종합적인 보고서 생성</li>
						</ul>
					</div>
				{/if}
			</div>
		</div>
	</div>
{/if}
