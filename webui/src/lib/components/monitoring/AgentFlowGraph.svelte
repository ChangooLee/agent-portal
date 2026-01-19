<script lang="ts">
	import { writable } from 'svelte/store';
	import { SvelteFlow, Controls, Background, MiniMap } from '@xyflow/svelte';
	import '@xyflow/svelte/dist/style.css';
	import type { AgentFlowGraph } from '$lib/monitoring/types';

	export let flowGraph: AgentFlowGraph;

	// 단계별 색상 매핑
	const stageColors: Record<string, { bg: string; border: string }> = {
		'Client Request': { bg: 'linear-gradient(135deg, #3B82F6 0%, #1D4ED8 100%)', border: '#1D4ED8' },
		'Input Guardrail': { bg: 'linear-gradient(135deg, #F97316 0%, #EA580C 100%)', border: '#EA580C' },
		'LiteLLM Proxy': { bg: 'linear-gradient(135deg, #10B981 0%, #059669 100%)', border: '#059669' },
		'LLM Provider': { bg: 'linear-gradient(135deg, #8B5CF6 0%, #7C3AED 100%)', border: '#7C3AED' },
		'Langflow Agent': { bg: 'linear-gradient(135deg, #F59E0B 0%, #D97706 100%)', border: '#D97706' },
		'Flowise Agent': { bg: 'linear-gradient(135deg, #F59E0B 0%, #D97706 100%)', border: '#D97706' },
		'AutoGen Agent': { bg: 'linear-gradient(135deg, #F59E0B 0%, #D97706 100%)', border: '#D97706' },
		'TextToSQL Agent': { bg: 'linear-gradient(135deg, #06B6D4 0%, #0891B2 100%)', border: '#0891B2' },
		'MCP Tools': { bg: 'linear-gradient(135deg, #EC4899 0%, #DB2777 100%)', border: '#DB2777' },
		'Output Guardrail': { bg: 'linear-gradient(135deg, #F97316 0%, #EA580C 100%)', border: '#EA580C' },
	};

	function formatLatency(ms: number): string {
		if (ms < 1000) return `${ms.toFixed(0)}ms`;
		return `${(ms / 1000).toFixed(2)}s`;
	}

	function formatTokens(tokens: number): string {
		if (tokens >= 1000) return `${(tokens / 1000).toFixed(1)}K`;
		return tokens.toString();
	}

	// Convert AgentFlowGraph to XYFlow format
	$: nodes = writable(
		flowGraph.nodes.map((node) => {
			const stageName = node.data.stage_name || node.label;
			const colors = stageColors[stageName] || { bg: '#f3f4f6', border: '#d1d5db' };
			const isGuardrail = node.data.is_guardrail || stageName.includes('Guardrail');
			
			// 노드 라벨 구성
			const labelParts = [
				isGuardrail ? `Guardrail: ${stageName}` : stageName,
				`${node.data.call_count} calls`,
				`${formatLatency(node.data.avg_latency_ms || 0)}`,
			];
			
			// 토큰이 있는 경우에만 표시
			if (node.data.total_tokens > 0) {
				labelParts.push(`${formatTokens(node.data.total_tokens)} tokens`);
			}
			
			// 비용이 있는 경우에만 표시
			if (node.data.total_cost > 0) {
				labelParts.push(`$${node.data.total_cost.toFixed(6)}`);
			}
			
			// 에러/차단이 있는 경우 표시
			if (node.data.error_count > 0) {
				labelParts.push(`${node.data.error_count} blocked`);
			}

			return {
				id: node.id,
				type: 'default',
				data: {
					label: labelParts.join('\n')
				},
				position: node.position,
				style: {
					background: colors.bg,
					color: '#1f2937',
					border: `2px solid ${colors.border}`,
					borderRadius: isGuardrail ? '16px' : '12px',
					padding: '14px',
					fontSize: '10px',
					fontWeight: 'bold',
					textAlign: 'center',
					minWidth: '150px',
					boxShadow: isGuardrail 
						? '0 4px 12px rgba(249, 115, 22, 0.3)' 
						: '0 4px 6px rgba(0, 0, 0, 0.15)',
					whiteSpace: 'pre-line',
					lineHeight: '1.4',
					textShadow: '0 1px 2px rgba(255, 255, 255, 0.8)'
				}
			};
		})
	);

	$: edges = writable(
		flowGraph.edges.map((edge) => {
			const isBlocked = edge.data?.blocked;
			return {
				id: edge.id,
				source: edge.source,
				target: edge.target,
				label: edge.data?.label || '',
				animated: !isBlocked,
				style: { 
					stroke: isBlocked ? '#EF4444' : '#06b6d4', 
					strokeWidth: 2,
					strokeDasharray: isBlocked ? '5,5' : 'none'
				},
				labelStyle: { fontSize: '10px', fontWeight: 'bold', fill: '#cbd5e1' }
			};
		})
	);

	const fitViewOptions = {
		padding: 0.3
	};
</script>

<div class="h-[500px] w-full rounded-lg border border-slate-700/50 overflow-hidden">
	{#if flowGraph.nodes.length > 0}
		<SvelteFlow {nodes} {edges} {fitViewOptions} class="bg-slate-900">
			<Controls />
			<Background />
			<MiniMap nodeColor={() => '#06b6d4'} />
		</SvelteFlow>
	{:else}
		<div class="flex items-center justify-center h-full text-slate-400">
			<div class="text-center">
				<svg class="w-16 h-16 mx-auto mb-4 text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
				</svg>
				<p class="font-medium text-white">No flow data available</p>
				<p class="text-sm mt-1 text-slate-400">LLM 또는 Agent 호출이 발생하면 흐름이 표시됩니다.</p>
			</div>
		</div>
	{/if}
</div>

<!-- Legend -->
<div class="flex flex-wrap items-center gap-3 mt-4 text-xs">
	<div class="flex items-center gap-1.5">
		<div class="w-3 h-3 rounded" style="background: linear-gradient(135deg, #3B82F6 0%, #1D4ED8 100%)"></div>
		<span class="text-slate-300">Client</span>
	</div>
	<div class="flex items-center gap-1.5">
		<div class="w-3 h-3 rounded-full" style="background: linear-gradient(135deg, #F97316 0%, #EA580C 100%)"></div>
		<span class="text-slate-300">Guardrail</span>
	</div>
	<div class="flex items-center gap-1.5">
		<div class="w-3 h-3 rounded" style="background: linear-gradient(135deg, #10B981 0%, #059669 100%)"></div>
		<span class="text-slate-300">LiteLLM</span>
	</div>
	<div class="flex items-center gap-1.5">
		<div class="w-3 h-3 rounded" style="background: linear-gradient(135deg, #8B5CF6 0%, #7C3AED 100%)"></div>
		<span class="text-slate-300">LLM Provider</span>
	</div>
	<div class="flex items-center gap-1.5">
		<div class="w-3 h-3 rounded" style="background: linear-gradient(135deg, #F59E0B 0%, #D97706 100%)"></div>
		<span class="text-slate-300">Agent</span>
	</div>
	<div class="flex items-center gap-1.5">
		<div class="w-3 h-3 rounded" style="background: linear-gradient(135deg, #EC4899 0%, #DB2777 100%)"></div>
		<span class="text-slate-300">MCP Tools</span>
	</div>
</div>
