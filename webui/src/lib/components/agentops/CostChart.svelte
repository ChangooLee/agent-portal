<script lang="ts">
	import { Line } from 'svelte-chartjs';
	import {
		Chart,
		Title,
		Tooltip,
		Legend,
		LineElement,
		LinearScale,
		PointElement,
		CategoryScale,
		Filler
	} from 'chart.js';
	import type { CostDataPoint } from '$lib/agentops/types';

	// Register Chart.js components
	Chart.register(Title, Tooltip, Legend, LineElement, LinearScale, PointElement, CategoryScale, Filler);

	export let costData: CostDataPoint[];
	export let title: string = 'Cost Trend';
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
		labels: costData.map((d) => formatDate(d.timestamp, interval)),
		datasets: [
			{
				label: 'Cost ($)',
				data: costData.map((d) => d.cost),
				borderColor: '#0072CE',
				backgroundColor: 'rgba(0, 114, 206, 0.1)',
				tension: 0.4,
				fill: true,
				pointRadius: 4,
				pointHoverRadius: 6,
				pointBackgroundColor: '#0072CE',
				pointBorderColor: '#fff',
				pointBorderWidth: 2
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
							label += '$' + context.parsed.y.toFixed(4);
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
						return '$' + value.toFixed(2);
					}
				}
			}
		},
		interaction: {
			mode: 'nearest' as const,
			axis: 'x' as const,
			intersect: false
		}
	};
</script>

<div class="h-80 w-full">
	{#if costData.length > 0}
		<Line data={chartData} options={chartOptions} />
	{:else}
		<div class="flex items-center justify-center h-full text-gray-500 dark:text-gray-400">
			<p>No cost data available</p>
		</div>
	{/if}
</div>

