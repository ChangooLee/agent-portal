<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import type { SessionReplay, ReplayEvent } from '$lib/monitoring/types';
	import { getSessionReplay } from '$lib/monitoring/api-client';
	import EventCard from './EventCard.svelte';

	export let traceId: string;

	let loading = true;
	let error: string | null = null;
	let replay: SessionReplay | null = null;
	let currentEventIndex = 0;
	let isPlaying = false;
	let playbackSpeed = 1.0;
	let progressPercent = 0;
	let playbackInterval: number | null = null;

	const speedOptions = [0.5, 1.0, 2.0, 4.0];

	$: currentEvent = replay?.events[currentEventIndex] || null;
	$: progressPercent = replay ? (currentEventIndex / (replay.events.length - 1)) * 100 : 0;

	async function loadReplay() {
		loading = true;
		error = null;

		try {
			replay = await getSessionReplay(traceId);
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load session replay';
			console.error('Failed to load replay:', e);
		} finally {
			loading = false;
		}
	}

	function play() {
		if (!replay || currentEventIndex >= replay.events.length - 1) {
			// Reset to start if at the end
			if (currentEventIndex >= replay.events.length - 1) {
				currentEventIndex = 0;
			}
		}

		isPlaying = true;
		startPlayback();
	}

	function pause() {
		isPlaying = false;
		stopPlayback();
	}

	function startPlayback() {
		if (!replay) return;

		stopPlayback(); // Clear any existing interval

		playbackInterval = window.setInterval(() => {
			if (currentEventIndex < replay.events.length - 1) {
				currentEventIndex++;
			} else {
				pause(); // Auto-pause at the end
			}
		}, 1000 / playbackSpeed); // Adjust speed
	}

	function stopPlayback() {
		if (playbackInterval !== null) {
			clearInterval(playbackInterval);
			playbackInterval = null;
		}
	}

	function nextEvent() {
		if (replay && currentEventIndex < replay.events.length - 1) {
			currentEventIndex++;
		}
	}

	function prevEvent() {
		if (currentEventIndex > 0) {
			currentEventIndex--;
		}
	}

	function seekToEvent(index: number) {
		if (replay && index >= 0 && index < replay.events.length) {
			currentEventIndex = index;
		}
	}

	function seekToPercent(percent: number) {
		if (replay) {
			const index = Math.floor((percent / 100) * (replay.events.length - 1));
			seekToEvent(index);
		}
	}

	function handleScrubberClick(event: MouseEvent) {
		const target = event.currentTarget as HTMLElement;
		const rect = target.getBoundingClientRect();
		const percent = ((event.clientX - rect.left) / rect.width) * 100;
		seekToPercent(percent);
	}

	function formatTime(ms: number): string {
		const seconds = Math.floor(ms / 1000);
		const minutes = Math.floor(seconds / 60);
		const remainingSeconds = seconds % 60;
		return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
	}

	onMount(() => {
		loadReplay();
	});

	onDestroy(() => {
		stopPlayback();
	});
</script>

