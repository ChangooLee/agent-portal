<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import type { TraceFilters, FilterPreset } from '$lib/agentops/types';

	export let filters: TraceFilters;
	export let presets: FilterPreset[] = [];

	const dispatch = createEventDispatcher();

	let showAdvanced = false;
	let selectedPreset: string | null = null;

	const statusOptions = ['success', 'error', 'running'];
	const modelOptions = [
		'gpt-4',
		'gpt-4-turbo',
		'gpt-3.5-turbo',
		'claude-3-opus',
		'claude-3-sonnet',
		'claude-3-haiku'
	];

	function applyFilters() {
		dispatch('apply', filters);
	}

	function resetFilters() {
		filters = {
			start_time: new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString(),
			end_time: new Date().toISOString(),
			status: undefined,
			models: undefined,
			min_cost: undefined,
			max_cost: undefined,
			min_duration: undefined,
			max_duration: undefined,
			tags: undefined,
			search: undefined
		};
		selectedPreset = null;
		applyFilters();
	}

	function applyPreset(preset: FilterPreset) {
		filters = { ...preset.filters };
		selectedPreset = preset.id;
		applyFilters();
	}

	function savePreset() {
		const name = prompt('Enter preset name:');
		if (name) {
			const newPreset: FilterPreset = {
				id: Date.now().toString(),
				name,
				filters: { ...filters },
				created_at: new Date().toISOString()
			};
			presets = [...presets, newPreset];
			dispatch('savePreset', newPreset);
		}
	}

	function deletePreset(presetId: string) {
		if (confirm('Delete this preset?')) {
			presets = presets.filter((p) => p.id !== presetId);
			if (selectedPreset === presetId) {
				selectedPreset = null;
			}
			dispatch('deletePreset', presetId);
		}
	}

	// Format date for datetime-local input
	function formatDateTimeLocal(isoString: string): string {
		return new Date(isoString).toISOString().slice(0, 16);
	}

	// Parse datetime-local input to ISO string
	function parseDateTimeLocal(localString: string): string {
		return new Date(localString).toISOString();
	}
</script>

<div
	class="rounded-lg border border-white/20 bg-white/60 dark:bg-gray-800/60 p-6 backdrop-blur-sm shadow-sm space-y-4"
