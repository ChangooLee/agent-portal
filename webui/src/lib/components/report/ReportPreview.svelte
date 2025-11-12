<script lang="ts">
	import type { ReportTemplate } from './types';

	export let template: ReportTemplate | null = null;
</script>

<div class="flex h-full flex-col rounded-3xl border border-white/20 bg-white/65 p-0 shadow-2xl shadow-primary/5 backdrop-blur-2xl dark:border-gray-700/30 dark:bg-gray-900/55">
	<header class="flex items-center justify-between border-b border-white/10 px-6 py-4 dark:border-gray-800/40">
		<div>
			<h3 class="text-lg font-semibold text-gray-900 dark:text-gray-100">
				{template ? template.title : '보고서를 선택하세요'}
			</h3>
			<p class="text-sm text-gray-500 dark:text-gray-400">
				{template
					? template.description
					: '좌측 템플릿을 선택하면 미리보기가 여기에 표시됩니다.'}
			</p>
		</div>
		<div class="flex items-center gap-2">
			<button
				type="button"
				class="rounded-full border border-white/30 bg-white/80 px-3 py-1.5 text-xs font-medium text-gray-700 shadow-sm hover:bg-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40 dark:border-gray-700/40 dark:bg-gray-800/70 dark:text-gray-200"
			>
				복사
			</button>
			<button
				type="button"
				class="rounded-full bg-gradient-to-br from-primary via-secondary to-accent px-3.5 py-1.5 text-xs font-semibold text-white shadow-md shadow-primary/30 transition hover:scale-105 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/40"
			>
				다운로드
			</button>
		</div>
	</header>

	<div class="flex-1 overflow-y-auto px-6 py-6 scrollbar-thin scrollbar-track-transparent scrollbar-thumb-primary/20 dark:scrollbar-thumb-primary/30">
		{#if template}
			<article class="prose prose-sm max-w-none text-gray-800 dark:prose-invert dark:text-gray-100">
				{@html template.previewHtml}
			</article>
		{:else}
			<div class="flex h-full flex-col items-center justify-center text-center text-gray-500 dark:text-gray-400">
				<div class="mb-4 flex h-16 w-16 items-center justify-center rounded-full border border-dashed border-white/30 bg-white/40 dark:border-gray-700/40 dark:bg-gray-800/40">
					<span class="text-2xl">🧾</span>
				</div>
				<p class="text-sm leading-relaxed">
					좌측 템플릿을 선택하면<br />AI가 생성한 보고서 구조와 샘플 내용을 바로 확인할 수 있습니다.
				</p>
			</div>
		{/if}
	</div>
</div>

