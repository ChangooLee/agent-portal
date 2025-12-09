<script lang="ts">
	import type { ReportTemplate } from './types';

	export let template: ReportTemplate | null = null;
</script>

<div class="flex h-full flex-col rounded-xl border border-slate-800/50 bg-slate-900/80 p-0 shadow-xl shadow-black/20">
	<header class="flex items-center justify-between border-b border-slate-700/50 px-6 py-4">
		<div>
			<h3 class="text-lg font-semibold text-white">
				{template ? template.title : '보고서를 선택하세요'}
			</h3>
			<p class="text-sm text-slate-400">
				{template
					? template.description
					: '좌측 템플릿을 선택하면 미리보기가 여기에 표시됩니다.'}
			</p>
		</div>
		<div class="flex items-center gap-2">
			<button
				type="button"
				class="rounded-full border border-slate-700/50 bg-slate-800/50 px-3 py-1.5 text-xs font-medium text-slate-300 shadow-sm hover:bg-slate-800/80 hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500/50 transition-colors"
			>
				복사
			</button>
			<button
				type="button"
				class="rounded-full bg-indigo-600 hover:bg-indigo-500 px-3.5 py-1.5 text-xs font-semibold text-white shadow-md shadow-indigo-500/30 transition hover:scale-105 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500/50"
			>
				다운로드
			</button>
		</div>
	</header>

	<div class="flex-1 overflow-y-auto px-6 py-6 scrollbar-thin scrollbar-track-transparent scrollbar-thumb-indigo-500/20">
		{#if template}
			<article class="prose prose-sm max-w-none prose-invert prose-headings:text-white prose-p:text-slate-300 prose-strong:text-white prose-code:text-slate-300 prose-pre:text-slate-200 prose-blockquote:text-slate-300 prose-li:text-slate-300 prose-a:text-indigo-400 prose-table:text-slate-300">
				{@html template.previewHtml}
			</article>
		{:else}
			<div class="flex h-full flex-col items-center justify-center text-center">
				<div class="mb-4 flex h-16 w-16 items-center justify-center rounded-full border border-dashed border-slate-700/50 bg-slate-800/50">
					<span class="text-2xl">🧾</span>
				</div>
				<p class="text-sm leading-relaxed text-slate-400">
					좌측 템플릿을 선택하면<br />AI가 생성한 보고서 구조와 샘플 내용을 바로 확인할 수 있습니다.
				</p>
			</div>
		{/if}
	</div>
</div>

