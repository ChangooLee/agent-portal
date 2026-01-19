<script lang="ts">
	import { onDestroy } from 'svelte';
	import { slideStudioStore } from '../stores/slideStudioStore';

	export let onGenerate: (data: GenerateData) => void;

	interface GenerateData {
		prompt: string;
		goal?: string;
		audience?: string;
		tone?: string;
		slide_count: number;
		options?: {
			include_images?: boolean;
			use_playwright?: boolean;
		};
	}

	let prompt = '';
	let goal = '';
	let audience = '';
	let tone = 'formal';
	let slideCount = 10;
	let includeImages = true;
	let usePlaywright = false;
	let showAdvanced = false;

	const toneOptions = ['formal', 'casual', 'professional', 'friendly'];

	let store = slideStudioStore.get();
	const unsubscribe = slideStudioStore.subscribe((s) => {
		store = s;
	});

	onDestroy(() => {
		unsubscribe();
	});

	function handleSubmit() {
		if (!prompt.trim()) return;

		// Add user message to history
		slideStudioStore.addMessage({
			id: `msg-${Date.now()}`,
			role: 'user',
			content: prompt,
			timestamp: new Date().toISOString(),
			metadata: {
				goal: goal || undefined,
				audience: audience || undefined,
				tone: tone || undefined,
				slide_count: slideCount
			}
		});

		onGenerate({
			prompt,
			goal: goal || undefined,
			audience: audience || undefined,
			tone: tone || undefined,
			slide_count: slideCount,
			options: {
				include_images: includeImages,
				use_playwright: usePlaywright
			}
		});

		// Clear prompt but keep other fields
		prompt = '';
	}

	function handleKeyDown(e: KeyboardEvent) {
		if (e.key === 'Enter' && !e.shiftKey) {
			e.preventDefault();
			handleSubmit();
		}
	}
</script>

<div class="w-full max-w-4xl mx-auto px-4 pb-6">
	<div class="bg-gray-800/50 backdrop-blur-sm rounded-2xl border border-gray-700/50 shadow-lg">
		<!-- Main input area -->
		<div class="p-4">
			<textarea
				bind:value={prompt}
				on:keydown={handleKeyDown}
				placeholder="발표 주제와 요구 사항을 입력하세요..."
				class="w-full bg-transparent text-white placeholder-gray-400 resize-none focus:outline-none text-sm min-h-[60px] max-h-[200px]"
				rows="2"
			></textarea>
		</div>

		<!-- Options bar -->
		<div class="px-4 pb-3 flex items-center justify-between border-t border-gray-700/50">
			<div class="flex items-center gap-3">
				<!-- Advanced toggle -->
				<button
					on:click={() => showAdvanced = !showAdvanced}
					class="text-xs text-gray-400 hover:text-gray-300 transition-colors flex items-center gap-1"
				>
					<svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4" />
					</svg>
					{showAdvanced ? '간단히' : '고급 옵션'}
				</button>

				{#if showAdvanced}
					<!-- Slide count -->
					<div class="flex items-center gap-2">
						<label class="text-xs text-gray-400">슬라이드:</label>
						<input
							type="number"
							bind:value={slideCount}
							min="1"
							max="50"
							class="w-16 px-2 py-1 bg-gray-700 border border-gray-600 rounded text-white text-xs focus:outline-none focus:ring-1 focus:ring-purple-500"
						/>
					</div>

					<!-- Tone selector -->
					<select
						bind:value={tone}
						class="px-2 py-1 bg-gray-700 border border-gray-600 rounded text-white text-xs focus:outline-none focus:ring-1 focus:ring-purple-500"
					>
						{#each toneOptions as opt}
							<option value={opt}>{opt}</option>
						{/each}
					</select>
				{/if}
			</div>

			<!-- Action buttons -->
			<div class="flex items-center gap-2">
				{#if showAdvanced}
					<!-- Checkboxes -->
					<label class="flex items-center gap-1 text-xs text-gray-400 cursor-pointer">
						<input
							type="checkbox"
							bind:checked={includeImages}
							class="w-3 h-3 rounded bg-gray-700 border-gray-600 text-purple-600 focus:ring-purple-500"
						/>
						<span>이미지</span>
					</label>
					<label class="flex items-center gap-1 text-xs text-gray-400 cursor-pointer">
						<input
							type="checkbox"
							bind:checked={usePlaywright}
							class="w-3 h-3 rounded bg-gray-700 border-gray-600 text-purple-600 focus:ring-purple-500"
						/>
						<span>Playwright</span>
					</label>
				{/if}

				<!-- Send button -->
				<button
					on:click={handleSubmit}
					disabled={!prompt.trim() || store.globalStatus === 'generating'}
					class="px-4 py-2 bg-purple-600 hover:bg-purple-700 disabled:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed text-white rounded-lg transition-colors flex items-center gap-2 text-sm font-medium"
				>
					{#if store.globalStatus === 'generating'}
						<svg class="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
							<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
							<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
						</svg>
						생성 중...
					{:else}
						<svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
						</svg>
						전송
					{/if}
				</button>
			</div>
		</div>

		<!-- Advanced options (collapsible) -->
		{#if showAdvanced}
			<div class="px-4 pb-4 space-y-3 border-t border-gray-700/50 pt-3">
				<div>
					<label class="block text-xs font-medium text-gray-400 mb-1">목표 (선택사항)</label>
					<input
						type="text"
						bind:value={goal}
						placeholder="이 프레젠테이션의 목표는 무엇인가요?"
						class="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white text-sm placeholder-gray-500 focus:outline-none focus:ring-1 focus:ring-purple-500"
					/>
				</div>
				<div>
					<label class="block text-xs font-medium text-gray-400 mb-1">대상 (선택사항)</label>
					<input
						type="text"
						bind:value={audience}
						placeholder="누구를 위한 프레젠테이션인가요?"
						class="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white text-sm placeholder-gray-500 focus:outline-none focus:ring-1 focus:ring-purple-500"
					/>
				</div>
			</div>
		{/if}
	</div>
</div>
