<script lang="ts">
	import { onMount } from 'svelte';
	import { toast } from 'svelte-sonner';
	import Plus from '$lib/components/icons/Plus.svelte';
	import GarbageBin from '$lib/components/icons/GarbageBin.svelte';
	import Check from '$lib/components/icons/Check.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import Pencil from '$lib/components/icons/Pencil.svelte';
	import Bolt from '$lib/components/icons/Bolt.svelte';
	import Cube from '$lib/components/icons/Cube.svelte';
	import ChevronDown from '$lib/components/icons/ChevronDown.svelte';
	import ChevronRight from '$lib/components/icons/ChevronRight.svelte';

	const BACKEND_URL = 'http://localhost:8000';

	interface DBConnection {
		id: string;
		name: string;
		description: string | null;
		db_type: string;
		host: string;
		port: number;
		database_name: string;
		username: string;
		enabled: boolean;
		health_status: string;
		last_health_check: string | null;
		created_at: string;
		updated_at: string;
	}

	interface TableInfo {
		name: string;
		type: string;
		comment: string | null;
		columns: ColumnInfo[];
	}

	interface ColumnInfo {
		name: string;
		type: string;
		nullable: boolean;
		is_primary_key: boolean;
		is_foreign_key: boolean;
		foreign_key_ref: string | null;
		comment: string | null;
		business_term: string | null;
	}

	let connections: DBConnection[] = [];
	let loading = true;
	let showModal = false;
	let editingConnection: DBConnection | null = null;
	let showSchemaModal = false;
	let selectedConnection: DBConnection | null = null;
	let schemaData: { tables: TableInfo[] } | null = null;
	let schemaLoading = false;
	let expandedTables: Set<string> = new Set();
	let showQueryModal = false;
	let queryText = '';
	let queryResult: { columns: string[]; rows: any[]; rows_affected: number; execution_time_ms: number } | null = null;
	let queryLoading = false;

	// Form data
	let formData = {
		name: '',
		description: '',
		db_type: 'mariadb',
		host: '',
		port: 3306,
		database_name: '',
		username: '',
		password: '',
		enabled: true
	};

	const dbTypes = [
		{ value: 'mariadb', label: 'MariaDB', port: 3306 },
		{ value: 'mysql', label: 'MySQL', port: 3306 },
		{ value: 'postgresql', label: 'PostgreSQL', port: 5432 },
		{ value: 'clickhouse', label: 'ClickHouse', port: 8123 },
		{ value: 'oracle', label: 'Oracle', port: 1521 },
		{ value: 'mssql', label: 'MS SQL Server', port: 1433 },
		{ value: 'sap_hana', label: 'SAP HANA', port: 30015 }
	];

	onMount(async () => {
		await loadConnections();
	});

	async function loadConnections() {
		loading = true;
		try {
			const response = await fetch(`${BACKEND_URL}/datacloud/connections`);
			if (response.ok) {
				connections = await response.json();
			} else {
				toast.error('연결 목록 로드 실패');
			}
		} catch (e) {
			console.error('Failed to load connections:', e);
			toast.error('연결 목록 로드 실패');
		} finally {
			loading = false;
		}
	}

	function openAddModal() {
		editingConnection = null;
		formData = {
			name: '',
			description: '',
			db_type: 'mariadb',
			host: '',
			port: 3306,
			database_name: '',
			username: '',
			password: '',
			enabled: true
		};
		showModal = true;
	}

	function openEditModal(conn: DBConnection) {
		editingConnection = conn;
		formData = {
			name: conn.name,
			description: conn.description || '',
			db_type: conn.db_type,
			host: conn.host,
			port: conn.port,
			database_name: conn.database_name,
			username: conn.username,
			password: '',
			enabled: conn.enabled
		};
		showModal = true;
	}

	function onDbTypeChange() {
		const dbType = dbTypes.find(t => t.value === formData.db_type);
		if (dbType && !editingConnection) {
			formData.port = dbType.port;
		}
	}

	async function testNewConnection() {
		try {
			const response = await fetch(`${BACKEND_URL}/datacloud/connections/test-new`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify(formData)
			});
			const result = await response.json();
			if (result.success) {
				toast.success(`연결 성공 (${result.latency_ms}ms)`);
			} else {
				toast.error(`연결 실패: ${result.message}`);
			}
		} catch (e: any) {
			toast.error(`테스트 실패: ${e.message}`);
		}
	}

	async function saveConnection() {
		try {
			const url = editingConnection
				? `${BACKEND_URL}/datacloud/connections/${editingConnection.id}`
				: `${BACKEND_URL}/datacloud/connections`;
			const method = editingConnection ? 'PUT' : 'POST';

			const response = await fetch(url, {
				method,
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify(formData)
			});

			if (response.ok) {
				toast.success(editingConnection ? '연결 수정 완료' : '연결 추가 완료');
				showModal = false;
				await loadConnections();
			} else {
				const error = await response.json();
				toast.error(`저장 실패: ${error.detail}`);
			}
		} catch (e: any) {
			toast.error(`저장 실패: ${e.message}`);
		}
	}

	async function deleteConnection(conn: DBConnection) {
		if (!confirm(`'${conn.name}' 연결을 삭제하시겠습니까?`)) return;

		try {
			const response = await fetch(`${BACKEND_URL}/datacloud/connections/${conn.id}`, {
				method: 'DELETE'
			});

			if (response.ok) {
				toast.success('연결 삭제 완료');
				await loadConnections();
			} else {
				toast.error('삭제 실패');
			}
		} catch (e: any) {
			toast.error(`삭제 실패: ${e.message}`);
		}
	}

	async function testConnection(conn: DBConnection) {
		try {
			const response = await fetch(`${BACKEND_URL}/datacloud/connections/${conn.id}/test`, {
				method: 'POST'
			});
			const result = await response.json();
			if (result.success) {
				toast.success(`연결 성공 (${result.latency_ms}ms)`);
				await loadConnections();
			} else {
				toast.error(`연결 실패: ${result.message}`);
			}
		} catch (e: any) {
			toast.error(`테스트 실패: ${e.message}`);
		}
	}

	async function openSchemaModal(conn: DBConnection) {
		selectedConnection = conn;
		schemaData = null;
		schemaLoading = true;
		expandedTables = new Set();
		showSchemaModal = true;

		try {
			const response = await fetch(`${BACKEND_URL}/datacloud/connections/${conn.id}/schema`);
			if (response.ok) {
				schemaData = await response.json();
			} else {
				toast.error('스키마 로드 실패');
			}
		} catch (e: any) {
			toast.error(`스키마 로드 실패: ${e.message}`);
		} finally {
			schemaLoading = false;
		}
	}

	async function refreshSchema() {
		if (!selectedConnection) return;
		schemaLoading = true;
		try {
			const response = await fetch(`${BACKEND_URL}/datacloud/connections/${selectedConnection.id}/schema?refresh=true`);
			if (response.ok) {
				schemaData = await response.json();
				toast.success('스키마 새로고침 완료');
			} else {
				toast.error('스키마 새로고침 실패');
			}
		} catch (e: any) {
			toast.error(`새로고침 실패: ${e.message}`);
		} finally {
			schemaLoading = false;
		}
	}

	function toggleTable(tableName: string) {
		if (expandedTables.has(tableName)) {
			expandedTables.delete(tableName);
		} else {
			expandedTables.add(tableName);
		}
		expandedTables = expandedTables;
	}

	function openQueryModal(conn: DBConnection) {
		selectedConnection = conn;
		queryText = '';
		queryResult = null;
		showQueryModal = true;
	}

	async function executeQuery() {
		if (!selectedConnection || !queryText.trim()) return;
		queryLoading = true;
		queryResult = null;

		try {
			const response = await fetch(`${BACKEND_URL}/datacloud/connections/${selectedConnection.id}/query`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ query: queryText, limit: 100 })
			});

			if (response.ok) {
				queryResult = await response.json();
				toast.success(`쿼리 실행 완료 (${queryResult?.execution_time_ms ?? 0}ms, ${queryResult?.rows?.length ?? 0}건)`);
			} else {
				const error = await response.json();
				toast.error(`쿼리 실패: ${error.detail}`);
			}
		} catch (e: any) {
			toast.error(`쿼리 실패: ${e.message}`);
		} finally {
			queryLoading = false;
		}
	}

	function getHealthStatusColor(status: string): string {
		switch (status) {
			case 'healthy': return 'text-green-500';
			case 'unhealthy': return 'text-red-500';
			default: return 'text-gray-400';
		}
	}

	function getHealthStatusText(status: string): string {
		switch (status) {
			case 'healthy': return '정상';
			case 'unhealthy': return '오류';
			default: return '미확인';
		}
	}

	function getDbTypeLabel(type: string): string {
		return dbTypes.find(t => t.value === type)?.label || type;
	}
