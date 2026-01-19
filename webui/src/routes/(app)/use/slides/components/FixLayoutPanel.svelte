<script lang="ts">
	import { slideStudioStore } from '../stores/slideStudioStore';
	
	let store = slideStudioStore.get();
	
	const unsubscribe = slideStudioStore.subscribe((s) => {
		store = s;
	});
	
	let scope: 'slide' | 'selected' | 'deck' = 'slide';
	let mode: 'auto' | 'split' | 'simplify' = 'auto';
	let loading = false;
	let result: { fixed: number; remaining: number } | null = null;
	
	async function handleFixLayout() {
		if (!store.deck_id) return;
		
		loading = true;
		result = null;
		
		try {
			const slideId = scope === 'slide' ? store.selectedSlideIds[0] : undefined;
			const requestScope = scope === 'deck' ? 'deck' : 'slide';
			
			const response = await fetch(`/api/slides/${store.deck_id}/fix-layout`, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify({
					mode,
					scope: requestScope,
					slide_id: slideId
				})
			});
			
			if (!response.ok) {
				throw new Error('Failed to fix layout');
			}
			
			const data = await response.json();
			result = {
				fixed: data.fixed_slides || 0,
				remaining: 0  // TODO: Calculate remaining from quality check
			};
		} catch (error) {
			console.error('Fix layout error:', error);
			alert('Failed to fix layout: ' + error);
		} finally {
			loading = false;
		}
	}
</script>

<div class="space-y-4">
	<h3 class="text-sm font-semibold text-white mb-4">Fix Layout</h3>
	
	<!-- Scope -->
	<div>
		<label class="block text-sm font-medium text-gray-300 mb-2">
			Scope
		</label>
		<select
			bind:value={scope}
			class="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
		>
			<option value="slide">This Slide</option>
			<option value="selected">Selected Slides</option>
			<option value="deck">Entire Deck</option>
		</select>
	</div>
	
	<!-- Mode -->
	<div>
		<label class="block text-sm font-medium text-gray-300 mb-2">
			Mode
		</label>
		<select
			bind:value={mode}
			class="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
		>
			<option value="auto">Auto (Text compression + minimal changes)</option>
			<option value="split">Split (Overflow slide split)</option>
			<option value="simplify">Simplify (Layout simplification: 2-col → 1-col)</option>
		</select>
	</div>
	
	<!-- Run button -->
	<button
		on:click={handleFixLayout}
		disabled={loading || !store.deck_id}
		class="w-full px-4 py-2 rounded-lg bg-purple-600 hover:bg-purple-700 text-white font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
	>
		{loading ? 'Running...' : 'Run Fix Layout'}
	</button>
	
	<!-- Results -->
	{#if result}
		<div class="p-3 rounded-lg bg-green-500/10 border border-green-500/30">
			<div class="text-sm text-green-300">
				Fixed issues: {result.fixed}
			</div>
			{#if result.remaining > 0}
				<div class="text-xs text-gray-400 mt-1">
					Remaining: {result.remaining}
				</div>
			{/if}
		</div>
	{/if}
</div>
