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
	import type { PerformanceDataPoint } from '$lib/agentops/types';

	// Register Chart.js components
	Chart.register(Title, Tooltip, Legend, BarElement, LinearScale, CategoryScale);

	export let performanceData: PerformanceDataPoint[];
	export let title: string = 'Latency Distribution';

	// Calculate percentiles
	function calculatePercentile(data: number[], percentile: number): number {
		if (data.length === 0) return 0;
		const sorted = [...data].sort((a, b) => a - b);
		const index = Math.ceil((percentile / 100) * sorted.length) - 1;
		return sorted[index];
	}

	$: durations = performanceData.map((d) => d.duration);
	$: p50 = calculatePercentile(durations, 50);
	$: p95 = calculatePercentile(durations, 95);
	$: p99 = calculatePercentile(durations, 99);
	$: avgDuration = durations.length > 0 ? durations.reduce((a, b) => a + b, 0) / durations.length : 0;

	// Create histogram bins
	function createHistogram(data: number[], binCount: number = 20) {
		if (data.length === 0) return { labels: [], counts: [] };

		const min = Math.min(...data);
		const max = Math.max(...data);
		const binSize = (max - min) / binCount;

		const bins = Array(binCount).fill(0);
		const labels: string[] = [];

		for (let i = 0; i < binCount; i++) {
			const binStart = min + i * binSize;
			const binEnd = binStart + binSize;
			labels.push(`${binStart.toFixed(0)}-${binEnd.toFixed(0)}ms`);
		}

		data.forEach((value) => {
			const binIndex = Math.min(Math.floor((value - min) / binSize), binCount - 1);
			bins[binIndex]++;
		});

		return { labels, counts: bins };
	}

	$: histogram = createHistogram(durations);

	$: chartData = {
		labels: histogram.labels,
		datasets: [
			{
				label: 'Request Count',
				data: histogram.counts,
				backgroundColor: 'rgba(0, 114, 206, 0.7)',
				borderColor: 'rgba(0, 114, 206, 1)',
				borderWidth: 1
			}
		]
	};

	$: chartOptions = {
		responsive: true,
		maintainAspectRatio: false,
		plugins: {
			legend: {
				display: false
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
						return `Requests: ${context.parsed.y}`;
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
						size: 10
					},
					maxRotation: 45,
					minRotation: 45
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
					stepSize: 1
				}
			}
		}
	};

	// Calculate error rate
	$: errorRate =
		performanceData.length > 0
			? (
					(performanceData.filter((d) => d.status === 'error').length / performanceData.length) *
					100
				).toFixed(1)
			: '0.0';
</script>

<div class="space-y-4">
	<!-- Performance Metrics Cards -->
	<div class="grid grid-cols-2 md:grid-cols-4 gap-4">
		<div
			class="rounded-lg border border-white/20 bg-white/60 dark:bg-gray-800/60 p-4 backdrop-blur-sm"
		>
			<p class="text-xs text-gray-600 dark:text-gray-400 mb-1">Avg Latency</p>
			<p class="text-2xl font-bold text-gray-900 dark:text-gray-100">
				{avgDuration.toFixed(0)}ms
			</p>
		</div>
		<div
			class="rounded-lg border border-white/20 bg-white/60 dark:bg-gray-800/60 p-4 backdrop-blur-sm"
		>
			<p class="text-xs text-gray-600 dark:text-gray-400 mb-1">P50</p>
			<p class="text-2xl font-bold text-gray-900 dark:text-gray-100">{p50.toFixed(0)}ms</p>
		</div>
		<div
			class="rounded-lg border border-white/20 bg-white/60 dark:bg-gray-800/60 p-4 backdrop-blur-sm"
		>
			<p class="text-xs text-gray-600 dark:text-gray-400 mb-1">P95</p>
			<p class="text-2xl font-bold text-gray-900 dark:text-gray-100">{p95.toFixed(0)}ms</p>
		</div>
		<div
			class="rounded-lg border border-white/20 bg-white/60 dark:bg-gray-800/60 p-4 backdrop-blur-sm"
		>
			<p class="text-xs text-gray-600 dark:text-gray-400 mb-1">P99</p>
			<p class="text-2xl font-bold text-gray-900 dark:text-gray-100">{p99.toFixed(0)}ms</p>
		</div>
	</div>

	<!-- Error Rate Badge -->
	<div class="flex items-center gap-2">
		<span class="text-sm text-gray-600 dark:text-gray-400">Error Rate:</span>
		<span
			class="inline-flex items-center px-3 py-1 rounded-full text-sm font-semibold {parseFloat(
				errorRate
			) > 5
				? 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400'
				: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400'}"
		>
			{errorRate}%
		</span>
	</div>

	<!-- Histogram Chart -->
	<div class="h-80 w-full">
		{#if performanceData.length > 0}
			<Bar data={chartData} options={chartOptions} />
		{:else}
			<div class="flex items-center justify-center h-full text-gray-500 dark:text-gray-400">
				<p>No performance data available</p>
			</div>
		{/if}
	</div>
</div>

