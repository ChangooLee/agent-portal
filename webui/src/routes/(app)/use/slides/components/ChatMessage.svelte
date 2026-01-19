<script lang="ts">
	import type { ChatMessage } from '../stores/slideStudioStore';

	export let message: ChatMessage;

	$: isUser = message.role === 'user';
	$: timestamp = new Date(message.timestamp).toLocaleTimeString('ko-KR', {
		hour: '2-digit',
		minute: '2-digit'
	});
</script>

<div class="flex gap-3 {isUser ? 'flex-row-reverse' : 'flex-row'} mb-6">
	<!-- Avatar -->
	<div class="flex-shrink-0">
		{#if isUser}
			<div class="w-8 h-8 rounded-full bg-purple-600 flex items-center justify-center">
				<svg class="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
				</svg>
			</div>
		{:else}
			<div class="w-8 h-8 rounded-full bg-gray-700 flex items-center justify-center">
				<svg class="w-5 h-5 text-gray-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
				</svg>
			</div>
		{/if}
	</div>

	<!-- Message content -->
	<div class="flex-1 min-w-0">
		<div class="flex items-center gap-2 mb-1 {isUser ? 'justify-end' : 'justify-start'}">
			<span class="text-xs text-gray-400">{timestamp}</span>
		</div>
		<div class="rounded-2xl px-4 py-3 {isUser ? 'bg-purple-600 text-white ml-auto' : 'bg-gray-800 text-gray-100'} max-w-[80%] {isUser ? 'rounded-br-sm' : 'rounded-bl-sm'}">
			<div class="whitespace-pre-wrap break-words">{message.content}</div>
			{#if message.metadata && Object.keys(message.metadata).length > 0}
				<div class="mt-2 pt-2 border-t {isUser ? 'border-purple-500/30' : 'border-gray-700'}">
					{#if message.metadata.deck_id}
						<div class="text-xs opacity-75">Deck ID: {message.metadata.deck_id.substring(0, 8)}...</div>
					{/if}
					{#if message.metadata.slide_count}
						<div class="text-xs opacity-75">Slides: {message.metadata.slide_count}</div>
					{/if}
				</div>
			{/if}
		</div>
	</div>
</div>
