<script lang="ts">
	import { createEventDispatcher } from 'svelte';

	export let title: string;
	export let defaultOpen: boolean = false;
	export let disabled: boolean = false;

	let isOpen = defaultOpen;
	const dispatch = createEventDispatcher();

	function toggle() {
		if (disabled) return;
		isOpen = !isOpen;
		dispatch('toggle', { isOpen });
	}
</script>

<div class="border-b border-gray-800">
	<button
		on:click={toggle}
		disabled={disabled}
		class="w-full px-4 py-3 flex items-center justify-between text-left hover:bg-gray-800/50 transition-colors {disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}"
	>
		<span class="text-sm font-medium text-gray-300">{title}</span>
		<svg
			class="w-5 h-5 text-gray-400 transition-transform {isOpen ? 'rotate-180' : ''}"
			fill="none"
			viewBox="0 0 24 24"
			stroke="currentColor"
		>
			<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
		</svg>
	</button>
	{#if isOpen}
		<div class="px-4 pb-4">
			<slot />
		</div>
	{/if}
</div>
