<script lang="ts">
	import { slideStudioStore } from '../stores/slideStudioStore';
	
	let store = slideStudioStore.get();
	
	const unsubscribe = slideStudioStore.subscribe((s) => {
		store = s;
	});
	
	$: completedCount = store.slides.filter(
		s => s.stage === 'FINAL' || s.stage === 'FINAL_WITH_WARNINGS'
	).length;
	$: totalCount = store.slides.length;
	$: progress = totalCount > 0 ? Math.round((completedCount / totalCount) * 100) : 0;
	
	export let onGenerate: () => void;
	export let onStop: () => void;
	export let onExport: () => void;
	export let onSave: () => void;
	export let onRestore: () => void;
</script>

<div class="bg-gray-900/95 backdrop-blur-sm border-b border-gray-800 shrink-0">
	<div class="flex items-center justify-between px-6 py-3">
		<!-- Left: Project name and status -->
		<div class="flex items-center gap-4">
			<h2 class="text-lg font-semibold text-white">
				{store.deck_id ? store.deck_id.substring(0, 8) : 'New Deck'}
			</h2>
			{#if store.globalStatus === 'generating'}
				<span class="px-2 py-1 text-xs font-medium rounded-full bg-blue-500/20 text-blue-300 border border-blue-500/30">
					Generating
				</span>
			{:else if store.globalStatus === 'exporting'}
				<span class="px-2 py-1 text-xs font-medium rounded-full bg-yellow-500/20 text-yellow-300 border border-yellow-500/30">
					Exporting
				</span>
			{:else if store.globalStatus === 'ready'}
				<span class="px-2 py-1 text-xs font-medium rounded-full bg-green-500/20 text-green-300 border border-green-500/30">
					Ready
				</span>
			{/if}
		</div>
		
		<!-- Center: Progress -->
		<div class="flex items-center gap-3">
			<span class="text-sm text-gray-400">
				{completedCount} / {totalCount}
			</span>
			{#if store.globalStatus === 'generating'}
				<div class="w-32 h-2 bg-gray-700 rounded-full overflow-hidden">
					<div
						class="h-full bg-blue-500 transition-all duration-300"
						style="width: {progress}%"
					></div>
				</div>
			{/if}
		</div>
		
		<!-- Right: Actions -->
		<div class="flex items-center gap-2">
			<button
				on:click={onGenerate}
				class="px-4 py-2 text-sm font-medium rounded-lg bg-purple-600 hover:bg-purple-700 text-white transition-colors"
			>
				Generate
			</button>
			{#if store.globalStatus === 'generating'}
				<button
					on:click={onStop}
					class="px-4 py-2 text-sm font-medium rounded-lg bg-red-600 hover:bg-red-700 text-white transition-colors"
				>
					Stop
				</button>
			{/if}
			{#if store.globalStatus === 'ready'}
				<button
					on:click={onExport}
					class="px-4 py-2 text-sm font-medium rounded-lg bg-gray-700 hover:bg-gray-600 text-white transition-colors"
				>
					Export ▼
				</button>
			{/if}
			<button
				on:click={onSave}
				class="px-4 py-2 text-sm font-medium rounded-lg bg-gray-700 hover:bg-gray-600 text-white transition-colors"
			>
				Save Point
			</button>
			<button
				on:click={onRestore}
				class="px-4 py-2 text-sm font-medium rounded-lg bg-gray-700 hover:bg-gray-600 text-white transition-colors"
			>
				Restore ▼
			</button>
		</div>
	</div>
</div>
