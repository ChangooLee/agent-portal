<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import { fly, fade } from 'svelte/transition';
	import type { ExportOptions } from '$lib/agentops/types';
	import { exportTraces } from '$lib/agentops/api-client';

	export let isOpen: boolean = false;
	export let projectId: string;

	const dispatch = createEventDispatcher();

	let exportOptions: ExportOptions = {
		format: 'csv',
		include_spans: true,
		include_attributes: false,
		date_range: {
			start: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString(),
			end: new Date().toISOString()
		}
	};

	let exporting = false;
	let error: string | null = null;

	function close() {
		isOpen = false;
		dispatch('close');
	}

	async function handleExport() {
		exporting = true;
		error = null;

		try {
			const blob = await exportTraces(projectId, exportOptions);
			
			// Download the file
			const url = window.URL.createObjectURL(blob);
			const a = document.createElement('a');
			a.href = url;
			a.download = `agentops-traces-${Date.now()}.${exportOptions.format}`;
			document.body.appendChild(a);
			a.click();
			window.URL.revokeObjectURL(url);
			document.body.removeChild(a);

			dispatch('exported', exportOptions);
			close();
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to export traces';
			console.error('Export error:', e);
		} finally {
			exporting = false;
		}
	}

	function formatDateTimeLocal(isoString: string): string {
		return new Date(isoString).toISOString().slice(0, 16);
	}

	function parseDateTimeLocal(localString: string): string {
		return new Date(localString).toISOString();
	}
</script>

{#if isOpen}
	<!-- Backdrop -->
	<div
		class="fixed inset-0 bg-black/50 backdrop-blur-sm z-50"
		on:click={close}
		transition:fade={{ duration: 200 }}
	/>

	<!-- Dialog -->
	<div
		class="fixed inset-0 flex items-center justify-center z-50 p-4"
		transition:fly={{ y: 50, duration: 300 }}
	>
		<div
			class="bg-white dark:bg-gray-900 rounded-lg shadow-2xl max-w-md w-full p-6 space-y-6"
			on:click|stopPropagation
		>
			<!-- Header -->
			<div class="flex items-center justify-between">
				<h2 class="text-xl font-semibold text-gray-900 dark:text-gray-100">Export Traces</h2>
				<button
					on:click={close}
					class="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
					aria-label="Close dialog"
				>
					<svg
						class="w-5 h-5 text-gray-600 dark:text-gray-400"
						fill="none"
						stroke="currentColor"
						viewBox="0 0 24 24"
					>
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="2"
							d="M6 18L18 6M6 6l12 12"
						/>
					</svg>
				</button>
			</div>

			{#if error}
				<div
					class="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4"
				>
					<p class="text-red-800 dark:text-red-400 text-sm">{error}</p>
				</div>
			{/if}

			<!-- Format Selection -->
			<div>
				<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
					Export Format
				</label>
				<div class="grid grid-cols-3 gap-2">
					<button
						on:click={() => (exportOptions.format = 'csv')}
						class="px-4 py-2 rounded-lg text-sm font-medium transition-colors {exportOptions.format ===
						'csv'
							? 'bg-primary text-white'
							: 'bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700'}"
					>
						CSV
					</button>
					<button
						on:click={() => (exportOptions.format = 'json')}
						class="px-4 py-2 rounded-lg text-sm font-medium transition-colors {exportOptions.format ===
						'json'
							? 'bg-primary text-white'
							: 'bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700'}"
					>
						JSON
					</button>
					<button
						on:click={() => (exportOptions.format = 'pdf')}
						class="px-4 py-2 rounded-lg text-sm font-medium transition-colors {exportOptions.format ===
						'pdf'
							? 'bg-primary text-white'
							: 'bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700'}"
					>
						PDF
					</button>
				</div>
			</div>

			<!-- Date Range -->
			<div class="space-y-3">
				<div>
					<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
						Start Date
					</label>
					<input
						type="datetime-local"
						value={formatDateTimeLocal(exportOptions.date_range.start)}
						on:change={(e) => {
							exportOptions.date_range.start = parseDateTimeLocal(e.currentTarget.value);
						}}
						class="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all"
					/>
				</div>
				<div>
					<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
						End Date
					</label>
					<input
						type="datetime-local"
						value={formatDateTimeLocal(exportOptions.date_range.end)}
						on:change={(e) => {
							exportOptions.date_range.end = parseDateTimeLocal(e.currentTarget.value);
						}}
						class="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all"
					/>
				</div>
			</div>

			<!-- Options -->
			<div class="space-y-3">
				<label class="flex items-center gap-3 cursor-pointer">
					<input
						type="checkbox"
						bind:checked={exportOptions.include_spans}
						class="w-4 h-4 rounded border-gray-300 text-primary focus:ring-primary"
					/>
					<span class="text-sm text-gray-700 dark:text-gray-300">Include span details</span>
				</label>
				<label class="flex items-center gap-3 cursor-pointer">
					<input
						type="checkbox"
						bind:checked={exportOptions.include_attributes}
						class="w-4 h-4 rounded border-gray-300 text-primary focus:ring-primary"
					/>
					<span class="text-sm text-gray-700 dark:text-gray-300">Include span attributes</span>
				</label>
			</div>

			<!-- Actions -->
			<div class="flex items-center justify-end gap-3 pt-4 border-t border-gray-200 dark:border-gray-700">
				<button
					on:click={close}
					disabled={exporting}
					class="px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
				>
					Cancel
				</button>
				<button
					on:click={handleExport}
					disabled={exporting}
					class="px-4 py-2 rounded-lg bg-primary text-white hover:opacity-90 transition-opacity disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
				>
					{#if exporting}
						<div class="loading loading-spinner loading-sm"></div>
						<span>Exporting...</span>
					{:else}
						<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
							/>
						</svg>
						<span>Export</span>
					{/if}
				</button>
			</div>
		</div>
	</div>
{/if}

