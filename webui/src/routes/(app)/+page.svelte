<script lang="ts">
	import Chat from '$lib/components/chat/Chat.svelte';
	import Help from '$lib/components/layout/Help.svelte';
	import { WEBUI_NAME } from '$lib/stores';
</script>

<svelte:head>
	<title>{$WEBUI_NAME || 'SFN AI Portal'}</title>
</svelte:head>

<Help />
<Chat />
