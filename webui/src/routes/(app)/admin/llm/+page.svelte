<script lang="ts">
	import { onMount } from 'svelte';
	
	// Types
	interface Provider {
		id: string;
		name: string;
		description: string;
		color: string;
		prefix: string;
		requires_api_key: boolean;
		default_api_base?: string;
	}
	
	interface Model {
		model_id: string;
		model_name: string;
		provider: string;
		model: string;
		api_base?: string;
		max_tokens?: number;
		input_cost_per_token?: number;
		output_cost_per_token?: number;
		mode?: string;
		db_model: boolean;
		litellm_params?: Record<string, unknown>;
	}
	
	// State
	let loading = true;
	let error = '';
	let providers: Provider[] = [];
	let models: Model[] = [];
	let selectedProvider = 'all';
	let showAddModal = false;
	let showEditModal = false;
	let editingModel: Model | null = null;
	let testingModel: string | null = null;
	let testResult: { success: boolean; message: string } | null = null;
	
	// Form state
	let formData = {
		model_name: '',
		provider: '',
		model: '',
		api_key: '',
		api_base: '',
		max_tokens: '',
		timeout: '60',
		rpm: '',
		tpm: ''
	};
	
	// Stats
	$: totalModels = models.length;
	$: activeProviders = [...new Set(models.map(m => m.provider))].length;
	$: dbModels = models.filter(m => m.db_model).length;
	
	$: heroStats = [
		{ label: '등록된 모델', value: totalModels, hint: 'LiteLLM에 등록된 총 모델 수' },
		{ label: '활성 Provider', value: activeProviders, hint: '사용 중인 Provider 수' },
		{ label: 'DB 모델', value: dbModels, hint: 'DB에 저장된 동적 모델 수' }
	];
	
	$: filteredModels = selectedProvider === 'all' 
		? models 
		: models.filter(m => m.provider === selectedProvider);
	
	// Load data
	async function loadData() {
		try {
			loading = true;
			error = '';
			
			const [providersRes, modelsRes] = await Promise.all([
				fetch('/api/llm/providers'),
				fetch('/api/llm/models')
			]);
			
			if (!providersRes.ok) throw new Error('Failed to fetch providers');
			if (!modelsRes.ok) throw new Error('Failed to fetch models');
			
			providers = await providersRes.json();
			const modelsData = await modelsRes.json();
			models = modelsData.models || [];
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load data';
		} finally {
			loading = false;
		}
	}
	
	// Add model
	async function addModel() {
		try {
			const payload = {
				model_name: formData.model_name,
				litellm_params: {
					model: formData.model,
					api_key: formData.api_key || undefined,
					api_base: formData.api_base || undefined,
					timeout: formData.timeout ? parseInt(formData.timeout) : undefined,
					max_tokens: formData.max_tokens ? parseInt(formData.max_tokens) : undefined,
					rpm: formData.rpm ? parseInt(formData.rpm) : undefined,
					tpm: formData.tpm ? parseInt(formData.tpm) : undefined
				}
			};
			
			const response = await fetch('/api/llm/models', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify(payload)
			});
			
			if (!response.ok) {
				const err = await response.json();
				throw new Error(err.detail || 'Failed to add model');
			}
			
			showAddModal = false;
			resetForm();
			await loadData();
		} catch (e) {
			alert(e instanceof Error ? e.message : 'Failed to add model');
		}
	}
	
	// Update model
	async function updateModel() {
		if (!editingModel) return;
		
		try {
			const payload = {
				model_name: formData.model_name,
				litellm_params: {
					model: formData.model,
					api_key: formData.api_key || undefined,
					api_base: formData.api_base || undefined,
					timeout: formData.timeout ? parseInt(formData.timeout) : undefined,
					max_tokens: formData.max_tokens ? parseInt(formData.max_tokens) : undefined
				}
			};
			
			const response = await fetch(`/api/llm/models/${editingModel.model_id}`, {
				method: 'PATCH',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify(payload)
			});
			
			if (!response.ok) {
				const err = await response.json();
				throw new Error(err.detail || 'Failed to update model');
			}
			
			showEditModal = false;
			editingModel = null;
			resetForm();
			await loadData();
		} catch (e) {
			alert(e instanceof Error ? e.message : 'Failed to update model');
		}
	}
	
	// Delete model
	async function deleteModel(modelId: string) {
		if (!confirm('정말로 이 모델을 삭제하시겠습니까?')) return;
		
		try {
			const response = await fetch(`/api/llm/models/${modelId}`, {
				method: 'DELETE'
			});
			
			if (!response.ok) {
				const err = await response.json();
				throw new Error(err.detail || 'Failed to delete model');
			}
			
			await loadData();
		} catch (e) {
			alert(e instanceof Error ? e.message : 'Failed to delete model');
		}
	}
	
	// Test model
	async function testModel(modelId: string) {
		try {
			testingModel = modelId;
			testResult = null;
			
			const response = await fetch(`/api/llm/models/${modelId}/test`, {
				method: 'POST'
			});
			
			const result = await response.json();
			testResult = {
				success: result.success,
				message: result.success 
					? `응답: "${result.response}" (${result.usage?.total_tokens || 0} tokens)`
					: `오류: ${result.error}`
			};
		} catch (e) {
			testResult = {
				success: false,
				message: e instanceof Error ? e.message : 'Test failed'
			};
		} finally {
			testingModel = null;
		}
	}
	
	// Open edit modal
	function openEditModal(model: Model) {
		editingModel = model;
		formData = {
			model_name: model.model_name,
			provider: model.provider,
			model: model.model,
			api_key: '',
			api_base: model.api_base || '',
			max_tokens: model.max_tokens?.toString() || '',
			timeout: '60',
			rpm: '',
			tpm: ''
		};
		showEditModal = true;
	}
	
	// Reset form
	function resetForm() {
		formData = {
			model_name: '',
			provider: '',
			model: '',
			api_key: '',
			api_base: '',
			max_tokens: '',
			timeout: '60',
			rpm: '',
			tpm: ''
		};
	}
	
	// Get provider color
	function getProviderColor(providerId: string): string {
		const provider = providers.find(p => p.id === providerId);
		return provider?.color || '#6b7280';
	}
	
	// Get provider name
	function getProviderName(providerId: string): string {
		const provider = providers.find(p => p.id === providerId);
		return provider?.name || providerId;
	}
	
	onMount(() => {
		loadData();
	});
