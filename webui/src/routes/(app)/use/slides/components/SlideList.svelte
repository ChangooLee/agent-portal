<script lang="ts">
	import { slideStudioStore } from '../stores/slideStudioStore';
	
	let store = slideStudioStore.get();
	
	const unsubscribe = slideStudioStore.subscribe((s) => {
		store = s;
	});
	
	export let onSlideSelect: (slideId: string, multi: boolean) => void;
	
	function handleClick(slideId: string, event: MouseEvent) {
		const multi = event.shiftKey || event.metaKey || event.ctrlKey;
		onSlideSelect(slideId, multi);
	}
	
	function getStageBadgeClass(stage: string): string {
		switch (stage) {
			case 'PLANNED':
				return 'bg-gray-500/20 text-gray-300 border-gray-500/30';
			case 'DRAFTING':
				return 'bg-blue-500/20 text-blue-300 border-blue-500/30';
			case 'LAYOUTING':
				return 'bg-purple-500/20 text-purple-300 border-purple-500/30';
			case 'VERIFYING':
				return 'bg-yellow-500/20 text-yellow-300 border-yellow-500/30';
			case 'REFLECTING':
				return 'bg-orange-500/20 text-orange-300 border-orange-500/30';
			case 'PREVIEW_RENDERING':
				return 'bg-indigo-500/20 text-indigo-300 border-indigo-500/30';
			case 'FINAL':
				return 'bg-green-500/20 text-green-300 border-green-500/30';
			case 'FINAL_WITH_WARNINGS':
				return 'bg-yellow-500/20 text-yellow-300 border-yellow-500/30';
			case 'ERROR':
				return 'bg-red-500/20 text-red-300 border-red-500/30';
			case 'STOPPED':
				return 'bg-gray-500/20 text-gray-300 border-gray-500/30';
			default:
				return 'bg-gray-500/20 text-gray-300 border-gray-500/30';
		}
	}
</script>

<div class="h-full overflow-y-auto bg-gray-900 border-r border-gray-800">
	<div class="p-4 space-y-3">
		{#each store.slides as slide (slide.slide_id)}
			<button
				on:click={(e) => handleClick(slide.slide_id, e)}
				class="w-full p-3 rounded-lg bg-gray-800/50 hover:bg-gray-800 border transition-colors text-left
					{store.selectedSlideIds.includes(slide.slide_id) ? 'border-purple-500 bg-purple-500/10' : 'border-gray-700'}"
			>
				<!-- Thumbnail -->
				<div class="w-full aspect-video bg-gray-700 rounded mb-2 flex items-center justify-center overflow-hidden">
					{#if slide.thumbnailUrl}
						{#if slide.thumbnailUrl.startsWith('data:text/html')}
							<!-- HTML preview (iframe) -->
							{@html atob(slide.thumbnailUrl.split(',')[1]).substring(0, 100)}
							<div class="text-gray-500 text-xs">HTML Preview</div>
						{:else}
							<!-- Image thumbnail -->
							<img src={slide.thumbnailUrl} alt={slide.title} class="w-full h-full object-cover rounded" />
						{/if}
					{:else}
						<div class="text-gray-500 text-xs">No preview</div>
					{/if}
				</div>
				
				<!-- Slide info -->
				<div class="flex items-start justify-between gap-2">
					<div class="flex-1 min-w-0">
						<div class="flex items-center gap-2 mb-1">
							<span class="text-xs font-medium text-gray-400">
								#{slide.slide_id.split('_')[1] || '?'}
							</span>
							<span class="text-xs px-2 py-0.5 rounded bg-gray-700 text-gray-300">
								{slide.type}
							</span>
						</div>
						<h3 class="text-sm font-medium text-white truncate">
							{slide.title || 'Untitled'}
						</h3>
					</div>
				</div>
				
				<!-- Stage badge and score -->
				<div class="flex items-center justify-between mt-2">
					<span class="text-xs px-2 py-0.5 rounded border {getStageBadgeClass(slide.stage)}">
						{slide.stage}
					</span>
					{#if slide.score !== null}
						<span class="text-xs text-gray-400">
							{Math.round(slide.score)}
						</span>
					{/if}
					{#if slide.issuesCount > 0}
						<span class="text-xs text-red-400">
							! {slide.issuesCount}
						</span>
					{/if}
				</div>
			</button>
		{/each}
	</div>
</div>
