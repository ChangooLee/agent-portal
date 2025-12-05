<script lang="ts">
	import Settings from '$lib/components/admin/Settings.svelte';
</script>

<div class="min-h-full bg-gray-950 text-slate-50">
	<!-- Hero Section -->
	<div class="relative overflow-hidden border-b border-slate-800/50">
		<div class="absolute inset-0 bg-gradient-to-br from-slate-600/5 via-transparent to-zinc-600/5"></div>
		<div class="absolute inset-0 bg-[linear-gradient(rgba(100,116,139,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(100,116,139,0.03)_1px,transparent_1px)] bg-[size:64px_64px]"></div>
		
		<div class="relative px-6 py-16 text-center">
			<h1 class="text-4xl md:text-5xl font-bold mb-4">
				<span class="bg-gradient-to-r from-white via-slate-200 to-slate-400 bg-clip-text text-transparent">
					⚙️ 설정
				</span>
			</h1>
			<p class="text-lg text-slate-400 max-w-2xl mx-auto">
				플랫폼 전역 설정을 안전하게 관리하세요.
			</p>
		</div>
	</div>

	<div class="px-6 py-8">
		<div class="bg-slate-900/80 border border-slate-800/50 rounded-2xl shadow-xl shadow-black/20 p-6">
			<Settings />
		</div>
	</div>
</div>