</script>

<div class="min-h-full bg-gray-950 text-slate-50">
	<!-- Hero Section -->
	<div class="relative overflow-hidden border-b border-slate-800/50">
		<div class="absolute inset-0 bg-gradient-to-br from-blue-600/5 via-transparent to-cyan-600/5"></div>
		<div class="absolute inset-0 bg-[linear-gradient(rgba(59,130,246,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(59,130,246,0.03)_1px,transparent_1px)] bg-[size:64px_64px]"></div>
		
		<div class="relative px-6 py-12">
			<div class="flex flex-wrap items-center justify-between gap-4 mb-4">
				<h1 class="text-4xl md:text-5xl font-bold">
					<span class="bg-gradient-to-r from-white via-slate-200 to-slate-400 bg-clip-text text-transparent">
						🧠 LLM 관리
					</span>
				</h1>
				<button
					on:click={() => { resetForm(); showAddModal = true; }}
					class="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-medium shadow-lg shadow-blue-500/25 hover:shadow-xl transition-all duration-300"
				>
					<svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
					</svg>
					모델 추가
				</button>
			</div>
			<p class="text-lg text-slate-400 max-w-2xl mb-8">
				LiteLLM을 통해 다양한 LLM Provider와 모델을 관리합니다.
			</p>
			
			<!-- Stats Cards -->
			<div class="grid grid-cols-2 md:grid-cols-3 gap-4">
				{#each heroStats as stat}
					<div class="bg-slate-900/80 border border-slate-800/50 rounded-xl p-4 shadow-lg shadow-black/20">
						<div class="text-2xl font-bold text-white">
							{stat.value}개
						</div>
						<div class="text-xs text-gray-500 dark:text-gray-400">{stat.label}</div>
					</div>
				{/each}
			</div>
		</div>
	</div>
	
	<div class="px-6 py-8 space-y-6">
		<!-- Provider Filter -->
		<div class="bg-slate-900/80 border border-slate-800/50 rounded-2xl shadow-lg shadow-black/20 p-4">
			<div class="flex flex-wrap gap-2">
				<button
					on:click={() => selectedProvider = 'all'}
					class="px-4 py-2 rounded-xl text-sm font-medium transition-all duration-200
						{selectedProvider === 'all'
							? 'bg-blue-600 text-white'
							: 'bg-slate-800 text-slate-300 hover:bg-slate-700'}"
				>
					전체
				</button>
				{#each [...new Set(models.map(m => m.provider))] as providerId}
					<button
						on:click={() => selectedProvider = providerId}
						class="px-4 py-2 rounded-xl text-sm font-medium transition-all duration-200 flex items-center gap-2
							{selectedProvider === providerId
								? 'bg-blue-600 text-white'
								: 'bg-slate-800 text-slate-300 hover:bg-slate-700'}"
					>
						<span
							class="w-2 h-2 rounded-full"
							style="background-color: {getProviderColor(providerId)}"
						></span>
						{getProviderName(providerId)}
					</button>
				{/each}
			</div>
		</div>
		
		<!-- Models Table -->
		<div class="bg-slate-900/80 border border-slate-800/50 rounded-2xl shadow-xl shadow-black/20 overflow-hidden">
		{#if loading}
			<div class="p-8 text-center text-gray-500">로딩 중...</div>
		{:else if error}
			<div class="p-8 text-center text-red-500">{error}</div>
		{:else if filteredModels.length === 0}
			<div class="p-8 text-center text-gray-500">등록된 모델이 없습니다.</div>
		{:else}
			<table class="w-full">
				<thead class="bg-gray-50/50 dark:bg-gray-700/50">
					<tr>
						<th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">모델명</th>
						<th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">Provider</th>
						<th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">모델 ID</th>
						<th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">API Base</th>
						<th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">타입</th>
						<th class="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">작업</th>
					</tr>
				</thead>
				<tbody class="divide-y divide-gray-200/50 dark:divide-gray-700/50">
					{#each filteredModels as model}
						<tr class="hover:bg-gray-50/50 dark:hover:bg-gray-700/30 transition-colors">
							<td class="px-6 py-4 whitespace-nowrap">
								<div class="font-medium text-gray-900 dark:text-white">{model.model_name}</div>
							</td>
							<td class="px-6 py-4 whitespace-nowrap">
								<div class="flex items-center gap-2">
									<span
										class="w-2 h-2 rounded-full"
										style="background-color: {getProviderColor(model.provider)}"
									></span>
									<span class="text-gray-600 dark:text-gray-300">{getProviderName(model.provider)}</span>
								</div>
							</td>
							<td class="px-6 py-4">
								<code class="text-xs bg-gray-100 dark:bg-gray-700 px-2 py-1 rounded text-gray-800 dark:text-gray-200">
									{model.model}
								</code>
							</td>
							<td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
								{model.api_base || '-'}
							</td>
							<td class="px-6 py-4 whitespace-nowrap">
								{#if model.db_model}
									<span class="px-2 py-1 text-xs rounded-full bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-300">DB</span>
								{:else}
									<span class="px-2 py-1 text-xs rounded-full bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400">Config</span>
								{/if}
							</td>
							<td class="px-6 py-4 whitespace-nowrap text-right">
								<div class="flex items-center justify-end gap-2">
									<button
										on:click={() => testModel(model.model_name)}
										disabled={testingModel === model.model_name}
										class="px-3 py-1 text-xs rounded-lg bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 hover:bg-blue-200 dark:hover:bg-blue-900/50 transition-colors disabled:opacity-50"
									>
										{testingModel === model.model_name ? '테스트 중...' : '테스트'}
									</button>
									{#if model.db_model}
										<button
											on:click={() => openEditModal(model)}
											class="px-3 py-1 text-xs rounded-lg bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
										>
											수정
										</button>
										<button
											on:click={() => deleteModel(model.model_id)}
											class="px-3 py-1 text-xs rounded-lg bg-red-100 dark:bg-red-900/30 text-red-700 dark:text-red-300 hover:bg-red-200 dark:hover:bg-red-900/50 transition-colors"
										>
											삭제
										</button>
									{/if}
								</div>
							</td>
						</tr>
					{/each}
				</tbody>
			</table>
		{/if}
	</div>
	
	<!-- Test Result Toast -->
	{#if testResult}
		<div class="fixed bottom-4 right-4 max-w-sm p-4 rounded-xl shadow-lg {testResult.success ? 'bg-green-500' : 'bg-red-500'} text-white">
			<div class="flex items-start gap-3">
				<div class="flex-1">
					<div class="font-medium">{testResult.success ? '테스트 성공' : '테스트 실패'}</div>
					<div class="text-sm text-white/80">{testResult.message}</div>
				</div>
				<button on:click={() => testResult = null} class="text-white/80 hover:text-white">
					<svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
					</svg>
				</button>
			</div>
		</div>
	{/if}
</div>

</div>

<!-- Add Model Modal -->
{#if showAddModal}
<div class="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
	<div class="bg-white dark:bg-gray-800 rounded-2xl shadow-xl max-w-2xl w-full max-h-[90vh] overflow-hidden">
		<!-- Header -->
		<div class="px-6 py-4 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
			<h2 class="text-lg font-semibold text-gray-900 dark:text-white">새 모델 추가</h2>
			<button on:click={() => showAddModal = false} class="text-gray-500 hover:text-gray-700 dark:hover:text-gray-300">
				<svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
				</svg>
			</button>
		</div>
		
		<!-- Content -->
		<div class="p-6 space-y-4 overflow-y-auto max-h-[60vh]">
			<!-- Provider Selection -->
			<div>
				<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Provider</label>
				<select
					bind:value={formData.provider}
					on:change={() => {
						const provider = providers.find(p => p.id === formData.provider);
						if (provider?.default_api_base) {
							formData.api_base = provider.default_api_base;
						}
						formData.model = provider?.prefix || '';
					}}
					class="w-full px-4 py-2 rounded-xl border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary focus:border-transparent"
				>
					<option value="">Provider 선택...</option>
					{#each providers as provider}
						<option value={provider.id}>{provider.name} - {provider.description}</option>
					{/each}
				</select>
			</div>
			
			<!-- Model Name -->
			<div>
				<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">모델 표시명</label>
				<input
					type="text"
					bind:value={formData.model_name}
					placeholder="예: GPT-4 Turbo"
					class="w-full px-4 py-2 rounded-xl border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary focus:border-transparent"
				/>
			</div>
			
			<!-- Model ID -->
			<div>
				<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">모델 ID (공식 명칭 사용)</label>
				<input
					type="text"
					bind:value={formData.model}
					placeholder="예: openrouter/qwen/qwen3-235b-a22b-2507"
					class="w-full px-4 py-2 rounded-xl border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary focus:border-transparent"
				/>
				<p class="mt-1 text-xs text-gray-500">Provider의 공식 모델 명칭을 사용하세요. 예: qwen/qwen3-235b-a22b-2507</p>
			</div>
			
			<!-- API Key -->
			<div>
				<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">API Key</label>
				<input
					type="password"
					bind:value={formData.api_key}
					placeholder="sk-..."
					class="w-full px-4 py-2 rounded-xl border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary focus:border-transparent"
				/>
			</div>
			
			<!-- API Base -->
			<div>
				<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">API Base URL (선택)</label>
				<input
					type="text"
					bind:value={formData.api_base}
					placeholder="https://api.openai.com/v1"
					class="w-full px-4 py-2 rounded-xl border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary focus:border-transparent"
				/>
			</div>
			
			<!-- Advanced Settings -->
			<details class="group">
				<summary class="cursor-pointer text-sm font-medium text-gray-700 dark:text-gray-300 flex items-center gap-2">
					<svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4 transition-transform group-open:rotate-90" fill="none" viewBox="0 0 24 24" stroke="currentColor">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
					</svg>
					고급 설정
				</summary>
				<div class="mt-4 space-y-4 pl-6">
					<div class="grid grid-cols-2 gap-4">
						<div>
							<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Max Tokens</label>
							<input
								type="number"
								bind:value={formData.max_tokens}
								placeholder="4096"
								class="w-full px-4 py-2 rounded-xl border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary focus:border-transparent"
							/>
						</div>
						<div>
							<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Timeout (초)</label>
							<input
								type="number"
								bind:value={formData.timeout}
								placeholder="60"
								class="w-full px-4 py-2 rounded-xl border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary focus:border-transparent"
							/>
						</div>
					</div>
					<div class="grid grid-cols-2 gap-4">
						<div>
							<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">RPM (요청/분)</label>
							<input
								type="number"
								bind:value={formData.rpm}
								placeholder="60"
								class="w-full px-4 py-2 rounded-xl border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary focus:border-transparent"
							/>
						</div>
						<div>
							<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">TPM (토큰/분)</label>
							<input
								type="number"
								bind:value={formData.tpm}
								placeholder="100000"
								class="w-full px-4 py-2 rounded-xl border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary focus:border-transparent"
							/>
						</div>
					</div>
				</div>
			</details>
		</div>
		
		<!-- Footer -->
		<div class="px-6 py-4 border-t border-gray-200 dark:border-gray-700 flex justify-end gap-3">
			<button
				on:click={() => showAddModal = false}
				class="px-4 py-2 rounded-xl bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
			>
				취소
			</button>
			<button
				on:click={addModel}
				disabled={!formData.model_name || !formData.model}
				class="px-4 py-2 rounded-xl bg-primary text-white hover:bg-primary/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
			>
				추가
			</button>
		</div>
	</div>
</div>
{/if}

<!-- Edit Model Modal -->
{#if showEditModal && editingModel}
<div class="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 flex items-center justify-center p-4">
	<div class="bg-white dark:bg-gray-800 rounded-2xl shadow-xl max-w-2xl w-full max-h-[90vh] overflow-hidden">
		<!-- Header -->
		<div class="px-6 py-4 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
			<h2 class="text-lg font-semibold text-gray-900 dark:text-white">모델 수정</h2>
			<button on:click={() => { showEditModal = false; editingModel = null; }} class="text-gray-500 hover:text-gray-700 dark:hover:text-gray-300">
				<svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
				</svg>
			</button>
		</div>
		
		<!-- Content -->
		<div class="p-6 space-y-4 overflow-y-auto max-h-[60vh]">
			<!-- Model Name -->
			<div>
				<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">모델 표시명</label>
				<input
					type="text"
					bind:value={formData.model_name}
					class="w-full px-4 py-2 rounded-xl border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary focus:border-transparent"
				/>
			</div>
			
			<!-- Model ID -->
			<div>
				<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">모델 ID</label>
				<input
					type="text"
					bind:value={formData.model}
					class="w-full px-4 py-2 rounded-xl border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary focus:border-transparent"
				/>
			</div>
			
			<!-- API Key -->
			<div>
				<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">API Key (변경 시에만 입력)</label>
				<input
					type="password"
					bind:value={formData.api_key}
					placeholder="변경하지 않으려면 비워두세요"
					class="w-full px-4 py-2 rounded-xl border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary focus:border-transparent"
				/>
			</div>
			
			<!-- API Base -->
			<div>
				<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">API Base URL</label>
				<input
					type="text"
					bind:value={formData.api_base}
					class="w-full px-4 py-2 rounded-xl border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary focus:border-transparent"
				/>
			</div>
			
			<!-- Max Tokens -->
			<div>
				<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">Max Tokens</label>
				<input
					type="number"
					bind:value={formData.max_tokens}
					class="w-full px-4 py-2 rounded-xl border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-primary focus:border-transparent"
				/>
			</div>
		</div>
		
		<!-- Footer -->
		<div class="px-6 py-4 border-t border-gray-200 dark:border-gray-700 flex justify-end gap-3">
			<button
				on:click={() => { showEditModal = false; editingModel = null; }}
				class="px-4 py-2 rounded-xl bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
			>
				취소
			</button>
			<button
				on:click={updateModel}
				class="px-4 py-2 rounded-xl bg-primary text-white hover:bg-primary/90 transition-colors"
			>
				저장
			</button>
		</div>
	</div>
</div>
{/if}
