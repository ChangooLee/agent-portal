<script lang="ts">
	import { slideStudioStore } from '../stores/slideStudioStore';
	
	let store = slideStudioStore.get();
	let previewMode: 'preview' | 'edit' | 'diff' = 'preview';
	
	const unsubscribe = slideStudioStore.subscribe((s) => {
		store = s;
	});
	
	// UTF-8 safe base64 decoder
	function decodeBase64Utf8(base64: string): string {
		try {
			// Decode base64 to binary string
			const binaryString = atob(base64);
			// Convert binary string to UTF-8
			const bytes = new Uint8Array(binaryString.length);
			for (let i = 0; i < binaryString.length; i++) {
				bytes[i] = binaryString.charCodeAt(i);
			}
			// Decode UTF-8
			return new TextDecoder('utf-8').decode(bytes);
		} catch (e) {
			console.error('Base64 decode error:', e);
			return '';
		}
	}
	
	$: selectedSlide = store.slides.find(s => store.selectedSlideIds.includes(s.slide_id));
	$: isHtmlPreview = selectedSlide?.thumbnailUrl?.startsWith('data:text/html');
	$: previewHtml = isHtmlPreview && selectedSlide?.thumbnailUrl 
		? decodeBase64Utf8(selectedSlide.thumbnailUrl.split(',')[1]) 
		: null;
</script>

<div class="h-full flex flex-col bg-gray-950">
	<!-- Mode tabs -->
	<div class="flex border-b border-gray-800 px-4 pt-4">
		<button
			on:click={() => previewMode = 'preview'}
			class="px-4 py-2 text-sm font-medium transition-colors
				{previewMode === 'preview'
					? 'text-purple-400 border-b-2 border-purple-400'
					: 'text-gray-400 hover:text-gray-300'}"
		>
			Preview
		</button>
		<button
			on:click={() => previewMode = 'edit'}
			class="px-4 py-2 text-sm font-medium transition-colors
				{previewMode === 'edit'
					? 'text-purple-400 border-b-2 border-purple-400'
					: 'text-gray-400 hover:text-gray-300'}"
		>
			Edit
		</button>
		<button
			on:click={() => previewMode = 'diff'}
			class="px-4 py-2 text-sm font-medium transition-colors
				{previewMode === 'diff'
					? 'text-purple-400 border-b-2 border-purple-400'
					: 'text-gray-400 hover:text-gray-300'}"
		>
			Diff
		</button>
	</div>
	
	<!-- Preview content -->
	<div class="flex-1 flex items-center justify-center p-8 overflow-auto">
		{#if selectedSlide}
			<div class="w-full max-w-4xl">
				{#if previewMode === 'preview'}
					<!-- Preview mode -->
					<div class="bg-white rounded-lg shadow-xl overflow-hidden">
						<!-- 16:9 aspect ratio container -->
						<div class="aspect-video bg-gray-100 flex items-center justify-center relative">
							{#if isHtmlPreview && previewHtml}
								<!-- HTML preview -->
								<iframe
									srcdoc={previewHtml}
									class="w-full h-full border-0"
									sandbox="allow-same-origin"
								></iframe>
							{:else if selectedSlide.thumbnailUrl}
								<!-- Image thumbnail -->
								<img
									src={selectedSlide.thumbnailUrl}
									alt={selectedSlide.title}
									class="w-full h-full object-contain"
								/>
							{:else}
								<!-- Skeleton -->
								<div class="text-gray-400 text-center">
									<div class="text-sm">{selectedSlide.title || 'Untitled'}</div>
									<div class="text-xs mt-2 text-gray-500">{selectedSlide.stage}</div>
								</div>
							{/if}
						</div>
					</div>
				{:else if previewMode === 'edit'}
					<!-- Edit mode -->
					<div class="bg-white rounded-lg shadow-xl overflow-hidden relative" style="width: {selectedSlide ? '1920px' : '100%'}; height: {selectedSlide ? '1080px' : '600px'}; transform: scale(0.5); transform-origin: top left;">
						{#if isHtmlPreview && previewHtml}
							<!-- Editable HTML preview -->
							<iframe
								srcdoc={previewHtml}
								class="w-full h-full border-0 pointer-events-auto"
								sandbox="allow-same-origin allow-scripts"
							></iframe>
						{:else if selectedSlide.thumbnailUrl}
							<!-- Image thumbnail (editable) -->
							<img
								src={selectedSlide.thumbnailUrl}
								alt={selectedSlide.title}
								class="w-full h-full object-contain"
							/>
						{:else}
							<div class="text-gray-400 text-center">
								<div class="text-sm">{selectedSlide.title || 'Untitled'}</div>
							</div>
						{/if}
					</div>
					<div class="text-xs text-gray-500 mt-2">
						Edit mode: Click elements to select, drag to move, resize handles to resize
					</div>
				{:else}
					<!-- Diff mode placeholder -->
					<div class="text-center text-gray-500">
						<div class="text-sm">Diff mode - Coming in Step 6</div>
					</div>
				{/if}
			</div>
		{:else}
			<div class="text-center text-gray-500">
				<div class="text-lg">Select a slide to preview</div>
			</div>
		{/if}
	</div>
</div>
