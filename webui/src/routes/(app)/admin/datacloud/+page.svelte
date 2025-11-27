<script lang="ts">
	import { onMount } from 'svelte';
	import { toast } from 'svelte-sonner';
	import Plus from '$lib/components/icons/Plus.svelte';
	import GarbageBin from '$lib/components/icons/GarbageBin.svelte';
	import Check from '$lib/components/icons/Check.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
	import Pencil from '$lib/components/icons/Pencil.svelte';
	import Play from '$lib/components/icons/Play.svelte';
	import Database from '$lib/components/icons/Database.svelte';
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
	let queryResult: { columns: string[]; rows: any[]; row_count: number; execution_time_ms: number } | null = null;
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
				toast.success(`쿼리 실행 완료 (${queryResult?.execution_time_ms}ms, ${queryResult?.row_count}건)`);
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

<div class="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 p-6">
	<!-- Hero Section -->
	<div class="mb-8 relative overflow-hidden rounded-2xl bg-gradient-to-r from-emerald-600/20 via-teal-600/20 to-cyan-600/20 backdrop-blur-xl border border-white/10 p-8">
		<div class="absolute inset-0 bg-[url('data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iNjAiIGhlaWdodD0iNjAiIHZpZXdCb3g9IjAgMCA2MCA2MCIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj48ZyBmaWxsPSJub25lIiBmaWxsLXJ1bGU9ImV2ZW5vZGQiPjxwYXRoIGQ9Ik0zNiAxOGMzLjMxNCAwIDYgMi42ODYgNiA2cy0yLjY4NiA2LTYgNi02LTIuNjg2LTYtNiAyLjY4Ni02IDYtNiIgc3Ryb2tlPSJyZ2JhKDI1NSwyNTUsMjU1LDAuMSkiIHN0cm9rZS13aWR0aD0iMiIvPjwvZz48L3N2Zz4=')] opacity-20"></div>
		<div class="relative z-10">
			<div class="flex items-center gap-4 mb-4">
				<div class="p-3 bg-emerald-500/20 rounded-xl">
					<Database class="w-8 h-8 text-emerald-400" />
				</div>
				<div>
					<h1 class="text-3xl font-bold text-white">Data Cloud</h1>
					<p class="text-gray-400">Zero Copy 데이터베이스 커넥터 - 데이터 복제 없이 실시간 연결</p>
				</div>
			</div>
			<div class="flex gap-4 mt-6">
				<div class="bg-white/5 rounded-xl px-4 py-3 border border-white/10">
					<div class="text-2xl font-bold text-white">{connections.length}</div>
					<div class="text-sm text-gray-400">등록된 연결</div>
				</div>
				<div class="bg-white/5 rounded-xl px-4 py-3 border border-white/10">
					<div class="text-2xl font-bold text-green-400">{connections.filter(c => c.health_status === 'healthy').length}</div>
					<div class="text-sm text-gray-400">정상 연결</div>
				</div>
				<div class="bg-white/5 rounded-xl px-4 py-3 border border-white/10">
					<div class="text-2xl font-bold text-cyan-400">{new Set(connections.map(c => c.db_type)).size}</div>
					<div class="text-sm text-gray-400">DB 유형</div>
				</div>
			</div>
		</div>
	</div>

	<!-- Actions -->
	<div class="flex justify-between items-center mb-6">
		<h2 class="text-xl font-semibold text-white">데이터베이스 연결</h2>
		<button
			on:click={openAddModal}
			class="flex items-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg transition-colors"
		>
			<Plus class="w-5 h-5" />
			새 연결 추가
		</button>
	</div>

	<!-- Connections Grid -->
	{#if loading}
		<div class="flex justify-center items-center h-64">
			<div class="animate-spin rounded-full h-12 w-12 border-4 border-emerald-500 border-t-transparent"></div>
		</div>
	{:else if connections.length === 0}
		<div class="text-center py-16 bg-white/5 rounded-xl border border-white/10">
			<Database class="w-16 h-16 text-gray-500 mx-auto mb-4" />
			<h3 class="text-lg font-medium text-gray-300">등록된 연결이 없습니다</h3>
			<p class="text-gray-500 mt-2">새 연결을 추가하여 데이터베이스에 연결하세요</p>
		</div>
	{:else}
		<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
			{#each connections as conn}
				<div class="bg-white/5 backdrop-blur-xl rounded-xl border border-white/10 p-5 hover:border-emerald-500/50 transition-all">
					<div class="flex items-start justify-between mb-4">
						<div class="flex items-center gap-3">
							<div class="p-2 bg-emerald-500/20 rounded-lg">
								<Database class="w-5 h-5 text-emerald-400" />
							</div>
							<div>
								<h3 class="font-semibold text-white">{conn.name}</h3>
								<p class="text-sm text-gray-400">{getDbTypeLabel(conn.db_type)}</p>
							</div>
						</div>
						<div class="flex items-center gap-1">
							<span class={`text-sm ${getHealthStatusColor(conn.health_status)}`}>
								{getHealthStatusText(conn.health_status)}
							</span>
						</div>
					</div>

					<div class="space-y-2 text-sm text-gray-400 mb-4">
						<div class="flex justify-between">
							<span>호스트:</span>
							<span class="text-gray-300">{conn.host}:{conn.port}</span>
						</div>
						<div class="flex justify-between">
							<span>데이터베이스:</span>
							<span class="text-gray-300">{conn.database_name}</span>
						</div>
						<div class="flex justify-between">
							<span>사용자:</span>
							<span class="text-gray-300">{conn.username}</span>
						</div>
					</div>

					<div class="flex gap-2 pt-4 border-t border-white/10">
						<button
							on:click={() => testConnection(conn)}
							class="flex-1 flex items-center justify-center gap-1 px-3 py-2 bg-blue-600/20 hover:bg-blue-600/30 text-blue-400 rounded-lg text-sm transition-colors"
						>
							<Play class="w-4 h-4" />
							테스트
						</button>
						<button
							on:click={() => openSchemaModal(conn)}
							class="flex-1 flex items-center justify-center gap-1 px-3 py-2 bg-purple-600/20 hover:bg-purple-600/30 text-purple-400 rounded-lg text-sm transition-colors"
						>
							스키마
						</button>
						<button
							on:click={() => openQueryModal(conn)}
							class="flex-1 flex items-center justify-center gap-1 px-3 py-2 bg-emerald-600/20 hover:bg-emerald-600/30 text-emerald-400 rounded-lg text-sm transition-colors"
						>
							쿼리
						</button>
						<button
							on:click={() => openEditModal(conn)}
							class="p-2 bg-gray-600/20 hover:bg-gray-600/30 text-gray-400 rounded-lg transition-colors"
						>
							<Pencil class="w-4 h-4" />
						</button>
						<button
							on:click={() => deleteConnection(conn)}
							class="p-2 bg-red-600/20 hover:bg-red-600/30 text-red-400 rounded-lg transition-colors"
						>
							<GarbageBin class="w-4 h-4" />
						</button>
					</div>
				</div>
			{/each}
		</div>
	{/if}
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
						<Play class="w-4 h-4" />
					{/if}
					실행
				</button>
			</div>

			{#if queryResult}
				<div class="flex-1 overflow-auto border-t border-white/10">
					<div class="p-4 bg-slate-900/50 text-sm text-gray-400">
						{queryResult.row_count}건 조회됨 ({queryResult.execution_time_ms}ms)
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

