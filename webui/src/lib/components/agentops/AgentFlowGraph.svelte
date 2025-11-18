<script lang="ts">
	import { writable } from 'svelte/store';
	import { SvelteFlow, Controls, Background, MiniMap } from '@xyflow/svelte';
	import '@xyflow/svelte/dist/style.css';
	import type { AgentFlowGraph } from '$lib/agentops/types';

	export let flowGraph: AgentFlowGraph;

	// Convert AgentFlowGraph to XYFlow format
	$: nodes = writable(
		flowGraph.nodes.map((node) => ({
			id: node.id,
			type: node.type === 'agent' ? 'default' : node.type === 'tool' ? 'input' : 'output',
			data: {
				label: `${node.label}\n${node.data.total_calls} calls\n$${node.data.total_cost.toFixed(4)}\n${node.data.avg_duration.toFixed(0)}ms`
			},
			position: node.position,
			style: getNodeStyle(node.type)
		}))
	);

	$: edges = writable(
		flowGraph.edges.map((edge) => ({
			id: edge.id,
			source: edge.source,
			target: edge.target,
			label: edge.label || `${edge.data.message_count} msgs`,
			animated: edge.animated || true,
			style: { stroke: '#0072CE', strokeWidth: 2 }
		}))
	);

	function getNodeStyle(type: string) {
		switch (type) {
			case 'agent':
				return {
					background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
					color: 'white',
					border: '2px solid #5a67d8',
					borderRadius: '12px',
					padding: '16px',
					fontSize: '12px',
					fontWeight: 'bold',
					textAlign: 'center',
					minWidth: '150px',
					boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)'
				};
			case 'tool':
				return {
					background: 'linear-gradient(135deg, #10b981 0%, #059669 100%)',
					color: 'white',
					border: '2px solid #059669',
					borderRadius: '12px',
					padding: '16px',
					fontSize: '12px',
					fontWeight: 'bold',
					textAlign: 'center',
					minWidth: '150px',
					boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)'
				};
			case 'llm':
				return {
					background: 'linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%)',
					color: 'white',
					border: '2px solid #1d4ed8',
					borderRadius: '12px',
					padding: '16px',
					fontSize: '12px',
					fontWeight: 'bold',
					textAlign: 'center',
					minWidth: '150px',
					boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)'
				};
			default:
				return {
					background: '#f3f4f6',
					color: '#111827',
					border: '2px solid #d1d5db',
					borderRadius: '12px',
					padding: '16px',
					fontSize: '12px',
					fontWeight: 'bold',
					textAlign: 'center',
					minWidth: '150px',
					boxShadow: '0 4px 6px rgba(0, 0, 0, 0.1)'
				};
		}
	}

	const fitViewOptions = {
		padding: 0.2
	};
</script>

<div class="h-[600px] w-full rounded-lg border border-gray-200 dark:border-gray-700 overflow-hidden">
	{#if flowGraph.nodes.length > 0}
		<SvelteFlow {nodes} {edges} {fitViewOptions} class="bg-gray-50 dark:bg-gray-900">
			<Controls />
			<Background />
			<MiniMap nodeColor={(node) => {
				if (node.type === 'default') return '#667eea';
				if (node.type === 'input') return '#10b981';
				if (node.type === 'output') return '#3b82f6';
				return '#d1d5db';
			}} />
		</SvelteFlow>
	{:else}
		<div class="flex items-center justify-center h-full text-gray-500 dark:text-gray-400">
			<p>No agent flow data available</p>
		</div>
	{/if}
</div>

<!-- Legend -->
<div class="flex items-center gap-6 mt-4 text-sm">
	<div class="flex items-center gap-2">
		<div class="w-4 h-4 rounded" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%)"></div>
		<span class="text-gray-700 dark:text-gray-300">Agent</span>
	</div>
	<div class="flex items-center gap-2">
		<div class="w-4 h-4 rounded" style="background: linear-gradient(135deg, #10b981 0%, #059669 100%)"></div>
		<span class="text-gray-700 dark:text-gray-300">Tool</span>
	</div>
	<div class="flex items-center gap-2">
		<div class="w-4 h-4 rounded" style="background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%)"></div>
		<span class="text-gray-700 dark:text-gray-300">LLM</span>
	</div>
</div>

