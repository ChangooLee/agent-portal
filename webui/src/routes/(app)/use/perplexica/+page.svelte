<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { fly, fade } from 'svelte/transition';
	import { toast } from 'svelte-sonner';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';
	import { afterNavigate } from '$app/navigation';
	import Markdown from '$lib/components/chat/Messages/Markdown.svelte';
	import { applyPatch } from 'rfc6902';
	
	// 원본 Perplexica 구조에 맞춘 타입 정의
	type Chunk = {
		content: string;
		metadata: Record<string, any>;
	};
	
	type TextBlock = {
		id: string;
		type: 'text';
		data: string;
	};
	
	type SourceBlock = {
		id: string;
		type: 'source';
		data: Chunk[];
	};
	
	type SuggestionBlock = {
		id: string;
		type: 'suggestion';
		data: string[];
	};
	
	type WidgetBlock = {
		id: string;
		type: 'widget';
		data: {
			widgetType: string;
			params: Record<string, any>;
		};
	};
	
	type ReasoningResearchBlock = {
		id: string;
		type: 'reasoning';
		reasoning: string;
	};
	
	type SearchingResearchBlock = {
		id: string;
		type: 'searching';
		searching: string[];
	};
	
	type SearchResultsResearchBlock = {
		id: string;
		type: 'search_results';
		reading: Chunk[];
	};
	
	type ReadingResearchBlock = {
		id: string;
		type: 'reading';
		reading: Chunk[];
	};
	
	type ResearchBlockSubStep =
		| ReasoningResearchBlock
		| SearchingResearchBlock
		| SearchResultsResearchBlock
		| ReadingResearchBlock;
	
	type ResearchBlock = {
		id: string;
		type: 'research';
		data: {
			subSteps: ResearchBlockSubStep[];
		};
	};
	
	type Block = TextBlock | SourceBlock | SuggestionBlock | WidgetBlock | ResearchBlock;
	
	// 원본 Perplexica Message 구조
	interface Message {
		messageId: string;
		chatId: string;
		backendId?: string;
		query: string;
		responseBlocks: Block[];
		status: 'answering' | 'completed' | 'error';
		createdAt: Date;
	}
	
	// 원본 Perplexica Section 구조
	interface Section {
		message: Message;
		parsedTextBlocks: string[];
		sources: Chunk[];
		suggestions?: string[];
		widgets: Array<{
			widgetType: string;
			params: Record<string, any>;
		}>;
		speechMessage: string;
		thinkingEnded: boolean;
	}
	
	// 레거시 호환을 위한 타입 (점진적 제거 예정)
	interface MessageSection {
		messageId: string;
		query: string;
		response: string;
		sources: Array<{
			pageContent: string;
			metadata: Record<string, any>;
		}>;
		suggestions?: string[];
		createdAt: Date;
		isLoading?: boolean;
	}
	
	// Focus Mode 타입
	type FocusMode = 'webSearch' | 'academicSearch' | 'youtubeSearch' | 'writingAssistant' | 'wolframAlpha' | 'redditSearch';
	
	// Optimization Mode 타입
	type OptimizationMode = 'speed' | 'balanced' | 'quality';
	
	// 모델 프로바이더 타입
	interface ModelProvider {
        id: string;
        name: string;
		chatModels: Array<{ key: string; name: string }>;
		embeddingModels: Array<{ key: string; name: string }>;
	}
	
	// 채팅 히스토리 타입
	interface ChatHistory {
		id: string;
		title: string;
		createdAt: string;
		updatedAt: string;
		focusMode: string;
	}
	
	let messages: Message[] = [];
	let sections: Section[] = [];
	let inputValue = '';
	let isLoading = false;
	let researchEnded = false;
	let messageAppeared = false;
	
	// 채팅 히스토리 (원본 Perplexica 구조)
	let chatHistory: Array<[string, string]> = [];
	let messagesContainer: HTMLDivElement;
	let dividerRef: HTMLDivElement | null = null;
	let dividerWidth = 0;
	let focusModePopoverRef: HTMLDivElement;
	let optimizationModePopoverRef: HTMLDivElement;
	let modelSelectorPopoverRef: HTMLDivElement;
	let exportPopoverRef: HTMLDivElement;
	// Single/Multi mode용 별도 ref
	let singleOptimizationModePopoverRef: HTMLDivElement | undefined;
	let singleFocusModePopoverRef: HTMLDivElement | undefined;
	let singleModelSelectorPopoverRef: HTMLDivElement | undefined;
	let multiFocusModePopoverRef: HTMLDivElement | undefined;
	let multiModelSelectorPopoverRef: HTMLDivElement | undefined;
	
	// Helper function for conditional dividerRef binding
	function handleDividerRef(node: HTMLDivElement, isLast: boolean) {
		if (isLast) {
			dividerRef = node;
		}
		return {
			destroy() {
				if (dividerRef === node) {
					dividerRef = null;
				}
			}
		};
	}
	
	// Focus Mode 설정
	const focusModes: Array<{ value: FocusMode; label: string; icon: string }> = [
		{ value: 'webSearch', label: '웹 검색', icon: '' },
		{ value: 'academicSearch', label: '학술 검색', icon: '' },
		{ value: 'youtubeSearch', label: 'YouTube 검색', icon: '' },
		{ value: 'writingAssistant', label: '글쓰기 보조', icon: '' },
		{ value: 'wolframAlpha', label: '계산/분석', icon: '' },
		{ value: 'redditSearch', label: 'Reddit 검색', icon: '' }
	];
	let selectedFocusMode: FocusMode = 'webSearch';
	
	// Optimization Mode 설정
	let selectedOptimizationMode: OptimizationMode = 'balanced';
	
	// 모델 설정
	let providers: ModelProvider[] = [];
	let selectedChatModel: { providerId: string; key: string } | null = null;
	let selectedEmbeddingModel: { providerId: string; key: string } | null = null;
	let loadingProviders = false;
	
	// 채팅 히스토리 (라이브러리 페이지로 이동)
	let currentChatId: string | null = null;
	let loadingHistory = false;
	let isMounted = false;
	
	// 시스템 지시사항
	let systemInstructions = '';
	
	// Popover 상태
	let showFocusModePopover = false;
	let showOptimizationModePopover = false;
	let showModelSelectorPopover = false;
	let modelSearchQuery = '';
	
	// Settings 다이얼로그 상태
	let showSettingsDialog = false;
	let settingsActiveSection: 'preferences' | 'personalization' | 'models' = 'personalization';
	
	// Export Popover 상태
	let showExportPopover = false;
	
	// Sources 모달 상태
	let sourcesModalOpen: Record<string, boolean> = {};
	
	// 이미지/비디오 위젯 상태
	interface ImageData {
		url: string;
		img_src: string;
		title: string;
	}
	
	interface VideoData {
		url: string;
		img_src: string;
		title: string;
		iframe_src: string;
	}
	
	let imageWidgets: Record<string, { images: ImageData[] | null; loading: boolean }> = {};
	let videoWidgets: Record<string, { videos: VideoData[] | null; loading: boolean }> = {};
	let lightboxOpen: Record<string, { open: boolean; slides: any[]; currentIndex: number }> = {};
	
	// Optimization Mode 설정
	const optimizationModes: Array<{ value: OptimizationMode; title: string; description: string; icon: string }> = [
		{ value: 'speed', title: '속도', description: '빠른 응답을 위해 최적화합니다.', icon: '' },
		{ value: 'balanced', title: '균형', description: '속도와 품질의 균형을 맞춥니다.', icon: '' },
		{ value: 'quality', title: '품질', description: '높은 품질의 응답을 위해 최적화합니다.', icon: '' }
	];
	
	// 필터된 프로바이더
	$: filteredProviders = providers.map((provider) => ({
		...provider,
		chatModels: provider.chatModels.filter(
			(model) =>
				model.name.toLowerCase().includes(modelSearchQuery.toLowerCase()) ||
				provider.name.toLowerCase().includes(modelSearchQuery.toLowerCase())
		),
		embeddingModels: provider.embeddingModels.filter(
			(model) =>
				model.name.toLowerCase().includes(modelSearchQuery.toLowerCase()) ||
				provider.name.toLowerCase().includes(modelSearchQuery.toLowerCase())
		)
	})).filter((provider) => provider.chatModels.length > 0 || provider.embeddingModels.length > 0);
	
	// 프로바이더 목록 로드
	async function loadProviders() {
		loadingProviders = true;
		try {
			const response = await fetch('/api/perplexica/providers');
			if (response.ok) {
				const data = await response.json();
				providers = data.providers || [];
				
				// 기본 모델 선택 (qwen 모델 우선, 없으면 chatModels와 embeddingModels가 모두 있는 첫 번째 provider)
				if (providers.length > 0) {
					const validProvider = providers.find(
						p => p.chatModels.length > 0 && p.embeddingModels.length > 0
					);
					if (validProvider && validProvider.chatModels.length > 0 && validProvider.embeddingModels.length > 0) {
						// qwen 모델 우선 선택
						const qwenModel = validProvider.chatModels.find(
							m => m.key.includes('qwen') || m.name.toLowerCase().includes('qwen')
						);
						const selectedModel = qwenModel || validProvider.chatModels[0];
						
						if (selectedModel && selectedModel.key) {
							selectedChatModel = {
								providerId: validProvider.id,
								key: selectedModel.key
							};
						}
						
						if (validProvider.embeddingModels[0] && validProvider.embeddingModels[0].key) {
							selectedEmbeddingModel = {
								providerId: validProvider.id,
								key: validProvider.embeddingModels[0].key
							};
						}
					} else {
						console.warn('No valid provider with both chat and embedding models found');
						toast.error('사용 가능한 모델을 찾을 수 없습니다.');
					}
				} else {
					console.warn('No providers found');
					toast.error('모델 프로바이더를 찾을 수 없습니다.');
				}
			} else {
				throw new Error(`Failed to load providers: ${response.status}`);
			}
		} catch (e) {
			console.error('Failed to load providers:', e);
			toast.error('모델 프로바이더를 불러오는데 실패했습니다.');
		} finally {
			loadingProviders = false;
		}
	}
	
	// 라이브러리 페이지로 이동
	function goToLibrary() {
		goto('/use/perplexica/library');
	}
	
	// 특정 채팅 로드
	async function loadChat(chatId: string) {
		// 이미 같은 채팅을 로드 중이면 스킵
		if (currentChatId === chatId && messages.length > 0) {
			console.log('[Perplexica] Chat already loaded:', chatId);
			return;
		}
		
		loadingHistory = true;
		try {
			console.log('[Perplexica] Loading chat:', chatId);
			const response = await fetch(`/api/perplexica/chats/${chatId}`);
			if (!response.ok) {
				if (response.status === 404) {
					throw new Error('채팅을 찾을 수 없습니다.');
				} else if (response.status >= 500) {
					throw new Error('서버 오류가 발생했습니다. 잠시 후 다시 시도해주세요.');
				} else {
					throw new Error(`채팅을 불러오는데 실패했습니다. (${response.status})`);
				}
			}
			
			const data = await response.json();
			console.log('[Perplexica] Chat data loaded:', data);
			
			// 빈 응답 또는 잘못된 데이터 형식 처리
			if (!data || !Array.isArray(data.messages)) {
				throw new Error('채팅 데이터 형식이 올바르지 않습니다.');
			}
			
			// 원본 Perplexica 구조: messages는 responseBlocks를 포함
			const loadedMessages: Message[] = (data.messages || []).map((msg: any) => ({
				messageId: msg.messageId,
				chatId: msg.chatId || chatId,
				backendId: msg.backendId,
				query: msg.query,
				responseBlocks: msg.responseBlocks || [],
				status: (msg.status || 'completed') as 'answering' | 'completed' | 'error',
				createdAt: new Date(msg.createdAt || Date.now())
			}));
			
			console.log('[Perplexica] Loaded messages:', loadedMessages.length, loadedMessages);
			messages = loadedMessages;
			currentChatId = chatId;
			selectedFocusMode = (data.chat?.focusMode || 'webSearch') as FocusMode;
			setTimeout(scrollToBottom, 100);
		} catch (e: any) {
			console.error('[Perplexica] Failed to load chat:', e);
			const errorMessage = e.message || '채팅을 불러오는데 실패했습니다.';
			toast.error(errorMessage);
			// 에러 발생 시 새 채팅 시작
			startNewChat();
		} finally {
			loadingHistory = false;
		}
	}
	
	// 새 채팅 시작
	function startNewChat() {
		currentChatId = null;
		messages = [];
		sections = [];
		researchEnded = false;
		messageAppeared = false;
	}
	
	// 메시지를 섹션으로 변환 (원본 Perplexica 구조)
	function messagesToSections(): Section[] {
		console.debug('[Perplexica] messagesToSections called, messages:', messages.length);
		return messages.map((msg) => {
			console.debug('[Perplexica] Processing message:', msg.messageId, 'responseBlocks:', msg.responseBlocks?.length || 0);
			const textBlocks: string[] = [];
			let speechMessage = '';
			let thinkingEnded = false;
			let suggestions: string[] = [];
			
			// responseBlocks가 없거나 비어있는 경우 기본값 반환
			if (!msg.responseBlocks || msg.responseBlocks.length === 0) {
				return {
					message: msg,
					parsedTextBlocks: [],
					sources: [],
					suggestions: undefined,
					widgets: [],
					speechMessage: '',
					thinkingEnded: false
				};
			}
			
			const sourceBlocks = msg.responseBlocks.filter(
				(block): block is SourceBlock => block.type === 'source'
			);
			const sources = sourceBlocks.flatMap((block) => block.data || []);
			
			const widgetBlocks = msg.responseBlocks
				.filter((b): b is WidgetBlock => b.type === 'widget')
				.map((b) => b.data)
				.filter((d) => d != null);
			
			msg.responseBlocks.forEach((block) => {
				console.debug('[Perplexica] Processing block:', block.type, block.id);
				if (block.type === 'text') {
					// block.data가 없거나 비어있는 경우 처리
					if (!block.data || typeof block.data !== 'string') {
						textBlocks.push('');
						return;
					}
					
					let processedText = block.data;
					const citationRegex = /\[([^\]]+)\]/g;
					const regex = /\[(\d+)\]/g;
					
					// [widgets_result] 플레이스홀더 제거 (위젯은 별도로 렌더링됨)
					processedText = processedText.replace(/\[widgets_result\]/g, '');
					
					// thinking 태그 처리
					if (processedText.includes('<think>')) {
						const openThinkTag = (processedText.match(/<think>/g)?.length || 0);
						const closeThinkTag = (processedText.match(/<\/think>/g)?.length || 0);
						
						if (openThinkTag && !closeThinkTag) {
							processedText += '</think> <a> </a>';
						}
					}
					
					if (block.data.includes('</think>')) {
						thinkingEnded = true;
					}
					
					// Citation 처리 - 표준 Markdown 링크 형식으로 변환
					if (sources.length > 0) {
						processedText = processedText.replace(
							citationRegex,
							(_, capturedContent: string) => {
								const numbers = capturedContent
									.split(',')
									.map((numStr) => numStr.trim());
								
								const linksMarkdown = numbers
									.map((numStr) => {
										const number = parseInt(numStr);
										
										if (isNaN(number) || number <= 0) {
											return `[${numStr}]`;
										}
										
										const source = sources[number - 1];
										const url = source?.metadata?.url;
										
										if (url) {
											// 표준 Markdown 링크 형식으로 변환
											return `[${numStr}](${url})`;
										} else {
											return `[${numStr}]`;
										}
									})
									.join(' ');
								
								return linksMarkdown;
							}
						);
						speechMessage += block.data.replace(regex, '');
					} else {
						processedText = processedText.replace(regex, '');
						speechMessage += block.data.replace(regex, '');
					}
					
					textBlocks.push(processedText);
				} else if (block.type === 'suggestion') {
					const suggestionBlock = block as SuggestionBlock;
					if (suggestionBlock.data && Array.isArray(suggestionBlock.data)) {
						suggestions = suggestionBlock.data;
					}
				}
			});
			
			return {
				message: msg,
				parsedTextBlocks: textBlocks,
				sources: sources,
				suggestions: suggestions.length > 0 ? suggestions : undefined,
				widgets: widgetBlocks,
				speechMessage: speechMessage,
				thinkingEnded: thinkingEnded
			};
		});
	}
	
	// 섹션 배열 업데이트 (반응형) - messages 변경 시 자동 업데이트
	$: messages, sections = messagesToSections();
	$: console.debug('[Perplexica] Sections updated:', sections.length, 'messages:', messages.length);
	
	// 메시지 핸들러 (원본 useChat.tsx의 getMessageHandler 로직)
	function getMessageHandler(message: Message) {
		const messageId = message.messageId;
		
		return (data: any) => {
			console.debug('[Perplexica] Received event:', data.type, data);
			
			if (data.type === 'error') {
				toast.error(data.data);
				isLoading = false;
				messages = [...messages.map((msg) =>
					msg.messageId === messageId
						? { ...msg, status: 'error' as const }
						: msg
				)];
				return;
			}
			
			if (data.type === 'researchComplete') {
				console.debug('[Perplexica] Research complete');
				researchEnded = true;
				const currentMsg = messages.find((m) => m.messageId === messageId);
				if (currentMsg?.responseBlocks.find(
					(b) => b.type === 'source' && (b as SourceBlock).data.length > 0
				)) {
					messageAppeared = true;
				}
			}
			
			if (data.type === 'block') {
				console.debug('[Perplexica] Block event:', data.block.type, data.block.id);
				messages = [...messages.map((msg) => {
					if (msg.messageId === messageId) {
						const exists = msg.responseBlocks.findIndex(
							(b) => b.id === data.block.id
						);
						
						if (exists !== -1) {
							const existingBlocks = [...msg.responseBlocks];
							existingBlocks[exists] = data.block;
							
							return {
								...msg,
								responseBlocks: existingBlocks,
							};
						}
						
						return {
							...msg,
							responseBlocks: [...msg.responseBlocks, data.block],
						};
					}
					return msg;
				})];
				
				if (
					(data.block.type === 'source' && (data.block as SourceBlock).data.length > 0) ||
					data.block.type === 'text'
				) {
					messageAppeared = true;
				}
			}
			
			if (data.type === 'updateBlock') {
				console.debug('[Perplexica] UpdateBlock event:', data.blockId, data.patch);
				messages = [...messages.map((msg) => {
					if (msg.messageId === messageId) {
						const updatedBlocks = msg.responseBlocks.map((block) => {
							if (block.id === data.blockId) {
								const updatedBlock = { ...block };
								applyPatch(updatedBlock, data.patch);
								return updatedBlock;
							}
							return block;
						});
						return { ...msg, responseBlocks: updatedBlocks };
					}
					return msg;
				})];
			}
			
			if (data.type === 'messageEnd') {
				console.debug('[Perplexica] MessageEnd event');
				const currentMsg = messages.find((msg) => msg.messageId === messageId);
				
				messages = [...messages.map((msg) =>
					msg.messageId === messageId
						? { ...msg, status: 'completed' as const }
						: msg
				)];
				
				const newHistory: [string, string][] = [
					...chatHistory,
					['human', message.query],
					[
						'assistant',
						currentMsg?.responseBlocks.find((b) => b.type === 'text')?.data ||
							'',
					],
				];
				
				chatHistory = newHistory;
				
				isLoading = false;
				
				// suggestions 로드 (소스가 있고 suggestions가 없을 때)
				const hasSourceBlocks = currentMsg?.responseBlocks.some(
					(block) => block.type === 'source' && (block as SourceBlock).data.length > 0
				);
				const hasSuggestions = currentMsg?.responseBlocks.some(
					(block) => block.type === 'suggestion'
				);
				
				// 히스토리는 라이브러리 페이지에서 관리
			}
		};
	}
	
	// 메시지 전송 (원본 구조)
	async function sendMessage() {
		if (!inputValue.trim() || isLoading) return;
		if (!selectedChatModel || !selectedEmbeddingModel) {
			toast.error('모델을 선택해주세요.');
			return;
		}
		
		const question = inputValue.trim();
		inputValue = '';
		isLoading = true;
		researchEnded = false;
		messageAppeared = false;
		
		// 새 채팅이면 chatId 생성
		if (!currentChatId) {
			currentChatId = generateChatId();
		}
		
		const messageId = generateId();
		const backendId = generateBackendId();
		
		// 원본 Perplexica Message 구조로 생성
		const newMessage: Message = {
			messageId,
			chatId: currentChatId,
			backendId,
			query: question,
			responseBlocks: [],
			status: 'answering',
			createdAt: new Date(),
		};
		
		messages = [...messages, newMessage];
		setTimeout(scrollToBottom, 50);
		
		// focusMode를 sources 배열로 변환
		const focusModeToSources: Record<FocusMode, string[]> = {
			'webSearch': ['web'],
			'academicSearch': ['academic'],
			'youtubeSearch': ['web'],
			'writingAssistant': ['web'],
			'wolframAlpha': ['web'],
			'redditSearch': ['discussions']
		};
		const sources = focusModeToSources[selectedFocusMode] || ['web'];
		
		// 채팅 히스토리 생성 (원본 구조)
		const history: Array<[string, string]> = messages
			.filter((m) => m.status === 'completed')
			.flatMap((m) => {
				const textBlock = m.responseBlocks.find((b) => b.type === 'text') as TextBlock | undefined;
				return [
					['human', m.query] as [string, string],
					['assistant', textBlock?.data || ''] as [string, string]
				];
			});
		
		try {
			const response = await fetch('/api/perplexica/chat', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					message: {
						messageId,
						chatId: currentChatId,
						content: question
					},
					optimizationMode: selectedOptimizationMode,
					sources: sources,
					history: history,
					files: [],
					chatModel: {
						providerId: selectedChatModel.providerId,
						key: selectedChatModel.key
					},
					embeddingModel: {
						providerId: selectedEmbeddingModel.providerId,
						key: selectedEmbeddingModel.key
					},
					systemInstructions: systemInstructions || null
				})
			});
			
			if (!response.ok) {
				throw new Error('API 요청 실패');
			}
			
			if (!response.body) {
				throw new Error('No response body');
			}
			
			const reader = response.body.getReader();
			const decoder = new TextDecoder('utf-8');
			
			let partialChunk = '';
			const messageHandler = getMessageHandler(newMessage);
			
			try {
				while (true) {
					const { value, done } = await reader.read();
					if (done) break;
					
					partialChunk += decoder.decode(value, { stream: true });
					
					// 원본 Perplexica 방식: 줄바꿈으로 분리하고 각 라인 파싱
					// 마지막 불완전한 줄은 보관
					const lines = partialChunk.split('\n');
					partialChunk = lines.pop() || ''; // 마지막 줄은 다음 청크와 합쳐질 수 있음
					
					for (const msg of lines) {
						if (!msg.trim()) continue;
						try {
							const json = JSON.parse(msg);
							console.debug('[Perplexica] Parsed JSON:', json.type);
							messageHandler(json);
						} catch (parseError) {
							// 개별 라인 파싱 실패는 무시 (불완전한 JSON일 수 있음)
							console.debug('[Perplexica] Failed to parse line:', parseError, msg.substring(0, 100));
						}
					}
				}
				
				// 마지막 남은 청크 처리
				if (partialChunk.trim()) {
					try {
						const json = JSON.parse(partialChunk.trim());
						console.debug('[Perplexica] Parsed final JSON:', json.type);
						messageHandler(json);
					} catch (e) {
						console.debug('[Perplexica] Failed to parse final chunk:', e);
					}
				}
			} catch (e: any) {
				console.error('Stream read error:', e);
				isLoading = false;
				toast.error('스트림 읽기 오류가 발생했습니다.');
			}
		} catch (e: any) {
			console.error('Failed to send message:', e);
		toast.error(e.message || '메시지 전송에 실패했습니다.');
		isLoading = false;
		messages = [...messages.map((msg) =>
			msg.messageId === messageId
				? { ...msg, status: 'error' as const }
				: msg
		)];
		}
	}
	
	function scrollToBottom() {
		if (messagesContainer) {
			messagesContainer.scrollTop = messagesContainer.scrollHeight;
		}
	}
	
	function generateId() {
		// 원본 Perplexica와 동일한 형식: crypto.randomBytes(7).toString('hex')
		const array = new Uint8Array(7);
		crypto.getRandomValues(array);
		return Array.from(array, byte => byte.toString(16).padStart(2, '0')).join('');
	}
	
	function generateChatId() {
		// 원본 Perplexica와 동일한 형식: crypto.randomBytes(20).toString('hex')
		const array = new Uint8Array(20);
		crypto.getRandomValues(array);
		return Array.from(array, byte => byte.toString(16).padStart(2, '0')).join('');
	}
	
	function generateBackendId() {
		// 원본 Perplexica와 동일한 형식: crypto.randomBytes(20).toString('hex')
		return generateChatId();
	}
	
	// 이미지 검색
	async function searchImages(messageId: string, query: string) {
		if (!selectedChatModel) return;
		
		imageWidgets[messageId] = { images: null, loading: true };
		imageWidgets = imageWidgets; // 반응형 업데이트
		
		try {
			// 원본 구조: chatHistory는 [['human', query], ['assistant', text]] 형식
			const history: Array<[string, string]> = messages
				.filter((m) => m.status === 'completed')
				.flatMap((m) => {
					const textBlock = m.responseBlocks.find((b) => b.type === 'text') as TextBlock | undefined;
					return [
						['human', m.query] as [string, string],
						['assistant', textBlock?.data || ''] as [string, string]
					];
				});
			
			const response = await fetch('/api/perplexica/images', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					query: query,
					chatHistory: history,
					chatModel: selectedChatModel
				})
			});
			
			if (!response.ok) throw new Error('이미지 검색 실패');
			
			const data = await response.json();
			const images = data.images || [];
			
			imageWidgets[messageId] = { images, loading: false };
			imageWidgets = imageWidgets;
			
			// 라이트박스 슬라이드 준비
			lightboxOpen[messageId] = {
				open: false,
				slides: images.map((img: ImageData) => ({ src: img.img_src })),
				currentIndex: 0
			};
			lightboxOpen = lightboxOpen;
		} catch (e) {
			console.error('Failed to search images:', e);
			imageWidgets[messageId] = { images: [], loading: false };
			imageWidgets = imageWidgets;
		}
	}
	
	// 비디오 검색
	async function searchVideos(messageId: string, query: string) {
		if (!selectedChatModel) return;
		
		videoWidgets[messageId] = { videos: null, loading: true };
		videoWidgets = videoWidgets;
		
		try {
			// 원본 구조: chatHistory는 [['human', query], ['assistant', text]] 형식
			const history: Array<[string, string]> = messages
				.filter((m) => m.status === 'completed')
				.flatMap((m) => {
					const textBlock = m.responseBlocks.find((b) => b.type === 'text') as TextBlock | undefined;
					return [
						['human', m.query] as [string, string],
						['assistant', textBlock?.data || ''] as [string, string]
					];
				});
			
			const response = await fetch('/api/perplexica/videos', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					query: query,
					chatHistory: history,
					chatModel: selectedChatModel
				})
			});
			
			if (!response.ok) throw new Error('비디오 검색 실패');
			
			const data = await response.json();
			const videos = data.videos || [];
			
			videoWidgets[messageId] = { videos, loading: false };
			videoWidgets = videoWidgets;
			
			// 라이트박스 슬라이드 준비
			if (!lightboxOpen[messageId]) {
				lightboxOpen[messageId] = { open: false, slides: [], currentIndex: 0 };
			}
			lightboxOpen[messageId].slides = [
				...lightboxOpen[messageId].slides,
				...videos.map((video: VideoData) => ({
					type: 'video',
					src: video.img_src,
					iframe_src: video.iframe_src
				}))
			];
			lightboxOpen = lightboxOpen;
		} catch (e) {
			console.error('Failed to search videos:', e);
			videoWidgets[messageId] = { videos: [], loading: false };
			videoWidgets = videoWidgets;
		}
	}
	
	// Export 기능
	function exportAsMarkdown() {
		if (messages.length === 0) {
			toast.error('내보낼 메시지가 없습니다.');
			return;
		}
		
		const date = new Date().toLocaleString('ko-KR');
		let md = `# 💬 AI 검색 대화 내보내기\n\n`;
		md += `*내보낸 날짜: ${date}*\n\n---\n`;
		
		messages.forEach((message) => {
			md += `\n---\n`;
			md += `**🧑 사용자**  \n`;
			md += `*${message.createdAt.toLocaleString('ko-KR')}*\n\n`;
			md += `> ${message.query.replace(/\n/g, '\n> ')}\n`;
			
			// 응답 블록 처리
			const textBlocks = message.responseBlocks.filter((b): b is TextBlock => b.type === 'text');
			if (textBlocks.length > 0) {
				md += `\n**🤖 AI**  \n\n`;
				textBlocks.forEach((block) => {
					md += `> ${block.data.replace(/\n/g, '\n> ')}\n`;
				});
			}
			
			// 소스 처리
			const sourceBlocks = message.responseBlocks.filter((b): b is SourceBlock => b.type === 'source');
			if (sourceBlocks.length > 0) {
				md += `\n**출처:**\n`;
				sourceBlocks.forEach((block) => {
					block.data.forEach((src, i) => {
						const url = src.metadata?.url || '';
						md += `- [${i + 1}] [${url}](${url})\n`;
					});
				});
			}
		});
		
		md += '\n---\n';
		
		const blob = new Blob([md], { type: 'text/markdown' });
		const url = URL.createObjectURL(blob);
		const a = document.createElement('a');
		a.href = url;
		a.download = `ai-search-chat-${new Date().toISOString().split('T')[0]}.md`;
		document.body.appendChild(a);
		a.click();
		setTimeout(() => {
			document.body.removeChild(a);
			URL.revokeObjectURL(url);
		}, 0);
		
		showExportPopover = false;
		toast.success('Markdown 파일로 내보냈습니다.');
	}
	
	// 외부 클릭 감지
	function setupClickOutside() {
		const handleClick = (event: MouseEvent) => {
			if (focusModePopoverRef && !focusModePopoverRef.contains(event.target as Node)) {
				showFocusModePopover = false;
			}
			if (optimizationModePopoverRef && !optimizationModePopoverRef.contains(event.target as Node)) {
				showOptimizationModePopover = false;
			}
			if (modelSelectorPopoverRef && !modelSelectorPopoverRef.contains(event.target as Node)) {
				showModelSelectorPopover = false;
			}
			if (singleOptimizationModePopoverRef && !singleOptimizationModePopoverRef.contains(event.target as Node)) {
				showOptimizationModePopover = false;
			}
			if (singleFocusModePopoverRef && !singleFocusModePopoverRef.contains(event.target as Node)) {
				showFocusModePopover = false;
			}
			if (singleModelSelectorPopoverRef && !singleModelSelectorPopoverRef.contains(event.target as Node)) {
				showModelSelectorPopover = false;
			}
			if (multiFocusModePopoverRef && !multiFocusModePopoverRef.contains(event.target as Node)) {
				showFocusModePopover = false;
			}
			if (multiModelSelectorPopoverRef && !multiModelSelectorPopoverRef.contains(event.target as Node)) {
				showModelSelectorPopover = false;
			}
			if (exportPopoverRef && !exportPopoverRef.contains(event.target as Node)) {
				showExportPopover = false;
			}
		};
		document.addEventListener('click', handleClick);
		return () => document.removeEventListener('click', handleClick);
	}
	
	// Divider 너비 업데이트
	function updateDividerWidth() {
		if (dividerRef) {
			dividerWidth = dividerRef.offsetWidth;
		}
	}
	
	// URL 변경 처리 함수
	function handleUrlChange() {
		const chatId = $page.url.searchParams.get('chatId');
		console.log('[Perplexica] URL changed, chatId:', chatId, 'currentChatId:', currentChatId);
		if (chatId && chatId !== currentChatId) {
			console.log('[Perplexica] Loading chat from URL:', chatId);
			loadChat(chatId);
		} else if (!chatId && currentChatId) {
			console.log('[Perplexica] No chatId in URL, starting new chat');
			startNewChat();
		}
	}
	
	// URL 쿼리 파라미터 변경 감지 (reactive) - $page.url.href를 사용하여 변경 감지
	$: if (isMounted && $page.url.href) {
		handleUrlChange();
	}
	
	// afterNavigate로도 URL 변경 감지
	afterNavigate(({ to }) => {
		if (to && isMounted) {
			console.log('[Perplexica] afterNavigate triggered, URL:', to.url.href);
			handleUrlChange();
		}
	});
	
	onMount(() => {
		loadProviders();
		setupClickOutside();
		
		// Divider 너비 업데이트
		updateDividerWidth();
		const resizeObserver = new ResizeObserver(() => {
			updateDividerWidth();
		});
		if (dividerRef) {
			resizeObserver.observe(dividerRef);
		}
		window.addEventListener('resize', updateDividerWidth);
		
		// 초기 URL 쿼리 파라미터 확인
		const chatId = $page.url.searchParams.get('chatId');
		console.log('[Perplexica] onMount, initial chatId:', chatId, 'URL:', $page.url.href);
		if (chatId) {
			loadChat(chatId);
		} else {
			startNewChat();
		}
		
		// reactive statement 활성화
		isMounted = true;
		
		return () => {
			if (dividerRef) {
				resizeObserver.unobserve(dividerRef);
			}
			resizeObserver.disconnect();
			window.removeEventListener('resize', updateDividerWidth);
		};
	});
	
	// 섹션 변경 시 divider 너비 업데이트
	$: if (sections.length > 0) {
		setTimeout(updateDividerWidth, 100);
    }
