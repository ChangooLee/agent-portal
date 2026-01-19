<script lang="ts">
	import { slideStudioStore } from '../stores/slideStudioStore';
	
	let store = slideStudioStore.get();
	
	const unsubscribe = slideStudioStore.subscribe((s) => {
		store = s;
	});
	
	$: selectedSlideId = store.selectedSlideIds[0] || null;
	$: logs = selectedSlideId ? store.eventLog.bySlideId[selectedSlideId] || [] : [];
</script>

<div class="space-y-4">
	<h3 class="text-sm font-semibold text-white mb-4">Generation Log</h3>
	
	{#if selectedSlideId}
		<div class="space-y-2">
			{#each logs as log}
				<div class="text-xs text-gray-400 border-l-2 border-gray-700 pl-3 py-1">
					<div class="text-gray-500 mb-1">
						{new Date(log.timestamp).toLocaleTimeString()}
					</div>
					<div class="text-gray-300">
						<span class="font-medium text-purple-400">{log.stage}</span>
						{#if log.message}
							<span class="ml-2">- {log.message}</span>
						{/if}
					</div>
				</div>
			{/each}
		</div>
	{:else}
		<div class="text-sm text-gray-500">Select a slide to view progress</div>
	{/if}
</div>
