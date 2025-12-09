<script lang="ts">
	import { createEventDispatcher } from 'svelte';
	import type { ReportTemplate } from './types';

	type TemplateSelectEvent = {
	id: string;
	};

	const dispatch = createEventDispatcher<{
	select: TemplateSelectEvent;
	}>();

	export let templates: ReportTemplate[] = [];
	export let selectedId: string | null = null;

	const handleSelect = (templateId: string) => {
	if (templateId === selectedId) {
	return;
	}

	dispatch('select', { id: templateId });
	};
</script>

<div class="flex flex-col gap-4">
	<div class="flex flex-col gap-1">
		<div class="flex items-center gap-2">
			<span class="inline-flex rounded-full bg-indigo-500/20 text-indigo-400 border border-indigo-500/30 px-2.5 py-1 text-xs font-semibold">
				AI Research
			</span>
			<p class="text-sm text-slate-400">
				검증된 템플릿으로 보고서를 빠르게 구성하세요.
			</p>
		</div>
		<h2 class="text-2xl font-bold text-white">
			보고서 템플릿
		</h2>
	</div>

	<div class="grid grid-cols-1 gap-3 @md:grid-cols-2">
		{#each templates as template}
			<button
				type="button"
				class={`group relative flex flex-col gap-3 overflow-hidden rounded-xl border px-4 py-4 text-left transition-all duration-300 ease-out hover:-translate-y-1 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500/50 ${
					selectedId === template.id
						? 'bg-slate-900/80 border-indigo-500/50 shadow-xl shadow-black/30'
						: 'bg-slate-900/80 border-slate-800/50 shadow-lg shadow-black/20 hover:bg-slate-800/80 hover:border-indigo-500/50 hover:shadow-xl hover:shadow-black/30'
				}`}
				aria-pressed={selectedId === template.id}
				on:click={() => handleSelect(template.id)}
			>
				<div class="flex items-start justify-between">
					<div class="flex flex-col gap-1">
						<span class="text-xs font-semibold uppercase tracking-widest text-indigo-400">
							{template.category}
						</span>
						<h3 class="text-lg font-semibold text-white">
							{template.title}
						</h3>
					</div>

					<div class="relative">
						<div class="absolute inset-0 rounded-full bg-indigo-500/20 blur-md opacity-75 group-hover:opacity-100 transition" />
						<div class="relative flex h-10 w-10 items-center justify-center rounded-full border border-indigo-500/30 bg-indigo-500/20 shadow-inner">
							<div class="size-5 rounded-full bg-indigo-500/60 group-hover:scale-110 transition-transform" />
						</div>
					</div>
				</div>

				<p class="line-clamp-2 text-sm text-slate-300">
					{template.description}
				</p>

				<div class="flex flex-wrap gap-1.5">
					{#each template.tags as tag}
						<span class="inline-flex rounded-full border border-slate-700/50 bg-slate-800/50 px-2 py-0.5 text-xs font-medium text-slate-300">
							#{tag}
						</span>
					{/each}
				</div>

				<div class="flex flex-wrap gap-3 pt-1">
					{#each template.metrics as metric}
						<div
							class={`min-w-[6rem] rounded-xl border px-2.5 py-2 text-left shadow-sm transition ${
								metric.accent === 'primary'
									? 'bg-indigo-500/20 text-indigo-400 border-indigo-500/30'
									: metric.accent === 'secondary'
										? 'bg-purple-500/20 text-purple-400 border-purple-500/30'
										: metric.accent === 'accent'
											? 'bg-pink-500/20 text-pink-400 border-pink-500/30'
											: 'bg-slate-800/50 text-slate-300 border-slate-700/50'
							}`}
						>
							<div class="text-xs font-medium uppercase tracking-wide">
								{metric.label}
							</div>
							<div class="text-base font-semibold text-white">
								{metric.value}
							</div>
						</div>
					{/each}
				</div>
			</button>
		{/each}
	</div>
</div>

