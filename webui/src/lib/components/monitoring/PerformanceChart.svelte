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
	import type { PerformanceDataPoint } from '$lib/monitoring/types';

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
				backgroundColor: 'rgba(6, 182, 212, 0.7)',
				borderColor: 'rgba(6, 182, 212, 1)',
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
				backgroundColor: 'rgba(15, 23, 42, 0.95)',
				titleColor: '#fff',
				bodyColor: '#fff',
				borderColor: 'rgba(6, 182, 212, 1)',
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
				color: '#ffffff',
				font: {
					size: 16,
					weight: 'bold' as const
				}
			}
		},
		scales: {
			x: {
				grid: {
					display: true,
					color: 'rgba(148, 163, 184, 0.1)'
				},
				ticks: {
					color: '#cbd5e1',
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
					color: 'rgba(148, 163, 184, 0.1)'
				},
				ticks: {
					color: '#cbd5e1',
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
			class="bg-slate-900/80 border border-slate-800/50 rounded-xl p-6 shadow-lg shadow-black/20 hover:shadow-xl hover:shadow-black/30 hover:bg-slate-800/80 hover:border-cyan-500/50 hover:-translate-y-1 transition-all duration-300"
		>
			<p class="text-sm text-slate-400 mb-2">Avg Latency</p>
			<p class="text-2xl font-bold text-white">
				{avgDuration.toFixed(0)}ms
			</p>
		</div>
		<div
			class="bg-slate-900/80 border border-slate-800/50 rounded-xl p-6 shadow-lg shadow-black/20 hover:shadow-xl hover:shadow-black/30 hover:bg-slate-800/80 hover:border-cyan-500/50 hover:-translate-y-1 transition-all duration-300"
		>
			<p class="text-sm text-slate-400 mb-2">P50</p>
			<p class="text-2xl font-bold text-white">{p50.toFixed(0)}ms</p>
		</div>
		<div
			class="bg-slate-900/80 border border-slate-800/50 rounded-xl p-6 shadow-lg shadow-black/20 hover:shadow-xl hover:shadow-black/30 hover:bg-slate-800/80 hover:border-cyan-500/50 hover:-translate-y-1 transition-all duration-300"
		>
			<p class="text-sm text-slate-400 mb-2">P95</p>
			<p class="text-2xl font-bold text-white">{p95.toFixed(0)}ms</p>
		</div>
		<div
			class="bg-slate-900/80 border border-slate-800/50 rounded-xl p-6 shadow-lg shadow-black/20 hover:shadow-xl hover:shadow-black/30 hover:bg-slate-800/80 hover:border-cyan-500/50 hover:-translate-y-1 transition-all duration-300"
		>
			<p class="text-sm text-slate-400 mb-2">P99</p>
			<p class="text-2xl font-bold text-white">{p99.toFixed(0)}ms</p>
		</div>
	</div>

	<!-- Error Rate Badge -->
	<div class="flex items-center gap-2">
		<span class="text-sm text-slate-400">Error Rate:</span>
		<span
			class="inline-flex items-center px-3 py-1 rounded-full text-sm font-semibold border {parseFloat(
				errorRate
			) > 5
				? 'bg-red-500/20 text-red-400 border-red-500/30'
				: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30'}"
		>
			{errorRate}%
		</span>
	</div>

	<!-- Histogram Chart -->
	<div class="h-80 w-full">
		{#if performanceData.length > 0}
			<Bar data={chartData} options={chartOptions} />
		{:else}
			<div class="flex items-center justify-center h-full text-slate-400">
				<p>No performance data available</p>
			</div>
		{/if}
	</div>
</div>