</script>

<svelte:head>
	<title>Data Cloud | Admin</title>
</svelte:head>

<div class="flex w-full flex-col min-h-full px-3 py-4 @md:px-6 @md:py-6">
	<div class="mx-auto flex w-full max-w-[1200px] flex-col gap-6">
		<!-- Hero Section -->
		<section class="relative overflow-hidden rounded-3xl border border-white/20 bg-white/60 p-6 shadow-2xl shadow-emerald-500/10 backdrop-blur-2xl dark:border-gray-700/30 dark:bg-gray-900/60">
			<div class="absolute inset-0 bg-gradient-to-br from-emerald-500/20 via-teal-500/10 to-cyan-500/20 opacity-60" />
			<div class="pointer-events-none absolute -right-10 -top-12 h-40 w-40 rounded-full bg-gradient-to-br from-emerald-500/40 to-teal-500/30 blur-3xl" />
			<div class="relative flex flex-col gap-5">
				<div class="flex flex-wrap items-center justify-between gap-3">
					<div class="flex flex-wrap items-center gap-3">
						<span class="inline-flex items-center gap-2 rounded-full bg-white/90 px-3 py-1 text-xs font-medium text-gray-600 shadow-sm dark:bg-gray-800/80 dark:text-gray-200">
							<span class="h-1.5 w-1.5 rounded-full bg-gradient-to-r from-emerald-500 via-teal-500 to-cyan-500" />
							Data Cloud
						</span>
						<h1 class="text-2xl font-semibold tracking-tight text-gray-900 dark:text-gray-100">
							Zero Copy 데이터베이스 커넥터
						</h1>
					</div>
					<button
						on:click={openAddModal}
						class="flex items-center gap-2 px-4 py-2 rounded-xl bg-gradient-to-br from-emerald-500 to-teal-500 text-white font-medium shadow-lg hover:shadow-xl transition-all hover:scale-105"
					>
						<Plus class="size-5" />
						<span>연결 추가</span>
					</button>
				</div>

				<p class="max-w-3xl text-sm text-gray-600 dark:text-gray-300">
					데이터 복제 없이 실시간으로 데이터베이스에 연결하여 스키마 조회 및 쿼리를 실행할 수 있습니다.
				</p>

				<div class="grid grid-cols-3 gap-3 @md:grid-cols-4 @lg:grid-cols-6">
					<div class="rounded-2xl border border-white/30 bg-white/70 px-4 py-3 text-left shadow-md shadow-emerald-500/10 transition dark:border-gray-700/30 dark:bg-gray-900/50">
						<div class="text-[11px] font-medium uppercase tracking-wide text-emerald-600 dark:text-emerald-400">총 연결</div>
						<div class="text-xl font-semibold text-gray-900 dark:text-gray-100">{connections.length}</div>
						<div class="pt-1 text-xs text-gray-500 dark:text-gray-400">등록됨</div>
					</div>
					<div class="rounded-2xl border border-white/30 bg-white/70 px-4 py-3 text-left shadow-md shadow-emerald-500/10 transition dark:border-gray-700/30 dark:bg-gray-900/50">
						<div class="text-[11px] font-medium uppercase tracking-wide text-emerald-600 dark:text-emerald-400">정상</div>
						<div class="text-xl font-semibold text-gray-900 dark:text-gray-100">{connections.filter(c => c.health_status === 'healthy').length}</div>
						<div class="pt-1 text-xs text-gray-500 dark:text-gray-400">연결됨</div>
					</div>
					<div class="rounded-2xl border border-white/30 bg-white/70 px-4 py-3 text-left shadow-md shadow-emerald-500/10 transition dark:border-gray-700/30 dark:bg-gray-900/50">
						<div class="text-[11px] font-medium uppercase tracking-wide text-emerald-600 dark:text-emerald-400">DB 유형</div>
						<div class="text-xl font-semibold text-gray-900 dark:text-gray-100">{new Set(connections.map(c => c.db_type)).size}</div>
						<div class="pt-1 text-xs text-gray-500 dark:text-gray-400">지원</div>
					</div>
				</div>
			</div>
		</section>

		<!-- Connection List -->
		<div class="bg-white/60 dark:bg-gray-900/50 backdrop-blur-xl rounded-xl border border-white/20 dark:border-gray-700/20 shadow-xl overflow-hidden">
			{#if loading}
				<div class="flex items-center justify-center py-12">
					<div class="animate-spin rounded-full h-8 w-8 border-b-2 border-emerald-500"></div>
				</div>
			{:else if connections.length === 0}
				<div class="text-center py-12">
					<Cube class="size-16 mx-auto text-gray-300 dark:text-gray-600 mb-4" />
					<h3 class="text-lg font-medium text-gray-900 dark:text-gray-100 mb-2">등록된 연결이 없습니다</h3>
					<p class="text-gray-500 dark:text-gray-400 mb-4">데이터베이스 연결을 추가하여 시작하세요.</p>
					<button
						on:click={openAddModal}
						class="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-emerald-500 text-white hover:bg-emerald-600 transition-colors"
					>
						<Plus class="size-5" />
						<span>첫 번째 연결 추가</span>
					</button>
				</div>
			{:else}
				<div class="overflow-x-auto">
					<table class="w-full">
						<thead class="bg-gray-50/50 dark:bg-gray-800/50">
							<tr>
								<th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">데이터베이스</th>
								<th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">상태</th>
								<th class="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">호스트</th>
								<th class="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">작업</th>
							</tr>
						</thead>
						<tbody class="divide-y divide-gray-200/50 dark:divide-gray-700/50">
							{#each connections as conn}
								<tr class="hover:bg-gray-50/50 dark:hover:bg-gray-800/30 transition-colors">
									<td class="px-6 py-4">
										<div class="flex items-center gap-3">
											<div class="p-2 rounded-lg bg-emerald-100 dark:bg-emerald-900/30">
												<Cube class="size-5 text-emerald-600 dark:text-emerald-400" />
											</div>
											<div>
												<div class="font-medium text-gray-900 dark:text-gray-100">{conn.name}</div>
												<div class="text-sm text-gray-500 dark:text-gray-400">{getDbTypeLabel(conn.db_type)}</div>
											</div>
										</div>
									</td>
									<td class="px-6 py-4">
										<span class="inline-flex items-center gap-1 px-2 py-1 rounded-full text-xs font-medium {conn.health_status === 'healthy' ? 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400' : conn.health_status === 'unhealthy' ? 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400' : 'bg-gray-100 text-gray-800 dark:bg-gray-700/30 dark:text-gray-400'}">
											{#if conn.health_status === 'healthy'}
												<Check class="size-3" />
											{:else if conn.health_status === 'unhealthy'}
												<XMark class="size-3" />
											{/if}
											{getHealthStatusText(conn.health_status)}
										</span>
									</td>
									<td class="px-6 py-4">
										<div class="text-sm text-gray-900 dark:text-gray-100">{conn.host}:{conn.port}</div>
										<div class="text-sm text-gray-500 dark:text-gray-400">{conn.database_name}</div>
									</td>
									<td class="px-6 py-4">
										<div class="flex items-center justify-end gap-2">
											<button
												on:click={() => testConnection(conn)}
												class="p-2 text-gray-400 hover:text-emerald-500 hover:bg-emerald-50 dark:hover:bg-emerald-900/20 rounded-lg transition-colors"
												title="연결 테스트"
											>
												<Bolt class="size-4" />
											</button>
											<button
												on:click={() => openSchemaModal(conn)}
												class="px-3 py-1.5 text-sm text-emerald-600 dark:text-emerald-400 hover:bg-emerald-50 dark:hover:bg-emerald-900/20 rounded-lg transition-colors"
											>
												스키마
											</button>
											<button
												on:click={() => openQueryModal(conn)}
												class="px-3 py-1.5 text-sm text-teal-600 dark:text-teal-400 hover:bg-teal-50 dark:hover:bg-teal-900/20 rounded-lg transition-colors"
											>
												쿼리
											</button>
											<button
												on:click={() => openEditModal(conn)}
												class="p-2 text-gray-400 hover:text-blue-500 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded-lg transition-colors"
												title="편집"
											>
												<Pencil class="size-4" />
											</button>
											<button
												on:click={() => deleteConnection(conn)}
												class="p-2 text-gray-400 hover:text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors"
												title="삭제"
											>
												<GarbageBin class="size-4" />
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

<!-- Add/Edit Connection Modal -->
{#if showModal}
	<div class="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
		<div class="bg-slate-800 rounded-2xl border border-white/10 w-full max-w-lg max-h-[90vh] overflow-y-auto">
			<div class="p-6 border-b border-white/10">
				<h2 class="text-xl font-semibold text-white">
					{editingConnection ? '연결 수정' : '새 연결 추가'}
				</h2>
			</div>

			<div class="p-6 space-y-4">
				<div>
					<label class="block text-sm font-medium text-gray-300 mb-1">연결 이름</label>
					<input
						type="text"
						bind:value={formData.name}
						class="w-full px-4 py-2 bg-white/5 border border-white/10 rounded-lg text-white focus:border-emerald-500 focus:outline-none"
						placeholder="예: Production MariaDB"
					/>
				</div>

				<div>
					<label class="block text-sm font-medium text-gray-300 mb-1">설명</label>
					<input
						type="text"
						bind:value={formData.description}
						class="w-full px-4 py-2 bg-white/5 border border-white/10 rounded-lg text-white focus:border-emerald-500 focus:outline-none"
						placeholder="선택사항"
					/>
				</div>

				<div>
					<label class="block text-sm font-medium text-gray-300 mb-1">데이터베이스 유형</label>
					<select
						bind:value={formData.db_type}
						on:change={onDbTypeChange}
						class="w-full px-4 py-2 bg-white/5 border border-white/10 rounded-lg text-white focus:border-emerald-500 focus:outline-none"
					>
						{#each dbTypes as dbType}
							<option value={dbType.value}>{dbType.label}</option>
						{/each}
					</select>
				</div>

				<div class="grid grid-cols-3 gap-4">
					<div class="col-span-2">
						<label class="block text-sm font-medium text-gray-300 mb-1">호스트</label>
						<input
							type="text"
							bind:value={formData.host}
							class="w-full px-4 py-2 bg-white/5 border border-white/10 rounded-lg text-white focus:border-emerald-500 focus:outline-none"
							placeholder="localhost"
						/>
					</div>
					<div>
						<label class="block text-sm font-medium text-gray-300 mb-1">포트</label>
						<input
							type="number"
							bind:value={formData.port}
							class="w-full px-4 py-2 bg-white/5 border border-white/10 rounded-lg text-white focus:border-emerald-500 focus:outline-none"
						/>
					</div>
				</div>

				<div>
					<label class="block text-sm font-medium text-gray-300 mb-1">데이터베이스 이름</label>
					<input
						type="text"
						bind:value={formData.database_name}
						class="w-full px-4 py-2 bg-white/5 border border-white/10 rounded-lg text-white focus:border-emerald-500 focus:outline-none"
						placeholder="database_name"
					/>
				</div>

				<div class="grid grid-cols-2 gap-4">
					<div>
						<label class="block text-sm font-medium text-gray-300 mb-1">사용자 이름</label>
						<input
							type="text"
							bind:value={formData.username}
							class="w-full px-4 py-2 bg-white/5 border border-white/10 rounded-lg text-white focus:border-emerald-500 focus:outline-none"
							placeholder="username"
						/>
					</div>
					<div>
						<label class="block text-sm font-medium text-gray-300 mb-1">비밀번호</label>
						<input
							type="password"
							bind:value={formData.password}
							class="w-full px-4 py-2 bg-white/5 border border-white/10 rounded-lg text-white focus:border-emerald-500 focus:outline-none"
							placeholder={editingConnection ? '변경 시 입력' : '비밀번호'}
						/>
					</div>
				</div>

				<div class="flex items-center gap-2">
					<input
						type="checkbox"
						id="enabled"
						bind:checked={formData.enabled}
						class="w-4 h-4 rounded border-white/10 bg-white/5 text-emerald-500 focus:ring-emerald-500"
					/>
					<label for="enabled" class="text-sm text-gray-300">활성화</label>
				</div>
			</div>

			<div class="p-6 border-t border-white/10 flex justify-between">
				<button
					on:click={testNewConnection}
					class="px-4 py-2 bg-blue-600/20 hover:bg-blue-600/30 text-blue-400 rounded-lg transition-colors"
				>
					연결 테스트
				</button>
				<div class="flex gap-2">
					<button
						on:click={() => showModal = false}
						class="px-4 py-2 bg-gray-600/20 hover:bg-gray-600/30 text-gray-300 rounded-lg transition-colors"
					>
						취소
					</button>
					<button
						on:click={saveConnection}
						class="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg transition-colors"
					>
						{editingConnection ? '수정' : '추가'}
					</button>
				</div>
			</div>
		</div>
	</div>
{/if}

<!-- Schema Modal -->
{#if showSchemaModal && selectedConnection}
	<div class="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
		<div class="bg-slate-800 rounded-2xl border border-white/10 w-full max-w-4xl max-h-[90vh] overflow-hidden flex flex-col">
			<div class="p-6 border-b border-white/10 flex justify-between items-center">
				<div>
					<h2 class="text-xl font-semibold text-white">스키마 탐색</h2>
					<p class="text-sm text-gray-400">{selectedConnection.name} - {selectedConnection.database_name}</p>
				</div>
				<div class="flex gap-2">
					<button
						on:click={refreshSchema}
						disabled={schemaLoading}
						class="px-3 py-1 bg-blue-600/20 hover:bg-blue-600/30 text-blue-400 rounded-lg text-sm transition-colors disabled:opacity-50"
					>
						새로고침
					</button>
					<button
						on:click={() => showSchemaModal = false}
						class="p-2 hover:bg-white/10 rounded-lg transition-colors"
					>
						<XMark class="w-5 h-5 text-gray-400" />
					</button>
				</div>
			</div>

			<div class="flex-1 overflow-y-auto p-6">
				{#if schemaLoading}
					<div class="flex justify-center items-center h-64">
						<div class="animate-spin rounded-full h-12 w-12 border-4 border-purple-500 border-t-transparent"></div>
					</div>
				{:else if schemaData && schemaData.tables}
					<div class="space-y-2">
						{#each schemaData.tables as table}
							<div class="bg-white/5 rounded-lg border border-white/10">
								<button
									on:click={() => toggleTable(table.name)}
									class="w-full flex items-center justify-between p-4 hover:bg-white/5 transition-colors"
								>
									<div class="flex items-center gap-3">
										{#if expandedTables.has(table.name)}
											<ChevronDown class="w-4 h-4 text-gray-400" />
										{:else}
											<ChevronRight class="w-4 h-4 text-gray-400" />
										{/if}
										<span class="font-medium text-white">{table.name}</span>
										<span class="text-xs px-2 py-0.5 bg-purple-500/20 text-purple-400 rounded">
											{table.type}
										</span>
										<span class="text-sm text-gray-500">
											{table.columns?.length || 0} 컬럼
										</span>
									</div>
								</button>

								{#if expandedTables.has(table.name) && table.columns}
									<div class="border-t border-white/10 p-4">
										<table class="w-full text-sm">
											<thead>
												<tr class="text-gray-400">
													<th class="text-left py-2 px-3">컬럼명</th>
													<th class="text-left py-2 px-3">타입</th>
													<th class="text-left py-2 px-3">NULL</th>
													<th class="text-left py-2 px-3">키</th>
													<th class="text-left py-2 px-3">설명</th>
												</tr>
											</thead>
											<tbody>
												{#each table.columns as col}
													<tr class="border-t border-white/5 hover:bg-white/5">
														<td class="py-2 px-3 text-white">{col.name}</td>
														<td class="py-2 px-3 text-gray-400 font-mono text-xs">{col.type}</td>
														<td class="py-2 px-3">
															{#if col.nullable}
																<span class="text-yellow-400">YES</span>
															{:else}
																<span class="text-gray-500">NO</span>
															{/if}
														</td>
														<td class="py-2 px-3">
															{#if col.is_primary_key}
																<span class="text-xs px-1.5 py-0.5 bg-yellow-500/20 text-yellow-400 rounded">PK</span>
															{/if}
															{#if col.is_foreign_key}
																<span class="text-xs px-1.5 py-0.5 bg-blue-500/20 text-blue-400 rounded">FK</span>
															{/if}
														</td>
														<td class="py-2 px-3 text-gray-500">
															{col.comment || col.business_term || '-'}
														</td>
													</tr>
												{/each}
											</tbody>
										</table>
									</div>
								{/if}
							</div>
						{/each}
					</div>
				{:else}
					<div class="text-center py-16 text-gray-400">
						스키마 정보가 없습니다
					</div>
				{/if}
			</div>
		</div>
	</div>
{/if}

<!-- Query Modal -->
{#if showQueryModal && selectedConnection}
	<div class="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
		<div class="bg-slate-800 rounded-2xl border border-white/10 w-full max-w-5xl max-h-[90vh] overflow-hidden flex flex-col">
			<div class="p-6 border-b border-white/10 flex justify-between items-center">
				<div>
					<h2 class="text-xl font-semibold text-white">쿼리 실행</h2>
					<p class="text-sm text-gray-400">{selectedConnection.name} - {selectedConnection.database_name}</p>
				</div>
				<button
					on:click={() => showQueryModal = false}
					class="p-2 hover:bg-white/10 rounded-lg transition-colors"
				>
					<XMark class="w-5 h-5 text-gray-400" />
				</button>
			</div>

			<div class="p-6 space-y-4">
				<div>
					<label class="block text-sm font-medium text-gray-300 mb-2">SQL 쿼리</label>
					<textarea
						bind:value={queryText}
						rows="4"
						class="w-full px-4 py-3 bg-slate-900 border border-white/10 rounded-lg text-white font-mono text-sm focus:border-emerald-500 focus:outline-none"
						placeholder="SELECT * FROM table_name LIMIT 10"
					></textarea>
				</div>

				<button
					on:click={executeQuery}
					disabled={queryLoading || !queryText.trim()}
					class="flex items-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg transition-colors disabled:opacity-50"
				>
					{#if queryLoading}
						<div class="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent"></div>
					{:else}
						<Bolt class="w-4 h-4" />
					{/if}
					실행
				</button>
			</div>

		{#if queryResult}
			<div class="flex-1 overflow-auto border-t border-white/10">
				<div class="p-4 bg-slate-900/50 text-sm text-gray-400">
					{queryResult.rows?.length ?? 0}건 조회됨 ({queryResult.execution_time_ms ?? 0}ms)
				</div>
					<div class="overflow-x-auto">
						<table class="w-full text-sm">
							<thead class="bg-slate-900/50 sticky top-0">
								<tr>
									{#each queryResult.columns as col}
										<th class="text-left py-3 px-4 text-gray-400 font-medium border-b border-white/10">{col}</th>
									{/each}
								</tr>
							</thead>
							<tbody>
								{#each queryResult.rows as row}
									<tr class="border-b border-white/5 hover:bg-white/5">
										{#each queryResult.columns as col}
											<td class="py-2 px-4 text-gray-300 font-mono text-xs">
												{row[col] !== null ? String(row[col]).substring(0, 100) : 'NULL'}
											</td>
										{/each}
									</tr>
								{/each}
							</tbody>
						</table>
					</div>
				</div>
			{/if}
		</div>
	</div>
{/if}