>
	<!-- Header -->
	<div class="flex items-center justify-between">
		<h3 class="text-lg font-semibold text-gray-900 dark:text-gray-100">Filters</h3>
		<div class="flex items-center gap-2">
			<button
				on:click={savePreset}
				class="px-3 py-1.5 text-sm rounded-lg bg-primary text-white hover:opacity-90 transition-opacity"
			>
				Save Preset
			</button>
			<button
				on:click={resetFilters}
				class="px-3 py-1.5 text-sm rounded-lg border border-gray-300 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors"
			>
				Reset
			</button>
		</div>
	</div>

	<!-- Saved Presets -->
	{#if presets.length > 0}
		<div>
			<p class="text-sm text-gray-600 dark:text-gray-400 mb-2">Saved Presets</p>
			<div class="flex flex-wrap gap-2">
				{#each presets as preset}
					<button
						on:click={() => applyPreset(preset)}
						class="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm transition-colors {selectedPreset ===
						preset.id
							? 'bg-primary text-white'
							: 'bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700'}"
					>
						<span>{preset.name}</span>
						<button
							on:click|stopPropagation={() => deletePreset(preset.id)}
							class="hover:text-red-500 transition-colors"
						>
							<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									stroke-width="2"
									d="M6 18L18 6M6 6l12 12"
								/>
							</svg>
						</button>
					</button>
				{/each}
			</div>
		</div>
	{/if}

	<!-- Date Range -->
	<div class="grid grid-cols-2 gap-4">
		<div>
			<label class="block text-sm text-gray-600 dark:text-gray-400 mb-1">Start Time</label>
			<input
				type="datetime-local"
				value={formatDateTimeLocal(filters.start_time)}
				on:change={(e) => {
					filters.start_time = parseDateTimeLocal(e.currentTarget.value);
					applyFilters();
				}}
				class="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all"
			/>
		</div>
		<div>
			<label class="block text-sm text-gray-600 dark:text-gray-400 mb-1">End Time</label>
			<input
				type="datetime-local"
				value={formatDateTimeLocal(filters.end_time)}
				on:change={(e) => {
					filters.end_time = parseDateTimeLocal(e.currentTarget.value);
					applyFilters();
				}}
				class="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all"
			/>
		</div>
	</div>

	<!-- Search -->
	<div>
		<label class="block text-sm text-gray-600 dark:text-gray-400 mb-1">Search</label>
		<input
			type="text"
			bind:value={filters.search}
			on:input={applyFilters}
			placeholder="Search traces..."
			class="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all"
		/>
	</div>

	<!-- Status Filter -->
	<div>
		<label class="block text-sm text-gray-600 dark:text-gray-400 mb-2">Status</label>
		<div class="flex flex-wrap gap-2">
			{#each statusOptions as status}
				<button
					on:click={() => {
						if (!filters.status) filters.status = [];
						const index = filters.status.indexOf(status);
						if (index > -1) {
							filters.status.splice(index, 1);
						} else {
							filters.status.push(status);
						}
						applyFilters();
					}}
					class="px-3 py-1.5 rounded-lg text-sm transition-colors {filters.status?.includes(
						status
					)
						? 'bg-primary text-white'
						: 'bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700'}"
				>
					{status}
				</button>
			{/each}
		</div>
	</div>

	<!-- Advanced Filters Toggle -->
	<button
		on:click={() => (showAdvanced = !showAdvanced)}
		class="flex items-center gap-2 text-sm text-primary dark:text-primary-light hover:underline"
	>
		<svg
			class="w-4 h-4 transition-transform {showAdvanced ? 'rotate-90' : ''}"
			fill="none"
			stroke="currentColor"
			viewBox="0 0 24 24"
		>
			<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
		</svg>
		Advanced Filters
	</button>

	{#if showAdvanced}
		<div class="space-y-4 pt-4 border-t border-gray-200 dark:border-gray-700">
			<!-- Model Filter -->
			<div>
				<label class="block text-sm text-gray-600 dark:text-gray-400 mb-2">Models</label>
				<div class="flex flex-wrap gap-2">
					{#each modelOptions as model}
						<button
							on:click={() => {
								if (!filters.models) filters.models = [];
								const index = filters.models.indexOf(model);
								if (index > -1) {
									filters.models.splice(index, 1);
								} else {
									filters.models.push(model);
								}
								applyFilters();
							}}
							class="px-3 py-1.5 rounded-lg text-sm transition-colors {filters.models?.includes(
								model
							)
								? 'bg-primary text-white'
								: 'bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-700'}"
						>
							{model}
						</button>
					{/each}
				</div>
			</div>

			<!-- Cost Range -->
			<div class="grid grid-cols-2 gap-4">
				<div>
					<label class="block text-sm text-gray-600 dark:text-gray-400 mb-1">Min Cost ($)</label>
					<input
						type="number"
						bind:value={filters.min_cost}
						on:input={applyFilters}
						step="0.01"
						placeholder="0.00"
						class="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all"
					/>
				</div>
				<div>
					<label class="block text-sm text-gray-600 dark:text-gray-400 mb-1">Max Cost ($)</label>
					<input
						type="number"
						bind:value={filters.max_cost}
						on:input={applyFilters}
						step="0.01"
						placeholder="100.00"
						class="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all"
					/>
				</div>
			</div>

			<!-- Duration Range -->
			<div class="grid grid-cols-2 gap-4">
				<div>
					<label class="block text-sm text-gray-600 dark:text-gray-400 mb-1">Min Duration (ms)</label>
					<input
						type="number"
						bind:value={filters.min_duration}
						on:input={applyFilters}
						placeholder="0"
						class="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all"
					/>
				</div>
				<div>
					<label class="block text-sm text-gray-600 dark:text-gray-400 mb-1">Max Duration (ms)</label>
					<input
						type="number"
						bind:value={filters.max_duration}
						on:input={applyFilters}
						placeholder="10000"
						class="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all"
					/>
				</div>
			</div>

			<!-- Tags -->
			<div>
				<label class="block text-sm text-gray-600 dark:text-gray-400 mb-1">Tags (comma-separated)</label>
				<input
					type="text"
					value={filters.tags?.join(', ') || ''}
					on:input={(e) => {
						const value = e.currentTarget.value;
						filters.tags = value ? value.split(',').map((t) => t.trim()) : undefined;
						applyFilters();
					}}
					placeholder="production, critical"
					class="w-full px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all"
				/>
			</div>
		</div>
	{/if}
</div>

