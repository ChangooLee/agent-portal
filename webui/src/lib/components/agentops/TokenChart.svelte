<script lang="ts">
	import { Bar } from 'svelte-chartjs';
	import {
		Chart,
		Title,
		Tooltip,
		Legend,
		BarElement,
		LinearScale,
		CategoryScale
	} from 'chart.js';
	import type { TokenDataPoint } from '$lib/agentops/types';

	// Register Chart.js components
	Chart.register(Title, Tooltip, Legend, BarElement, LinearScale, CategoryScale);

	export let tokenData: TokenDataPoint[];
	export let title: string = 'Token Usage';
	export let interval: 'hour' | 'day' | 'week' = 'day';

	function formatDate(timestamp: string, interval: 'hour' | 'day' | 'week'): string {
		const date = new Date(timestamp);
		switch (interval) {
			case 'hour':
				return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
			case 'day':
				return date.toLocaleDateString([], { month: 'short', day: 'numeric' });
			case 'week':
				return `Week ${Math.ceil(date.getDate() / 7)}`;
			default:
				return date.toLocaleDateString();
		}
	}

	$: chartData = {
		labels: tokenData.map((d) => formatDate(d.timestamp, interval)),
		datasets: [
			{
				label: 'Prompt Tokens',
				data: tokenData.map((d) => d.prompt_tokens),
				backgroundColor: 'rgba(59, 130, 246, 0.7)',
				borderColor: 'rgba(59, 130, 246, 1)',
				borderWidth: 1
			},
			{
				label: 'Completion Tokens',
				data: tokenData.map((d) => d.completion_tokens),
				backgroundColor: 'rgba(16, 185, 129, 0.7)',
				borderColor: 'rgba(16, 185, 129, 1)',
				borderWidth: 1
			},
			{
				label: 'Cache Hits',
				data: tokenData.map((d) => d.cache_hits),
				backgroundColor: 'rgba(139, 92, 246, 0.7)',
				borderColor: 'rgba(139, 92, 246, 1)',
				borderWidth: 1
			}
		]
	};

	$: chartOptions = {
		responsive: true,
		maintainAspectRatio: false,
		plugins: {
			legend: {
				display: true,
				position: 'top' as const,
				labels: {
					color: '#6B7280',
					font: {
						size: 12
					}
				}
			},
			tooltip: {
				mode: 'index' as const,
				intersect: false,
				backgroundColor: 'rgba(0, 0, 0, 0.8)',
				titleColor: '#fff',
				bodyColor: '#fff',
				borderColor: '#0072CE',
				borderWidth: 1,
				padding: 12,
				displayColors: true,
				callbacks: {
					label: function (context: any) {
						let label = context.dataset.label || '';
						if (label) {
							label += ': ';
						}
						if (context.parsed.y !== null) {
							label += context.parsed.y.toLocaleString() + ' tokens';
						}
						return label;
					}
				}
			},
			title: {
				display: true,
				text: title,
				color: '#111827',
				font: {
					size: 16,
					weight: 'bold' as const
				}
			}
		},
		scales: {
			x: {
				stacked: true,
				grid: {
					display: false
				},
				ticks: {
					color: '#6B7280',
					font: {
						size: 11
					}
				}
			},
			y: {
				stacked: true,
				beginAtZero: true,
				grid: {
					color: 'rgba(0, 0, 0, 0.05)'
				},
				ticks: {
					color: '#6B7280',
					font: {
						size: 11
					},
					callback: function (value: any) {
						return value.toLocaleString();
					}
				}
			}
		}
	};

	// Calculate cache hit rate
	$: cacheHitRate =
		tokenData.length > 0
			? (
					(tokenData.reduce((sum, d) => sum + d.cache_hits, 0) /
						tokenData.reduce((sum, d) => sum + d.prompt_tokens + d.completion_tokens, 0)) *
					100
				).toFixed(1)
			: '0.0';
</script>

<div class="space-y-4">
	<!-- Cache Hit Rate Badge -->
	<div class="flex items-center justify-between">
		<div class="flex items-center gap-2">
			<span class="text-sm text-gray-600 dark:text-gray-400">Cache Hit Rate:</span>
			<span
				class="inline-flex items-center px-3 py-1 rounded-full text-sm font-semibold bg-purple-100 text-purple-800 dark:bg-purple-900/30 dark:text-purple-400"
			>
				{cacheHitRate}%
			</span>
		</div>
	</div>

	<!-- Chart -->
	<div class="h-80 w-full">
		{#if tokenData.length > 0}
			<Bar data={chartData} options={chartOptions} />
		{:else}
			<div class="flex items-center justify-center h-full text-gray-500 dark:text-gray-400">
				<p>No token usage data available</p>
			</div>
		{/if}
	</div>
</div>

