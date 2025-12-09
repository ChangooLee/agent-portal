<script lang="ts">
	import Evaluations from '$lib/components/admin/Evaluations.svelte';
</script>

<div class="min-h-full bg-gray-950 text-slate-50">
	<!-- Hero Section -->
	<div class="relative overflow-hidden border-b border-slate-800/50">
		<div class="absolute inset-0 bg-gradient-to-br from-amber-600/5 via-transparent to-yellow-600/5"></div>
		<div class="absolute inset-0 bg-[linear-gradient(rgba(245,158,11,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(245,158,11,0.03)_1px,transparent_1px)] bg-[size:64px_64px]"></div>
		
		<div class="relative px-6 py-8 text-center">
			<h1 class="text-3xl md:text-4xl font-bold mb-3 text-white">
				🏆 리더보드
			</h1>
			<p class="text-base text-amber-200/80">
				모델과 에이전트 성능을 한눈에 비교하세요.
			</p>
		</div>
	</div>

	<div class="px-6 py-8">
		<div class="bg-slate-900/80 border border-slate-800/50 rounded-2xl shadow-xl shadow-black/20 p-6">
			<Evaluations />
		</div>
	</div>
</div>
