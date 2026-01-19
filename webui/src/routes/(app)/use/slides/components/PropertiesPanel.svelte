<script lang="ts">
	import { slideStudioStore } from '../stores/slideStudioStore';
	
	let store = slideStudioStore.get();
	
	const unsubscribe = slideStudioStore.subscribe((s) => {
		store = s;
	});
	
	$: selectedSlideId = store.selectedSlideIds[0] || null;
	$: selectedElementId = store.selectedElementId;
	
	let editingBbox = { x: 0, y: 0, w: 0, h: 0 };
	let editingStyle = {
		font_size: 18,
		font_family: 'Pretendard',
		color: '#1f2937',
		align: 'left'
	};
	
	async function handleBboxChange() {
		if (!store.deck_id || !selectedSlideId || !selectedElementId) return;
		
		try {
			await fetch(`/api/slides/${store.deck_id}/slides/${selectedSlideId}/elements/${selectedElementId}`, {
				method: 'PATCH',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify({
					bbox: editingBbox
				})
			});
		} catch (error) {
			console.error('Failed to update bbox:', error);
		}
	}
	
	async function handleStyleChange() {
		if (!store.deck_id || !selectedSlideId || !selectedElementId) return;
		
		try {
			await fetch(`/api/slides/${store.deck_id}/slides/${selectedSlideId}/elements/${selectedElementId}`, {
				method: 'PATCH',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify({
					style: editingStyle
				})
			});
		} catch (error) {
			console.error('Failed to update style:', error);
		}
	}
	
	async function handleReflow() {
		if (!store.deck_id) return;
		
		try {
			await fetch(`/api/slides/${store.deck_id}/reflow`, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify({
					scope: selectedSlideId ? 'slide' : 'deck',
					slide_id: selectedSlideId
				})
			});
		} catch (error) {
			console.error('Failed to reflow:', error);
		}
	}
</script>

<div class="space-y-4">
	<h3 class="text-sm font-semibold text-white mb-4">Properties</h3>
	
	{#if selectedElementId}
		<!-- Element properties -->
		<div class="space-y-4">
			<!-- Box (Position & Size) -->
			<div>
				<h4 class="text-xs font-medium text-gray-400 mb-2">Box</h4>
				<div class="grid grid-cols-2 gap-2">
					<div>
						<label class="block text-xs text-gray-500 mb-1">X</label>
						<input
							type="number"
							bind:value={editingBbox.x}
							on:change={handleBboxChange}
							class="w-full px-2 py-1 bg-gray-700 border border-gray-600 rounded text-white text-sm"
						/>
					</div>
					<div>
						<label class="block text-xs text-gray-500 mb-1">Y</label>
						<input
							type="number"
							bind:value={editingBbox.y}
							on:change={handleBboxChange}
							class="w-full px-2 py-1 bg-gray-700 border border-gray-600 rounded text-white text-sm"
						/>
					</div>
					<div>
						<label class="block text-xs text-gray-500 mb-1">W</label>
						<input
							type="number"
							bind:value={editingBbox.w}
							on:change={handleBboxChange}
							class="w-full px-2 py-1 bg-gray-700 border border-gray-600 rounded text-white text-sm"
						/>
					</div>
					<div>
						<label class="block text-xs text-gray-500 mb-1">H</label>
						<input
							type="number"
							bind:value={editingBbox.h}
							on:change={handleBboxChange}
							class="w-full px-2 py-1 bg-gray-700 border border-gray-600 rounded text-white text-sm"
						/>
					</div>
				</div>
			</div>
			
			<!-- Typography -->
			<div>
				<h4 class="text-xs font-medium text-gray-400 mb-2">Typography</h4>
				<div class="space-y-2">
					<div>
						<label class="block text-xs text-gray-500 mb-1">Font Size</label>
						<input
							type="number"
							bind:value={editingStyle.font_size}
							on:change={handleStyleChange}
							class="w-full px-2 py-1 bg-gray-700 border border-gray-600 rounded text-white text-sm"
						/>
					</div>
					<div>
						<label class="block text-xs text-gray-500 mb-1">Font Family</label>
						<select
							bind:value={editingStyle.font_family}
							on:change={handleStyleChange}
							class="w-full px-2 py-1 bg-gray-700 border border-gray-600 rounded text-white text-sm"
						>
							<option value="Pretendard">Pretendard</option>
							<option value="Noto Sans KR">Noto Sans KR</option>
						</select>
					</div>
					<div>
						<label class="block text-xs text-gray-500 mb-1">Color</label>
						<input
							type="color"
							bind:value={editingStyle.color}
							on:change={handleStyleChange}
							class="w-full h-8 bg-gray-700 border border-gray-600 rounded"
						/>
					</div>
					<div>
						<label class="block text-xs text-gray-500 mb-1">Align</label>
						<select
							bind:value={editingStyle.align}
							on:change={handleStyleChange}
							class="w-full px-2 py-1 bg-gray-700 border border-gray-600 rounded text-white text-sm"
						>
							<option value="left">Left</option>
							<option value="center">Center</option>
							<option value="right">Right</option>
						</select>
					</div>
				</div>
			</div>
			
			<!-- Reflow button -->
			<button
				on:click={handleReflow}
				class="w-full px-4 py-2 rounded-lg bg-gray-700 hover:bg-gray-600 text-white text-sm font-medium transition-colors"
			>
				Reflow Layout
			</button>
		</div>
	{:else}
		<!-- Slide properties (when no element selected) -->
		<div class="text-sm text-gray-500 text-center py-8">
			Select an element to edit properties
		</div>
	{/if}
</div>
