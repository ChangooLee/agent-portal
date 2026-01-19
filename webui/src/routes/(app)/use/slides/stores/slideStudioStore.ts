/**
 * Slide Studio Store
 * 
 * Manages deck state and SSE event handling
 */

export interface Slide {
	slide_id: string;
	title: string;
	type: string;
	stage: string;
	score: number | null;
	issuesCount: number;
	thumbnailUrl: string | null;
}

export interface ChatMessage {
	id: string;
	role: 'user' | 'assistant';
	content: string;
	timestamp: string;
	metadata?: {
		deck_id?: string;
		slide_count?: number;
		[key: string]: any;
	};
}

export interface DeckStore {
	deck_id: string | null;
	slides: Slide[];
	selectedSlideIds: string[];
	selectedElementId: string | null;
	globalStatus: 'idle' | 'generating' | 'exporting' | 'ready';
	viewMode: 'chat' | 'editor';
	messages: ChatMessage[];
	exportArtifacts: {
		pptxUrl?: string;
		pdfUrl?: string;
	};
	eventLog: {
		bySlideId: Record<string, Array<{
			timestamp: string;
			stage: string;
			message: string;
		}>>;
	};
}

function createSlideStudioStore() {
	let store: DeckStore = {
		deck_id: null,
		slides: [],
		selectedSlideIds: [],
		selectedElementId: null,
		globalStatus: 'idle',
		viewMode: 'chat',
		messages: [],
		exportArtifacts: {},
		eventLog: {
			bySlideId: {}
		}
	};

	const subscribers = new Set<(store: DeckStore) => void>();

	function subscribe(callback: (store: DeckStore) => void) {
		subscribers.add(callback);
		return () => {
			subscribers.delete(callback);
		};
	}

	function set(newStore: Partial<DeckStore>) {
		store = { ...store, ...newStore };
		subscribers.forEach(cb => cb(store));
	}

	function update(updater: (store: DeckStore) => Partial<DeckStore>) {
		const updates = updater(store);
		set(updates);
	}

	function get() {
		return store;
	}

	// SSE event handlers
	function handleSSEEvent(eventType: string, data: any) {
		switch (eventType) {
			case 'deck.created':
				update(s => ({
					...s,
					deck_id: data.deck_id,
					globalStatus: 'generating'
				}));
				break;

			case 'deck.plan.created':
				const slides: Slide[] = data.slides.map((s: any) => ({
					slide_id: s.slide_id,
					title: s.title || 'Untitled',
					type: s.type || 'BULLET',
					stage: 'PLANNED',
					score: null,
					issuesCount: 0,
					thumbnailUrl: null
				}));
				update(s => ({
					...s,
					slides,
					selectedSlideIds: slides.length > 0 ? [slides[0].slide_id] : []
				}));
				break;

			case 'slide.stage':
				update(s => {
					const slideIndex = s.slides.findIndex(slide => slide.slide_id === data.slide_id);
					if (slideIndex === -1) return s;

					const updatedSlides = [...s.slides];
					updatedSlides[slideIndex] = {
						...updatedSlides[slideIndex],
						stage: data.stage
					};

					// Update event log
					const logEntry = {
						timestamp: new Date().toISOString(),
						stage: data.stage,
						message: data.message || ''
					};
					const eventLog = { ...s.eventLog };
					if (!eventLog.bySlideId[data.slide_id]) {
						eventLog.bySlideId[data.slide_id] = [];
					}
					eventLog.bySlideId[data.slide_id].push(logEntry);

					return {
						...s,
						slides: updatedSlides,
						eventLog
					};
				});
				break;

			case 'slide.preview.updated':
				update(s => {
					const slideIndex = s.slides.findIndex(slide => slide.slide_id === data.slide_id);
					if (slideIndex === -1) return s;

					const updatedSlides = [...s.slides];
					updatedSlides[slideIndex] = {
						...updatedSlides[slideIndex],
						thumbnailUrl: data.thumbnail_url || data.thumbnail_data_uri || null
					};

					return {
						...s,
						slides: updatedSlides
					};
				});
				break;

			case 'slide.issues':
				update(s => {
					const slideIndex = s.slides.findIndex(slide => slide.slide_id === data.slide_id);
					if (slideIndex === -1) return s;

					const updatedSlides = [...s.slides];
					updatedSlides[slideIndex] = {
						...updatedSlides[slideIndex],
						score: data.score || null,
						issuesCount: data.issues?.length || 0
					};

					return {
						...s,
						slides: updatedSlides
					};
				});
				break;

			case 'slide.finalized':
				update(s => {
					const slideIndex = s.slides.findIndex(slide => slide.slide_id === data.slide_id);
					if (slideIndex === -1) return s;

					const updatedSlides = [...s.slides];
					updatedSlides[slideIndex] = {
						...updatedSlides[slideIndex],
						stage: 'FINAL',
						score: data.score || null
					};

					// Check if all slides are finalized
					const allFinalized = updatedSlides.every(
						slide => slide.stage === 'FINAL' || slide.stage === 'FINAL_WITH_WARNINGS' || slide.stage === 'ERROR'
					);

					return {
						...s,
						slides: updatedSlides,
						globalStatus: allFinalized ? 'ready' : s.globalStatus
					};
				});
				break;

			case 'export.started':
				update(s => ({
					...s,
					globalStatus: 'exporting'
				}));
				break;

			case 'export.finished':
				update(s => ({
					...s,
					globalStatus: 'ready',
					exportArtifacts: {
						pptxUrl: data.pptx_path,
						pdfUrl: data.pdf_path
					}
				}));
				break;

			case 'job.error':
				console.error('Job error:', data);
				break;

			case 'job.stopped':
				update(s => ({
					...s,
					globalStatus: 'ready'
				}));
				break;
		}
	}

	function addMessage(message: ChatMessage) {
		update(s => ({
			...s,
			messages: [...s.messages, message]
		}));
	}

	function clearMessages() {
		update(s => ({
			...s,
			messages: []
		}));
	}

	return {
		subscribe,
		set,
		update,
		get,
		handleSSEEvent,
		addMessage,
		clearMessages
	};
}

export const slideStudioStore = createSlideStudioStore();