</script>

<svelte:head>
    <title>AI 검색 | AI Agent Portal</title>
</svelte:head>

<div class="min-h-full bg-gray-950 text-slate-50 flex">
	<!-- 좌측 사이드바 (원본 Perplexica 구조) -->
	<div class="hidden lg:flex lg:w-[72px] lg:flex-col lg:shrink-0 border-r border-gray-800/50">
		<div class="flex flex-col items-center justify-center gap-y-6 bg-gray-900/80 backdrop-blur-sm px-2 py-8 shadow-sm h-full">
			<!-- 새 채팅 버튼 (Home) -->
			<a
				href="/use/perplexica"
				class="p-2.5 rounded-full bg-gray-800/60 text-gray-300 hover:opacity-70 hover:scale-105 transition duration-200"
				on:click|preventDefault={startNewChat}
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
					class="relative flex flex-col items-center justify-center space-y-0.5 cursor-pointer w-full py-2 rounded-lg hover:bg-gray-800/60 transition duration-200 {currentChatId === null ? 'bg-gray-800/60' : ''}"
				>
					<div class="rounded-lg p-1.5">
						<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-6 h-6 text-gray-300">
							<path stroke-linecap="round" stroke-linejoin="round" d="m2.25 12 8.954-8.955c.44-.439 1.152-.439 1.591 0L21.75 12M4.5 9.75v10.125c0 .621.504 1.125 1.125 1.125H9.75v-4.875c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125V21h4.125c.621 0 1.125-.504 1.125-1.125V9.75M8.25 21h8.25" />
						</svg>
					</div>
					<p class="text-[10px] text-gray-400">Home</p>
				</a>
				
				<!-- Library -->
				<a
					href="/use/perplexica/library"
					class="relative flex flex-col items-center justify-center space-y-0.5 cursor-pointer w-full py-2 rounded-lg hover:bg-gray-800/60 transition duration-200"
					on:click|preventDefault={goToLibrary}
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
				on:click={() => showSettingsDialog = true}
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
			on:click|preventDefault={startNewChat}
		>
			<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-5 h-5">
				<path stroke-linecap="round" stroke-linejoin="round" d="m2.25 12 8.954-8.955c.44-.439 1.152-.439 1.591 0L21.75 12M4.5 9.75v10.125c0 .621.504 1.125 1.125 1.125H9.75v-4.875c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125V21h4.125c.621 0 1.125-.504 1.125-1.125V9.75M8.25 21h8.25" />
			</svg>
			<p class="text-xs">Home</p>
		</a>
		<a
			href="/use/perplexica/library"
			class="relative flex flex-col items-center space-y-1 text-center w-full text-gray-300"
			on:click|preventDefault={goToLibrary}
		>
			<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-5 h-5">
				<path stroke-linecap="round" stroke-linejoin="round" d="M12 6.042A8.967 8.967 0 0 0 6 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 0 1 6 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 0 1 6-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0 0 18 18a8.967 8.967 0 0 0-6 2.292m0-14.25v14.25" />
			</svg>
			<p class="text-xs">Library</p>
		</a>
		<button
			type="button"
			on:click={() => showSettingsDialog = true}
			class="relative flex flex-col items-center space-y-1 text-center w-full text-gray-300"
		>
			<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-5 h-5">
				<path stroke-linecap="round" stroke-linejoin="round" d="M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.324.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 0 1 1.37.49l1.296 2.247a1.125 1.125 0 0 1-.26 1.431l-1.003.827c-.293.24-.438.613-.431.992a6.759 6.759 0 0 1 0 .255c-.007.378.138.75.43.99l1.005.828c.424.35.534.954.26 1.43l-1.298 2.247a1.125 1.125 0 0 1-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.57 6.57 0 0 1-.22.128c-.331.183-.581.495-.644.869l-.213 1.28c-.09.543-.56.941-1.11.941h-2.594c-.55 0-1.02-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 0 1-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 0 1-1.369-.49l-1.297-2.247a1.125 1.125 0 0 1 .26-1.431l1.004-.827c.292-.24.437-.613.43-.992a6.932 6.932 0 0 1 0-.255c.007-.378-.138-.75-.43-.99l-1.004-.828a1.125 1.125 0 0 1-.26-1.43l1.297-2.247a1.125 1.125 0 0 1 1.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.087.22-.128.332-.183.582-.495.644-.869l.214-1.281Z" />
				<path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z" />
			</svg>
			<p class="text-xs">Settings</p>
		</button>
	</div>
	
	<!-- 메인 컨텐츠 (중앙 정렬) -->
	<main class="flex-1 bg-gray-950 flex flex-col">
		<div class="max-w-4xl lg:mx-auto flex-1 flex flex-col min-h-0 w-full">
			<!-- 채팅 영역 -->
			<div class="flex flex-col flex-1 relative overflow-hidden min-h-0">
				<!-- Export 버튼 (우측 상단) -->
				<div class="absolute top-4 right-4 z-10">
					<div class="relative" bind:this={exportPopoverRef}>
						<button
							type="button"
							on:click={() => showExportPopover = !showExportPopover}
							class="p-2 rounded-lg hover:bg-gray-800/50 text-gray-400 hover:text-white transition-colors"
							disabled={messages.length === 0}
						>
							<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-4 h-4">
								<path stroke-linecap="round" stroke-linejoin="round" d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5M16.5 12 12 16.5m0 0L7.5 12m4.5 4.5V3" />
							</svg>
						</button>
						{#if showExportPopover}
							<div
								class="absolute right-0 top-full mt-2 w-64 bg-gray-800 border border-gray-700/50 rounded-lg shadow-xl z-50 overflow-hidden"
								transition:fly={{ y: 10, duration: 200 }}
							>
								<div class="p-2">
									<div class="mb-2">
										<p class="text-xs font-medium text-gray-400 uppercase tracking-wide px-2">내보내기</p>
									</div>
									<div class="space-y-1">
										<button
											type="button"
											on:click={exportAsMarkdown}
											class="w-full flex items-center gap-3 px-3 py-2 text-left rounded-xl hover:bg-gray-700/60 transition-colors"
										>
											<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-4 h-4 text-blue-400">
												<path stroke-linecap="round" stroke-linejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z" />
											</svg>
											<div>
												<p class="text-sm font-medium text-white">Markdown</p>
												<p class="text-xs text-gray-400">.md 형식</p>
											</div>
										</button>
									</div>
								</div>
							</div>
						{/if}
					</div>
				</div>
			
				<!-- 메시지 목록 (섹션 기반) -->
				<div
					bind:this={messagesContainer}
					class="flex-1 overflow-y-auto px-4 sm:px-4 md:px-8 py-8 pb-44 lg:pb-28 space-y-6"
				>
				{#if sections.length === 0 && inputValue === '' && !isLoading}
					<div class="flex items-center justify-center h-full">
						<div class="text-center">
							<div class="w-16 h-16 rounded-xl bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center mx-auto mb-4 shadow-lg shadow-blue-500/20">
								<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-8 h-8 text-white">
									<path stroke-linecap="round" stroke-linejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" />
								</svg>
							</div>
							<p class="text-gray-400 text-sm">검색할 내용을 입력하세요</p>
						</div>
					</div>
				{/if}
				
				{#each sections as section, sectionIndex (section.message.messageId)}
					<div class="space-y-6" in:fly={{ y: 10, duration: 200 }}>
						<!-- 질문 제목 (User Message) -->
						<div class="w-full pt-8 break-words">
							<div class="flex justify-end pb-1">
								<div class="max-w-[90%] px-5 py-2 rounded-3xl bg-blue-500/20 text-white border border-blue-500/30">
									<p class="whitespace-pre-wrap text-white">{section.message.query}</p>
								</div>
							</div>
						</div>
						
						<!-- 좌우 분할 레이아웃 -->
						<div class="flex flex-col space-y-9 lg:space-y-0 lg:flex-row lg:justify-between lg:space-x-9">
							<!-- 좌측 컨텐츠 (9/12) -->
							<div 
								use:handleDividerRef={sectionIndex === sections.length - 1}
								class="flex flex-col space-y-6 w-full lg:w-9/12"
							>
								<!-- Sources 섹션 -->
								{#if section.sources.length > 0}
									<div class="flex flex-col space-y-2">
										<div class="flex flex-row items-center space-x-2">
											<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-5 h-5 text-gray-400">
												<path stroke-linecap="round" stroke-linejoin="round" d="M12 6.042A8.967 8.967 0 0 0 6 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 0 1 6 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 0 1 6-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0 0 18 18a8.967 8.967 0 0 0-6 2.292m0-14.25v14.25" />
											</svg>
											<h3 class="text-white dark:text-white font-medium text-xl">Sources</h3>
										</div>
										<div class="grid grid-cols-2 lg:grid-cols-4 gap-2">
											{#each section.sources.slice(0, 3) as source, i}
												<a
													href={source.metadata.url || '#'}
													target="_blank"
													rel="noopener noreferrer"
													class="bg-gray-800/60 hover:bg-gray-700/60 dark:bg-gray-800 dark:hover:bg-gray-700 transition duration-200 rounded-lg p-3 flex flex-col space-y-2 font-medium border border-gray-700/50"
												>
													<p class="dark:text-white text-xs overflow-hidden whitespace-nowrap text-ellipsis">
														{source.metadata.title || source.metadata.url || '출처 없음'}
													</p>
													<div class="flex flex-row items-center justify-between">
														<div class="flex flex-row items-center space-x-1">
															{#if source.metadata.url && !source.metadata.url.includes('file_id://')}
																<img
																	src={`https://s2.googleusercontent.com/s2/favicons?domain_url=${source.metadata.url}`}
																	width={16}
																	height={16}
																	alt="favicon"
																	class="rounded-lg h-4 w-4"
																/>
															{:else}
																<div class="bg-gray-700 hover:bg-gray-600 transition duration-200 flex items-center justify-center w-4 h-4 rounded-full">
																	<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-3 h-3 text-gray-400">
																		<path stroke-linecap="round" stroke-linejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z" />
																	</svg>
        </div>
															{/if}
															<p class="text-xs text-gray-400 overflow-hidden whitespace-nowrap text-ellipsis">
																{source.metadata.url && source.metadata.url.includes('file_id://')
																	? 'Uploaded File'
																	: source.metadata.url
																		? source.metadata.url.replace(/.+\/\/|www.|\..+/g, '')
																		: 'Unknown'}
															</p>
    </div>
														<div class="flex flex-row items-center space-x-1 text-gray-400 text-xs">
															<div class="bg-gray-500 h-[4px] w-[4px] rounded-full" />
															<span>{i + 1}</span>
														</div>
													</div>
												</a>
											{/each}
											{#if section.sources.length > 3}
												<button
													on:click={() => {
														sourcesModalOpen[section.message.messageId] = true;
														sourcesModalOpen = sourcesModalOpen;
													}}
													class="bg-gray-800/60 hover:bg-gray-700/60 dark:bg-gray-800 dark:hover:bg-gray-700 transition duration-200 rounded-lg p-3 flex flex-col space-y-2 font-medium border border-gray-700/50"
												>
													<div class="flex flex-row items-center space-x-1">
														{#each section.sources.slice(3, 6) as source, i}
															{#if source.metadata.url && !source.metadata.url.includes('file_id://')}
																<img
																	src={`https://s2.googleusercontent.com/s2/favicons?domain_url=${source.metadata.url}`}
																	width={16}
																	height={16}
																	alt="favicon"
																	class="rounded-lg h-3 w-6 aspect-video object-cover"
																/>
															{/if}
														{/each}
													</div>
													<p class="text-xs text-gray-400">
														View {section.sources.length - 3} more
													</p>
												</button>
											{/if}
										</div>
									</div>
								{/if}
								
								<!-- Answer 섹션 -->
								<div class="flex flex-col space-y-2">
									<!-- Answer 제목은 sources가 있거나 parsedTextBlocks가 있을 때 표시 -->
									{#if section.sources.length > 0 || section.parsedTextBlocks.length > 0 || section.message.status === 'answering'}
										<div class="flex flex-row items-center space-x-2 mb-2">
											<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-5 h-5 text-gray-400">
												<path stroke-linecap="round" stroke-linejoin="round" d="M12 6.042A8.967 8.967 0 0 0 6 3.75c-1.052 0-2.062.18-3 .512v14.25A8.987 8.987 0 0 1 6 18c2.305 0 4.408.867 6 2.292m0-14.25a8.966 8.966 0 0 1 6-2.292c1.052 0 2.062.18 3 .512v14.25A8.987 8.987 0 0 0 18 18a8.967 8.967 0 0 0-6 2.292m0-14.25v14.25" />
                    </svg>
											<h3 class="text-white dark:text-white font-medium text-xl">Answer</h3>
                </div>
									{/if}
									
									<!-- Answer 내용은 parsedTextBlocks가 있거나 answering 상태일 때 표시 -->
									{#if section.parsedTextBlocks.length > 0 || section.message.status === 'answering'}
										<div class="w-full min-w-full markdown-prose text-slate-200">
											{#if section.message.status === 'answering'}
												<div class="flex items-center gap-2 mb-2">
													<div class="w-2 h-2 bg-blue-400 rounded-full animate-pulse"></div>
													<span class="text-xs text-slate-400">응답 생성 중...</span>
												</div>
											{/if}
											{#if section.parsedTextBlocks.length > 0}
												<Markdown content={section.parsedTextBlocks.join('\n\n')} />
											{/if}
										</div>
									{/if}
								</div>
								
								<!-- Related 제안 (마지막 섹션에만) -->
								{#if sectionIndex === sections.length - 1 && section.suggestions && section.suggestions.length > 0}
									<div class="mt-6">
										<div class="flex flex-row items-center space-x-2 mb-4">
											<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-5 h-5 text-gray-400">
												<path stroke-linecap="round" stroke-linejoin="round" d="M3.75 6.75h16.5M3.75 12h16.5m-16.5 5.25h16.5" />
											</svg>
											<h3 class="text-white dark:text-white font-medium text-xl">Related</h3>
										</div>
										<div class="space-y-0">
											{#each section.suggestions as suggestion, i}
												<div>
													<div class="h-px bg-gray-800/40" />
													<button
														on:click={() => {
															inputValue = suggestion;
															sendMessage();
														}}
														class="group w-full py-4 text-left transition-colors duration-200 hover:bg-gray-800/40"
													>
														<div class="flex items-center justify-between gap-3">
															<div class="flex flex-row space-x-3 items-center">
																<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-4 h-4 text-gray-500 group-hover:text-blue-400 transition-colors duration-200 flex-shrink-0">
																	<path stroke-linecap="round" stroke-linejoin="round" d="M6 12 3.269 3.125A59.769 59.769 0 0 1 21 12m0 0-3.269 3.125A59.769 59.769 0 0 1 3 12m18 0v-1.5m0 1.5v1.5" />
																</svg>
																<p class="text-sm text-gray-300 group-hover:text-blue-400 transition-colors duration-200 leading-relaxed">
																	{suggestion}
																</p>
                </div>
															<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-4 h-4 text-gray-500 group-hover:text-blue-400 transition-colors duration-200 flex-shrink-0">
																<path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
															</svg>
            </div>
													</button>
												</div>
											{/each}
										</div>
									</div>
								{/if}
        </div>

							<!-- 우측 위젯 (3/12, sticky) -->
							{#if section.parsedTextBlocks.length > 0 || section.message.status === 'answering' || section.widgets.length > 0}
								<div class="lg:sticky lg:top-20 flex flex-col items-center space-y-3 w-full lg:w-3/12 z-30 h-full pb-4">
									<!-- 날씨/계산/주식 위젯 -->
									{#each section.widgets as widget}
										{#if widget.widgetType === 'weather' && !widget.params?.error && widget.params?.current}
											<div class="w-full relative overflow-hidden rounded-lg shadow-md bg-gray-200 dark:bg-gray-800">
												<div class="relative p-4 text-gray-800 dark:text-white">
													<div class="flex items-start justify-between mb-3">
														<div class="flex items-center gap-3">
															<div class="w-16 h-16 flex items-center justify-center text-4xl">
																{#if (widget.params?.current?.weather_code || 0) === 0 || (widget.params?.current?.weather_code || 0) === 1}
																	{(widget.params?.current?.is_day === 1) ? 'Sunny' : 'Clear'}
																{:else if (widget.params?.current?.weather_code || 0) === 2 || (widget.params?.current?.weather_code || 0) === 3}
																	{(widget.params?.current?.is_day === 1) ? 'Partly Cloudy' : 'Cloudy'}
																{:else if (widget.params?.current?.weather_code || 0) >= 45 && (widget.params?.current?.weather_code || 0) <= 48}
																	Fog
																{:else if (widget.params?.current?.weather_code || 0) >= 51 && (widget.params?.current?.weather_code || 0) <= 67}
																	Rain
																{:else if (widget.params?.current?.weather_code || 0) >= 71 && (widget.params?.current?.weather_code || 0) <= 77}
																	Snow
																{:else if (widget.params?.current?.weather_code || 0) >= 80 && (widget.params?.current?.weather_code || 0) <= 82}
																	Rain Showers
																{:else if (widget.params?.current?.weather_code || 0) >= 95 && (widget.params?.current?.weather_code || 0) <= 99}
																	Thunderstorm
																{:else}
																	Sunny
																{/if}
															</div>
															<div>
																<div class="flex items-baseline gap-1">
																	<span class="text-4xl font-bold">
																		{Math.round(widget.params?.current?.temperature_2m || 0)}°
																	</span>
																	<span class="text-lg">°C</span>
																</div>
																<p class="text-sm font-medium mt-0.5">
																	{widget.params?.location || 'Unknown'}
																</p>
															</div>
														</div>
														<div class="text-right">
															{#if widget.params?.daily?.temperature_2m_max?.[0] !== undefined && widget.params?.daily?.temperature_2m_min?.[0] !== undefined}
																<p class="text-xs font-medium opacity-90">
																	{Math.round(widget.params.daily.temperature_2m_max[0])}° {Math.round(widget.params.daily.temperature_2m_min[0])}°
																</p>
															{/if}
														</div>
													</div>
													<div class="grid grid-cols-2 gap-2 text-xs">
														<div>
															<p class="opacity-70">체감 온도</p>
															<p class="font-semibold">{Math.round(widget.params?.current?.apparent_temperature || 0)}°</p>
														</div>
														<div>
															<p class="opacity-70">습도</p>
															<p class="font-semibold">{widget.params?.current?.relative_humidity_2m || 0}%</p>
														</div>
														<div>
															<p class="opacity-70">바람</p>
															<p class="font-semibold">{Math.round(widget.params?.current?.wind_speed_10m || 0)} km/h</p>
														</div>
														<div>
															<p class="opacity-70">기압</p>
															<p class="font-semibold">{Math.round(widget.params?.current?.pressure_msl || 0)} hPa</p>
														</div>
													</div>
												</div>
											</div>
										{:else if widget.widgetType === 'calculation_result' && !widget.params?.error && widget.params?.result}
											<div class="w-full bg-gray-800/60 rounded-lg p-4 border border-gray-700/50">
												<p class="text-xs text-gray-400 mb-2">계산 결과</p>
												<p class="text-2xl font-bold text-white">{widget.params.result}</p>
												<p class="text-sm text-gray-400 mt-1">{widget.params?.expression || ''}</p>
											</div>
										{:else if widget.widgetType === 'stock' && !widget.params?.error && widget.params?.symbol && widget.params?.price}
											<div class="w-full bg-gray-800/60 rounded-lg p-4 border border-gray-700/50">
												<p class="text-xs text-gray-400 mb-2">주식 정보</p>
												<p class="text-xl font-bold text-white">{widget.params.symbol}</p>
												<p class="text-sm text-gray-400 mt-1">{widget.params.price}</p>
											</div>
										{/if}
									{/each}
									
									<!-- 이미지 검색 위젯 -->
									<div class="w-full">
										{#if !imageWidgets[section.message.messageId]}
											<button
												on:click={() => searchImages(section.message.messageId, section.message.query)}
												class="border border-dashed border-gray-700 hover:bg-gray-800/60 active:scale-95 duration-200 transition px-4 py-2 flex flex-row items-center justify-between rounded-lg text-gray-300 text-sm w-full"
											>
												<div class="flex flex-row items-center space-x-2">
													<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-4 h-4">
														<path stroke-linecap="round" stroke-linejoin="round" d="m2.25 15.75 5.159-5.159a2.25 2.25 0 0 1 3.182 0l5.159 5.159m-1.5-1.5 1.409-1.409a2.25 2.25 0 0 1 3.182 0l2.909 2.909m-18 3.75h16.5a1.5 1.5 0 0 0 1.5-1.5V6a1.5 1.5 0 0 0-1.5-1.5H3.75A1.5 1.5 0 0 0 2.25 6v12a1.5 1.5 0 0 0 1.5 1.5Zm10.5-11.25h.008v.008h-.008V8.25Zm.375 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Z" />
													</svg>
													<p>Search images</p>
												</div>
												<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-4 h-4 text-blue-400">
													<path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
												</svg>
											</button>
										{:else if imageWidgets[section.message.messageId].loading}
											<div class="grid grid-cols-2 gap-2">
												{#each Array(4) as _, i}
													<div class="bg-gray-800/60 h-32 w-full rounded-lg animate-pulse aspect-video object-cover" />
												{/each}
											</div>
										{:else if imageWidgets[section.message.messageId].loading}
											<div class="grid grid-cols-2 gap-2">
												{#each Array(4) as _, i}
													<div class="bg-gray-800/60 h-32 w-full rounded-lg animate-pulse aspect-video object-cover" />
												{/each}
											</div>
										{:else}
											{@const widget = imageWidgets[section.message.messageId]}
											{#if widget && widget.images && widget.images.length > 0}
												<div class="grid grid-cols-2 gap-2">
													{#each widget.images.slice(0, 3) as image, i}
													<img
														src={image.img_src}
														alt={image.title}
														class="h-full w-full aspect-video object-cover rounded-lg transition duration-200 active:scale-95 hover:scale-[1.02] cursor-zoom-in"
														role="button"
														tabindex="0"
														on:click={() => {
															const msgId = section.message.messageId;
															if (!lightboxOpen[msgId]) {
																lightboxOpen[msgId] = { open: false, slides: [], currentIndex: 0 };
															}
															const lightbox = lightboxOpen[msgId];
															if (lightbox) {
																lightbox.open = true;
																lightbox.currentIndex = i;
																lightboxOpen = lightboxOpen;
															}
														}}
														on:keydown={(e) => {
															if (e.key === 'Enter' || e.key === ' ') {
																const msgId = section.message.messageId;
																if (!lightboxOpen[msgId]) {
																	lightboxOpen[msgId] = { open: false, slides: [], currentIndex: 0 };
																}
																const lightbox = lightboxOpen[msgId];
																if (lightbox) {
																	lightbox.open = true;
																	lightbox.currentIndex = i;
																	lightboxOpen = lightboxOpen;
																}
															}
														}}
													/>
													{/each}
													{#if widget.images.length > 4}
														<button
															on:click={() => {
																const msgId = section.message.messageId;
																if (!lightboxOpen[msgId]) {
																	lightboxOpen[msgId] = { open: false, slides: [], currentIndex: 0 };
																}
																const lightbox = lightboxOpen[msgId];
																if (lightbox) {
																	lightbox.open = true;
																	lightbox.currentIndex = 0;
																	lightboxOpen = lightboxOpen;
																}
															}}
															class="bg-gray-800/60 hover:bg-gray-700/60 transition duration-200 active:scale-95 hover:scale-[1.02] h-auto w-full rounded-lg flex flex-col justify-between text-white p-2"
														>
															<div class="flex flex-row items-center space-x-1">
																{#each widget.images.slice(3, 6) as image, i}
																	<img
																		src={image.img_src}
																		alt={image.title}
																		class="h-3 w-6 rounded-sm aspect-video object-cover"
																	/>
																{/each}
															</div>
															<p class="text-gray-400 text-xs">
																View {widget.images.length - 3} more
															</p>
														</button>
													{/if}
												</div>
											{/if}
										{/if}
									</div>
									
									<!-- 비디오 검색 위젯 -->
									<div class="w-full">
										{#if !videoWidgets[section.message.messageId]}
											<button
												on:click={() => searchVideos(section.message.messageId, section.message.query)}
												class="border border-dashed border-gray-700 hover:bg-gray-800/60 active:scale-95 duration-200 transition px-4 py-2 flex flex-row items-center justify-between rounded-lg text-gray-300 text-sm w-full"
											>
												<div class="flex flex-row items-center space-x-2">
													<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-4 h-4">
														<path stroke-linecap="round" stroke-linejoin="round" d="m15.75 10.5 4.72-4.72a.75.75 0 0 1 1.28.53v11.38a.75.75 0 0 1-1.28.53l-4.72-4.72M4.5 18.75h9a2.25 2.25 0 0 0 2.25-2.25v-9a2.25 2.25 0 0 0-2.25-2.25h-9A2.25 2.25 0 0 0 2.25 7.5v9a2.25 2.25 0 0 0 2.25 2.25Z" />
													</svg>
													<p>Search videos</p>
												</div>
												<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-4 h-4 text-blue-400">
													<path stroke-linecap="round" stroke-linejoin="round" d="M12 4.5v15m7.5-7.5h-15" />
												</svg>
											</button>
										{:else if videoWidgets[section.message.messageId].loading}
											<div class="grid grid-cols-2 gap-2">
												{#each Array(4) as _, i}
													<div class="bg-gray-800/60 h-32 w-full rounded-lg animate-pulse aspect-video object-cover" />
												{/each}
											</div>
										{:else}
											{@const videoWidget = videoWidgets[section.message.messageId]}
											{#if videoWidget && videoWidget.videos && videoWidget.videos.length > 0}
												<div class="grid grid-cols-2 gap-2">
													{#each videoWidget.videos.slice(0, 3) as video, i}
													<div
														class="relative transition duration-200 active:scale-95 hover:scale-[1.02] cursor-pointer"
														role="button"
														tabindex="0"
														on:click={() => {
															const msgId = section.message.messageId;
															if (!lightboxOpen[msgId]) {
																lightboxOpen[msgId] = { open: false, slides: [], currentIndex: 0 };
															}
															const lightbox = lightboxOpen[msgId];
															if (lightbox) {
																lightbox.open = true;
																lightbox.currentIndex = i;
																lightboxOpen = lightboxOpen;
															}
														}}
														on:keydown={(e) => {
															if (e.key === 'Enter' || e.key === ' ') {
																const msgId = section.message.messageId;
																if (!lightboxOpen[msgId]) {
																	lightboxOpen[msgId] = { open: false, slides: [], currentIndex: 0 };
																}
																const lightbox = lightboxOpen[msgId];
																if (lightbox) {
																	lightbox.open = true;
																	lightbox.currentIndex = i;
																	lightboxOpen = lightboxOpen;
																}
															}
														}}
													>
														<img
															src={video.img_src}
															alt={video.title}
															class="relative h-full w-full aspect-video object-cover rounded-lg"
														/>
														<div class="absolute bg-white/70 dark:bg-black/70 text-black/70 dark:text-white/70 px-2 py-1 flex flex-row items-center space-x-1 bottom-1 right-1 rounded-md">
															<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-3 h-3">
																<path stroke-linecap="round" stroke-linejoin="round" d="M5.25 5.653c0-.856.917-1.398 1.667-.986l11.54 6.348a1.125 1.125 0 0 1 0 1.971l-11.54 6.347a1.125 1.125 0 0 1-1.667-.985V5.653Z" />
															</svg>
															<p class="text-xs">Video</p>
														</div>
													</div>
													{/each}
													{#if videoWidget.videos.length > 4}
														<button
															on:click={() => {
																const msgId = section.message.messageId;
																if (!lightboxOpen[msgId]) {
																	lightboxOpen[msgId] = { open: false, slides: [], currentIndex: 0 };
																}
																const lightbox = lightboxOpen[msgId];
																if (lightbox) {
																	lightbox.open = true;
																	lightbox.currentIndex = 0;
																	lightboxOpen = lightboxOpen;
																}
															}}
															class="bg-gray-800/60 hover:bg-gray-700/60 transition duration-200 active:scale-95 hover:scale-[1.02] h-auto w-full rounded-lg flex flex-col justify-between text-white p-2"
														>
															<div class="flex flex-row items-center space-x-1">
																{#each videoWidget.videos.slice(3, 6) as video, i}
																	<img
																		src={video.img_src}
																		alt={video.title}
																		class="h-3 w-6 rounded-sm aspect-video object-cover"
																	/>
																{/each}
															</div>
															<p class="text-gray-400 text-xs">
																View {videoWidget.videos.length - 3} more
															</p>
														</button>
													{/if}
												</div>
											{/if}
										{/if}
									</div>
								</div>
							{/if}
						</div>
						
						<!-- 섹션 구분선 -->
						{#if sectionIndex < sections.length - 1}
							<div class="h-px w-full bg-gray-800/50" />
						{/if}
					</div>
				{/each}
				
				<!-- 로딩 중 표시 -->
				{#if isLoading && sections.length > 0 && sections[sections.length - 1]?.message.status === 'answering'}
					<div class="flex items-center gap-2 p-3 rounded-lg bg-gray-800/60 border border-gray-700/50">
						<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-4 h-4 text-blue-400 animate-spin">
							<path stroke-linecap="round" stroke-linejoin="round" d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0 3.181 3.183a8.25 8.25 0 0 0 13.803-3.7M4.031 9.865a8.25 8.25 0 0 1 13.803-3.7l3.181 3.182m0-4.991v4.99" />
                                    </svg>
						<span class="text-sm text-gray-300">Brainstorming...</span>
					</div>
				{/if}
			</div>
			
			<!-- 입력 영역 (원본 Perplexica처럼 고정) -->
			{#if sections.length === 0}
				<!-- 메시지가 없을 때: 중앙에 배치 -->
				<div class="fixed z-40 bottom-24 lg:bottom-6 left-1/2 -translate-x-1/2 max-w-2xl w-full px-4">
					<form 
						on:submit|preventDefault={sendMessage}
						class="w-full"
					>
						<div class="flex flex-col bg-gray-800/60 dark:bg-gray-800/60 px-3 pt-5 pb-3 rounded-2xl w-full border border-gray-700/50 dark:border-gray-700/50 shadow-sm transition-all duration-200 focus-within:border-blue-500/50 dark:focus-within:border-blue-500/50">
							<textarea
								bind:value={inputValue}
								placeholder="Ask anything..."
								rows="2"
								disabled={isLoading}
								class="px-2 bg-transparent placeholder:text-[15px] placeholder:text-slate-400 text-sm text-white resize-none focus:outline-none w-full max-h-24 lg:max-h-36 xl:max-h-48"
							></textarea>
							<div class="flex flex-row items-center justify-between mt-4">
								<!-- Optimization Mode (왼쪽) -->
								<div class="relative" bind:this={optimizationModePopoverRef}>
									<button
										type="button"
										on:click={() => showOptimizationModePopover = !showOptimizationModePopover}
										class="p-2 text-white rounded-xl hover:bg-gray-700/60 active:scale-95 transition duration-200 focus:outline-none"
									>
										<div class="flex flex-row items-center space-x-1">
											<span class="text-base">{optimizationModes.find(m => m.value === selectedOptimizationMode)?.icon}</span>
											<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-4 h-4 text-white {showOptimizationModePopover ? 'rotate-180' : ''} transition-transform">
												<path stroke-linecap="round" stroke-linejoin="round" d="m19.5 8.25-7.5 7.5-7.5-7.5" />
                                    </svg>
										</div>
									</button>
									{#if showOptimizationModePopover}
										<div
											class="absolute bottom-full left-0 mb-2 w-64 bg-gray-800 border border-gray-700/50 rounded-lg shadow-xl z-50 overflow-hidden"
											transition:fly={{ y: 10, duration: 200 }}
										>
											<div class="p-2 space-y-1">
												{#each optimizationModes as mode}
													<button
														type="button"
														on:click={() => {
															selectedOptimizationMode = mode.value;
															showOptimizationModePopover = false;
														}}
														class="w-full text-left px-3 py-2 rounded-lg hover:bg-gray-700/60 transition-colors {selectedOptimizationMode === mode.value ? 'bg-blue-500/20 border border-blue-500/30' : ''}"
													>
														<div class="flex items-center justify-between">
															<div class="flex items-center gap-2 text-sm text-gray-200">
																<span>{mode.icon}</span>
																<span class="font-medium">{mode.title}</span>
															</div>
														</div>
														<p class="text-xs text-gray-400 mt-0.5 ml-6">{mode.description}</p>
													</button>
												{/each}
											</div>
										</div>
									{/if}
								</div>
								
								<!-- 오른쪽 버튼들 (Sources, Model Selector) -->
								<div class="flex flex-row items-center space-x-2">
									<!-- Focus Mode (Sources) -->
									<div class="relative" bind:this={focusModePopoverRef}>
										<button
											type="button"
											on:click={() => showFocusModePopover = !showFocusModePopover}
											class="p-2 text-white rounded-lg hover:bg-gray-700/60 active:scale-95 transition duration-200 focus:outline-none"
										>
											<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-[18px] h-auto text-white">
												<path stroke-linecap="round" stroke-linejoin="round" d="M12 21a9.004 9.004 0 0 0 8.716-6.747M12 21a9.004 9.004 0 0 1-8.716-6.747M12 21c2.485 0 4.5-4.03 4.5-9S14.485 3 12 3m0 18c-2.485 0-4.5-4.03-4.5-9S9.515 3 12 3m0 0a8.997 8.997 0 0 1 7.843 4.582M12 3a8.997 8.997 0 0 0-7.843 4.582m15.686 0A11.953 11.953 0 0 1 12 10.5c-2.998 0-5.74-1.1-7.843-2.918m15.686 0A8.959 8.959 0 0 1 21 12c0 .778-.099 1.533-.284 2.253m0 0A17.919 17.919 0 0 1 12 16.5c-3.162 0-6.133-.815-8.716-2.247m0 0A9.015 9.015 0 0 1 3 12c0-1.605.42-3.113 1.157-4.418" />
                                    </svg>
										</button>
										{#if showFocusModePopover}
											<div
												class="absolute bottom-full right-0 mb-2 w-64 bg-gray-800 border border-gray-700/50 rounded-lg shadow-xl z-50 overflow-hidden"
												transition:fly={{ y: 10, duration: 200 }}
											>
												<div class="p-2 space-y-1">
													{#each focusModes as mode}
														<button
															type="button"
															on:click={() => {
																selectedFocusMode = mode.value;
																showFocusModePopover = false;
															}}
															class="w-full text-left px-3 py-2 rounded-lg hover:bg-gray-700/60 transition-colors {selectedFocusMode === mode.value ? 'bg-blue-500/20 border border-blue-500/30' : ''}"
														>
															<div class="flex items-center gap-2 text-sm text-gray-200">
																<span>{mode.icon}</span>
																<span>{mode.label}</span>
															</div>
														</button>
													{/each}
												</div>
											</div>
										{/if}
									</div>
									
									<!-- Model Selector -->
									<div class="relative" bind:this={modelSelectorPopoverRef}>
										<button
											type="button"
											on:click={() => showModelSelectorPopover = !showModelSelectorPopover}
											class="p-2 text-white rounded-lg hover:bg-gray-700/60 active:scale-95 transition duration-200 focus:outline-none disabled:opacity-50"
											disabled={loadingProviders || !selectedChatModel || !selectedEmbeddingModel}
										>
											<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-4 h-4 text-white">
												<path stroke-linecap="round" stroke-linejoin="round" d="M8.25 3v1.5M4.5 8.25H3m18 0h-1.5m-1.5 0V12m0 4.5V12m0 4.5h-1.5m-1.5 0H15m-6 0H4.5m0 0H3m1.5 0v-1.5M15 12v4.5m0-4.5h-1.5m1.5 0H12m-6 0H4.5m0 0V12m0 0H3m1.5 0h1.5m0 0H9m-1.5 0v-1.5M9 3H6.75m0 0H4.5m2.25 0v1.5M9 3v1.5m0 0V8.25m0-4.5h2.25m0 0H15m-2.25 0v1.5M15 3h2.25m0 0H21m-2.25 0v1.5M21 3v1.5m0 0V8.25m0-4.5H18.75m0 0H15m2.25 0h2.25m0 0H21" />
                                    </svg>
										</button>
										{#if showModelSelectorPopover}
											<div
												class="absolute bottom-full right-0 mb-2 w-80 max-h-96 bg-gray-800 border border-gray-700/50 rounded-lg shadow-xl z-50 overflow-hidden flex flex-col"
												transition:fly={{ y: 10, duration: 200 }}
											>
												<div class="p-2 border-b border-gray-700/50">
													<input
														type="text"
														bind:value={modelSearchQuery}
														placeholder="모델 검색..."
														class="w-full px-3 py-2 bg-gray-700/50 border border-gray-600/50 rounded-lg text-white placeholder-gray-400 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500/50"
													/>
												</div>
												<div class="flex-1 overflow-y-auto p-2 space-y-3">
													{#if loadingProviders}
														<div class="text-center text-gray-400 py-4 text-sm">로딩 중...</div>
													{:else if filteredProviders.length === 0}
														<div class="text-center text-gray-400 py-4 text-sm">모델을 찾을 수 없습니다</div>
                                {:else}
														{#each filteredProviders as provider}
															<div class="space-y-2">
																<h4 class="text-xs font-semibold text-gray-400 uppercase px-2">{provider.name}</h4>
																<div class="space-y-1">
																	{#if provider.chatModels.length > 0}
																		<div class="text-xs text-gray-500 px-2">Chat Models</div>
																		{#each provider.chatModels as model}
																			<button
																				type="button"
																				on:click={() => {
																					selectedChatModel = { providerId: provider.id, key: model.key };
																					showModelSelectorPopover = false;
																				}}
																				class="w-full text-left px-3 py-1.5 rounded-lg hover:bg-gray-700/60 transition-colors text-sm {selectedChatModel?.providerId === provider.id && selectedChatModel?.key === model.key ? 'bg-blue-500/20 border border-blue-500/30' : 'text-gray-200'}"
																			>
																				{model.name}
																			</button>
																		{/each}
																	{/if}
																	{#if provider.embeddingModels.length > 0}
																		<div class="text-xs text-gray-500 px-2 mt-2">Embedding Models</div>
																		{#each provider.embeddingModels as model}
																			<button
																				type="button"
																				on:click={() => {
																					selectedEmbeddingModel = { providerId: provider.id, key: model.key };
																					showModelSelectorPopover = false;
																				}}
																				class="w-full text-left px-3 py-1.5 rounded-lg hover:bg-gray-700/60 transition-colors text-sm {selectedEmbeddingModel?.providerId === provider.id && selectedEmbeddingModel?.key === model.key ? 'bg-blue-500/20 border border-blue-500/30' : 'text-gray-200'}"
																			>
																				{model.name}
																			</button>
																		{/each}
																	{/if}
																</div>
															</div>
														{/each}
													{/if}
												</div>
											</div>
										{/if}
									</div>
								</div>
								
								<!-- 전송 버튼 -->
								<button
									type="submit"
									disabled={inputValue.trim().length === 0 || isLoading}
									class="bg-[#24A0ED] text-white disabled:text-black/50 dark:disabled:text-white/50 hover:bg-opacity-85 transition duration-100 disabled:bg-[#e0e0dc79] dark:disabled:bg-[#ececec21] rounded-full p-2"
								>
									<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-4 h-4">
										<path stroke-linecap="round" stroke-linejoin="round" d="M13.5 4.5 21 12m0 0-7.5 7.5M21 12H3" />
                                    </svg>
								</button>
							</div>
						</div>
					</form>
				</div>
			{:else if dividerWidth > 0}
				<!-- 메시지가 있을 때: dividerWidth 기반 중앙 배치 -->
				<div class="fixed z-40 bottom-24 lg:bottom-6" style="width: {Math.max(dividerWidth, 600)}px; max-width: 800px; left: 50%; transform: translateX(-50%);">
					<form 
						on:submit|preventDefault={sendMessage}
						class="w-full relative"
					>
						<!-- 그라데이션 오버레이 (입력 영역 위에만) -->
						<div class="pointer-events-none absolute -bottom-6 left-0 right-0 h-[calc(100%+24px+24px)] dark:hidden" style="background: linear-gradient(to top, #ffffff 0%, #ffffff 35%, rgba(255,255,255,0.95) 45%, rgba(255,255,255,0.85) 55%, rgba(255,255,255,0.7) 65%, rgba(255,255,255,0.5) 75%, rgba(255,255,255,0.3) 85%, rgba(255,255,255,0.1) 92%, transparent 100%);"></div>
						<div class="pointer-events-none absolute -bottom-6 left-0 right-0 h-[calc(100%+24px+24px)] hidden dark:block" style="background: linear-gradient(to top, #0d1117 0%, #0d1117 35%, rgba(13,17,23,0.95) 45%, rgba(13,17,23,0.85) 55%, rgba(13,17,23,0.7) 65%, rgba(13,17,23,0.5) 75%, rgba(13,17,23,0.3) 85%, rgba(13,17,23,0.1) 92%, transparent 100%);"></div>
						<div class="relative bg-gray-800/60 dark:bg-gray-800/60 p-4 flex items-center overflow-visible border border-gray-700/50 dark:border-gray-700/50 shadow-sm transition-all duration-200 focus-within:border-blue-500/50 dark:focus-within:border-blue-500/50 {inputValue.trim().length > 0 && inputValue.split('\n').length >= 2 ? 'flex-col rounded-2xl' : 'flex-row rounded-full'}">
							{#if inputValue.trim().length === 0 || inputValue.split('\n').length < 2}
								<!-- Single mode: 설정 버튼 표시 -->
								<div class="flex items-center gap-2 mr-2">
									<!-- Optimization Mode -->
									<div class="relative" bind:this={singleOptimizationModePopoverRef}>
									<button
										type="button"
										on:click={() => showOptimizationModePopover = !showOptimizationModePopover}
										class="p-2 text-white rounded-xl hover:bg-gray-700/60 active:scale-95 transition duration-200 focus:outline-none"
									>
										<div class="flex flex-row items-center space-x-1">
											<span class="text-base">{optimizationModes.find(m => m.value === selectedOptimizationMode)?.icon}</span>
											<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-4 h-4 text-white {showOptimizationModePopover ? 'rotate-180' : ''} transition-transform">
												<path stroke-linecap="round" stroke-linejoin="round" d="m19.5 8.25-7.5 7.5-7.5-7.5" />
											</svg>
										</div>
									</button>
										{#if showOptimizationModePopover}
											<div
												class="absolute bottom-full left-0 mb-2 w-64 bg-gray-800 border border-gray-700/50 rounded-lg shadow-xl z-50 overflow-hidden"
												transition:fly={{ y: 10, duration: 200 }}
											>
												<div class="p-2 space-y-1">
													{#each optimizationModes as mode}
														<button
															type="button"
															on:click={() => {
																selectedOptimizationMode = mode.value;
																showOptimizationModePopover = false;
															}}
															class="w-full text-left px-3 py-2 rounded-lg hover:bg-gray-700/60 transition-colors {selectedOptimizationMode === mode.value ? 'bg-blue-500/20 border border-blue-500/30' : ''}"
														>
															<div class="flex items-center justify-between">
																<div class="flex items-center gap-2 text-sm text-gray-200">
																	<span>{mode.icon}</span>
																	<span class="font-medium">{mode.title}</span>
																</div>
															</div>
															<p class="text-xs text-gray-400 mt-0.5 ml-6">{mode.description}</p>
														</button>
													{/each}
												</div>
											</div>
                                {/if}
                            </div>

									<!-- Focus Mode -->
									<div class="relative" bind:this={singleFocusModePopoverRef}>
										<button
											type="button"
											on:click={() => showFocusModePopover = !showFocusModePopover}
											class="p-2 text-white rounded-lg hover:bg-gray-700/60 active:scale-95 transition duration-200 focus:outline-none"
										>
											<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-[18px] h-auto text-white">
												<path stroke-linecap="round" stroke-linejoin="round" d="M12 21a9.004 9.004 0 0 0 8.716-6.747M12 21a9.004 9.004 0 0 1-8.716-6.747M12 21c2.485 0 4.5-4.03 4.5-9S14.485 3 12 3m0 18c-2.485 0-4.5-4.03-4.5-9S9.515 3 12 3m0 0a8.997 8.997 0 0 1 7.843 4.582M12 3a8.997 8.997 0 0 0-7.843 4.582m15.686 0A11.953 11.953 0 0 1 12 10.5c-2.998 0-5.74-1.1-7.843-2.918m15.686 0A8.959 8.959 0 0 1 21 12c0 .778-.099 1.533-.284 2.253m0 0A17.919 17.919 0 0 1 12 16.5c-3.162 0-6.133-.815-8.716-2.247m0 0A9.015 9.015 0 0 1 3 12c0-1.605.42-3.113 1.157-4.418" />
											</svg>
										</button>
										{#if showFocusModePopover}
											<div
												class="absolute bottom-full right-0 mb-2 w-64 bg-gray-800 border border-gray-700/50 rounded-lg shadow-xl z-50 overflow-hidden"
												transition:fly={{ y: 10, duration: 200 }}
											>
												<div class="p-2 space-y-1">
													{#each focusModes as mode}
														<button
															type="button"
															on:click={() => {
																selectedFocusMode = mode.value;
																showFocusModePopover = false;
															}}
															class="w-full text-left px-3 py-2 rounded-lg hover:bg-gray-700/60 transition-colors {selectedFocusMode === mode.value ? 'bg-blue-500/20 border border-blue-500/30' : ''}"
														>
															<div class="flex items-center gap-2 text-sm text-gray-200">
																<span>{mode.icon}</span>
																<span>{mode.label}</span>
															</div>
														</button>
													{/each}
												</div>
											</div>
										{/if}
									</div>
									
									<!-- Model Selector -->
									<div class="relative" bind:this={singleModelSelectorPopoverRef}>
										<button
											type="button"
											on:click={() => showModelSelectorPopover = !showModelSelectorPopover}
											class="p-2 text-white rounded-lg hover:bg-gray-700/60 active:scale-95 transition duration-200 focus:outline-none disabled:opacity-50"
											disabled={loadingProviders || !selectedChatModel || !selectedEmbeddingModel}
										>
											<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-4 h-4 text-white">
												<path stroke-linecap="round" stroke-linejoin="round" d="M8.25 3v1.5M4.5 8.25H3m18 0h-1.5m-1.5 0V12m0 4.5V12m0 4.5h-1.5m-1.5 0H15m-6 0H4.5m0 0H3m1.5 0v-1.5M15 12v4.5m0-4.5h-1.5m1.5 0H12m-6 0H4.5m0 0V12m0 0H3m1.5 0h1.5m0 0H9m-1.5 0v-1.5M9 3H6.75m0 0H4.5m2.25 0v1.5M9 3v1.5m0 0V8.25m0-4.5h2.25m0 0H15m-2.25 0v1.5M15 3h2.25m0 0H21m-2.25 0v1.5M21 3v1.5m0 0V8.25m0-4.5H18.75m0 0H15m2.25 0h2.25m0 0H21" />
											</svg>
										</button>
										{#if showModelSelectorPopover}
											<div
												class="absolute bottom-full right-0 mb-2 w-80 max-h-96 bg-gray-800 border border-gray-700/50 rounded-lg shadow-xl z-50 overflow-hidden flex flex-col"
												transition:fly={{ y: 10, duration: 200 }}
											>
												<div class="p-2 border-b border-gray-700/50">
													<input
														type="text"
														bind:value={modelSearchQuery}
														placeholder="모델 검색..."
														class="w-full px-3 py-2 bg-gray-700/50 border border-gray-600/50 rounded-lg text-white placeholder-gray-400 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500/50"
													/>
												</div>
												<div class="flex-1 overflow-y-auto p-2 space-y-3">
													{#if loadingProviders}
														<div class="text-center text-gray-400 py-4 text-sm">로딩 중...</div>
													{:else if filteredProviders.length === 0}
														<div class="text-center text-gray-400 py-4 text-sm">모델을 찾을 수 없습니다</div>
													{:else}
														{#each filteredProviders as provider}
															<div class="space-y-2">
																<h4 class="text-xs font-semibold text-gray-400 uppercase px-2">{provider.name}</h4>
																<div class="space-y-1">
																	{#if provider.chatModels.length > 0}
																		<div class="text-xs text-gray-500 px-2">Chat Models</div>
																		{#each provider.chatModels as model}
																			<button
																				type="button"
																				on:click={() => {
																					selectedChatModel = { providerId: provider.id, key: model.key };
																					showModelSelectorPopover = false;
																				}}
																				class="w-full text-left px-3 py-1.5 rounded-lg hover:bg-gray-700/60 transition-colors text-sm {selectedChatModel?.providerId === provider.id && selectedChatModel?.key === model.key ? 'bg-blue-500/20 border border-blue-500/30' : 'text-gray-200'}"
																			>
																				{model.name}
																			</button>
																		{/each}
																	{/if}
																	{#if provider.embeddingModels.length > 0}
																		<div class="text-xs text-gray-500 px-2 mt-2">Embedding Models</div>
																		{#each provider.embeddingModels as model}
																			<button
																				type="button"
																				on:click={() => {
																					selectedEmbeddingModel = { providerId: provider.id, key: model.key };
																					showModelSelectorPopover = false;
																				}}
																				class="w-full text-left px-3 py-1.5 rounded-lg hover:bg-gray-700/60 transition-colors text-sm {selectedEmbeddingModel?.providerId === provider.id && selectedEmbeddingModel?.key === model.key ? 'bg-blue-500/20 border border-blue-500/30' : 'text-gray-200'}"
																			>
																				{model.name}
																			</button>
																		{/each}
																	{/if}
                        </div>
                    </div>
                {/each}
													{/if}
            </div>
        </div>
										{/if}
    </div>
								</div>
								
								<textarea
									bind:value={inputValue}
									placeholder="Ask a follow-up"
									rows="1"
									disabled={isLoading}
									class="transition bg-transparent placeholder:text-slate-400 text-sm text-white resize-none focus:outline-none w-full px-2 max-h-24 lg:max-h-36 xl:max-h-48 flex-grow flex-shrink"
									style="min-height: auto;"
								></textarea>
								<button
									type="submit"
									disabled={inputValue.trim().length === 0 || isLoading}
									class="bg-[#24A0ED] text-white disabled:text-black/50 dark:disabled:text-white/50 hover:bg-opacity-85 transition duration-100 disabled:bg-[#e0e0dc79] dark:disabled:bg-[#ececec21] rounded-full p-2"
								>
									<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-4 h-4">
										<path stroke-linecap="round" stroke-linejoin="round" d="M4.5 10.5 12 3m0 0 7.5 7.5M12 3v18m0 0-7.5-7.5M12 21l7.5-7.5" />
									</svg>
								</button>
							{:else}
								<!-- Multi mode: 설정 버튼들 위에 표시 -->
								<div class="flex items-center gap-2 mb-2 w-full">
									<!-- Focus Mode Popover -->
									<div class="relative" bind:this={multiFocusModePopoverRef}>
									<button
										type="button"
										on:click={() => showFocusModePopover = !showFocusModePopover}
										class="p-2 text-white rounded-lg hover:bg-gray-700/60 active:scale-95 transition duration-200 focus:outline-none"
									>
										<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-[18px] h-auto text-white">
											<path stroke-linecap="round" stroke-linejoin="round" d="M12 21a9.004 9.004 0 0 0 8.716-6.747M12 21a9.004 9.004 0 0 1-8.716-6.747M12 21c2.485 0 4.5-4.03 4.5-9S14.485 3 12 3m0 18c-2.485 0-4.5-4.03-4.5-9S9.515 3 12 3m0 0a8.997 8.997 0 0 1 7.843 4.582M12 3a8.997 8.997 0 0 0-7.843 4.582m15.686 0A11.953 11.953 0 0 1 12 10.5c-2.998 0-5.74-1.1-7.843-2.918m15.686 0A8.959 8.959 0 0 1 21 12c0 .778-.099 1.533-.284 2.253m0 0A17.919 17.919 0 0 1 12 16.5c-3.162 0-6.133-.815-8.716-2.247m0 0A9.015 9.015 0 0 1 3 12c0-1.605.42-3.113 1.157-4.418" />
										</svg>
									</button>
										{#if showFocusModePopover}
											<div
												class="absolute bottom-full right-0 mb-2 w-64 bg-gray-800 border border-gray-700/50 rounded-lg shadow-xl z-50 overflow-hidden"
												transition:fly={{ y: 10, duration: 200 }}
											>
												<div class="p-2 space-y-1">
													{#each focusModes as mode}
														<button
															type="button"
															on:click={() => {
																selectedFocusMode = mode.value;
																showFocusModePopover = false;
															}}
															class="w-full text-left px-3 py-2 rounded-lg hover:bg-gray-700/60 transition-colors {selectedFocusMode === mode.value ? 'bg-blue-500/20 border border-blue-500/30' : ''}"
														>
															<div class="flex items-center gap-2 text-sm text-gray-200">
																<span>{mode.icon}</span>
																<span>{mode.label}</span>
															</div>
														</button>
													{/each}
												</div>
											</div>
										{/if}
									</div>
									
									<!-- Model Selector -->
									<div class="relative" bind:this={modelSelectorPopoverRef}>
										<button
											type="button"
											on:click={() => showModelSelectorPopover = !showModelSelectorPopover}
											class="p-2 text-white rounded-lg hover:bg-gray-700/60 active:scale-95 transition duration-200 focus:outline-none disabled:opacity-50"
											disabled={loadingProviders || !selectedChatModel || !selectedEmbeddingModel}
										>
											<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-4 h-4 text-white">
												<path stroke-linecap="round" stroke-linejoin="round" d="M8.25 3v1.5M4.5 8.25H3m18 0h-1.5m-1.5 0V12m0 4.5V12m0 4.5h-1.5m-1.5 0H15m-6 0H4.5m0 0H3m1.5 0v-1.5M15 12v4.5m0-4.5h-1.5m1.5 0H12m-6 0H4.5m0 0V12m0 0H3m1.5 0h1.5m0 0H9m-1.5 0v-1.5M9 3H6.75m0 0H4.5m2.25 0v1.5M9 3v1.5m0 0V8.25m0-4.5h2.25m0 0H15m-2.25 0v1.5M15 3h2.25m0 0H21m-2.25 0v1.5M21 3v1.5m0 0V8.25m0-4.5H18.75m0 0H15m2.25 0h2.25m0 0H21" />
											</svg>
										</button>
										{#if showModelSelectorPopover}
											<div
												class="absolute bottom-full right-0 mb-2 w-80 max-h-96 bg-gray-800 border border-gray-700/50 rounded-lg shadow-xl z-50 overflow-hidden flex flex-col"
												transition:fly={{ y: 10, duration: 200 }}
											>
												<div class="p-2 border-b border-gray-700/50">
													<input
														type="text"
														bind:value={modelSearchQuery}
														placeholder="모델 검색..."
														class="w-full px-3 py-2 bg-gray-700/50 border border-gray-600/50 rounded-lg text-white placeholder-gray-400 text-sm focus:outline-none focus:ring-1 focus:ring-blue-500/50"
													/>
												</div>
												<div class="flex-1 overflow-y-auto p-2 space-y-3">
													{#if loadingProviders}
														<div class="text-center text-gray-400 py-4 text-sm">로딩 중...</div>
													{:else if filteredProviders.length === 0}
														<div class="text-center text-gray-400 py-4 text-sm">모델을 찾을 수 없습니다</div>
													{:else}
														{#each filteredProviders as provider}
															<div class="space-y-2">
																<h4 class="text-xs font-semibold text-gray-400 uppercase px-2">{provider.name}</h4>
																<div class="space-y-1">
																	{#if provider.chatModels.length > 0}
																		<div class="text-xs text-gray-500 px-2">Chat Models</div>
																		{#each provider.chatModels as model}
																			<button
																				type="button"
																				on:click={() => {
																					selectedChatModel = { providerId: provider.id, key: model.key };
																					showModelSelectorPopover = false;
																				}}
																				class="w-full text-left px-3 py-1.5 rounded-lg hover:bg-gray-700/60 transition-colors text-sm {selectedChatModel?.providerId === provider.id && selectedChatModel?.key === model.key ? 'bg-blue-500/20 border border-blue-500/30' : 'text-gray-200'}"
																			>
																				{model.name}
																			</button>
																		{/each}
																	{/if}
																	{#if provider.embeddingModels.length > 0}
																		<div class="text-xs text-gray-500 px-2 mt-2">Embedding Models</div>
																		{#each provider.embeddingModels as model}
																			<button
																				type="button"
																				on:click={() => {
																					selectedEmbeddingModel = { providerId: provider.id, key: model.key };
																					showModelSelectorPopover = false;
																				}}
																				class="w-full text-left px-3 py-1.5 rounded-lg hover:bg-gray-700/60 transition-colors text-sm {selectedEmbeddingModel?.providerId === provider.id && selectedEmbeddingModel?.key === model.key ? 'bg-blue-500/20 border border-blue-500/30' : 'text-gray-200'}"
																			>
																				{model.name}
																			</button>
																		{/each}
																	{/if}
																</div>
															</div>
														{/each}
													{/if}
												</div>
											</div>
										{/if}
									</div>
								</div>
								
								<textarea
									bind:value={inputValue}
									placeholder="Ask a follow-up"
									rows="3"
									disabled={isLoading}
									class="transition bg-transparent placeholder:text-slate-400 text-sm text-white resize-none focus:outline-none w-full px-2 max-h-24 lg:max-h-36 xl:max-h-48 flex-grow flex-shrink"
								></textarea>
								<div class="flex flex-row items-center justify-between w-full pt-2">
									<div></div>
									<button
										type="submit"
										disabled={inputValue.trim().length === 0 || isLoading}
										class="bg-[#24A0ED] text-white disabled:text-black/50 dark:disabled:text-white/50 hover:bg-opacity-85 transition duration-100 disabled:bg-[#e0e0dc79] dark:disabled:bg-[#ececec21] rounded-full p-2"
									>
										<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-4 h-4">
											<path stroke-linecap="round" stroke-linejoin="round" d="M4.5 10.5 12 3m0 0 7.5 7.5M12 3v18m0 0-7.5-7.5M12 21l7.5-7.5" />
										</svg>
									</button>
								</div>
							{/if}
						</div>
					</form>
				</div>
			{/if}
			</div>
		</div>
	</main>
	
	<!-- Sources 모달 -->
	{#each Object.keys(sourcesModalOpen) as messageId}
		{#if sourcesModalOpen[messageId]}
			{@const section = sections.find(s => s.message.messageId === messageId)}
			{#if section}
				<div
					class="fixed inset-0 z-50 flex items-center justify-center backdrop-blur-md bg-black/50"
					on:click={() => {
						sourcesModalOpen[messageId] = false;
						sourcesModalOpen = sourcesModalOpen;
					}}
					on:keydown={(e) => e.key === 'Escape' && (sourcesModalOpen[messageId] = false, sourcesModalOpen = sourcesModalOpen)}
					role="button"
					tabindex="0"
				>
					<div
						class="bg-gray-900 border border-gray-700/50 rounded-2xl p-6 max-w-2xl w-full max-h-[80vh] overflow-hidden flex flex-col"
						on:click|stopPropagation
						on:keydown|stopPropagation
						role="dialog"
						tabindex="-1"
					>
						<div class="flex items-center justify-between mb-4">
							<h3 class="text-lg font-medium text-white">Sources</h3>
							<button
								on:click={() => {
									sourcesModalOpen[messageId] = false;
									sourcesModalOpen = sourcesModalOpen;
								}}
								class="p-1 rounded-lg hover:bg-gray-800 text-gray-400 hover:text-white transition-colors"
							>
								<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-5 h-5">
									<path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
								</svg>
							</button>
						</div>
						<div class="flex-1 overflow-y-auto pr-2">
							<div class="grid grid-cols-2 gap-2">
								{#each section.sources as source, i}
									<a
										href={source.metadata.url || '#'}
										target="_blank"
										rel="noopener noreferrer"
										class="bg-gray-800/60 hover:bg-gray-700/60 border border-gray-700/50 transition duration-200 rounded-lg p-3 flex flex-col space-y-2 font-medium"
									>
										<p class="text-white text-xs overflow-hidden whitespace-nowrap text-ellipsis">
											{source.metadata.title || source.metadata.url || '출처 없음'}
										</p>
										<div class="flex flex-row items-center justify-between">
											<div class="flex flex-row items-center space-x-1">
												{#if source.metadata.url && !source.metadata.url.includes('file_id://')}
													<img
														src={`https://s2.googleusercontent.com/s2/favicons?domain_url=${source.metadata.url}`}
														width={16}
														height={16}
														alt="favicon"
														class="rounded-lg h-4 w-4"
													/>
												{:else}
													<div class="bg-gray-700 hover:bg-gray-600 transition duration-200 flex items-center justify-center w-4 h-4 rounded-full">
														<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-3 h-3 text-gray-400">
															<path stroke-linecap="round" stroke-linejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z" />
														</svg>
													</div>
												{/if}
												<p class="text-xs text-gray-400 overflow-hidden whitespace-nowrap text-ellipsis">
													{source.metadata.url && source.metadata.url.includes('file_id://')
														? 'Uploaded File'
														: source.metadata.url
															? source.metadata.url.replace(/.+\/\/|www.|\..+/g, '')
															: 'Unknown'}
												</p>
											</div>
											<div class="flex flex-row items-center space-x-1 text-gray-400 text-xs">
												<div class="bg-gray-500 h-[4px] w-[4px] rounded-full" />
												<span>{i + 1}</span>
											</div>
										</div>
									</a>
								{/each}
							</div>
						</div>
					</div>
				</div>
			{/if}
		{/if}
	{/each}
	
	<!-- 라이트박스 모달 -->
	{#each Object.keys(lightboxOpen) as messageId}
		{#if lightboxOpen[messageId]?.open && lightboxOpen[messageId]?.slides?.length > 0}
			<div
				class="fixed inset-0 z-50 flex items-center justify-center backdrop-blur-md bg-black/80"
				on:click={() => {
					lightboxOpen[messageId].open = false;
					lightboxOpen = lightboxOpen;
				}}
				on:keydown={(e) => e.key === 'Escape' && (lightboxOpen[messageId].open = false, lightboxOpen = lightboxOpen)}
				role="button"
				tabindex="0"
			>
				<div class="relative max-w-7xl max-h-[90vh] w-full h-full flex items-center justify-center p-4">
					<button
						on:click|stopPropagation={() => {
							lightboxOpen[messageId].open = false;
							lightboxOpen = lightboxOpen;
						}}
						class="absolute top-4 right-4 p-2 rounded-full bg-gray-800/80 hover:bg-gray-700/80 text-white transition-colors z-10"
					>
						<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-6 h-6">
							<path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
						</svg>
					</button>
					
					{#if lightboxOpen[messageId].slides[lightboxOpen[messageId].currentIndex]?.type === 'video'}
						<div class="w-full h-full flex items-center justify-center">
							<iframe
								src={`${lightboxOpen[messageId].slides[lightboxOpen[messageId].currentIndex].iframe_src}${lightboxOpen[messageId].slides[lightboxOpen[messageId].currentIndex].iframe_src.includes('?') ? '&' : '?'}enablejsapi=1`}
								class="aspect-video max-h-[95vh] w-[95vw] rounded-2xl md:w-[80vw]"
								allowFullScreen
								allow="accelerometer; autoplay; encrypted-media; gyroscope; picture-in-picture"
							/>
						</div>
					{:else}
						<img
							src={lightboxOpen[messageId].slides[lightboxOpen[messageId].currentIndex]?.src}
							alt="Lightbox image"
							class="max-w-full max-h-[90vh] object-contain rounded-lg"
							on:click|stopPropagation
						/>
					{/if}
					
					{#if lightboxOpen[messageId].slides.length > 1}
						<button
							on:click|stopPropagation={() => {
								lightboxOpen[messageId].currentIndex = (lightboxOpen[messageId].currentIndex - 1 + lightboxOpen[messageId].slides.length) % lightboxOpen[messageId].slides.length;
								lightboxOpen = lightboxOpen;
							}}
							class="absolute left-4 top-1/2 -translate-y-1/2 p-2 rounded-full bg-gray-800/80 hover:bg-gray-700/80 text-white transition-colors"
						>
							<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-6 h-6">
								<path stroke-linecap="round" stroke-linejoin="round" d="M15.75 19.5 8.25 12l7.5-7.5" />
							</svg>
						</button>
						<button
							on:click|stopPropagation={() => {
								lightboxOpen[messageId].currentIndex = (lightboxOpen[messageId].currentIndex + 1) % lightboxOpen[messageId].slides.length;
								lightboxOpen = lightboxOpen;
							}}
							class="absolute right-4 top-1/2 -translate-y-1/2 p-2 rounded-full bg-gray-800/80 hover:bg-gray-700/80 text-white transition-colors"
						>
							<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-6 h-6">
								<path stroke-linecap="round" stroke-linejoin="round" d="m8.25 4.5 7.5 7.5-7.5 7.5" />
							</svg>
						</button>
					{/if}
				</div>
			</div>
		{/if}
	{/each}
	
	<!-- Settings 다이얼로그 -->
	{#if showSettingsDialog}
		<div
			class="fixed inset-0 z-50 flex items-center justify-center backdrop-blur-md bg-black/30"
			on:click={() => showSettingsDialog = false}
			on:keydown={(e) => e.key === 'Escape' && (showSettingsDialog = false)}
			role="button"
			tabindex="0"
		>
			<div
				class="bg-gray-900 border border-gray-700/50 rounded-xl h-[calc(100vh-10%)] w-[calc(100vw-10%)] md:h-[calc(100vh-20%)] md:w-[calc(100vw-30%)] overflow-hidden flex flex-col max-w-4xl"
				on:click|stopPropagation
				on:keydown|stopPropagation
				role="dialog"
				tabindex="-1"
			>
				<!-- 헤더 -->
				<div class="px-6 py-4 border-b border-gray-800/50 flex items-center justify-between">
					<h2 class="text-lg font-semibold text-white">설정</h2>
					<button
						on:click={() => showSettingsDialog = false}
						class="p-1 hover:bg-gray-800 rounded-lg transition-colors text-gray-400 hover:text-white"
					>
						<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-5 h-5">
							<path stroke-linecap="round" stroke-linejoin="round" d="M6 18 18 6M6 6l12 12" />
						</svg>
					</button>
				</div>
				
				<!-- 본문 -->
				<div class="flex flex-1 overflow-hidden">
					<!-- 사이드바 -->
					<div class="hidden lg:flex flex-col w-64 border-r border-gray-800/50 px-3 pt-3 overflow-y-auto">
						<button
							on:click={() => settingsActiveSection = 'personalization'}
							class="flex items-center gap-2 px-2 py-1.5 rounded-lg text-sm transition-colors {settingsActiveSection === 'personalization' ? 'bg-gray-800/60 text-white' : 'text-gray-400 hover:text-white hover:bg-gray-800/40'}"
						>
							<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="w-4 h-4">
								<path stroke-linecap="round" stroke-linejoin="round" d="M9.594 3.94c.09-.542.56-.94 1.11-.94h2.593c.55 0 1.02.398 1.11.94l.213 1.281c.063.374.313.686.645.87.074.04.147.083.22.127.324.196.72.257 1.075.124l1.217-.456a1.125 1.125 0 0 1 1.37.49l1.296 2.247a1.125 1.125 0 0 1-.26 1.431l-1.003.827c-.293.24-.438.613-.431.992a6.759 6.759 0 0 1 0 .255c-.007.378.138.75.43.99l1.005.828c.424.35.534.954.26 1.43l-1.298 2.247a1.125 1.125 0 0 1-1.369.491l-1.217-.456c-.355-.133-.75-.072-1.076.124a6.57 6.57 0 0 1-.22.128c-.331.183-.581.495-.644.869l-.213 1.28c-.09.543-.56.941-1.11.941h-2.594c-.55 0-1.02-.398-1.11-.94l-.213-1.281c-.062-.374-.312-.686-.644-.87a6.52 6.52 0 0 1-.22-.127c-.325-.196-.72-.257-1.076-.124l-1.217.456a1.125 1.125 0 0 1-1.369-.49l-1.297-2.247a1.125 1.125 0 0 1 .26-1.431l1.004-.827c.292-.24.437-.613.43-.992a6.932 6.932 0 0 1 0-.255c.007-.378-.138-.75-.43-.99l-1.004-.828a1.125 1.125 0 0 1-.26-1.43l1.297-2.247a1.125 1.125 0 0 1 1.37-.491l1.216.456c.356.133.751.072 1.076-.124.072-.044.146-.087.22-.128.332-.183.582-.495.644-.869l.214-1.281Z" />
								<path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z" />
							</svg>
							Personalization
						</button>
					</div>
					
					<!-- 콘텐츠 -->
					<div class="flex-1 overflow-y-auto p-6">
						{#if settingsActiveSection === 'personalization'}
							<div class="space-y-4">
								<div>
									<h3 class="text-base font-semibold text-white mb-2">시스템 지시사항</h3>
									<p class="text-sm text-gray-400 mb-3">AI의 행동이나 톤을 정의하는 지침을 입력하세요.</p>
									<textarea
										bind:value={systemInstructions}
										placeholder="예: 항상 한국어로 답변하고, 전문적이면서도 친근한 톤을 유지하세요."
										class="w-full h-32 px-4 py-3 bg-gray-800/60 border border-gray-700/50 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500/50 resize-none text-sm"
									></textarea>
								</div>
							</div>
						{/if}
					</div>
				</div>
				
				<!-- 푸터 -->
				<div class="px-6 py-4 border-t border-gray-800/50 flex justify-end gap-3">
					<button
						on:click={() => showSettingsDialog = false}
						class="px-4 py-2 rounded-lg bg-gray-800/60 hover:bg-gray-700/60 text-white transition-colors"
					>
						닫기
					</button>
					<button
						on:click={() => {
							showSettingsDialog = false;
							toast.success('설정이 저장되었습니다.');
						}}
						class="px-4 py-2 rounded-lg bg-gradient-to-r from-blue-500 to-purple-500 text-white hover:shadow-lg transition-all"
					>
						저장
					</button>
				</div>
			</div>
		</div>
	{/if}
</div>
