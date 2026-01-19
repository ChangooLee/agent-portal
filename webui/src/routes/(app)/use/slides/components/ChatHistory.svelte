<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
	import { slideStudioStore } from '../stores/slideStudioStore';
	import ChatMessage from './ChatMessage.svelte';

	let store = slideStudioStore.get();
	let messagesEnd: HTMLDivElement;

	const unsubscribe = slideStudioStore.subscribe((s) => {
		store = s;
		// Auto-scroll to bottom when new message arrives
		setTimeout(() => {
			if (messagesEnd) {
				messagesEnd.scrollIntoView({ behavior: 'smooth' });
			}
		}, 100);
	});

	onMount(() => {
		// Scroll to bottom on mount
		setTimeout(() => {
			if (messagesEnd) {
				messagesEnd.scrollIntoView({ behavior: 'smooth' });
			}
		}, 100);
	});

	onDestroy(() => {
		unsubscribe();
	});
</script>

<div class="flex-1 overflow-y-auto px-4 py-6">
	{#if store.messages.length === 0}
		<div class="flex flex-col items-center justify-center h-full text-center">
			<h2 class="text-2xl font-semibold text-white mb-2">슬라이드를 만들 준비가 되셨나요?</h2>
			<div class="text-gray-400 space-y-2 max-w-md">
				<div>• 주제만 말하면 완전한 전문 슬라이드를 제공</div>
				<div>• 자동 연구하고 결과를 슬라이드로 컴파일</div>
				<div>• AI를 사용하거나 웹에서 이미지, 비디오, 사운드 추가</div>
				<div>• 어떤 문서든 가져와서 AI 슬라이드로 변환</div>
			</div>
		</div>
	{:else}
		<div class="max-w-4xl mx-auto">
			{#each store.messages as message (message.id)}
				<ChatMessage {message} />
			{/each}
			<div bind:this={messagesEnd}></div>
		</div>
	{/if}
</div>
