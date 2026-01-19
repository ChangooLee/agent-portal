<script lang="ts">
	import { slideStudioStore } from '../stores/slideStudioStore';
	import ProgressPanel from './ProgressPanel.svelte';
	import IssuesPanel from './IssuesPanel.svelte';
	import FixLayoutPanel from './FixLayoutPanel.svelte';
	import AssetsPanel from './AssetsPanel.svelte';
	import PropertiesPanel from './PropertiesPanel.svelte';
	import FactCheckPanel from './FactCheckPanel.svelte';
	import AccordionItem from './AccordionItem.svelte';
	
	let store = slideStudioStore.get();
	
	const unsubscribe = slideStudioStore.subscribe((s) => {
		store = s;
	});
</script>

<div class="h-full flex flex-col bg-gray-900 border-l border-gray-800 overflow-y-auto">
	<div class="p-4 space-y-0">
		<AccordionItem title="Progress" defaultOpen={true}>
			<ProgressPanel />
		</AccordionItem>
		
		<AccordionItem title="Issues">
			<IssuesPanel />
		</AccordionItem>
		
		<AccordionItem title="Fix Layout">
			<FixLayoutPanel />
		</AccordionItem>
		
		<AccordionItem title="Rewrite">
			<div class="text-gray-400 text-sm py-4">Rewrite panel - Coming in Step 3</div>
		</AccordionItem>
		
		<AccordionItem title="Properties">
			<PropertiesPanel />
		</AccordionItem>
		
		<AccordionItem title="Assets">
			<AssetsPanel />
		</AccordionItem>
		
		<AccordionItem title="Fact Check">
			<FactCheckPanel />
		</AccordionItem>
		
		<AccordionItem title="Generation Log">
			<div class="space-y-2">
				{#if store.selectedSlideIds[0]}
					{#each (store.eventLog.bySlideId[store.selectedSlideIds[0]] || []) as log}
						<div class="text-xs text-gray-400 border-l-2 border-gray-700 pl-3 py-1">
							<div class="text-gray-500 mb-1">
								{new Date(String(log.timestamp)).toLocaleTimeString()}
							</div>
							<div class="text-gray-300">
								<span class="font-medium text-purple-400">{String(log.stage)}</span>
								{#if log.message}
									<span class="ml-2">- {String(log.message)}</span>
								{/if}
							</div>
						</div>
					{/each}
				{:else}
					<div class="text-sm text-gray-500 py-4">Select a slide to view progress</div>
				{/if}
			</div>
		</AccordionItem>
	</div>
</div>
