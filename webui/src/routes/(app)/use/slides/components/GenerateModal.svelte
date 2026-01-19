<script lang="ts">
	export let open = false;
	export let onClose: () => void;
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
	
	const toneOptions = ['formal', 'casual', 'professional', 'friendly'];
	
	function handleSubmit() {
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
		onClose();
	}
</script>

{#if open}
	<div
		class="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4"
		on:click={onClose}
		role="button"
		tabindex="0"
	>
		<div
			class="bg-gray-800 rounded-2xl shadow-xl max-w-2xl w-full max-h-[90vh] overflow-hidden"
			on:click|stopPropagation
		>
			<!-- Header -->
			<div class="px-6 py-4 border-b border-gray-700 flex items-center justify-between">
				<h2 class="text-lg font-semibold text-white">Generate Slides</h2>
				<button
					on:click={onClose}
					class="p-1 hover:bg-gray-700 rounded-lg transition-colors"
				>
					<svg class="w-5 h-5 text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
					</svg>
				</button>
			</div>
			
			<!-- Content -->
			<div class="p-6 space-y-4 overflow-y-auto max-h-[calc(90vh-140px)]">
				<div>
					<label class="block text-sm font-medium text-gray-300 mb-2">
						Topic / Prompt *
					</label>
					<input
						type="text"
						bind:value={prompt}
						placeholder="Enter topic for your presentation"
						class="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-purple-500"
					/>
				</div>
				
				<div>
					<label class="block text-sm font-medium text-gray-300 mb-2">
						Goal (Optional)
					</label>
					<input
						type="text"
						bind:value={goal}
						placeholder="What is the goal of this presentation?"
						class="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-purple-500"
					/>
				</div>
				
				<div>
					<label class="block text-sm font-medium text-gray-300 mb-2">
						Audience (Optional)
					</label>
					<input
						type="text"
						bind:value={audience}
						placeholder="Who is the target audience?"
						class="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-purple-500"
					/>
				</div>
				
				<div>
					<label class="block text-sm font-medium text-gray-300 mb-2">
						Tone
					</label>
					<select
						bind:value={tone}
						class="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-purple-500"
					>
						{#each toneOptions as opt}
							<option value={opt}>{opt}</option>
						{/each}
					</select>
				</div>
				
				<div>
					<label class="block text-sm font-medium text-gray-300 mb-2">
						Slide Count
					</label>
					<input
						type="number"
						bind:value={slideCount}
						min="1"
						max="50"
						class="w-full px-4 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-purple-500"
					/>
				</div>
				
				<div class="flex items-center gap-2">
					<input
						type="checkbox"
						bind:checked={includeImages}
						id="include-images"
						class="w-4 h-4 rounded bg-gray-700 border-gray-600 text-purple-600 focus:ring-purple-500"
					/>
					<label for="include-images" class="text-sm text-gray-300">
						Include images (Asset Library / Icons / Placeholders)
					</label>
				</div>
				
				<div class="flex items-center gap-2">
					<input
						type="checkbox"
						bind:checked={usePlaywright}
						id="use-playwright"
						class="w-4 h-4 rounded bg-gray-700 border-gray-600 text-purple-600 focus:ring-purple-500"
					/>
					<label for="use-playwright" class="text-sm text-gray-300">
						Use Playwright verification (advanced)
					</label>
				</div>
			</div>
			
			<!-- Footer -->
			<div class="px-6 py-4 border-t border-gray-700 flex justify-end gap-3">
				<button
					on:click={onClose}
					class="px-4 py-2 rounded-lg bg-gray-700 hover:bg-gray-600 text-white transition-colors"
				>
					Cancel
				</button>
				<button
					on:click={handleSubmit}
					disabled={!prompt.trim()}
					class="px-4 py-2 rounded-lg bg-purple-600 hover:bg-purple-700 text-white transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
				>
					Generate
				</button>
			</div>
		</div>
	</div>
{/if}
