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

	// Vite 프록시를 통해 백엔드 API 호출 (CORS 우회)
	const BACKEND_URL = '/api';

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

	// Business Terms Modal
	let showTermsModal = false;
	let termsData: { terms: any[] } | null = null;
	let termsLoading = false;
	let newTerm = {
		term_type: 'column',
		technical_name: '',
		business_name: '',
		description: '',
		schema_name: '',
		table_name: '',
		column_name: ''
	};

	// Permissions Modal
	let showPermissionsModal = false;
	let permissionsData: { permissions: any[] } | null = null;
	let permissionsLoading = false;
	let newPermission = {
		user_id: '',
		group_id: '',
		permission_type: 'read'
	};

	// Text-to-SQL
	let naturalLanguageQuery = '';
	let sqlGenerating = false;

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

	// ========================
	// Business Terms Functions
	// ========================
	async function openTermsModal(conn: DBConnection) {
		selectedConnection = conn;
		termsData = null;
		termsLoading = true;
		showTermsModal = true;
		newTerm = {
			term_type: 'column',
			technical_name: '',
			business_name: '',
			description: '',
			schema_name: '',
			table_name: '',
			column_name: ''
		};

		try {
			const response = await fetch(`${BACKEND_URL}/datacloud/connections/${conn.id}/terms`);
			if (response.ok) {
				termsData = await response.json();
			} else {
				toast.error('용어집 로드 실패');
			}
		} catch (e: any) {
			toast.error(`용어집 로드 실패: ${e.message}`);
		} finally {
			termsLoading = false;
		}
	}

	async function addTerm() {
		if (!selectedConnection || !newTerm.technical_name || !newTerm.business_name) {
			toast.error('기술명과 비즈니스명을 입력하세요');
			return;
		}

		try {
			const response = await fetch(`${BACKEND_URL}/datacloud/connections/${selectedConnection.id}/terms`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify(newTerm)
			});

			if (response.ok) {
				toast.success('용어 추가 완료');
				await openTermsModal(selectedConnection);
			} else {
				const error = await response.json();
				toast.error(`추가 실패: ${error.detail}`);
			}
		} catch (e: any) {
			toast.error(`추가 실패: ${e.message}`);
		}
	}

	async function deleteTerm(termId: string) {
		if (!confirm('이 용어를 삭제하시겠습니까?')) return;

		try {
			const response = await fetch(`${BACKEND_URL}/datacloud/terms/${termId}`, {
				method: 'DELETE'
			});

			if (response.ok) {
				toast.success('용어 삭제 완료');
				if (selectedConnection) await openTermsModal(selectedConnection);
			} else {
				toast.error('삭제 실패');
			}
		} catch (e: any) {
			toast.error(`삭제 실패: ${e.message}`);
		}
	}

	// ========================
	// Permissions Functions
	// ========================
	async function openPermissionsModal(conn: DBConnection) {
		selectedConnection = conn;
		permissionsData = null;
		permissionsLoading = true;
		showPermissionsModal = true;
		newPermission = { user_id: '', group_id: '', permission_type: 'read' };

		try {
			const response = await fetch(`${BACKEND_URL}/datacloud/connections/${conn.id}/permissions`);
			if (response.ok) {
				permissionsData = await response.json();
			} else {
				toast.error('권한 로드 실패');
			}
		} catch (e: any) {
			toast.error(`권한 로드 실패: ${e.message}`);
		} finally {
			permissionsLoading = false;
		}
	}

	async function addPermission() {
		if (!selectedConnection || (!newPermission.user_id && !newPermission.group_id)) {
			toast.error('사용자 ID 또는 그룹 ID를 입력하세요');
			return;
		}

		try {
			const response = await fetch(`${BACKEND_URL}/datacloud/connections/${selectedConnection.id}/permissions`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify(newPermission)
			});

			if (response.ok) {
				toast.success('권한 추가 완료');
				await openPermissionsModal(selectedConnection);
			} else {
				const error = await response.json();
				toast.error(`추가 실패: ${error.detail}`);
			}
		} catch (e: any) {
			toast.error(`추가 실패: ${e.message}`);
		}
	}

	async function deletePermission(permissionId: string) {
		if (!confirm('이 권한을 삭제하시겠습니까?')) return;

		try {
			const response = await fetch(`${BACKEND_URL}/datacloud/permissions/${permissionId}`, {
				method: 'DELETE'
			});

			if (response.ok) {
				toast.success('권한 삭제 완료');
				if (selectedConnection) await openPermissionsModal(selectedConnection);
			} else {
				toast.error('삭제 실패');
			}
		} catch (e: any) {
			toast.error(`삭제 실패: ${e.message}`);
		}
	}

	// ========================
	// Text-to-SQL Functions
	// ========================
	async function generateSQL() {
		if (!selectedConnection || !naturalLanguageQuery.trim()) {
			toast.error('질문을 입력하세요');
			return;
		}

		sqlGenerating = true;
		try {
			const response = await fetch(`${BACKEND_URL}/datacloud/connections/${selectedConnection.id}/generate-sql`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ question: naturalLanguageQuery })
			});

			if (response.ok) {
				const result = await response.json();
				queryText = result.sql;
				toast.success('SQL이 생성되었습니다. 필요시 수정 후 실행하세요.');
			} else {
				const error = await response.json();
				toast.error(`SQL 생성 실패: ${error.detail}`);
			}
		} catch (e: any) {
			toast.error(`SQL 생성 실패: ${e.message}`);
		} finally {
			sqlGenerating = false;
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
		<section class="relative overflow-hidden rounded-3xl border border-white/20 bg-white/60 p-6 shadow-2xl shadow-primary/10 backdrop-blur-2xl dark:border-gray-700/30 dark:bg-gray-900/60">
			<div class="absolute inset-0 bg-gradient-to-br from-primary/20 via-secondary/10 to-accent/20 opacity-60" />
			<div class="pointer-events-none absolute -right-10 -top-12 h-40 w-40 rounded-full bg-gradient-to-br from-primary/40 to-secondary/30 blur-3xl" />
			<div class="relative flex flex-col gap-5">
				<div class="flex flex-wrap items-center justify-between gap-3">
					<div class="flex flex-wrap items-center gap-3">
						<span class="inline-flex items-center gap-2 rounded-full bg-white/90 px-3 py-1 text-xs font-medium text-gray-600 shadow-sm dark:bg-gray-800/80 dark:text-gray-200">
							<span class="h-1.5 w-1.5 rounded-full bg-gradient-to-r from-primary via-secondary to-accent" />
							Data Cloud
						</span>
						<h1 class="text-2xl font-semibold tracking-tight text-gray-900 dark:text-gray-100">
							Zero Copy 데이터베이스 커넥터
						</h1>
					</div>
					<button
						on:click={openAddModal}
						class="flex items-center gap-2 px-4 py-2 rounded-xl bg-gradient-to-br from-primary/90 via-secondary/90 to-accent/90 text-white font-medium shadow-lg shadow-primary/30 hover:shadow-xl transition-all hover:scale-105"
					>
						<Plus class="size-5" />
						<span>연결 추가</span>
					</button>
				</div>

				<p class="max-w-3xl text-sm text-gray-600 dark:text-gray-300">
					데이터 복제 없이 실시간으로 데이터베이스에 연결하여 스키마 조회 및 쿼리를 실행할 수 있습니다.
				</p>

				<div class="grid grid-cols-2 md:grid-cols-4 gap-4 mt-2">
					<div class="bg-white/60 dark:bg-gray-800/60 backdrop-blur-sm rounded-2xl p-4 border border-white/20 dark:border-gray-700/20 shadow-sm">
						<div class="flex items-center gap-3">
							<div class="p-2 rounded-lg bg-blue-100 dark:bg-blue-900/30">
								<Cube class="size-5 text-blue-600 dark:text-blue-400" />
							</div>
							<div>
								<div class="text-2xl font-bold text-gray-900 dark:text-gray-100">{connections.length}</div>
								<div class="text-xs text-gray-500 dark:text-gray-400">총 연결</div>
							</div>
						</div>
					</div>
					<div class="bg-white/60 dark:bg-gray-800/60 backdrop-blur-sm rounded-2xl p-4 border border-white/20 dark:border-gray-700/20 shadow-sm">
						<div class="flex items-center gap-3">
							<div class="p-2 rounded-lg bg-green-100 dark:bg-green-900/30">
								<Check class="size-5 text-green-600 dark:text-green-400" />
							</div>
							<div>
								<div class="text-2xl font-bold text-gray-900 dark:text-gray-100">{connections.filter(c => c.health_status === 'healthy').length}</div>
								<div class="text-xs text-gray-500 dark:text-gray-400">정상 연결</div>
							</div>
						</div>
					</div>
					<div class="bg-white/60 dark:bg-gray-800/60 backdrop-blur-sm rounded-2xl p-4 border border-white/20 dark:border-gray-700/20 shadow-sm">
						<div class="flex items-center gap-3">
							<div class="p-2 rounded-lg bg-purple-100 dark:bg-purple-900/30">
								<svg class="size-5 text-purple-600 dark:text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20.25 6.375c0 2.278-3.694 4.125-8.25 4.125S3.75 8.653 3.75 6.375m16.5 0c0-2.278-3.694-4.125-8.25-4.125S3.75 4.097 3.75 6.375m16.5 0v11.25c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125V6.375" />
								</svg>
							</div>
							<div>
								<div class="text-2xl font-bold text-gray-900 dark:text-gray-100">{new Set(connections.map(c => c.db_type)).size}</div>
								<div class="text-xs text-gray-500 dark:text-gray-400">DB 유형</div>
							</div>
						</div>
					</div>
					<div class="bg-white/60 dark:bg-gray-800/60 backdrop-blur-sm rounded-2xl p-4 border border-white/20 dark:border-gray-700/20 shadow-sm">
						<div class="flex items-center gap-3">
							<div class="p-2 rounded-lg bg-orange-100 dark:bg-orange-900/30">
								<XMark class="size-5 text-orange-600 dark:text-orange-400" />
							</div>
							<div>
								<div class="text-2xl font-bold text-gray-900 dark:text-gray-100">{connections.filter(c => c.health_status === 'unhealthy').length}</div>
								<div class="text-xs text-gray-500 dark:text-gray-400">오류 연결</div>
							</div>
						</div>
					</div>
				</div>
			</div>
		</section>

		<!-- Connection List -->
		<div class="bg-white/60 dark:bg-gray-900/50 backdrop-blur-xl rounded-xl border border-white/20 dark:border-gray-700/20 shadow-xl overflow-hidden">
			{#if loading}
				<div class="flex items-center justify-center py-12">
					<div class="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500"></div>
				</div>
			{:else if connections.length === 0}
				<div class="text-center py-12">
					<Cube class="size-16 mx-auto text-gray-300 dark:text-gray-600 mb-4" />
					<h3 class="text-lg font-medium text-gray-900 dark:text-gray-100 mb-2">등록된 연결이 없습니다</h3>
					<p class="text-gray-500 dark:text-gray-400 mb-4">데이터베이스 연결을 추가하여 시작하세요.</p>
					<button
						on:click={openAddModal}
						class="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-gradient-to-br from-primary/90 via-secondary/90 to-accent/90 text-white hover:shadow-lg transition-all"
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
											<div class="p-2 rounded-lg bg-blue-100 dark:bg-blue-900/30">
												<Cube class="size-5 text-blue-600 dark:text-blue-400" />
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
												class="p-2 text-gray-400 hover:text-green-500 hover:bg-green-50 dark:hover:bg-green-900/20 rounded-lg transition-colors"
												title="연결 테스트"
											>
												<Bolt class="size-4" />
											</button>
											<button
												on:click={() => openSchemaModal(conn)}
												class="px-3 py-1.5 text-sm text-blue-600 dark:text-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded-lg transition-colors"
											>
												스키마
											</button>
											<button
												on:click={() => openQueryModal(conn)}
												class="px-3 py-1.5 text-sm text-indigo-600 dark:text-indigo-400 hover:bg-indigo-50 dark:hover:bg-indigo-900/20 rounded-lg transition-colors"
											>
												쿼리
											</button>
											<button
												on:click={() => openTermsModal(conn)}
												class="px-3 py-1.5 text-sm text-amber-600 dark:text-amber-400 hover:bg-amber-50 dark:hover:bg-amber-900/20 rounded-lg transition-colors"
											>
												용어집
											</button>
											<button
												on:click={() => openPermissionsModal(conn)}
												class="px-3 py-1.5 text-sm text-purple-600 dark:text-purple-400 hover:bg-purple-50 dark:hover:bg-purple-900/20 rounded-lg transition-colors"
											>
												권한
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
		<div class="bg-white dark:bg-gray-800 rounded-2xl border border-gray-200 dark:border-gray-700 w-full max-w-lg max-h-[90vh] overflow-y-auto shadow-2xl">
			<div class="p-6 border-b border-gray-200 dark:border-gray-700">
				<h2 class="text-xl font-semibold text-gray-900 dark:text-white">
					{editingConnection ? '연결 수정' : '새 연결 추가'}
				</h2>
			</div>

			<div class="p-6 space-y-4">
				<div>
					<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">연결 이름</label>
					<input
						type="text"
						bind:value={formData.name}
						class="w-full px-4 py-2 bg-white dark:bg-gray-900 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-900 dark:text-white focus:border-blue-500 focus:ring-1 focus:ring-blue-500 focus:outline-none"
						placeholder="예: Production MariaDB"
					/>
				</div>

				<div>
					<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">설명</label>
					<input
						type="text"
						bind:value={formData.description}
						class="w-full px-4 py-2 bg-white dark:bg-gray-900 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-900 dark:text-white focus:border-blue-500 focus:ring-1 focus:ring-blue-500 focus:outline-none"
						placeholder="선택사항"
					/>
				</div>

				<div>
					<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">데이터베이스 유형</label>
					<select
						bind:value={formData.db_type}
						on:change={onDbTypeChange}
						class="w-full px-4 py-2 bg-white dark:bg-gray-900 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-900 dark:text-white focus:border-blue-500 focus:ring-1 focus:ring-blue-500 focus:outline-none"
					>
						{#each dbTypes as dbType}
							<option value={dbType.value}>{dbType.label}</option>
						{/each}
					</select>
				</div>

				<div class="grid grid-cols-3 gap-4">
					<div class="col-span-2">
						<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">호스트</label>
						<input
							type="text"
							bind:value={formData.host}
							class="w-full px-4 py-2 bg-white dark:bg-gray-900 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-900 dark:text-white focus:border-blue-500 focus:ring-1 focus:ring-blue-500 focus:outline-none"
							placeholder="localhost"
						/>
					</div>
					<div>
						<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">포트</label>
						<input
							type="number"
							bind:value={formData.port}
							class="w-full px-4 py-2 bg-white dark:bg-gray-900 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-900 dark:text-white focus:border-blue-500 focus:ring-1 focus:ring-blue-500 focus:outline-none"
						/>
					</div>
				</div>

				<div>
					<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">데이터베이스 이름</label>
					<input
						type="text"
						bind:value={formData.database_name}
						class="w-full px-4 py-2 bg-white dark:bg-gray-900 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-900 dark:text-white focus:border-blue-500 focus:ring-1 focus:ring-blue-500 focus:outline-none"
						placeholder="database_name"
					/>
				</div>

				<div class="grid grid-cols-2 gap-4">
					<div>
						<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">사용자 이름</label>
						<input
							type="text"
							bind:value={formData.username}
							class="w-full px-4 py-2 bg-white dark:bg-gray-900 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-900 dark:text-white focus:border-blue-500 focus:ring-1 focus:ring-blue-500 focus:outline-none"
							placeholder="username"
						/>
					</div>
					<div>
						<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">비밀번호</label>
						<input
							type="password"
							bind:value={formData.password}
							class="w-full px-4 py-2 bg-white dark:bg-gray-900 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-900 dark:text-white focus:border-blue-500 focus:ring-1 focus:ring-blue-500 focus:outline-none"
							placeholder={editingConnection ? '변경 시 입력' : '비밀번호'}
						/>
					</div>
				</div>

				<div class="flex items-center gap-2">
					<input
						type="checkbox"
						id="enabled"
						bind:checked={formData.enabled}
						class="w-4 h-4 rounded border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-900 text-blue-500 focus:ring-blue-500"
					/>
					<label for="enabled" class="text-sm text-gray-700 dark:text-gray-300">활성화</label>
				</div>
			</div>

			<div class="p-6 border-t border-gray-200 dark:border-gray-700 flex justify-between">
				<button
					on:click={testNewConnection}
					class="px-4 py-2 bg-blue-100 dark:bg-blue-900/30 hover:bg-blue-200 dark:hover:bg-blue-900/50 text-blue-600 dark:text-blue-400 rounded-lg transition-colors"
				>
					연결 테스트
				</button>
				<div class="flex gap-2">
					<button
						on:click={() => showModal = false}
						class="px-4 py-2 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300 rounded-lg transition-colors"
					>
						취소
					</button>
					<button
						on:click={saveConnection}
						class="px-4 py-2 bg-gradient-to-br from-primary/90 via-secondary/90 to-accent/90 hover:shadow-lg text-white rounded-lg transition-all"
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
		<div class="bg-white dark:bg-gray-800 rounded-2xl border border-gray-200 dark:border-gray-700 w-full max-w-4xl max-h-[90vh] overflow-hidden flex flex-col shadow-2xl">
			<div class="p-6 border-b border-gray-200 dark:border-gray-700 flex justify-between items-center">
				<div>
					<h2 class="text-xl font-semibold text-gray-900 dark:text-white">스키마 탐색</h2>
					<p class="text-sm text-gray-600 dark:text-gray-400">{selectedConnection.name} - {selectedConnection.database_name}</p>
				</div>
				<div class="flex gap-2">
					<button
						on:click={refreshSchema}
						disabled={schemaLoading}
						class="px-3 py-1.5 bg-blue-100 dark:bg-blue-900/30 hover:bg-blue-200 dark:hover:bg-blue-900/50 text-blue-600 dark:text-blue-400 rounded-lg text-sm transition-colors disabled:opacity-50"
					>
						새로고침
					</button>
					<button
						on:click={() => showSchemaModal = false}
						class="flex items-center gap-1.5 px-3 py-1.5 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300 rounded-lg text-sm transition-colors"
					>
						<XMark class="w-4 h-4" />
						<span>닫기</span>
					</button>
				</div>
			</div>

			<div class="flex-1 overflow-y-auto p-6 bg-gray-50 dark:bg-gray-900/50">
				{#if schemaLoading}
					<div class="flex justify-center items-center h-64">
						<div class="animate-spin rounded-full h-12 w-12 border-4 border-blue-500 border-t-transparent"></div>
					</div>
				{:else if schemaData && schemaData.tables}
					<div class="space-y-2">
						{#each schemaData.tables as table}
							<div class="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
								<button
									on:click={() => toggleTable(table.name)}
									class="w-full flex items-center justify-between p-4 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors"
								>
									<div class="flex items-center gap-3">
										{#if expandedTables.has(table.name)}
											<ChevronDown class="w-4 h-4 text-gray-500 dark:text-gray-400" />
										{:else}
											<ChevronRight class="w-4 h-4 text-gray-500 dark:text-gray-400" />
										{/if}
										<span class="font-medium text-gray-900 dark:text-white">{table.name}</span>
										<span class="text-xs px-2 py-0.5 bg-purple-100 dark:bg-purple-900/30 text-purple-600 dark:text-purple-400 rounded">
											{table.type}
										</span>
										<span class="text-sm text-gray-500 dark:text-gray-400">
											{table.columns?.length || 0} 컬럼
										</span>
									</div>
								</button>

								{#if expandedTables.has(table.name) && table.columns}
									<div class="border-t border-gray-200 dark:border-gray-700 p-4">
										<table class="w-full text-sm">
											<thead>
												<tr class="text-gray-500 dark:text-gray-400">
													<th class="text-left py-2 px-3">컬럼명</th>
													<th class="text-left py-2 px-3">타입</th>
													<th class="text-left py-2 px-3">NULL</th>
													<th class="text-left py-2 px-3">키</th>
													<th class="text-left py-2 px-3">설명</th>
												</tr>
											</thead>
											<tbody>
												{#each table.columns as col}
													<tr class="border-t border-gray-100 dark:border-gray-700/50 hover:bg-gray-50 dark:hover:bg-gray-700/30">
														<td class="py-2 px-3 text-gray-900 dark:text-white">{col.name}</td>
														<td class="py-2 px-3 text-gray-500 dark:text-gray-400 font-mono text-xs">{col.type}</td>
														<td class="py-2 px-3">
															{#if col.nullable}
																<span class="text-amber-600 dark:text-yellow-400">YES</span>
															{:else}
																<span class="text-gray-500">NO</span>
															{/if}
														</td>
														<td class="py-2 px-3">
															{#if col.is_primary_key}
																<span class="text-xs px-1.5 py-0.5 bg-amber-100 dark:bg-yellow-900/30 text-amber-600 dark:text-yellow-400 rounded">PK</span>
															{/if}
															{#if col.is_foreign_key}
																<span class="text-xs px-1.5 py-0.5 bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 rounded">FK</span>
															{/if}
														</td>
														<td class="py-2 px-3 text-gray-500 dark:text-gray-400">
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
					<div class="text-center py-16 text-gray-500 dark:text-gray-400">
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
		<div class="bg-white dark:bg-gray-800 rounded-2xl border border-gray-200 dark:border-gray-700 w-full max-w-5xl max-h-[90vh] overflow-hidden flex flex-col shadow-2xl">
			<div class="p-6 border-b border-gray-200 dark:border-gray-700 flex justify-between items-center">
				<div>
					<h2 class="text-xl font-semibold text-gray-900 dark:text-white">쿼리 실행</h2>
					<p class="text-sm text-gray-600 dark:text-gray-400">{selectedConnection.name} - {selectedConnection.database_name}</p>
				</div>
				<button
					on:click={() => showQueryModal = false}
					class="flex items-center gap-1.5 px-3 py-1.5 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300 rounded-lg text-sm transition-colors"
				>
					<XMark class="w-4 h-4" />
					<span>닫기</span>
				</button>
			</div>

			<div class="p-6 space-y-4">
				<!-- Text-to-SQL Section -->
				<div class="bg-gradient-to-r from-blue-50 to-indigo-50 dark:from-blue-900/20 dark:to-indigo-900/20 rounded-xl border border-blue-200 dark:border-blue-800 p-4">
					<div class="flex items-center gap-2 mb-2">
						<svg class="w-4 h-4 text-blue-600 dark:text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
						</svg>
						<label class="text-sm font-medium text-blue-700 dark:text-blue-300">AI SQL 생성</label>
						<span class="text-xs text-gray-500 dark:text-gray-400">(자연어 → SQL)</span>
					</div>
					<div class="flex gap-2">
						<input
							bind:value={naturalLanguageQuery}
							type="text"
							class="flex-1 px-4 py-2 bg-white dark:bg-gray-900 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-900 dark:text-white text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 focus:outline-none"
							placeholder="예: 각 DB 타입별 연결 수를 보여줘"
							on:keypress={(e) => e.key === 'Enter' && generateSQL()}
						/>
						<button
							on:click={generateSQL}
							disabled={sqlGenerating || !naturalLanguageQuery.trim()}
							class="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg transition-colors disabled:opacity-50 text-sm"
						>
							{#if sqlGenerating}
								<div class="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent"></div>
							{:else}
								<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
								</svg>
							{/if}
							SQL 생성
						</button>
					</div>
					<p class="text-xs text-gray-500 dark:text-gray-400 mt-2">스키마 정보를 기반으로 SQL이 생성됩니다. 생성 후 수정하여 실행하세요.</p>
				</div>

				<!-- SQL Editor Section -->
				<div>
					<label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">SQL 쿼리</label>
					<textarea
						bind:value={queryText}
						rows="4"
						class="w-full px-4 py-3 bg-white dark:bg-gray-900 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-900 dark:text-white font-mono text-sm focus:border-blue-500 focus:ring-1 focus:ring-blue-500 focus:outline-none"
						placeholder="SELECT * FROM table_name LIMIT 10"
					></textarea>
				</div>

				<button
					on:click={executeQuery}
					disabled={queryLoading || !queryText.trim()}
					class="flex items-center gap-2 px-4 py-2 bg-gradient-to-br from-primary/90 via-secondary/90 to-accent/90 hover:shadow-lg text-white rounded-lg transition-all disabled:opacity-50"
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
			<div class="flex-1 overflow-auto border-t border-gray-200 dark:border-gray-700">
				<div class="p-4 bg-gray-50 dark:bg-gray-900/50 text-sm text-gray-600 dark:text-gray-400">
					{queryResult.rows?.length ?? 0}건 조회됨 ({queryResult.execution_time_ms ?? 0}ms)
				</div>
					<div class="overflow-x-auto">
						<table class="w-full text-sm">
							<thead class="bg-gray-50 dark:bg-gray-900/50 sticky top-0">
								<tr>
									{#each queryResult.columns as col}
										<th class="text-left py-3 px-4 text-gray-600 dark:text-gray-400 font-medium border-b border-gray-200 dark:border-gray-700">{col}</th>
									{/each}
								</tr>
							</thead>
							<tbody>
								{#each queryResult.rows as row}
									<tr class="border-b border-gray-100 dark:border-gray-700/50 hover:bg-gray-50 dark:hover:bg-gray-700/30">
										{#each queryResult.columns as col}
											<td class="py-2 px-4 text-gray-700 dark:text-gray-300 font-mono text-xs">
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

<!-- Business Terms Modal -->
{#if showTermsModal && selectedConnection}
	<div class="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
		<div class="bg-white dark:bg-gray-800 rounded-2xl border border-gray-200 dark:border-gray-700 w-full max-w-3xl max-h-[90vh] overflow-hidden flex flex-col shadow-2xl">
			<div class="p-6 border-b border-gray-200 dark:border-gray-700 flex justify-between items-center">
				<div>
					<h2 class="text-xl font-semibold text-gray-900 dark:text-white">비즈니스 용어집</h2>
					<p class="text-sm text-gray-600 dark:text-gray-400">{selectedConnection.name} - 기술명 ↔ 비즈니스명 매핑</p>
				</div>
				<button
					on:click={() => showTermsModal = false}
					class="flex items-center gap-1.5 px-3 py-1.5 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300 rounded-lg text-sm transition-colors"
				>
					<XMark class="w-4 h-4" />
					<span>닫기</span>
				</button>
			</div>

			<div class="flex-1 overflow-y-auto p-6 bg-gray-50 dark:bg-gray-900/50">
				{#if termsLoading}
					<div class="flex justify-center items-center h-32">
						<div class="animate-spin rounded-full h-8 w-8 border-4 border-amber-500 border-t-transparent"></div>
					</div>
				{:else}
					<!-- Add Term Form -->
					<div class="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4 mb-6">
						<h3 class="text-sm font-medium text-gray-900 dark:text-white mb-3">용어 추가</h3>
						<div class="grid grid-cols-3 gap-3 mb-3">
							<div>
								<label class="block text-xs text-gray-600 dark:text-gray-400 mb-1">유형</label>
								<select bind:value={newTerm.term_type} class="w-full px-3 py-2 bg-white dark:bg-gray-900 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-900 dark:text-white text-sm">
									<option value="column">컬럼</option>
									<option value="table">테이블</option>
									<option value="schema">스키마</option>
								</select>
							</div>
							<div>
								<label class="block text-xs text-gray-600 dark:text-gray-400 mb-1">기술명 *</label>
								<input bind:value={newTerm.technical_name} type="text" class="w-full px-3 py-2 bg-white dark:bg-gray-900 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-900 dark:text-white text-sm" placeholder="user_id" />
							</div>
							<div>
								<label class="block text-xs text-gray-600 dark:text-gray-400 mb-1">비즈니스명 *</label>
								<input bind:value={newTerm.business_name} type="text" class="w-full px-3 py-2 bg-white dark:bg-gray-900 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-900 dark:text-white text-sm" placeholder="사용자 ID" />
							</div>
						</div>
						<div class="grid grid-cols-3 gap-3 mb-3">
							<div>
								<label class="block text-xs text-gray-600 dark:text-gray-400 mb-1">테이블명</label>
								<input bind:value={newTerm.table_name} type="text" class="w-full px-3 py-2 bg-white dark:bg-gray-900 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-900 dark:text-white text-sm" placeholder="users" />
							</div>
							<div class="col-span-2">
								<label class="block text-xs text-gray-600 dark:text-gray-400 mb-1">설명</label>
								<input bind:value={newTerm.description} type="text" class="w-full px-3 py-2 bg-white dark:bg-gray-900 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-900 dark:text-white text-sm" placeholder="용어 설명" />
							</div>
						</div>
						<button on:click={addTerm} class="px-4 py-2 bg-amber-600 hover:bg-amber-700 text-white rounded-lg text-sm transition-colors">
							용어 추가
						</button>
					</div>

					<!-- Terms List -->
					{#if termsData && termsData.terms && termsData.terms.length > 0}
						<div class="overflow-x-auto bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
							<table class="w-full text-sm">
								<thead>
									<tr class="text-gray-500 dark:text-gray-400 border-b border-gray-200 dark:border-gray-700">
										<th class="text-left py-2 px-3">유형</th>
										<th class="text-left py-2 px-3">기술명</th>
										<th class="text-left py-2 px-3">비즈니스명</th>
										<th class="text-left py-2 px-3">테이블</th>
										<th class="text-left py-2 px-3">설명</th>
										<th class="text-right py-2 px-3">작업</th>
									</tr>
								</thead>
								<tbody>
									{#each termsData.terms as term}
										<tr class="border-b border-gray-100 dark:border-gray-700/50 hover:bg-gray-50 dark:hover:bg-gray-700/30">
											<td class="py-2 px-3">
												<span class="text-xs px-2 py-0.5 rounded {term.term_type === 'column' ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400' : term.term_type === 'table' ? 'bg-green-100 dark:bg-green-900/30 text-green-600 dark:text-green-400' : 'bg-purple-100 dark:bg-purple-900/30 text-purple-600 dark:text-purple-400'}">
													{term.term_type}
												</span>
											</td>
											<td class="py-2 px-3 text-gray-900 dark:text-white font-mono text-xs">{term.technical_name}</td>
											<td class="py-2 px-3 text-amber-600 dark:text-amber-400">{term.business_name}</td>
											<td class="py-2 px-3 text-gray-500 dark:text-gray-400">{term.table_name || '-'}</td>
											<td class="py-2 px-3 text-gray-500">{term.description || '-'}</td>
											<td class="py-2 px-3 text-right">
												<button on:click={() => deleteTerm(term.id)} class="p-1 text-gray-400 hover:text-red-500 transition-colors">
													<GarbageBin class="size-4" />
												</button>
											</td>
										</tr>
									{/each}
								</tbody>
							</table>
						</div>
					{:else}
						<div class="text-center py-8 text-gray-500 dark:text-gray-400">
							등록된 용어가 없습니다. 위 폼에서 용어를 추가하세요.
						</div>
					{/if}
				{/if}
			</div>
		</div>
	</div>
{/if}

<!-- Permissions Modal -->
{#if showPermissionsModal && selectedConnection}
	<div class="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50 p-4">
		<div class="bg-white dark:bg-gray-800 rounded-2xl border border-gray-200 dark:border-gray-700 w-full max-w-2xl max-h-[90vh] overflow-hidden flex flex-col shadow-2xl">
			<div class="p-6 border-b border-gray-200 dark:border-gray-700 flex justify-between items-center">
				<div>
					<h2 class="text-xl font-semibold text-gray-900 dark:text-white">권한 관리</h2>
					<p class="text-sm text-gray-600 dark:text-gray-400">{selectedConnection.name} - 사용자/그룹별 접근 권한</p>
				</div>
				<button
					on:click={() => showPermissionsModal = false}
					class="flex items-center gap-1.5 px-3 py-1.5 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300 rounded-lg text-sm transition-colors"
				>
					<XMark class="w-4 h-4" />
					<span>닫기</span>
				</button>
			</div>

			<div class="flex-1 overflow-y-auto p-6 bg-gray-50 dark:bg-gray-900/50">
				{#if permissionsLoading}
					<div class="flex justify-center items-center h-32">
						<div class="animate-spin rounded-full h-8 w-8 border-4 border-purple-500 border-t-transparent"></div>
					</div>
				{:else}
					<!-- Add Permission Form -->
					<div class="bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700 p-4 mb-6">
						<h3 class="text-sm font-medium text-gray-900 dark:text-white mb-3">권한 추가</h3>
						<div class="grid grid-cols-3 gap-3 mb-3">
							<div>
								<label class="block text-xs text-gray-600 dark:text-gray-400 mb-1">사용자 ID</label>
								<input bind:value={newPermission.user_id} type="text" class="w-full px-3 py-2 bg-white dark:bg-gray-900 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-900 dark:text-white text-sm" placeholder="user@example.com" />
							</div>
							<div>
								<label class="block text-xs text-gray-600 dark:text-gray-400 mb-1">그룹 ID</label>
								<input bind:value={newPermission.group_id} type="text" class="w-full px-3 py-2 bg-white dark:bg-gray-900 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-900 dark:text-white text-sm" placeholder="data-team" />
							</div>
							<div>
								<label class="block text-xs text-gray-600 dark:text-gray-400 mb-1">권한 유형</label>
								<select bind:value={newPermission.permission_type} class="w-full px-3 py-2 bg-white dark:bg-gray-900 border border-gray-300 dark:border-gray-600 rounded-lg text-gray-900 dark:text-white text-sm">
									<option value="read">읽기 (read)</option>
									<option value="write">쓰기 (write)</option>
									<option value="admin">관리자 (admin)</option>
								</select>
							</div>
						</div>
						<p class="text-xs text-gray-500 dark:text-gray-400 mb-3">* 사용자 ID 또는 그룹 ID 중 하나는 필수입니다.</p>
						<button on:click={addPermission} class="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white rounded-lg text-sm transition-colors">
							권한 추가
						</button>
					</div>

					<!-- Permissions List -->
					{#if permissionsData && permissionsData.permissions && permissionsData.permissions.length > 0}
						<div class="overflow-x-auto bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
							<table class="w-full text-sm">
								<thead>
									<tr class="text-gray-500 dark:text-gray-400 border-b border-gray-200 dark:border-gray-700">
										<th class="text-left py-2 px-3">대상</th>
										<th class="text-left py-2 px-3">유형</th>
										<th class="text-left py-2 px-3">권한</th>
										<th class="text-left py-2 px-3">부여일</th>
										<th class="text-right py-2 px-3">작업</th>
									</tr>
								</thead>
								<tbody>
									{#each permissionsData.permissions as perm}
										<tr class="border-b border-gray-100 dark:border-gray-700/50 hover:bg-gray-50 dark:hover:bg-gray-700/30">
											<td class="py-2 px-3 text-gray-900 dark:text-white">
												{perm.user_id || perm.group_id || '-'}
											</td>
											<td class="py-2 px-3">
												<span class="text-xs px-2 py-0.5 rounded {perm.user_id ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400' : 'bg-green-100 dark:bg-green-900/30 text-green-600 dark:text-green-400'}">
													{perm.user_id ? '사용자' : '그룹'}
												</span>
											</td>
											<td class="py-2 px-3">
												<span class="text-xs px-2 py-0.5 rounded {perm.permission_type === 'admin' ? 'bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400' : perm.permission_type === 'write' ? 'bg-amber-100 dark:bg-amber-900/30 text-amber-600 dark:text-amber-400' : 'bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400'}">
													{perm.permission_type}
												</span>
											</td>
											<td class="py-2 px-3 text-gray-500 dark:text-gray-400 text-xs">
												{perm.created_at ? new Date(perm.created_at).toLocaleDateString('ko-KR') : '-'}
											</td>
											<td class="py-2 px-3 text-right">
												<button on:click={() => deletePermission(perm.id)} class="p-1 text-gray-400 hover:text-red-500 transition-colors">
													<GarbageBin class="size-4" />
												</button>
											</td>
										</tr>
									{/each}
								</tbody>
							</table>
						</div>
					{:else}
						<div class="text-center py-8 text-gray-500 dark:text-gray-400">
							등록된 권한이 없습니다. 위 폼에서 권한을 추가하세요.
						</div>
					{/if}
				{/if}
			</div>
		</div>
	</div>
{/if}