<div class="space-y-6">
	{#if loading}
		<div class="flex items-center justify-center h-64">
			<div class="flex flex-col items-center gap-3">
				<div class="loading loading-spinner loading-lg text-primary"></div>
				<p class="text-gray-600 dark:text-gray-400">Loading session replay...</p>
			</div>
		</div>
	{:else if error}
		<div
			class="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4"
		>
			<p class="text-red-800 dark:text-red-400 font-medium">Error loading replay</p>
			<p class="text-red-600 dark:text-red-500 text-sm mt-1">{error}</p>
		</div>
	{:else if replay}
		<!-- Player Controls -->
		<div
			class="rounded-lg border border-white/20 bg-white/60 dark:bg-gray-800/60 p-4 backdrop-blur-sm shadow-sm"
		>
			<!-- Timeline Scrubber -->
			<div class="mb-4">
				<div
					class="relative h-2 bg-gray-200 dark:bg-gray-700 rounded-full cursor-pointer overflow-hidden"
					on:click={handleScrubberClick}
				>
					<!-- Progress Bar -->
					<div
						class="absolute inset-y-0 left-0 bg-primary dark:bg-primary-light transition-all"
						style="width: {progressPercent}%"
					></div>

					<!-- Event Markers -->
					{#each replay.events as event, i}
						{@const markerPercent = (i / (replay.events.length - 1)) * 100}
						<button
							class="absolute top-1/2 -translate-y-1/2 w-3 h-3 rounded-full bg-gray-400 dark:bg-gray-500 hover:bg-primary dark:hover:bg-primary-light transition-colors {i ===
							currentEventIndex
								? 'ring-2 ring-primary dark:ring-primary-light bg-primary dark:bg-primary-light'
								: ''}"
							style="left: {markerPercent}%"
							on:click|stopPropagation={() => seekToEvent(i)}
						></button>
					{/each}
				</div>

				<!-- Time Display -->
				<div class="flex items-center justify-between mt-2 text-sm text-gray-600 dark:text-gray-400">
					<span>{currentEvent ? formatTime(currentEvent.relative_time) : '0:00'}</span>
					<span>Event {currentEventIndex + 1} / {replay.events.length}</span>
					<span>{formatTime(replay.total_duration)}</span>
				</div>
			</div>

			<!-- Control Buttons -->
			<div class="flex items-center justify-center gap-4">
				<!-- Previous Event -->
				<button
					on:click={prevEvent}
					disabled={currentEventIndex === 0}
					class="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
					aria-label="Previous event"
				>
					<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="2"
							d="M15 19l-7-7 7-7"
						/>
					</svg>
				</button>

				<!-- Play/Pause -->
				<button
					on:click={isPlaying ? pause : play}
					class="p-3 rounded-full bg-primary dark:bg-primary-light text-white hover:opacity-90 transition-opacity"
					aria-label={isPlaying ? 'Pause' : 'Play'}
				>
					{#if isPlaying}
						<svg class="w-8 h-8" fill="currentColor" viewBox="0 0 24 24">
							<path d="M6 4h4v16H6V4zm8 0h4v16h-4V4z" />
						</svg>
					{:else}
						<svg class="w-8 h-8" fill="currentColor" viewBox="0 0 24 24">
							<path d="M8 5v14l11-7z" />
						</svg>
					{/if}
				</button>

				<!-- Next Event -->
				<button
					on:click={nextEvent}
					disabled={currentEventIndex >= replay.events.length - 1}
					class="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
					aria-label="Next event"
				>
					<svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
					</svg>
				</button>

				<!-- Speed Control -->
				<div class="ml-4 flex items-center gap-2">
					<span class="text-sm text-gray-600 dark:text-gray-400">Speed:</span>
					<select
						bind:value={playbackSpeed}
						on:change={() => {
							if (isPlaying) {
								startPlayback(); // Restart with new speed
							}
						}}
						class="px-2 py-1 rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 text-sm"
					>
						{#each speedOptions as speed}
							<option value={speed}>{speed}x</option>
						{/each}
					</select>
				</div>
			</div>
		</div>

		<!-- Current Event Display -->
		{#if currentEvent}
			<div class="animate-fadeIn">
				<EventCard event={currentEvent} />
			</div>
		{/if}

		<!-- Event Timeline (All Events) -->
		<div
			class="rounded-lg border border-white/20 bg-white/60 dark:bg-gray-800/60 p-4 backdrop-blur-sm shadow-sm"
		>
			<h3 class="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">Event Timeline</h3>
			<div class="space-y-2 max-h-96 overflow-y-auto">
				{#each replay.events as event, i}
					<button
						on:click={() => seekToEvent(i)}
						class="w-full text-left p-3 rounded-lg border transition-all {i === currentEventIndex
							? 'border-primary bg-primary/10 dark:bg-primary-light/10'
							: 'border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800'}"
					>
						<div class="flex items-center justify-between">
							<div class="flex items-center gap-3">
								<span
									class="text-xs font-mono text-gray-500 dark:text-gray-400 min-w-[60px]"
								>
									{formatTime(event.relative_time)}
								</span>
								<span class="text-sm font-medium text-gray-900 dark:text-gray-100">
									{event.span_name}
								</span>
								<span
									class="text-xs px-2 py-1 rounded-full {event.type === 'llm_call'
										? 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400'
										: event.type === 'tool_use'
											? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400'
											: event.type === 'error'
												? 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400'
												: 'bg-gray-100 text-gray-800 dark:bg-gray-700/30 dark:text-gray-300'}"
								>
									{event.type}
								</span>
							</div>
							{#if i === currentEventIndex}
								<svg class="w-5 h-5 text-primary" fill="currentColor" viewBox="0 0 20 20">
									<path
										fill-rule="evenodd"
										d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
										clip-rule="evenodd"
									/>
								</svg>
							{/if}
						</div>
					</button>
				{/each}
			</div>
		</div>
	{/if}
</div>

<style>
	@keyframes fadeIn {
		from {
			opacity: 0;
			transform: translateY(10px);
		}
		to {
			opacity: 1;
			transform: translateY(0);
		}
	}

	.animate-fadeIn {
		animation: fadeIn 0.3s ease-out;
	}
</style>

