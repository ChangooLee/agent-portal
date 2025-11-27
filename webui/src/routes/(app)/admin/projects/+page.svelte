<script lang="ts">
	import { onMount, getContext } from 'svelte';
	import { user, WEBUI_NAME } from '$lib/stores';
	import Plus from '$lib/components/icons/Plus.svelte';
	import FolderOpen from '$lib/components/icons/FolderOpen.svelte';
	import Pencil from '$lib/components/icons/Pencil.svelte';
	import GarbageBin from '$lib/components/icons/GarbageBin.svelte';

	const i18n = getContext('i18n');

	interface Project {
		id: string;
		name: string;
		description: string | null;
		default_model: string | null;
		settings: any;
		created_at: string;
		updated_at: string;
	}

	let projects: Project[] = [];
	let loading = true;
	let error: string | null = null;

	// Modal state
	let showModal = false;
	let modalMode: 'create' | 'edit' = 'create';
	let editingProject: Project | null = null;

	// Form state
	let formName = '';
	let formDescription = '';
	let formDefaultModel = '';

	const API_BASE = 'http://localhost:8000/api/projects';

	async function loadProjects() {
		loading = true;
		error = null;
		try {
			const response = await fetch(API_BASE);
			if (!response.ok) {
				throw new Error(`Failed to load projects: ${response.statusText}`);
			}
			const data = await response.json();
			projects = data.projects;
		} catch (e: any) {
			error = e.message;
			console.error('Failed to load projects:', e);
		} finally {
			loading = false;
		}
	}

	function openCreateModal() {
		modalMode = 'create';
		editingProject = null;
		formName = '';
		formDescription = '';
		formDefaultModel = '';
		showModal = true;
	}

	function openEditModal(project: Project) {
		modalMode = 'edit';
		editingProject = project;
		formName = project.name;
		formDescription = project.description || '';
		formDefaultModel = project.default_model || '';
		showModal = true;
	}

	function closeModal() {
		showModal = false;
		editingProject = null;
	}

	async function handleSubmit() {
		try {
			const body = {
				name: formName,
				description: formDescription || null,
				default_model: formDefaultModel || null
			};

			if (modalMode === 'create') {
				const response = await fetch(API_BASE, {
					method: 'POST',
					headers: { 'Content-Type': 'application/json' },
					body: JSON.stringify(body)
				});
				if (!response.ok) {
					throw new Error(`Failed to create project: ${response.statusText}`);
				}
			} else if (editingProject) {
				const response = await fetch(`${API_BASE}/${editingProject.id}`, {
					method: 'PUT',
					headers: { 'Content-Type': 'application/json' },
					body: JSON.stringify(body)
				});
				if (!response.ok) {
					throw new Error(`Failed to update project: ${response.statusText}`);
				}
			}

			closeModal();
			await loadProjects();
		} catch (e: any) {
			error = e.message;
			console.error('Failed to save project:', e);
		}
	}

	async function deleteProject(project: Project) {
		if (!confirm(`Are you sure you want to delete "${project.name}"?`)) {
			return;
		}

		try {
			const response = await fetch(`${API_BASE}/${project.id}`, {
				method: 'DELETE'
			});
			if (!response.ok) {
				throw new Error(`Failed to delete project: ${response.statusText}`);
			}
			await loadProjects();
		} catch (e: any) {
			error = e.message;
			console.error('Failed to delete project:', e);
		}
	}

	function formatDate(dateStr: string): string {
		return new Date(dateStr).toLocaleDateString('ko-KR', {
			year: 'numeric',
			month: 'short',
			day: 'numeric'
		});
	}

	onMount(() => {
		loadProjects();
	});
</script>

<svelte:head>
	<title>Projects - {$WEBUI_NAME}</title>
</svelte:head>

