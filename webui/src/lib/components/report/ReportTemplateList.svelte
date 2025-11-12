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
			<span class="inline-flex rounded-full bg-gradient-to-r from-primary/80 via-secondary/80 to-accent/80 px-2.5 py-1 text-xs font-semibold text-white shadow-sm shadow-primary/30">
				AI Research
			</span>
			<p class="text-sm text-gray-500 dark:text-gray-400">
				검증된 템플릿으로 보고서를 빠르게 구성하세요.
			</p>
		</div>
		<h2 class="text-xl font-semibold text-gray-900 dark:text-gray-50">
			보고서 템플릿
		</h2>
	</div>

	<div class="grid grid-cols-1 gap-3 @md:grid-cols-2">
		{#each templates as template}
			<button
				type="button"
				class={`group relative flex flex-col gap-3 overflow-hidden rounded-2xl border px-4 py-4 text-left transition-all duration-300 ease-out backdrop-blur-2xl hover:-translate-y-1 hover:bg-white/70 hover:shadow-2xl hover:shadow-primary/10 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 dark:hover:bg-gray-900/65 ${
					selectedId === template.id
						? 'border-primary/60 bg-white/70 shadow-xl shadow-primary/20 dark:bg-gray-900/65'
						: 'border-white/20 bg-white/60 shadow-lg dark:border-gray-700/20 dark:bg-gray-900/55'
				}`}
				aria-pressed={selectedId === template.id}
				on:click={() => handleSelect(template.id)}
			>
				<div class="flex items-start justify-between">
					<div class="flex flex-col gap-1">
						<span class="text-xs font-semibold uppercase tracking-widest text-primary dark:text-primary-light">
							{template.category}
						</span>
						<h3 class="text-lg font-semibold text-gray-900 dark:text-gray-100">
							{template.title}
						</h3>
					</div>

					<div class="relative">
						<div class="absolute inset-0 rounded-full bg-gradient-to-br from-primary/40 via-secondary/40 to-accent/40 blur-md opacity-75 group-hover:opacity-100 transition" />
						<div class="relative flex h-10 w-10 items-center justify-center rounded-full border border-white/40 dark:border-gray-700/40 bg-white/70 dark:bg-gray-900/60 shadow-inner">
							<div class="size-5 rounded-full bg-gradient-to-br from-primary to-secondary opacity-80 group-hover:scale-110 transition-transform" />
						</div>
					</div>
				</div>

				<p class="line-clamp-2 text-sm text-gray-600 dark:text-gray-300">
					{template.description}
				</p>

				<div class="flex flex-wrap gap-1.5">
					{#each template.tags as tag}
						<span class="inline-flex rounded-full border border-white/40 dark:border-gray-700/40 bg-white/50 px-2 py-0.5 text-xs font-medium text-gray-600 dark:text-gray-300 shadow-sm">
							#{tag}
						</span>
					{/each}
				</div>

				<div class="flex flex-wrap gap-3 pt-1">
					{#each template.metrics as metric}
						<div
							class={`min-w-[6rem] rounded-xl border border-white/30 px-2.5 py-2 text-left shadow-sm transition ${
								metric.accent === 'primary'
									? 'bg-primary/10 text-primary dark:text-primary-light'
									: metric.accent === 'secondary'
										? 'bg-secondary/10 text-secondary dark:text-secondary-light'
										: metric.accent === 'accent'
											? 'bg-accent/10 text-accent dark:text-accent-light'
											: 'bg-white/40 dark:bg-gray-900/40 text-gray-700 dark:text-gray-200'
							}`}
						>
							<div class="text-xs font-medium uppercase tracking-wide">
								{metric.label}
							</div>
							<div class="text-base font-semibold">
								{metric.value}
							</div>
						</div>
					{/each}
				</div>
			</button>
		{/each}
	</div>
</div>

