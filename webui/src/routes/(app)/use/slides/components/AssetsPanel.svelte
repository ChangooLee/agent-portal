<script lang="ts">
	import { slideStudioStore } from '../stores/slideStudioStore';
	
	let store = slideStudioStore.get();
	let searchQuery = '';
	let assetType: 'all' | 'icon' | 'photo' | 'illustration' | 'bg' = 'all';
	let assets: Array<{
		id: string;
		type: string;
		path: string;
	}> = [];
	let loading = false;
	
	const unsubscribe = slideStudioStore.subscribe((s) => {
		store = s;
	});
	
	async function loadAssets() {
		loading = true;
		try {
			// TODO: Implement API endpoint for assets
			// For now, show placeholder
			assets = [];
		} catch (error) {
			console.error('Failed to load assets:', error);
		} finally {
			loading = false;
		}
	}
	
	$: if (assetType) {
		loadAssets();
	}
	
	function handleAssetClick(asset: any) {
		// TODO: Implement asset selection and insertion
		console.log('Asset selected:', asset);
	}
	
	function handleReplaceImage() {
		// TODO: Implement image replacement
		console.log('Replace image');
	}
</script>

<div class="space-y-4">
	<h3 class="text-sm font-semibold text-white mb-4">Assets</h3>
	
	<!-- Search and filter -->
	<div class="space-y-2">
		<input
			type="text"
			bind:value={searchQuery}
			placeholder="Search assets..."
			class="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
		/>
		<select
			bind:value={assetType}
			class="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-lg text-white text-sm focus:outline-none focus:ring-2 focus:ring-purple-500"
		>
			<option value="all">All Types</option>
			<option value="icon">Icons</option>
			<option value="photo">Photos</option>
			<option value="illustration">Illustrations</option>
			<option value="bg">Backgrounds</option>
		</select>
	</div>
	
	<!-- Asset grid -->
	{#if loading}
		<div class="text-center text-gray-500 py-8">Loading...</div>
	{:else if assets.length > 0}
		<div class="grid grid-cols-2 gap-2">
			{#each assets as asset}
				<button
					on:click={() => handleAssetClick(asset)}
					class="aspect-square bg-gray-700 rounded-lg hover:bg-gray-600 transition-colors flex items-center justify-center overflow-hidden"
				>
					{#if asset.path}
						<img src={asset.path} alt={asset.id} class="w-full h-full object-cover" />
					{:else}
						<div class="text-gray-500 text-xs">{asset.type}</div>
					{/if}
				</button>
			{/each}
		</div>
	{:else}
		<div class="text-center text-gray-500 py-8">
			<div class="text-sm">No assets found</div>
			<div class="text-xs mt-2">Asset library will be available in production</div>
		</div>
	{/if}
	
	<!-- Replace image button -->
	{#if store.selectedElementId}
		<button
			on:click={handleReplaceImage}
			class="w-full px-4 py-2 rounded-lg bg-purple-600 hover:bg-purple-700 text-white text-sm font-medium transition-colors"
		>
			Replace Image
		</button>
	{/if}
</div>
