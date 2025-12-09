<script lang="ts">
	import { onMount } from 'svelte';

	type ChatMessage = {
		id: string;
		role: 'user' | 'assistant';
		content: string;
		timestamp: string;
	};

	export let placeholder: string =
		'보고서에 포함하고 싶은 요구사항이나 데이터를 입력해보세요.';

	let messages: ChatMessage[] = [];
	let inputValue = '';
	let containerElement: HTMLDivElement | null = null;
	let isComposing = false;

	const formatTime = (date: Date) =>
		date.toLocaleTimeString([], {
			hour: '2-digit',
			minute: '2-digit'
		});

	const scrollToBottom = () => {
		if (containerElement) {
			containerElement.scrollTo({
				top: containerElement.scrollHeight,
				behavior: 'smooth'
			});
		}
	};

	const createId = () =>
		typeof crypto !== 'undefined' && 'randomUUID' in crypto
			? crypto.randomUUID()
			: Math.random().toString(36).slice(2, 10);

	const addMessage = (message: Omit<ChatMessage, 'id' | 'timestamp'>) => {
		const now = new Date();
		messages = [
			...messages,
			{
				id: createId(),
				timestamp: formatTime(now),
				...message
			}
		];

		scrollToBottom();
	};

	const submit = async () => {
		const trimmed = inputValue.trim();
		if (!trimmed) {
			return;
		}

		addMessage({ role: 'user', content: trimmed });
		inputValue = '';

		setTimeout(() => {
			addMessage({
				role: 'assistant',
				content:
					'요청을 검토했습니다. 핵심 지표와 요약을 분석에 반영하도록 준비하겠습니다.'
			});
		}, 800);
	};

	const handleKeyDown = (event: KeyboardEvent) => {
		if (event.key === 'Enter' && !event.shiftKey && !isComposing) {
			event.preventDefault();
			submit();
		}
	};

	onMount(() => {
		messages = [
			{
				id: createId(),
				role: 'assistant',
				content: '어떤 인사이트를 담고 싶은지 알려주시면 맞춤형 보고서를 제안드릴게요.',
				timestamp: formatTime(new Date())
			}
		];
	});
</script>

<div class="flex h-full min-h-[22rem] flex-col rounded-xl border border-slate-800/50 bg-slate-900/80 px-0 py-0 shadow-xl shadow-black/20">
	<header class="flex items-center justify-between border-b border-slate-700/50 px-4 py-3">
		<div class="flex flex-col">
			<h3 class="text-sm font-semibold text-white">
				보고서 어시스턴트
			</h3>
			<p class="text-xs text-slate-400">요약, 지표 정리, 차트 생성 지원</p>
		</div>
		<div class="inline-flex items-center gap-2 rounded-full bg-indigo-500/20 text-indigo-400 border border-indigo-500/30 px-3 py-1 text-xs font-semibold">
			<span>실시간 AI</span>
		</div>
	</header>

	<div
		bind:this={containerElement}
		class="flex-1 space-y-3 overflow-y-auto px-4 py-4 scrollbar-none"
	>
		{#each messages as message (message.id)}
			<div
				class={`max-w-[85%] rounded-xl px-4 py-3 text-sm shadow-md transition ${
					message.role === 'user'
						? 'ml-auto bg-indigo-500/20 text-white border border-indigo-500/30 shadow-indigo-500/30'
						: 'bg-slate-800/50 text-slate-200 border border-slate-700/50'
				}`}
			>
				<p class="leading-relaxed">{message.content}</p>
				<span class="mt-2 block text-right text-[11px] text-slate-400">{message.timestamp}</span>
			</div>
		{/each}
	</div>

	<form
		class="border-t border-slate-700/50 px-4 py-3"
		on:submit|preventDefault={submit}
	>
		<div class="flex items-end gap-2 rounded-xl border border-slate-700/50 bg-slate-800/50 px-3 py-2 shadow-inner transition focus-within:border-indigo-500/50 focus-within:ring-2 focus-within:ring-indigo-500/50">
			<textarea
				class="max-h-32 flex-1 resize-none bg-transparent text-sm text-white outline-none placeholder:text-slate-400"
				rows="1"
				bind:value={inputValue}
				placeholder={placeholder}
				on:keydown={handleKeyDown}
				on:compositionstart={() => (isComposing = true)}
				on:compositionend={() => (isComposing = false)}
			/>

			<button
				type="submit"
				class="rounded-full bg-indigo-600 hover:bg-indigo-500 px-4 py-2 text-xs font-semibold text-white shadow-lg shadow-indigo-500/30 transition hover:scale-105 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500/50"
				aria-label="메시지 전송"
			>
				전송
			</button>
		</div>
	</form>
</div>

