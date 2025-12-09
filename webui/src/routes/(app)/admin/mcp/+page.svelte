<script lang="ts">
	import { getContext, onMount } from 'svelte';
	import { user, WEBUI_NAME } from '$lib/stores';
	import { goto } from '$app/navigation';
	import Cube from '$lib/components/icons/Cube.svelte';
	import Plus from '$lib/components/icons/Plus.svelte';
	import GarbageBin from '$lib/components/icons/GarbageBin.svelte';
	import Pencil from '$lib/components/icons/Pencil.svelte';
	import ArrowPath from '$lib/components/icons/ArrowPath.svelte';
	import Check from '$lib/components/icons/Check.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import UsersSolid from '$lib/components/icons/UsersSolid.svelte';
	import { toast } from 'svelte-sonner';
	import { getUsers } from '$lib/apis/users';
	import { getGroups } from '$lib/apis/groups';

	const i18n = getContext('i18n');

	// State
	interface MCPServer {
		id: string;
		name: string;
		description: string | null;
		endpoint_url: string;
		transport_type: string;
		auth_type: string;
		auth_config: any;
		enabled: boolean;
		health_status: string;
		last_health_check: string | null;
		created_at: string;
		updated_at: string;
	}

	interface MCPTool {
		id: string;
		tool_name: string;
		tool_description: string | null;
		input_schema: any;
	}

	interface MCPPermission {
		id: string;
		server_id: string;
		permission_type: 'user' | 'group';
		target_id: string;
		granted_by: string | null;
		granted_at: string;
	}

	interface WebUIUser {
		id: string;
		name: string;
		email: string;
		role: string;
		profile_image_url: string;
	}

	interface WebUIGroup {
		id: string;
		name: string;
		description: string;
		user_ids: string[];
	}

	let servers: MCPServer[] = [];
	let loading = true;
	let showModal = false;
	let editMode = false;
	let selectedServer: MCPServer | null = null;
	let selectedServerTools: MCPTool[] = [];
	let showToolsModal = false;
	let testingServer: string | null = null;

	// Permission Modal State
	let showPermissionModal = false;
	let permissionServer: MCPServer | null = null;
	let permissionTab: 'users' | 'groups' = 'users';
	let permissions: MCPPermission[] = [];
	let allUsers: WebUIUser[] = [];
	let allGroups: WebUIGroup[] = [];
	let userQuery = '';
	let groupQuery = '';
	let loadingPermissions = false;

	// Form state
	let formData = {
		name: '',
		endpoint_url: '',
		description: '',
		transport_type: 'streamable_http',
		auth_type: 'none',
		auth_config: {} as any
	};

	// Stats - reactive to update when servers change
	$: totalServers = servers.length;
	$: enabledServers = servers.filter((s) => s.enabled).length;
	$: healthyServers = servers.filter((s) => s.health_status === 'healthy').length;

	// heroStats must be reactive to reflect updated server counts
	$: heroStats = [
		{ label: '등록된 서버', value: totalServers, hint: 'MCP 서버 총 개수' },
		{ label: '활성화', value: enabledServers, hint: '현재 활성화된 서버' },
		{ label: '정상 상태', value: healthyServers, hint: '헬스체크 통과' }
	];

	onMount(async () => {
		if ($user?.role !== 'admin') {
			await goto('/');
			return;
		}
		await loadServers();
	});

	async function loadServers() {
		loading = true;
		try {
			const response = await fetch('/api/mcp/servers');
			if (!response.ok) throw new Error('Failed to load servers');
			const data = await response.json();
			servers = data.servers || [];
		} catch (error) {
			console.error('Failed to load MCP servers:', error);
			toast.error('MCP 서버 목록을 불러오는데 실패했습니다.');
		} finally {
			loading = false;
		}
	}

	function openCreateModal() {
		editMode = false;
		formData = {
			name: '',
			endpoint_url: '',
			description: '',
			transport_type: 'streamable_http',
			auth_type: 'none',
			auth_config: {}
		};
		showModal = true;
	}

	function openEditModal(server: MCPServer) {
		editMode = true;
		selectedServer = server;
		formData = {
			name: server.name,
			endpoint_url: server.endpoint_url,
			description: server.description || '',
			transport_type: server.transport_type,
			auth_type: server.auth_type,
			auth_config: server.auth_config || {}
		};
		showModal = true;
	}

	function closeModal() {
		showModal = false;
		selectedServer = null;
	}

	async function handleSubmit() {
		try {
			if (editMode && selectedServer) {
				// Update
				const response = await fetch(`/api/mcp/servers/${selectedServer.id}`, {
					method: 'PUT',
					headers: { 'Content-Type': 'application/json' },
					body: JSON.stringify({
						name: formData.name,
						endpoint_url: formData.endpoint_url,
						description: formData.description || null,
						transport_type: formData.transport_type,
						auth_type: formData.auth_type,
						auth_config: formData.auth_type !== 'none' ? formData.auth_config : null
					})
				});
				if (!response.ok) throw new Error('Failed to update server');
				toast.success('MCP 서버가 수정되었습니다.');
			} else {
				// Create
				const response = await fetch('/api/mcp/servers', {
					method: 'POST',
					headers: { 'Content-Type': 'application/json' },
					body: JSON.stringify(formData)
				});
				if (!response.ok) throw new Error('Failed to create server');
				toast.success('MCP 서버가 등록되었습니다.');
			}
			closeModal();
			await loadServers();
		} catch (error) {
			console.error('Failed to save server:', error);
			toast.error('서버 저장에 실패했습니다.');
		}
	}

	async function deleteServer(server: MCPServer) {
		if (!confirm(`"${server.name}" 서버를 삭제하시겠습니까?`)) return;

		try {
			const response = await fetch(`/api/mcp/servers/${server.id}`, {
				method: 'DELETE'
			});
			if (!response.ok) throw new Error('Failed to delete server');
			toast.success('MCP 서버가 삭제되었습니다.');
			await loadServers();
		} catch (error) {
			console.error('Failed to delete server:', error);
			toast.error('서버 삭제에 실패했습니다.');
		}
	}

	async function testServer(server: MCPServer) {
		testingServer = server.id;
		try {
			const response = await fetch(`/api/mcp/servers/${server.id}/test`, {
				method: 'POST'
			});
			const result = await response.json();

			if (result.success) {
				toast.success(`연결 성공! ${result.tools?.length || 0}개 도구 발견 (${result.latency_ms}ms)`);
			} else {
				toast.error(`연결 실패: ${result.message}`);
			}
			await loadServers();
		} catch (error) {
			console.error('Failed to test server:', error);
			toast.error('연결 테스트에 실패했습니다.');
		} finally {
			testingServer = null;
		}
	}

	async function toggleServer(server: MCPServer) {
		try {
			const response = await fetch(`/api/mcp/servers/${server.id}`, {
				method: 'PUT',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ enabled: !server.enabled })
			});
			if (!response.ok) throw new Error('Failed to toggle server');
			toast.success(server.enabled ? '서버가 비활성화되었습니다.' : '서버가 활성화되었습니다.');
			await loadServers();
		} catch (error) {
			console.error('Failed to toggle server:', error);
			toast.error('상태 변경에 실패했습니다.');
		}
	}

	async function viewTools(server: MCPServer) {
		try {
			const response = await fetch(`/api/mcp/servers/${server.id}/tools`);
			if (!response.ok) throw new Error('Failed to load tools');
			selectedServerTools = await response.json();
			selectedServer = server;
			showToolsModal = true;
		} catch (error) {
			console.error('Failed to load tools:', error);
			toast.error('도구 목록을 불러오는데 실패했습니다.');
		}
	}

	function getHealthBadgeClass(status: string) {
		switch (status) {
			case 'healthy':
				return 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30';
			case 'unhealthy':
				return 'bg-red-500/20 text-red-400 border border-red-500/30';
			default:
				return 'bg-gray-100 text-gray-800 dark:bg-gray-700/30 dark:text-gray-400';
		}
	}

	function getHealthLabel(status: string) {
		switch (status) {
			case 'healthy':
				return '정상';
			case 'unhealthy':
				return '오류';
			default:
				return '미확인';
		}
	}

	function copyToClipboard(text: string) {
		navigator.clipboard.writeText(text);
		toast.success('클립보드에 복사되었습니다.');
	}

	// Permission Management Functions
	async function openPermissionModal(server: MCPServer) {
		permissionServer = server;
		showPermissionModal = true;
		loadingPermissions = true;
		permissionTab = 'users';
		userQuery = '';
		groupQuery = '';

		try {
			// Load permissions, users, and groups in parallel
			const [permissionsRes, usersRes, groupsRes] = await Promise.all([
				fetch(`/api/mcp/servers/${server.id}/permissions`).then((r) => r.json()),
				getUsers(localStorage.token),
				getGroups(localStorage.token)
			]);
			permissions = permissionsRes || [];
			allUsers = usersRes || [];
			allGroups = groupsRes || [];
		} catch (error) {
			console.error('Failed to load permissions data:', error);
			toast.error('권한 정보를 불러오는데 실패했습니다.');
			permissions = [];
			allUsers = [];
			allGroups = [];
		} finally {
			loadingPermissions = false;
		}
	}

	function closePermissionModal() {
		showPermissionModal = false;
		permissionServer = null;
		permissions = [];
	}

	function hasPermission(type: 'user' | 'group', targetId: string): boolean {
		return permissions.some((p) => p.permission_type === type && p.target_id === targetId);
	}

	function getPermissionId(type: 'user' | 'group', targetId: string): string | null {
		const perm = permissions.find((p) => p.permission_type === type && p.target_id === targetId);
		return perm ? perm.id : null;
	}

	async function togglePermission(type: 'user' | 'group', targetId: string) {
		if (!permissionServer) return;

		const existingPermId = getPermissionId(type, targetId);

		try {
			if (existingPermId) {
				// Revoke permission
				const response = await fetch(
					`/api/mcp/servers/${permissionServer.id}/permissions/${existingPermId}`,
					{ method: 'DELETE' }
				);
				if (!response.ok) throw new Error('Failed to revoke permission');
				permissions = permissions.filter((p) => p.id !== existingPermId);
				toast.success('권한이 회수되었습니다.');
			} else {
				// Grant permission
				const response = await fetch(
					`/api/mcp/servers/${permissionServer.id}/permissions`,
					{
						method: 'POST',
						headers: { 'Content-Type': 'application/json' },
						body: JSON.stringify({
							permission_type: type,
							target_id: targetId
						})
					}
				);
				if (!response.ok) throw new Error('Failed to grant permission');
				const newPerm = await response.json();
				permissions = [...permissions, newPerm];
				toast.success('권한이 부여되었습니다.');
			}
		} catch (error) {
			console.error('Failed to toggle permission:', error);
			toast.error('권한 변경에 실패했습니다.');
		}
	}

	// Filtered lists for search
	$: filteredUsers = allUsers.filter(
		(u) =>
			u.name.toLowerCase().includes(userQuery.toLowerCase()) ||
			u.email.toLowerCase().includes(userQuery.toLowerCase())
	);

	$: filteredGroups = allGroups.filter((g) =>
		g.name.toLowerCase().includes(groupQuery.toLowerCase())
	);

	// Count permissions
	$: userPermissionCount = permissions.filter((p) => p.permission_type === 'user').length;
	$: groupPermissionCount = permissions.filter((p) => p.permission_type === 'group').length;