<div class="flex flex-col w-full h-full min-h-screen p-6">
	<!-- Hero Section -->
	<div
		class="relative mb-6 overflow-hidden rounded-2xl bg-gradient-to-br from-blue-500/10 via-cyan-500/10 to-teal-500/10 dark:from-blue-400/5 dark:via-cyan-400/5 dark:to-teal-400/5"
	>
		<div class="absolute inset-0 bg-white/40 dark:bg-gray-900/40 backdrop-blur-xl"></div>

		<div class="relative px-8 py-8">
			<!-- Badge -->
			<div
				class="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-blue-500/10 dark:bg-blue-400/10 text-blue-600 dark:text-blue-400 text-sm font-medium mb-3 backdrop-blur-sm border border-blue-500/20 dark:border-blue-400/20"
			>
				<FolderOpen className="size-4" />
				<span>Project Management</span>
			</div>

			<!-- Title -->
			<h1 class="text-3xl font-bold text-gray-900 dark:text-white mb-3">Projects</h1>

			<!-- Description -->
			<p class="text-base text-gray-600 dark:text-gray-300 max-w-3xl">
				프로젝트를 생성하고 관리하세요. 각 프로젝트는 독립적인 모니터링 및 분석 단위입니다.
			</p>

			<!-- Stats -->
			<div class="flex items-center gap-6 mt-6">
				<div
					class="bg-white/60 dark:bg-gray-800/60 backdrop-blur-sm rounded-xl px-6 py-4 border border-white/20 dark:border-gray-700/20"
				>
					<div class="text-2xl font-bold text-blue-600 dark:text-blue-400">{projects.length}</div>
					<div class="text-sm text-gray-600 dark:text-gray-400">Total Projects</div>
				</div>
			</div>
		</div>
	</div>

	<!-- Actions -->
	<div class="flex justify-between items-center mb-6">
		<div class="text-lg font-semibold text-gray-800 dark:text-gray-200">All Projects</div>
		<button
			on:click={openCreateModal}
			class="flex items-center gap-2 px-4 py-2 rounded-xl bg-gradient-to-br from-blue-500 to-cyan-500 text-white font-medium hover:from-blue-600 hover:to-cyan-600 transition-all duration-200 shadow-lg shadow-blue-500/25"
		>
			<Plus className="size-4" />
			<span>New Project</span>
		</button>
	</div>

	<!-- Error Message -->
	{#if error}
		<div
			class="mb-6 p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-600 dark:text-red-400"
		>
			{error}
		</div>
	{/if}

	<!-- Loading State -->
	{#if loading}
		<div class="flex items-center justify-center py-12">
			<div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
		</div>
	{:else if projects.length === 0}
		<!-- Empty State -->
		<div
			class="flex flex-col items-center justify-center py-16 bg-white/60 dark:bg-gray-800/60 backdrop-blur-sm rounded-2xl border border-white/20 dark:border-gray-700/20"
		>
			<FolderOpen className="size-16 text-gray-400 mb-4" />
			<h3 class="text-lg font-semibold text-gray-700 dark:text-gray-300 mb-2">No projects yet</h3>
			<p class="text-gray-500 dark:text-gray-400 mb-6">
				Create your first project to start monitoring.
			</p>
			<button
				on:click={openCreateModal}
				class="flex items-center gap-2 px-4 py-2 rounded-xl bg-blue-500 text-white font-medium hover:bg-blue-600 transition-colors"
			>
				<Plus className="size-4" />
				<span>Create Project</span>
			</button>
		</div>
	{:else}
		<!-- Projects Grid -->
		<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
			{#each projects as project}
				<div
					class="bg-white/60 dark:bg-gray-800/60 backdrop-blur-sm rounded-xl p-6 border border-white/20 dark:border-gray-700/20 hover:shadow-lg transition-all duration-200"
				>
					<div class="flex items-start justify-between mb-4">
						<div
							class="w-10 h-10 rounded-lg bg-gradient-to-br from-blue-500/20 to-cyan-500/20 flex items-center justify-center"
						>
							<FolderOpen className="size-5 text-blue-600 dark:text-blue-400" />
						</div>
						<div class="flex items-center gap-1">
							<button
								on:click={() => openEditModal(project)}
								class="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
								title="Edit"
							>
								<Pencil className="size-4 text-gray-500 dark:text-gray-400" />
							</button>
							<button
								on:click={() => deleteProject(project)}
								class="p-2 rounded-lg hover:bg-red-100 dark:hover:bg-red-900/30 transition-colors"
								title="Delete"
							>
								<GarbageBin className="size-4 text-red-500 dark:text-red-400" />
							</button>
						</div>
					</div>

					<h3 class="text-lg font-semibold text-gray-900 dark:text-white mb-2">{project.name}</h3>

					{#if project.description}
						<p class="text-sm text-gray-600 dark:text-gray-400 mb-4 line-clamp-2">
							{project.description}
						</p>
					{:else}
						<p class="text-sm text-gray-400 dark:text-gray-500 mb-4 italic">No description</p>
					{/if}

					<div class="flex items-center justify-between text-xs text-gray-500 dark:text-gray-400">
						<span>ID: {project.id.slice(0, 8)}...</span>
						<span>{formatDate(project.created_at)}</span>
					</div>
				</div>
			{/each}
		</div>
	{/if}
</div>

<!-- Modal -->
{#if showModal}
	<div
		class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm"
		on:click|self={closeModal}
	>
		<div
			class="bg-white dark:bg-gray-800 rounded-2xl p-6 w-full max-w-md shadow-2xl border border-gray-200 dark:border-gray-700"
		>
			<h2 class="text-xl font-bold text-gray-900 dark:text-white mb-6">
				{modalMode === 'create' ? 'Create New Project' : 'Edit Project'}
			</h2>

			<form on:submit|preventDefault={handleSubmit} class="space-y-4">
				<div>
					<label
						for="name"
						class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
					>
						Project Name *
					</label>
					<input
						type="text"
						id="name"
						bind:value={formName}
						required
						class="w-full px-4 py-2 rounded-xl border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
						placeholder="My Project"
					/>
				</div>

				<div>
					<label
						for="description"
						class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
					>
						Description
					</label>
					<textarea
						id="description"
						bind:value={formDescription}
						rows="3"
						class="w-full px-4 py-2 rounded-xl border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
						placeholder="Project description..."
					></textarea>
				</div>

				<div>
					<label
						for="defaultModel"
						class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
					>
						Default Model
					</label>
					<input
						type="text"
						id="defaultModel"
						bind:value={formDefaultModel}
						class="w-full px-4 py-2 rounded-xl border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
						placeholder="gpt-4"
					/>
				</div>

				<div class="flex justify-end gap-3 mt-6">
					<button
						type="button"
						on:click={closeModal}
						class="px-4 py-2 rounded-xl border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
					>
						Cancel
					</button>
					<button
						type="submit"
						class="px-4 py-2 rounded-xl bg-blue-500 text-white font-medium hover:bg-blue-600 transition-colors"
					>
						{modalMode === 'create' ? 'Create' : 'Save Changes'}
					</button>
				</div>
			</form>
		</div>
	</div>
{/if}

