<script lang="ts">
	import { slideStudioStore } from '../stores/slideStudioStore';
	
	let store = slideStudioStore.get();
	
	const unsubscribe = slideStudioStore.subscribe((s) => {
		store = s;
	});
	
	$: selectedSlideId = store.selectedSlideIds[0] || null;
	$: selectedSlide = selectedSlideId ? store.slides.find(s => s.slide_id === selectedSlideId) : null;
	
	// For Step 3, we'll fetch issues from API
	// For now, show placeholder
	let issues: Array<{
		severity: string;
		slot: string;
		type: string;
		message: string;
		slot_id?: string;
	}> = [];
	
	async function loadIssues() {
		if (!store.deck_id || !selectedSlideId) return;
		
		try {
			const response = await fetch(`/api/slides/${store.deck_id}/quality`);
			if (response.ok) {
				const data = await response.json();
				const slideQuality = data.slides_quality[selectedSlideId];
				if (slideQuality) {
					// Issues are stored in slide IR, but for now we show metrics
					issues = []; // Will be populated from slide state in Step 3
				}
			}
		} catch (error) {
			console.error('Failed to load issues:', error);
		}
	}
	
	$: if (selectedSlideId) {
		loadIssues();
	}
	
	function getSeverityColor(severity: string): string {
		switch (severity) {
			case 'error':
				return 'text-red-400 border-red-500/30 bg-red-500/10';
			case 'warning':
				return 'text-yellow-400 border-yellow-500/30 bg-yellow-500/10';
			default:
				return 'text-gray-400 border-gray-500/30 bg-gray-500/10';
		}
	}
	
	function handleQuickAction(action: string) {
		// TODO: Implement quick actions in Step 3
		console.log('Quick action:', action);
	}
</script>

<div class="space-y-4">
	<h3 class="text-sm font-semibold text-white mb-4">Issues</h3>
	
	{#if selectedSlide}
		<div class="space-y-2">
			{#if issues.length > 0}
				{#each issues as issue}
					<div class="p-3 rounded-lg border {getSeverityColor(issue.severity)}">
						<div class="flex items-start justify-between gap-2">
							<div class="flex-1">
								<div class="text-xs font-medium mb-1">
									{issue.severity.toUpperCase()} - {issue.type}
								</div>
								<div class="text-sm text-gray-300">
									{issue.message}
								</div>
								{#if issue.slot_id}
									<div class="text-xs text-gray-500 mt-1">
										Slot: {issue.slot_id}
									</div>
								{/if}
							</div>
						</div>
						
						<!-- Quick actions -->
						<div class="flex gap-2 mt-2">
							{#if issue.type === 'overflow'}
								<button
									on:click={() => handleQuickAction('shorten_text')}
									class="text-xs px-2 py-1 rounded bg-gray-700 hover:bg-gray-600 text-white"
								>
									Shorten text
								</button>
							{/if}
							{#if issue.type === 'overlap'}
								<button
									on:click={() => handleQuickAction('adjust_layout')}
									class="text-xs px-2 py-1 rounded bg-gray-700 hover:bg-gray-600 text-white"
								>
									Adjust layout
								</button>
							{/if}
							{#if issue.type === 'font_too_small'}
								<button
									on:click={() => handleQuickAction('increase_font')}
									class="text-xs px-2 py-1 rounded bg-gray-700 hover:bg-gray-600 text-white"
								>
									Increase font
								</button>
							{/if}
						</div>
					</div>
				{/each}
			{:else}
				<div class="text-sm text-gray-500 text-center py-8">
					No issues found
				</div>
			{/if}
		</div>
	{:else}
		<div class="text-sm text-gray-500 text-center py-8">
			Select a slide to view issues
		</div>
	{/if}
</div>