</script>

<svelte:head>
	<title>MCP | {$WEBUI_NAME}</title>
</svelte:head>

{#if $user?.role !== 'admin'}
	<div class="text-red-500 p-6">
		{$i18n.t('Access Denied: Only administrators can view this page.')}
	</div>
{:else}
	<div class="min-h-full bg-gray-950 text-slate-50">
		<!-- Hero Section -->
		<div class="relative overflow-hidden border-b border-slate-800/50">
			<div class="absolute inset-0 bg-gradient-to-br from-purple-600/5 via-transparent to-pink-600/5"></div>
			<div class="absolute inset-0 bg-[linear-gradient(rgba(168,85,247,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(168,85,247,0.03)_1px,transparent_1px)] bg-[size:64px_64px]"></div>
			
			<div class="relative px-6 py-8">
				<div class="text-center mb-4">
					<h1 class="text-3xl md:text-4xl font-bold text-white mb-3">
						🔌 MCP 서버
					</h1>
					<p class="text-base text-purple-200/80 mb-6">
						MCP 서버를 등록하고 AI 에이전트에서 외부 도구로 활용할 수 있습니다.
					</p>
					<button
						on:click={openCreateModal}
						class="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-purple-600 hover:bg-purple-500 text-white font-medium shadow-lg shadow-purple-500/25 hover:shadow-xl hover:-translate-y-0.5 transition-all duration-300"
					>
						<Plus className="size-5" />
						<span>서버 추가</span>
					</button>
				</div>

				<div class="grid grid-cols-3 gap-4">
					{#each heroStats as stat}
						<div class="bg-slate-900/80 border border-slate-800/50 rounded-xl p-4 shadow-lg shadow-black/20">
							<div class="text-xs font-medium uppercase tracking-wide text-purple-400 mb-1">
								{stat.label}
							</div>
							<div class="text-2xl font-bold text-white">
								{stat.value}개
							</div>
							<div class="text-xs text-slate-500 mt-1">{stat.hint}</div>
						</div>
					{/each}
				</div>
			</div>
		</div>

		<div class="px-6 py-8">
			<!-- Server List -->
			<div class="bg-slate-900/80 border border-slate-800/50 rounded-2xl shadow-xl shadow-black/20 overflow-hidden">
				{#if loading}
					<div class="flex items-center justify-center py-12">
						<div
							class="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-500"
						></div>
					</div>
				{:else if servers.length === 0}
					<div class="text-center py-12">
						<Cube className="size-16 mx-auto text-gray-300 dark:text-gray-600 mb-4" />
						<h3 class="text-lg font-medium text-gray-900 dark:text-gray-100 mb-2">
							등록된 MCP 서버가 없습니다
						</h3>
						<p class="text-gray-500 dark:text-gray-400 mb-4">
							MCP 서버를 추가하여 AI 모델에 외부 도구 기능을 제공하세요.
						</p>
						<button
							on:click={openCreateModal}
							class="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-purple-500 text-white hover:bg-purple-600 transition-colors"
						>
							<Plus className="size-5" />
							<span>첫 번째 서버 추가</span>
						</button>
					</div>
				{:else}
					<div class="overflow-x-auto">
						<table class="w-full">
							<thead class="bg-slate-800/50 border-b border-slate-700/50">
								<tr>
									<th
										class="px-6 py-3 text-left text-xs font-medium text-white uppercase tracking-wider"
										>서버</th
									>
									<th
										class="px-6 py-3 text-left text-xs font-medium text-white uppercase tracking-wider"
										>상태</th
									>
									<th
										class="px-6 py-3 text-left text-xs font-medium text-white uppercase tracking-wider"
										>타입</th
									>
									<th
										class="px-6 py-3 text-right text-xs font-medium text-white uppercase tracking-wider"
										>작업</th
									>
								</tr>
							</thead>
							<tbody class="divide-y divide-slate-800/50">
								{#each servers as server}
									<tr class="border-b border-slate-800/50 hover:bg-slate-800/80 hover:border-purple-500/50 transition-all duration-200">
										<td class="px-6 py-4">
											<div class="flex items-center gap-3">
												<div
													class="p-2 rounded-lg bg-purple-500/20"
												>
													<Cube className="size-5 text-purple-400" />
												</div>
												<div>
													<div class="font-medium text-white">
														{server.name}
													</div>
													<div
														class="text-sm text-slate-400 truncate max-w-xs"
														title={server.endpoint_url}
													>
														{server.endpoint_url}
													</div>
												</div>
											</div>
										</td>
										<td class="px-6 py-4">
											<div class="flex items-center gap-2">
												<span
													class="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium {getHealthBadgeClass(
														server.health_status
													)}"
												>
													{#if server.health_status === 'healthy'}
														<Check className="size-3" />
													{:else if server.health_status === 'unhealthy'}
														<XMark className="size-3" />
													{/if}
													{getHealthLabel(server.health_status)}
												</span>
												{#if !server.enabled}
													<span
														class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-amber-500/20 text-amber-400 border border-amber-500/30"
													>
														비활성화
													</span>
												{/if}
											</div>
										</td>
										<td class="px-6 py-4">
											<span
												class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-500/20 text-blue-400 border border-blue-500/30"
											>
												{server.transport_type}
											</span>
										</td>
										<td class="px-6 py-4">
											<div class="flex items-center justify-end gap-2">
												<button
													on:click={() => testServer(server)}
													disabled={testingServer === server.id}
													class="p-2 text-gray-400 hover:text-green-600 dark:hover:text-green-400 transition-colors disabled:opacity-50"
													title="연결 테스트"
												>
													<ArrowPath
														className="size-4 {testingServer === server.id
															? 'animate-spin'
															: ''}"
													/>
												</button>
												<button
													on:click={() => viewTools(server)}
													class="p-2 text-gray-400 hover:text-blue-600 dark:hover:text-blue-400 transition-colors"
													title="도구 목록"
												>
													<Cube className="size-4" />
												</button>
												<button
													on:click={() => openPermissionModal(server)}
													class="p-2 text-gray-400 hover:text-orange-600 dark:hover:text-orange-400 transition-colors"
													title="권한 관리"
												>
													<UsersSolid className="size-4" />
												</button>
												<button
													on:click={() => toggleServer(server)}
													class="p-2 text-gray-400 hover:text-purple-600 dark:hover:text-purple-400 transition-colors"
													title={server.enabled ? '비활성화' : '활성화'}
												>
													{#if server.enabled}
														<Check className="size-4" />
													{:else}
														<XMark className="size-4" />
													{/if}
												</button>
												<button
													on:click={() => openEditModal(server)}
													class="p-2 text-gray-400 hover:text-blue-600 dark:hover:text-blue-400 transition-colors"
													title="수정"
												>
													<Pencil className="size-4" />
												</button>
												<button
													on:click={() => deleteServer(server)}
													class="p-2 text-gray-400 hover:text-red-600 dark:hover:text-red-400 transition-colors"
													title="삭제"
												>
													<GarbageBin className="size-4" />
												</button>
											</div>
										</td>
									</tr>
								{/each}
							</tbody>
						</table>
					</div>
				{/if}
			</div>
		</div>
	</div>

	<!-- Create/Edit Modal -->
	{#if showModal}
		<div
			class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm"
			on:click={closeModal}
		>
			<div
				class="bg-white dark:bg-gray-800 rounded-2xl shadow-2xl max-w-lg w-full max-h-[90vh] overflow-y-auto"
				on:click|stopPropagation
			>
				<div
					class="sticky top-0 bg-white dark:bg-gray-800 px-6 py-4 border-b border-gray-200 dark:border-gray-700"
				>
					<h2 class="text-xl font-semibold text-gray-900 dark:text-gray-100">
						{editMode ? 'MCP 서버 수정' : 'MCP 서버 추가'}
					</h2>
				</div>

				<form on:submit|preventDefault={handleSubmit} class="p-6 space-y-4">
					<div>
						<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
							서버 이름 <span class="text-red-500">*</span>
						</label>
						<input
							type="text"
							bind:value={formData.name}
							required
							class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-purple-500 focus:border-transparent"
							placeholder="My MCP Server"
						/>
					</div>

					<div>
						<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
							엔드포인트 URL <span class="text-red-500">*</span>
						</label>
						<input
							type="url"
							bind:value={formData.endpoint_url}
							required
							class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-purple-500 focus:border-transparent"
							placeholder="http://localhost:8080"
						/>
					</div>

					<div>
						<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
							설명
						</label>
						<textarea
							bind:value={formData.description}
							rows="2"
							class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-purple-500 focus:border-transparent"
							placeholder="서버 설명 (선택사항)"
						></textarea>
					</div>

					<div class="grid grid-cols-2 gap-4">
						<div>
							<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
								전송 타입
							</label>
							<select
								bind:value={formData.transport_type}
								class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-purple-500 focus:border-transparent"
							>
								<option value="streamable_http">Streamable HTTP</option>
								<option value="sse">SSE</option>
							</select>
						</div>

						<div>
							<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
								인증 타입
							</label>
							<select
								bind:value={formData.auth_type}
								class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-purple-500 focus:border-transparent"
							>
								<option value="none">없음</option>
								<option value="api_key">API Key</option>
								<option value="bearer">Bearer Token</option>
							</select>
						</div>
					</div>

					{#if formData.auth_type === 'api_key'}
						<div class="space-y-3 p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
							<div>
								<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
									API Key
								</label>
								<input
									type="password"
									bind:value={formData.auth_config.api_key}
									class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-purple-500 focus:border-transparent"
									placeholder="API Key"
								/>
							</div>
							<div>
								<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
									헤더 이름
								</label>
								<input
									type="text"
									bind:value={formData.auth_config.header_name}
									class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-purple-500 focus:border-transparent"
									placeholder="X-API-Key"
								/>
							</div>
						</div>
					{:else if formData.auth_type === 'bearer'}
						<div class="p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
							<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
								Bearer Token
							</label>
							<input
								type="password"
								bind:value={formData.auth_config.token}
								class="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-purple-500 focus:border-transparent"
								placeholder="Bearer Token"
							/>
						</div>
					{/if}

					<!-- 보안 안내 -->
					{#if !editMode}
						<div class="flex items-center gap-2 p-3 bg-purple-50 dark:bg-purple-900/20 rounded-lg border border-purple-200 dark:border-purple-700">
							<svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5 text-purple-600 dark:text-purple-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
							</svg>
							<span class="text-sm text-purple-700 dark:text-purple-300">
								<strong>보안 자동 적용:</strong> 모든 MCP 서버는 인증 및 요청 제한이 자동으로 적용됩니다.
							</span>
						</div>
					{/if}

					<div class="flex justify-end gap-3 pt-4">
						<button
							type="button"
							on:click={closeModal}
							class="px-4 py-2 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
						>
							취소
						</button>
						<button
							type="submit"
							class="px-4 py-2 bg-purple-500 text-white rounded-lg hover:bg-purple-600 transition-colors"
						>
							{editMode ? '수정' : '추가'}
						</button>
					</div>
				</form>
			</div>
		</div>
	{/if}

	<!-- Tools Modal -->
	{#if showToolsModal && selectedServer}
		<div
			class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm"
			on:click={() => (showToolsModal = false)}
		>
			<div
				class="bg-white dark:bg-gray-800 rounded-2xl shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto"
				on:click|stopPropagation
			>
				<div
					class="sticky top-0 bg-white dark:bg-gray-800 px-6 py-4 border-b border-gray-200 dark:border-gray-700 flex justify-between items-center"
				>
					<h2 class="text-xl font-semibold text-gray-900 dark:text-gray-100">
						{selectedServer.name} - 도구 목록
					</h2>
					<button
						on:click={() => (showToolsModal = false)}
						class="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
					>
						<XMark className="size-5" />
					</button>
				</div>

				<div class="p-6">
					{#if selectedServerTools.length === 0}
						<div class="text-center py-8 text-gray-500 dark:text-gray-400">
							<Cube className="size-12 mx-auto mb-3 opacity-50" />
							<p>등록된 도구가 없습니다.</p>
							<p class="text-sm mt-1">연결 테스트를 실행하여 도구를 동기화하세요.</p>
						</div>
					{:else}
						<div class="space-y-4">
							{#each selectedServerTools as tool}
								<div
									class="p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg border border-gray-200 dark:border-gray-600"
								>
									<div class="flex items-start justify-between">
										<div>
											<h3 class="font-medium text-gray-900 dark:text-gray-100">
												{tool.tool_name}
											</h3>
											{#if tool.tool_description}
												<p class="text-sm text-gray-600 dark:text-gray-400 mt-1">
													{tool.tool_description}
												</p>
											{/if}
										</div>
									</div>
									{#if tool.input_schema}
										<details class="mt-3">
											<summary
												class="text-sm text-purple-600 dark:text-purple-400 cursor-pointer"
											>
												입력 스키마 보기
											</summary>
											<pre
												class="mt-2 p-3 bg-gray-100 dark:bg-gray-800 rounded text-xs overflow-x-auto">{JSON.stringify(
													tool.input_schema,
													null,
													2
												)}</pre>
										</details>
									{/if}
								</div>
							{/each}
						</div>
					{/if}
				</div>
			</div>
		</div>
	{/if}

	<!-- Permission Modal -->
	{#if showPermissionModal && permissionServer}
		<div
			class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm"
			on:click={closePermissionModal}
		>
			<div
				class="bg-white dark:bg-gray-800 rounded-2xl shadow-2xl max-w-2xl w-full max-h-[90vh] overflow-y-auto"
				on:click|stopPropagation
			>
				<div
					class="sticky top-0 bg-white dark:bg-gray-800 px-6 py-4 border-b border-gray-200 dark:border-gray-700 flex justify-between items-center"
				>
					<div>
						<h2 class="text-xl font-semibold text-gray-900 dark:text-gray-100">
							{permissionServer.name} - 권한 관리
						</h2>
						<p class="text-sm text-gray-500 dark:text-gray-400 mt-1">
							이 MCP 서버에 접근할 수 있는 사용자와 그룹을 관리합니다.
						</p>
					</div>
					<button
						on:click={closePermissionModal}
						class="p-2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
					>
						<XMark className="size-5" />
					</button>
				</div>

				<div class="p-6">
					{#if loadingPermissions}
						<div class="flex items-center justify-center py-12">
							<div class="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-500"></div>
						</div>
					{:else}
						<!-- Tabs -->
						<div class="flex items-center gap-2 mb-6">
							<button
								on:click={() => (permissionTab = 'users')}
								class="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all
								{permissionTab === 'users'
									? 'bg-purple-500 text-white shadow-lg'
									: 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'}"
							>
								<UsersSolid className="size-4" />
								<span>사용자</span>
								{#if userPermissionCount > 0}
									<span
										class="px-1.5 py-0.5 rounded-full text-xs {permissionTab === 'users'
											? 'bg-white/20'
											: 'bg-purple-100 dark:bg-purple-900/30 text-purple-600 dark:text-purple-400'}"
									>
										{userPermissionCount}
									</span>
								{/if}
							</button>
							<button
								on:click={() => (permissionTab = 'groups')}
								class="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all
								{permissionTab === 'groups'
									? 'bg-purple-500 text-white shadow-lg'
									: 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'}"
							>
								<Cube className="size-4" />
								<span>그룹</span>
								{#if groupPermissionCount > 0}
									<span
										class="px-1.5 py-0.5 rounded-full text-xs {permissionTab === 'groups'
											? 'bg-white/20'
											: 'bg-purple-100 dark:bg-purple-900/30 text-purple-600 dark:text-purple-400'}"
									>
										{groupPermissionCount}
									</span>
								{/if}
							</button>
						</div>

						<!-- Users Tab -->
						{#if permissionTab === 'users'}
							<div class="space-y-4">
								<input
									type="text"
									bind:value={userQuery}
									placeholder="사용자 검색..."
									class="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-purple-500 focus:border-transparent"
								/>

								<div class="space-y-2 max-h-80 overflow-y-auto">
									{#if filteredUsers.length === 0}
										<div class="text-center py-8 text-gray-500 dark:text-gray-400">
											<p>사용자를 찾을 수 없습니다.</p>
										</div>
									{:else}
										{#each filteredUsers as user}
											<div
												class="flex items-center justify-between p-3 rounded-lg border {hasPermission(
													'user',
													user.id
												)
													? 'border-purple-300 dark:border-purple-600 bg-purple-50 dark:bg-purple-900/20'
													: 'border-gray-200 dark:border-gray-600 bg-gray-50 dark:bg-gray-700/50'} hover:shadow-sm transition-all"
											>
												<div class="flex items-center gap-3">
													<img
														src={user.profile_image_url || '/user.png'}
														alt={user.name}
														class="w-10 h-10 rounded-full object-cover"
													/>
													<div>
														<div class="font-medium text-gray-900 dark:text-gray-100">
															{user.name}
														</div>
														<div class="text-sm text-gray-500 dark:text-gray-400">
															{user.email}
														</div>
													</div>
													{#if user.role === 'admin'}
														<span
															class="px-2 py-0.5 rounded-full text-xs bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400"
														>
															관리자
														</span>
													{/if}
												</div>
												<button
													on:click={() => togglePermission('user', user.id)}
													class="px-3 py-1.5 rounded-lg text-sm font-medium transition-all {hasPermission(
														'user',
														user.id
													)
														? 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400 hover:bg-red-200 dark:hover:bg-red-900/50'
														: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400 hover:bg-purple-200 dark:hover:bg-purple-900/50'}"
												>
													{hasPermission('user', user.id) ? '권한 회수' : '권한 부여'}
												</button>
											</div>
										{/each}
									{/if}
								</div>
							</div>
						{/if}

						<!-- Groups Tab -->
						{#if permissionTab === 'groups'}
							<div class="space-y-4">
								<input
									type="text"
									bind:value={groupQuery}
									placeholder="그룹 검색..."
									class="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-2 focus:ring-purple-500 focus:border-transparent"
								/>

								<div class="space-y-2 max-h-80 overflow-y-auto">
									{#if filteredGroups.length === 0}
										<div class="text-center py-8 text-gray-500 dark:text-gray-400">
											<p>그룹을 찾을 수 없습니다.</p>
										</div>
									{:else}
										{#each filteredGroups as group}
											<div
												class="flex items-center justify-between p-3 rounded-lg border {hasPermission(
													'group',
													group.id
												)
													? 'border-purple-300 dark:border-purple-600 bg-purple-50 dark:bg-purple-900/20'
													: 'border-gray-200 dark:border-gray-600 bg-gray-50 dark:bg-gray-700/50'} hover:shadow-sm transition-all"
											>
												<div class="flex items-center gap-3">
													<div
														class="w-10 h-10 rounded-full bg-gradient-to-br from-purple-500 to-pink-500 flex items-center justify-center"
													>
														<Cube className="size-5 text-white" />
													</div>
													<div>
														<div class="font-medium text-gray-900 dark:text-gray-100">
															{group.name}
														</div>
														<div class="text-sm text-gray-500 dark:text-gray-400">
															{group.user_ids?.length || 0}명의 멤버
														</div>
													</div>
												</div>
												<button
													on:click={() => togglePermission('group', group.id)}
													class="px-3 py-1.5 rounded-lg text-sm font-medium transition-all {hasPermission(
														'group',
														group.id
													)
														? 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400 hover:bg-red-200 dark:hover:bg-red-900/50'
														: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400 hover:bg-purple-200 dark:hover:bg-purple-900/50'}"
												>
													{hasPermission('group', group.id) ? '권한 회수' : '권한 부여'}
												</button>
											</div>
										{/each}
									{/if}
								</div>
							</div>
						{/if}

						<!-- Info Box -->
						<div
							class="mt-6 flex items-start gap-2 p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-700"
						>
							<svg
								xmlns="http://www.w3.org/2000/svg"
								class="w-5 h-5 text-blue-600 dark:text-blue-400 flex-shrink-0 mt-0.5"
								fill="none"
								viewBox="0 0 24 24"
								stroke="currentColor"
							>
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									stroke-width="2"
									d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
								/>
							</svg>
							<div class="text-sm text-blue-700 dark:text-blue-300">
								<strong>권한 안내:</strong> 권한이 부여된 사용자 또는 그룹에 속한 사용자만 이 MCP
								서버에 접근할 수 있습니다. 관리자는 항상 모든 서버에 접근할 수 있습니다.
							</div>
						</div>
					{/if}
				</div>
			</div>
		</div>
	{/if}
{/if}
