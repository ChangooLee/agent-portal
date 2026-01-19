<script lang="ts">
	import { slideStudioStore } from '../stores/slideStudioStore';
	
	let store = slideStudioStore.get();
	
	const unsubscribe = slideStudioStore.subscribe((s) => {
		store = s;
	});
	
	$: selectedSlideId = store.selectedSlideIds[0] || null;
	
	let factCheckResults: {
		claims: Array<{claim: string; source: string; verified?: boolean}>;
		verified: Array<any>;
		unverified: Array<any>;
	} | null = null;
	let loading = false;
	
	async function runFactCheck() {
		if (!store.deck_id) return;
		
		loading = true;
		try {
			const response = await fetch(`/api/slides/${store.deck_id}/fact-check`, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				},
				body: JSON.stringify({
					documents: []  // TODO: Add document upload
				})
			});
			
			if (!response.ok) {
				throw new Error('Fact check failed');
			}
			
			factCheckResults = await response.json();
		} catch (error) {
			console.error('Fact check error:', error);
			alert('Failed to run fact check: ' + error);
		} finally {
			loading = false;
		}
	}
</script>

<div class="space-y-4">
	<h3 class="text-sm font-semibold text-white mb-4">Fact Check</h3>
	
	<button
		on:click={runFactCheck}
		disabled={loading || !store.deck_id}
		class="w-full px-4 py-2 rounded-lg bg-purple-600 hover:bg-purple-700 text-white font-medium transition-colors disabled:opacity-50"
	>
		{loading ? 'Checking...' : 'Run Fact Check'}
	</button>
	
	{#if factCheckResults}
		<div class="space-y-3">
			<!-- Verified claims -->
			{#if factCheckResults.verified.length > 0}
				<div>
					<h4 class="text-xs font-medium text-green-400 mb-2">
						Verified ({factCheckResults.verified.length})
					</h4>
					<div class="space-y-1">
						{#each factCheckResults.verified as claim}
							<div class="p-2 rounded bg-green-500/10 border border-green-500/30 text-sm text-gray-300">
								{claim.claim}
							</div>
						{/each}
					</div>
				</div>
			{/if}
			
			<!-- Unverified claims -->
			{#if factCheckResults.unverified.length > 0}
				<div>
					<h4 class="text-xs font-medium text-yellow-400 mb-2">
						Unverified ({factCheckResults.unverified.length})
					</h4>
					<div class="space-y-1">
						{#each factCheckResults.unverified as claim}
							<div class="p-2 rounded bg-yellow-500/10 border border-yellow-500/30 text-sm text-gray-300">
								{claim.claim}
								<div class="text-xs text-yellow-400 mt-1">Unverified</div>
							</div>
						{/each}
					</div>
				</div>
			{/if}
		</div>
	{:else}
		<div class="text-sm text-gray-500 text-center py-8">
			Click "Run Fact Check" to verify claims
		</div>
	{/if}
</div>
