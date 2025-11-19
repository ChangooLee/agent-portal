<script lang="ts">
	import { createEventDispatcher, onDestroy, onMount } from 'svelte';
	const dispatch = createEventDispatcher();

	let loaderElement: HTMLElement;

	let observer;

	onMount(() => {
		observer = new IntersectionObserver(
			(entries, observer) => {
				entries.forEach((entry) => {
					if (entry.isIntersecting) {
						// FIXME: setInterval 제거 - 무한 반복 호출 버그 수정
						// 한 번만 dispatch하고 observer를 일시적으로 중지
						dispatch('visible');
						observer.unobserve(loaderElement); // Stop observing until content is loaded
						
						// 컨텐츠 로드 후 다시 observe 시작 (약간의 지연 후)
						setTimeout(() => {
							if (loaderElement && observer) {
								observer.observe(loaderElement);
							}
						}, 500); // 500ms 후 다시 observe 시작
					}
				});
			},
			{
				root: null, // viewport
				rootMargin: '0px',
				threshold: 0.1 // When 10% of the loader is visible
			}
		);

		observer.observe(loaderElement);
	});

	onDestroy(() => {
		if (observer) {
			observer.disconnect();
		}
	});
</script>

<div bind:this={loaderElement}>
	<slot />
</div>
