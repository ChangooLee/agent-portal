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
	
	// Agent Thinking Flow (에이전트 사고 흐름)
	interface AgentStep {
		node: string;
		status: 'running' | 'completed' | 'error';
		description: string;
		details?: string;
		timestamp: number;
	}
	let agentSteps: AgentStep[] = [];
	let showAgentThinking = false;
	let agentReasoning = '';
	let agentAnswerSummary = '';
	
	// 노드별 한글 설명
	const nodeDescriptions: Record<string, string> = {
		entry: '질문 분석 중...',
		dialect_resolver: 'DB 종류 파악 중...',
		schema_selector: '관련 테이블 선택 중...',
		planner: '실행 계획 수립 중...',
		sql_generator: 'SQL 쿼리 생성 중...',
		sql_executor: 'SQL 실행 검증 중...',
		sql_repair: 'SQL 수정 중...',
		answer_formatter: '결과 정리 중...',
		human_review: '검토 필요'
	};
	
	// Model Selection
	let availableModels: { id: string; name: string }[] = [];
	let selectedModel = '';
	let modelsLoading = false;

	// DB 타입별 기본 프롬프트 (사용자 친화적)
	const defaultQueries: Record<string, string> = {
		mariadb: '테이블별 데이터 건수를 많은 순서로 보여줘',
		mysql: '테이블별 데이터 건수를 많은 순서로 보여줘',
		postgresql: '가장 큰 테이블 10개와 크기를 보여줘',
		clickhouse: 'otel_traces 테이블에서 최근 1시간 동안 가장 많이 호출된 서비스 5개를 보여줘',
		oracle: '테이블별 데이터 건수와 마지막 분석 일자를 보여줘',
		mssql: '각 테이블의 행 수와 인덱스 정보를 보여줘',
		sap_hana: '컬럼 저장 테이블의 메모리 사용량을 보여줘'
	};

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

	async function openQueryModal(conn: DBConnection) {
		selectedConnection = conn;
		queryText = '';
		queryResult = null;
		// 에이전트 사고 흐름 상태 초기화
		showAgentThinking = false;
		agentSteps = [];
		agentReasoning = '';
		agentAnswerSummary = '';
		showQueryModal = true;
		
		// DB 타입에 맞는 기본 프롬프트 설정
		naturalLanguageQuery = defaultQueries[conn.db_type] || '이 데이터베이스의 테이블 목록을 보여줘';
		
		// LiteLLM 모델 목록 로드
		await loadAvailableModels();
	}
	
	async function loadAvailableModels() {
		if (availableModels.length > 0) return; // 이미 로드됨
		
		modelsLoading = true;
		try {
			const response = await fetch(`${BACKEND_URL}/llm/models`);
			if (response.ok) {
				const data = await response.json();
				availableModels = data.data?.map((m: any) => ({
					id: m.id || m.model_name,
					name: m.id || m.model_name
				})) || [];
				
				// 첫 번째 모델을 기본 선택
				if (availableModels.length > 0 && !selectedModel) {
					selectedModel = availableModels[0].id;
				}
			}
		} catch (e) {
			console.error('Failed to load models:', e);
		} finally {
			modelsLoading = false;
		}
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
		showAgentThinking = true;
		agentSteps = [];
		agentReasoning = '';
		agentAnswerSummary = '';
		queryText = '';
		
		try {
			const requestBody: { question: string; model?: string } = {
				question: naturalLanguageQuery
			};
			
			// 선택된 모델이 있으면 포함
			if (selectedModel) {
				requestBody.model = selectedModel;
			}
			
			// SSE 스트리밍 요청
			const response = await fetch(`${BACKEND_URL}/text2sql/generate/stream`, {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({
					question: naturalLanguageQuery,
					connection_id: selectedConnection.id,
					model: selectedModel || undefined
				})
			});

			if (!response.ok) {
				const error = await response.json();
				throw new Error(error.detail || 'SQL 생성 실패');
			}

			const reader = response.body?.getReader();
			const decoder = new TextDecoder();
			
			if (!reader) {
				throw new Error('스트리밍을 지원하지 않습니다');
			}

			while (true) {
				const { done, value } = await reader.read();
				if (done) break;
				
				const chunk = decoder.decode(value, { stream: true });
				const lines = chunk.split('\n').filter(line => line.startsWith('data: '));
				
				for (const line of lines) {
					try {
						const data = JSON.parse(line.slice(6)); // "data: " 제거
						
						if (data.event === 'done') {
							// 최종 결과
							if (data.data?.sql) {
								queryText = data.data.sql;
							}
							if (data.data?.answer_summary) {
								agentAnswerSummary = data.data.answer_summary;
							}
							if (data.data?.success === false) {
								toast.error('SQL 생성 실패');
							} else {
								toast.success('SQL이 생성되었습니다. 필요시 수정 후 실행하세요.');
							}
							// 마지막 단계 완료 처리
							agentSteps = agentSteps.map(s => ({ ...s, status: 'completed' as const }));
						} else if (data.event === 'node_complete') {
							// 노드 완료 이벤트
							const nodeName = data.node || data.data?.node;
							const nodeDesc = nodeDescriptions[nodeName] || nodeName;
							
							// 이전 running 상태 완료 처리
							agentSteps = agentSteps.map(s => 
								s.status === 'running' ? { ...s, status: 'completed' as const } : s
							);
							
							// SQL이 생성되었으면 표시
							if (data.data?.sql) {
								queryText = data.data.sql;
							}
							
							// 새 단계 추가 (완료 상태로)
							const newStep: AgentStep = {
								node: nodeName,
								status: 'completed',
								description: nodeDesc,
								details: data.data?.plan ? JSON.stringify(data.data.plan, null, 2) : undefined,
								timestamp: Date.now()
							};
							agentSteps = [...agentSteps, newStep];
						} else if (data.event === 'start') {
							// 시작 이벤트 - UI 초기화 (이미 위에서 했지만 확인용)
							console.log('Text2SQL stream started:', data.data?.trace_id);
						} else if (data.event === 'error') {
							// 에러 이벤트
							toast.error(`SQL 생성 실패: ${data.data?.detail || '알 수 없는 오류'}`);
							agentSteps = agentSteps.map(s => 
								s.status === 'running' ? { ...s, status: 'error' as const } : s
							);
						}
					} catch (e) {
						console.debug('SSE parse error:', e);
					}
				}
			}
		} catch (e: any) {
			toast.error(`SQL 생성 실패: ${e.message}`);
			// 에러 발생 시 모든 단계 에러 처리
			agentSteps = agentSteps.map(s => 
				s.status === 'running' ? { ...s, status: 'error' as const } : s
			);
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

<div class="min-h-full bg-gray-950 text-slate-50">
	<!-- Hero Section -->
	<div class="relative overflow-hidden border-b border-slate-800/50">
		<div class="absolute inset-0 bg-gradient-to-br from-cyan-600/5 via-transparent to-blue-600/5"></div>
		<div class="absolute inset-0 bg-[linear-gradient(rgba(6,182,212,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(6,182,212,0.03)_1px,transparent_1px)] bg-[size:64px_64px]"></div>
		
		<div class="relative px-6 py-8">
			<div class="text-center mb-4">
				<h1 class="text-3xl md:text-4xl font-bold text-white mb-3">
					🗄️ Data Cloud
				</h1>
				<p class="text-base text-cyan-200/80 mb-6">
					데이터 복제 없이 실시간으로 데이터베이스에 연결하여 스키마 조회 및 쿼리를 실행할 수 있습니다.
				</p>
				<button
					on:click={openAddModal}
					class="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-cyan-600 hover:bg-cyan-500 text-white font-medium shadow-lg shadow-cyan-500/25 hover:shadow-xl hover:-translate-y-0.5 transition-all duration-300"
				>
					<Plus class="size-5" />
					<span>연결 추가</span>
				</button>
			</div>

			<!-- Stats Cards -->
			<div class="grid grid-cols-2 md:grid-cols-4 gap-4">
				<div class="bg-slate-900/80 backdrop-blur-sm rounded-xl p-4 border border-slate-800/50">
					<div class="flex items-center gap-3">
						<div class="p-2 rounded-lg bg-cyan-500/20">
							<Cube class="size-5 text-cyan-400" />
						</div>
						<div>
							<div class="text-2xl font-bold text-white">{connections.length}</div>
							<div class="text-xs text-slate-400">총 연결</div>
						</div>
					</div>
				</div>
				<div class="bg-slate-900/80 backdrop-blur-sm rounded-xl p-4 border border-slate-800/50">
					<div class="flex items-center gap-3">
						<div class="p-2 rounded-lg bg-emerald-500/20">
							<Check class="size-5 text-emerald-400" />
						</div>
						<div>
							<div class="text-2xl font-bold text-white">{connections.filter(c => c.health_status === 'healthy').length}</div>
							<div class="text-xs text-slate-400">정상 연결</div>
						</div>
					</div>
				</div>
				<div class="bg-slate-900/80 backdrop-blur-sm rounded-xl p-4 border border-slate-800/50">
					<div class="flex items-center gap-3">
						<div class="p-2 rounded-lg bg-violet-500/20">
							<svg class="size-5 text-violet-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20.25 6.375c0 2.278-3.694 4.125-8.25 4.125S3.75 8.653 3.75 6.375m16.5 0c0-2.278-3.694-4.125-8.25-4.125S3.75 4.097 3.75 6.375m16.5 0v11.25c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125V6.375" />
							</svg>
						</div>
						<div>
							<div class="text-2xl font-bold text-white">{new Set(connections.map(c => c.db_type)).size}</div>
							<div class="text-xs text-slate-400">DB 유형</div>
						</div>
					</div>
				</div>
				<div class="bg-slate-900/80 backdrop-blur-sm rounded-xl p-4 border border-slate-800/50">
					<div class="flex items-center gap-3">
						<div class="p-2 rounded-lg bg-orange-500/20">
							<XMark class="size-5 text-orange-400" />
						</div>
						<div>
							<div class="text-2xl font-bold text-white">{connections.filter(c => c.health_status === 'unhealthy').length}</div>
							<div class="text-xs text-slate-400">오류 연결</div>
						</div>
					</div>
				</div>
			</div>
		</div>
	</div>

	<!-- Content Section -->
	<div class="px-6 py-8">
		<!-- Connection List -->
		<div class="bg-slate-900/50 backdrop-blur-xl rounded-xl border border-slate-800/50 overflow-hidden">
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
						<thead class="bg-slate-800/50 border-b border-slate-700/50">
							<tr>
								<th class="px-6 py-3 text-left text-xs font-medium text-white uppercase tracking-wider">데이터베이스</th>
								<th class="px-6 py-3 text-left text-xs font-medium text-white uppercase tracking-wider">상태</th>
								<th class="px-6 py-3 text-left text-xs font-medium text-white uppercase tracking-wider">호스트</th>
								<th class="px-6 py-3 text-right text-xs font-medium text-white uppercase tracking-wider">작업</th>
							</tr>
						</thead>
						<tbody class="divide-y divide-slate-800/50">
							{#each connections as conn}
								<tr class="border-b border-slate-800/50 hover:bg-slate-800/80 hover:border-cyan-500/50 transition-all duration-200">
									<td class="px-6 py-4">
										<div class="flex items-center gap-3">
											<div class="p-2 rounded-lg bg-cyan-500/20">
												<Cube class="size-5 text-cyan-400" />
											</div>
											<div>
												<div class="font-medium text-white">{conn.name}</div>
												<div class="text-sm text-slate-400">{getDbTypeLabel(conn.db_type)}</div>
											</div>
										</div>
									</td>
									<td class="px-6 py-4">
										<span class="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-medium {conn.health_status === 'healthy' ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' : conn.health_status === 'unhealthy' ? 'bg-red-500/20 text-red-400 border border-red-500/30' : 'bg-slate-500/20 text-slate-400 border border-slate-500/30'}">
											{#if conn.health_status === 'healthy'}
												<Check class="size-3" />
											{:else if conn.health_status === 'unhealthy'}
												<XMark class="size-3" />
											{/if}
											{getHealthStatusText(conn.health_status)}
										</span>
									</td>
									<td class="px-6 py-4">
										<div class="text-sm text-white font-medium">{conn.host}:{conn.port}</div>
										<div class="text-sm text-slate-400">{conn.database_name}</div>
									</td>
									<td class="px-6 py-4">
										<div class="flex items-center justify-end gap-2">
											<button
												on:click={() => testConnection(conn)}
												class="p-2 text-slate-400 hover:text-emerald-400 hover:bg-emerald-500/20 rounded-lg transition-all duration-200"
												title="연결 테스트"
											>
												<Bolt class="size-4" />
											</button>
											<button
												on:click={() => openSchemaModal(conn)}
												class="px-3 py-1.5 text-sm text-cyan-400 hover:text-cyan-300 hover:bg-cyan-500/20 rounded-lg transition-all duration-200"
											>
												스키마
											</button>
											<button
												on:click={() => openQueryModal(conn)}
												class="px-3 py-1.5 text-sm text-blue-400 hover:text-blue-300 hover:bg-blue-500/20 rounded-lg transition-all duration-200"
											>
												쿼리
											</button>
											<button
												on:click={() => openTermsModal(conn)}
												class="px-3 py-1.5 text-sm text-amber-400 hover:text-amber-300 hover:bg-amber-500/20 rounded-lg transition-all duration-200"
											>
												용어집
											</button>
											<button
												on:click={() => openPermissionsModal(conn)}
												class="px-3 py-1.5 text-sm text-purple-400 hover:text-purple-300 hover:bg-purple-500/20 rounded-lg transition-all duration-200"
											>
												권한
											</button>
											<button
												on:click={() => openEditModal(conn)}
												class="p-2 text-slate-400 hover:text-cyan-400 hover:bg-cyan-500/20 rounded-lg transition-all duration-200"
												title="편집"
											>
												<Pencil class="size-4" />
											</button>
											<button
												on:click={() => deleteConnection(conn)}
												class="p-2 text-slate-400 hover:text-red-400 hover:bg-red-500/20 rounded-lg transition-all duration-200"
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
		<div class="bg-slate-900 border border-slate-800/50 rounded-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto shadow-xl shadow-black/30">
			<div class="px-6 py-4 border-b border-slate-700/50">
				<h2 class="text-xl font-semibold text-white">
					{editingConnection ? '연결 수정' : '새 연결 추가'}
				</h2>
			</div>

			<div class="p-6 space-y-4">
				<div>
					<label class="block text-sm font-medium text-white mb-1">연결 이름</label>
					<input
						type="text"
						bind:value={formData.name}
						class="w-full px-4 py-2 bg-slate-800/50 border border-slate-700/50 rounded-lg text-white focus:border-cyan-500/50 focus:ring-1 focus:ring-cyan-500/50 focus:outline-none placeholder:text-slate-400"
						placeholder="예: Production MariaDB"
					/>
				</div>

				<div>
					<label class="block text-sm font-medium text-white mb-1">설명</label>
					<input
						type="text"
						bind:value={formData.description}
						class="w-full px-4 py-2 bg-slate-800/50 border border-slate-700/50 rounded-lg text-white focus:border-cyan-500/50 focus:ring-1 focus:ring-cyan-500/50 focus:outline-none placeholder:text-slate-400"
						placeholder="선택사항"
					/>
				</div>

				<div>
					<label class="block text-sm font-medium text-white mb-1">데이터베이스 유형</label>
					<select
						bind:value={formData.db_type}
						on:change={onDbTypeChange}
						class="w-full px-4 py-2 bg-slate-800/50 border border-slate-700/50 rounded-lg text-white focus:border-cyan-500/50 focus:ring-1 focus:ring-cyan-500/50 focus:outline-none"
					>
						{#each dbTypes as dbType}
							<option value={dbType.value}>{dbType.label}</option>
						{/each}
					</select>
				</div>

				<div class="grid grid-cols-3 gap-4">
					<div class="col-span-2">
						<label class="block text-sm font-medium text-white mb-1">호스트</label>
						<input
							type="text"
							bind:value={formData.host}
							class="w-full px-4 py-2 bg-slate-800/50 border border-slate-700/50 rounded-lg text-white focus:border-cyan-500/50 focus:ring-1 focus:ring-cyan-500/50 focus:outline-none placeholder:text-slate-400"
							placeholder="localhost"
						/>
					</div>
					<div>
						<label class="block text-sm font-medium text-white mb-1">포트</label>
						<input
							type="number"
							bind:value={formData.port}
							class="w-full px-4 py-2 bg-slate-800/50 border border-slate-700/50 rounded-lg text-white focus:border-cyan-500/50 focus:ring-1 focus:ring-cyan-500/50 focus:outline-none placeholder:text-slate-400"
						/>
					</div>
				</div>

				<div>
					<label class="block text-sm font-medium text-white mb-1">데이터베이스 이름</label>
					<input
						type="text"
						bind:value={formData.database_name}
						class="w-full px-4 py-2 bg-slate-800/50 border border-slate-700/50 rounded-lg text-white focus:border-cyan-500/50 focus:ring-1 focus:ring-cyan-500/50 focus:outline-none placeholder:text-slate-400"
						placeholder="database_name"
					/>
				</div>

				<div class="grid grid-cols-2 gap-4">
					<div>
						<label class="block text-sm font-medium text-white mb-1">사용자 이름</label>
						<input
							type="text"
							bind:value={formData.username}
							class="w-full px-4 py-2 bg-slate-800/50 border border-slate-700/50 rounded-lg text-white focus:border-cyan-500/50 focus:ring-1 focus:ring-cyan-500/50 focus:outline-none placeholder:text-slate-400"
							placeholder="username"
						/>
					</div>
					<div>
						<label class="block text-sm font-medium text-white mb-1">비밀번호</label>
						<input
							type="password"
							bind:value={formData.password}
							class="w-full px-4 py-2 bg-slate-800/50 border border-slate-700/50 rounded-lg text-white focus:border-cyan-500/50 focus:ring-1 focus:ring-cyan-500/50 focus:outline-none placeholder:text-slate-400"
							placeholder={editingConnection ? '변경 시 입력' : '비밀번호'}
						/>
					</div>
				</div>

				<div class="flex items-center gap-2">
					<input
						type="checkbox"
						id="enabled"
						bind:checked={formData.enabled}
						class="w-4 h-4 rounded border-slate-700/50 bg-slate-800/50 text-cyan-500 focus:ring-cyan-500"
					/>
					<label for="enabled" class="text-sm text-slate-300">활성화</label>
				</div>
			</div>

			<div class="px-6 py-4 border-t border-slate-700/50 flex justify-between">
				<button
					on:click={testNewConnection}
					class="px-4 py-2 bg-cyan-500/20 hover:bg-cyan-500/30 text-cyan-400 rounded-lg transition-colors"
				>
					연결 테스트
				</button>
				<div class="flex gap-2">
					<button
						on:click={() => showModal = false}
						class="px-4 py-2 bg-slate-800/50 hover:bg-slate-800/80 text-slate-300 hover:text-white rounded-lg transition-colors"
					>
						취소
					</button>
					<button
						on:click={saveConnection}
						class="px-4 py-2 bg-cyan-600 hover:bg-cyan-500 text-white rounded-lg transition-colors"
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
		<div class="bg-slate-900 border border-slate-800/50 rounded-2xl w-full max-w-4xl max-h-[90vh] overflow-hidden flex flex-col shadow-xl shadow-black/30">
			<div class="px-6 py-4 border-b border-slate-700/50 flex justify-between items-center">
				<div>
					<h2 class="text-xl font-semibold text-white">스키마 탐색</h2>
					<p class="text-sm text-slate-400">{selectedConnection.name} - {selectedConnection.database_name}</p>
				</div>
				<div class="flex gap-2">
					<button
						on:click={refreshSchema}
						disabled={schemaLoading}
						class="px-3 py-1.5 bg-cyan-500/20 hover:bg-cyan-500/30 text-cyan-400 rounded-lg text-sm transition-colors disabled:opacity-50"
					>
						새로고침
					</button>
					<button
						on:click={() => showSchemaModal = false}
						class="flex items-center gap-1.5 px-3 py-1.5 bg-slate-800/50 hover:bg-slate-800/80 text-slate-300 hover:text-white rounded-lg text-sm transition-colors"
					>
						<XMark class="w-4 h-4" />
						<span>닫기</span>
					</button>
				</div>
			</div>

			<div class="flex-1 overflow-y-auto p-6 bg-slate-900">
				{#if schemaLoading}
					<div class="flex justify-center items-center h-64">
						<div class="animate-spin rounded-full h-12 w-12 border-4 border-cyan-500 border-t-transparent"></div>
					</div>
				{:else if schemaData && schemaData.tables}
					<div class="space-y-2">
						{#each schemaData.tables as table}
							<div class="bg-slate-800/50 rounded-lg border border-slate-700/50">
								<button
									on:click={() => toggleTable(table.name)}
									class="w-full flex items-center justify-between p-4 hover:bg-slate-800/80 transition-colors"
								>
									<div class="flex items-center gap-3">
										{#if expandedTables.has(table.name)}
											<ChevronDown class="w-4 h-4 text-slate-400" />
										{:else}
											<ChevronRight class="w-4 h-4 text-slate-400" />
										{/if}
										<span class="font-medium text-white">{table.name}</span>
										<span class="text-xs px-2 py-0.5 bg-purple-500/20 text-purple-400 border border-purple-500/30 rounded">
											{table.type}
										</span>
										<span class="text-sm text-slate-400">
											{table.columns?.length || 0} 컬럼
										</span>
									</div>
								</button>

								{#if expandedTables.has(table.name) && table.columns}
									<div class="border-t border-slate-700/50 p-4">
										<table class="w-full text-sm">
											<thead>
												<tr class="text-slate-400">
													<th class="text-left py-2 px-3">컬럼명</th>
													<th class="text-left py-2 px-3">타입</th>
													<th class="text-left py-2 px-3">NULL</th>
													<th class="text-left py-2 px-3">키</th>
													<th class="text-left py-2 px-3">설명</th>
												</tr>
											</thead>
											<tbody>
												{#each table.columns as col}
													<tr class="border-t border-slate-800/50 hover:bg-slate-800/80 transition-colors">
														<td class="py-2 px-3 text-white">{col.name}</td>
														<td class="py-2 px-3 text-slate-400 font-mono text-xs">{col.type}</td>
														<td class="py-2 px-3">
															{#if col.nullable}
																<span class="text-amber-400">YES</span>
															{:else}
																<span class="text-slate-500">NO</span>
															{/if}
														</td>
														<td class="py-2 px-3">
															{#if col.is_primary_key}
																<span class="text-xs px-1.5 py-0.5 bg-amber-500/20 text-amber-400 border border-amber-500/30 rounded">PK</span>
															{/if}
															{#if col.is_foreign_key}
																<span class="text-xs px-1.5 py-0.5 bg-blue-500/20 text-blue-400 border border-blue-500/30 rounded">FK</span>
															{/if}
														</td>
														<td class="py-2 px-3 text-slate-400">
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
					<div class="text-center py-16 text-slate-400">
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
		<div class="bg-slate-900 border border-slate-800/50 rounded-2xl w-full max-w-5xl max-h-[90vh] overflow-hidden flex flex-col shadow-xl shadow-black/30">
			<div class="px-6 py-4 border-b border-slate-700/50 flex justify-between items-center">
				<div>
					<h2 class="text-xl font-semibold text-white">쿼리 실행</h2>
					<p class="text-sm text-slate-400">{selectedConnection.name} - {selectedConnection.database_name}</p>
				</div>
				<button
					on:click={() => showQueryModal = false}
					class="flex items-center gap-1.5 px-3 py-1.5 bg-slate-800/50 hover:bg-slate-800/80 text-slate-300 hover:text-white rounded-lg text-sm transition-colors"
				>
					<XMark class="w-4 h-4" />
					<span>닫기</span>
				</button>
			</div>

			<div class="p-6 space-y-4 flex-1 overflow-y-auto">
				<!-- Text-to-SQL Section -->
				<div class="bg-blue-500/20 border border-blue-500/30 rounded-xl p-4">
					<div class="flex items-center justify-between mb-2">
						<div class="flex items-center gap-2">
							<svg class="w-4 h-4 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
							</svg>
							<label class="text-sm font-medium text-blue-300">AI SQL 생성</label>
							<span class="text-xs text-slate-400">(자연어 → SQL)</span>
						</div>
						<!-- Model Selection -->
						<div class="flex items-center gap-2">
							<label class="text-xs text-slate-400">모델:</label>
							{#if modelsLoading}
								<div class="animate-spin rounded-full h-4 w-4 border-2 border-blue-400 border-t-transparent"></div>
							{:else}
								<select
									bind:value={selectedModel}
									class="px-2 py-1 bg-slate-800/50 border border-slate-700/50 rounded text-xs text-slate-300 focus:border-blue-500/50 focus:ring-1 focus:ring-blue-500/50 focus:outline-none"
								>
									{#each availableModels as model}
										<option value={model.id}>{model.name}</option>
									{/each}
								</select>
							{/if}
						</div>
					</div>
					<div class="flex gap-2">
						<input
							bind:value={naturalLanguageQuery}
							type="text"
							class="flex-1 px-4 py-2 bg-slate-800/50 border border-slate-700/50 rounded-lg text-white text-sm focus:border-blue-500/50 focus:ring-1 focus:ring-blue-500/50 focus:outline-none placeholder:text-slate-400"
							placeholder="예: 각 DB 타입별 연결 수를 보여줘"
							on:keypress={(e) => e.key === 'Enter' && generateSQL()}
						/>
						<button
							on:click={generateSQL}
							disabled={sqlGenerating || !naturalLanguageQuery.trim()}
							class="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg transition-colors disabled:opacity-50 text-sm"
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
					<p class="text-xs text-slate-400 mt-2">스키마 정보를 기반으로 SQL이 생성됩니다. 생성 후 수정하여 실행하세요.</p>
				</div>

				<!-- Agent Thinking Flow Section (Compact) -->
				{#if showAgentThinking && (agentSteps.length > 0 || sqlGenerating)}
					<div class="bg-purple-500/20 border border-purple-500/30 rounded-lg px-4 py-2">
						{#if sqlGenerating}
							<!-- 진행 중: 현재 단계만 한 줄로 표시 -->
							{@const currentStep = agentSteps.find(s => s.status === 'running') || agentSteps[agentSteps.length - 1]}
							<div class="flex items-center gap-3">
								<div class="flex items-center gap-2">
									<svg class="w-4 h-4 text-purple-400 animate-pulse" fill="none" stroke="currentColor" viewBox="0 0 24 24">
										<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
									</svg>
									<span class="text-sm font-medium text-purple-300">
										{currentStep?.description || '처리 중...'}
									</span>
								</div>
								<div class="flex items-center gap-1 ml-auto">
									<span class="text-xs text-slate-400">
										{agentSteps.length}/7 단계
									</span>
									<div class="flex items-center gap-0.5">
										{#each Array(7) as _, i}
											<div class="w-1.5 h-1.5 rounded-full {i < agentSteps.length ? 'bg-purple-500' : 'bg-slate-600'}"></div>
										{/each}
									</div>
								</div>
							</div>
						{:else if agentAnswerSummary}
							<!-- 완료: 요약만 표시 -->
							<div class="flex items-start gap-2">
								<svg class="w-4 h-4 text-emerald-400 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
								</svg>
								<div class="flex-1 min-w-0">
									<p class="text-xs text-slate-300 line-clamp-2">{agentAnswerSummary}</p>
								</div>
								<button
									on:click={() => showAgentThinking = false}
									class="text-xs text-slate-400 hover:text-slate-300 flex-shrink-0"
								>
									닫기
								</button>
							</div>
						{:else}
							<!-- 완료했지만 요약이 없는 경우 -->
							<div class="flex items-center gap-2">
								<svg class="w-4 h-4 text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
								</svg>
								<span class="text-sm text-slate-300">SQL 생성 완료</span>
								<button
									on:click={() => showAgentThinking = false}
									class="text-xs text-slate-400 hover:text-slate-300 ml-auto"
								>
									닫기
								</button>
							</div>
						{/if}
					</div>
				{/if}

				<!-- SQL Editor Section -->
				<div>
					<label class="block text-sm font-medium text-white mb-2">SQL 쿼리</label>
					<textarea
						bind:value={queryText}
						rows="4"
						class="w-full px-4 py-3 bg-slate-800/50 border border-slate-700/50 rounded-lg text-white font-mono text-sm focus:border-blue-500/50 focus:ring-1 focus:ring-blue-500/50 focus:outline-none placeholder:text-slate-400"
						placeholder="SELECT * FROM table_name LIMIT 10"
					></textarea>
				</div>

				<button
					on:click={executeQuery}
					disabled={queryLoading || !queryText.trim()}
					class="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg transition-colors disabled:opacity-50"
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
			<div class="flex-1 overflow-auto border-t border-slate-700/50">
				<div class="p-4 bg-slate-800/50 text-sm text-slate-400">
					{queryResult.rows?.length ?? 0}건 조회됨 ({queryResult.execution_time_ms ?? 0}ms)
				</div>
					<div class="overflow-x-auto">
						<table class="w-full text-sm">
							<thead class="bg-slate-800/50 sticky top-0">
								<tr>
									{#each queryResult.columns as col}
										<th class="text-left py-3 px-4 text-slate-300 font-medium border-b border-slate-700/50">{col}</th>
									{/each}
								</tr>
							</thead>
							<tbody>
								{#each queryResult.rows as row}
									<tr class="border-b border-slate-800/50 hover:bg-slate-800/80 transition-colors">
										{#each queryResult.columns as col}
											<td class="py-2 px-4 text-slate-200 font-mono text-xs">
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
		<div class="bg-slate-900 border border-slate-800/50 rounded-2xl w-full max-w-3xl max-h-[90vh] overflow-hidden flex flex-col shadow-xl shadow-black/30">
			<div class="px-6 py-4 border-b border-slate-700/50 flex justify-between items-center">
				<div>
					<h2 class="text-xl font-semibold text-white">비즈니스 용어집</h2>
					<p class="text-sm text-slate-400">{selectedConnection.name} - 기술명 ↔ 비즈니스명 매핑</p>
				</div>
				<button
					on:click={() => showTermsModal = false}
					class="flex items-center gap-1.5 px-3 py-1.5 bg-slate-800/50 hover:bg-slate-800/80 text-slate-300 hover:text-white rounded-lg text-sm transition-colors"
				>
					<XMark class="w-4 h-4" />
					<span>닫기</span>
				</button>
			</div>

			<div class="flex-1 overflow-y-auto p-6 bg-slate-900">
				{#if termsLoading}
					<div class="flex justify-center items-center h-32">
						<div class="animate-spin rounded-full h-8 w-8 border-4 border-amber-500 border-t-transparent"></div>
					</div>
				{:else}
					<!-- Add Term Form -->
					<div class="bg-slate-800/50 rounded-lg border border-slate-700/50 p-4 mb-6">
						<h3 class="text-sm font-medium text-white mb-3">용어 추가</h3>
						<div class="grid grid-cols-3 gap-3 mb-3">
							<div>
								<label class="block text-xs text-slate-400 mb-1">유형</label>
								<select bind:value={newTerm.term_type} class="w-full px-3 py-2 bg-slate-800/50 border border-slate-700/50 rounded-lg text-white text-sm focus:border-amber-500/50 focus:ring-1 focus:ring-amber-500/50 focus:outline-none">
									<option value="column">컬럼</option>
									<option value="table">테이블</option>
									<option value="schema">스키마</option>
								</select>
							</div>
							<div>
								<label class="block text-xs text-slate-400 mb-1">기술명 *</label>
								<input bind:value={newTerm.technical_name} type="text" class="w-full px-3 py-2 bg-slate-800/50 border border-slate-700/50 rounded-lg text-white text-sm focus:border-amber-500/50 focus:ring-1 focus:ring-amber-500/50 focus:outline-none placeholder:text-slate-400" placeholder="user_id" />
							</div>
							<div>
								<label class="block text-xs text-slate-400 mb-1">비즈니스명 *</label>
								<input bind:value={newTerm.business_name} type="text" class="w-full px-3 py-2 bg-slate-800/50 border border-slate-700/50 rounded-lg text-white text-sm focus:border-amber-500/50 focus:ring-1 focus:ring-amber-500/50 focus:outline-none placeholder:text-slate-400" placeholder="사용자 ID" />
							</div>
						</div>
						<div class="grid grid-cols-3 gap-3 mb-3">
							<div>
								<label class="block text-xs text-slate-400 mb-1">테이블명</label>
								<input bind:value={newTerm.table_name} type="text" class="w-full px-3 py-2 bg-slate-800/50 border border-slate-700/50 rounded-lg text-white text-sm focus:border-amber-500/50 focus:ring-1 focus:ring-amber-500/50 focus:outline-none placeholder:text-slate-400" placeholder="users" />
							</div>
							<div class="col-span-2">
								<label class="block text-xs text-slate-400 mb-1">설명</label>
								<input bind:value={newTerm.description} type="text" class="w-full px-3 py-2 bg-slate-800/50 border border-slate-700/50 rounded-lg text-white text-sm focus:border-amber-500/50 focus:ring-1 focus:ring-amber-500/50 focus:outline-none placeholder:text-slate-400" placeholder="용어 설명" />
							</div>
						</div>
						<button on:click={addTerm} class="px-4 py-2 bg-amber-600 hover:bg-amber-500 text-white rounded-lg text-sm transition-colors">
							용어 추가
						</button>
					</div>

					<!-- Terms List -->
					{#if termsData && termsData.terms && termsData.terms.length > 0}
						<div class="overflow-x-auto bg-slate-800/50 rounded-lg border border-slate-700/50">
							<table class="w-full text-sm">
								<thead>
									<tr class="bg-slate-800/50 border-b border-slate-700/50">
										<th class="text-left py-2 px-3 text-white uppercase tracking-wider text-xs font-medium">유형</th>
										<th class="text-left py-2 px-3 text-white uppercase tracking-wider text-xs font-medium">기술명</th>
										<th class="text-left py-2 px-3 text-white uppercase tracking-wider text-xs font-medium">비즈니스명</th>
										<th class="text-left py-2 px-3 text-white uppercase tracking-wider text-xs font-medium">테이블</th>
										<th class="text-left py-2 px-3 text-white uppercase tracking-wider text-xs font-medium">설명</th>
										<th class="text-right py-2 px-3 text-white uppercase tracking-wider text-xs font-medium">작업</th>
									</tr>
								</thead>
								<tbody>
									{#each termsData.terms as term}
										<tr class="border-b border-slate-800/50 hover:bg-slate-800/80 hover:border-amber-500/50 transition-all duration-200">
											<td class="py-2 px-3">
												<span class="text-xs px-2 py-0.5 rounded {term.term_type === 'column' ? 'bg-blue-500/20 text-blue-400 border border-blue-500/30' : term.term_type === 'table' ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30' : 'bg-purple-500/20 text-purple-400 border border-purple-500/30'}">
													{term.term_type}
												</span>
											</td>
											<td class="py-2 px-3 text-white font-mono text-xs">{term.technical_name}</td>
											<td class="py-2 px-3 text-amber-400">{term.business_name}</td>
											<td class="py-2 px-3 text-slate-400">{term.table_name || '-'}</td>
											<td class="py-2 px-3 text-slate-400">{term.description || '-'}</td>
											<td class="py-2 px-3 text-right">
												<button on:click={() => deleteTerm(term.id)} class="p-1 text-slate-400 hover:text-red-400 hover:bg-red-500/20 rounded-lg transition-colors">
													<GarbageBin class="size-4" />
												</button>
											</td>
										</tr>
									{/each}
								</tbody>
							</table>
						</div>
					{:else}
						<div class="bg-slate-800/50 border border-slate-700/50 rounded-xl p-12 text-center">
							<p class="text-slate-400">등록된 용어가 없습니다. 위 폼에서 용어를 추가하세요.</p>
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
		<div class="bg-slate-900 border border-slate-800/50 rounded-2xl w-full max-w-2xl max-h-[90vh] overflow-hidden flex flex-col shadow-xl shadow-black/30">
			<div class="px-6 py-4 border-b border-slate-700/50 flex justify-between items-center">
				<div>
					<h2 class="text-xl font-semibold text-white">권한 관리</h2>
					<p class="text-sm text-slate-400">{selectedConnection.name} - 사용자/그룹별 접근 권한</p>
				</div>
				<button
					on:click={() => showPermissionsModal = false}
					class="flex items-center gap-1.5 px-3 py-1.5 bg-slate-800/50 hover:bg-slate-800/80 text-slate-300 hover:text-white rounded-lg text-sm transition-colors"
				>
					<XMark class="w-4 h-4" />
					<span>닫기</span>
				</button>
			</div>

			<div class="flex-1 overflow-y-auto p-6 bg-slate-900">
				{#if permissionsLoading}
					<div class="flex justify-center items-center h-32">
						<div class="animate-spin rounded-full h-8 w-8 border-4 border-purple-500 border-t-transparent"></div>
					</div>
				{:else}
					<!-- Add Permission Form -->
					<div class="bg-slate-800/50 rounded-lg border border-slate-700/50 p-4 mb-6">
						<h3 class="text-sm font-medium text-white mb-3">권한 추가</h3>
						<div class="grid grid-cols-3 gap-3 mb-3">
							<div>
								<label class="block text-xs text-slate-400 mb-1">사용자 ID</label>
								<input bind:value={newPermission.user_id} type="text" class="w-full px-3 py-2 bg-slate-800/50 border border-slate-700/50 rounded-lg text-white text-sm focus:border-purple-500/50 focus:ring-1 focus:ring-purple-500/50 focus:outline-none placeholder:text-slate-400" placeholder="user@example.com" />
							</div>
							<div>
								<label class="block text-xs text-slate-400 mb-1">그룹 ID</label>
								<input bind:value={newPermission.group_id} type="text" class="w-full px-3 py-2 bg-slate-800/50 border border-slate-700/50 rounded-lg text-white text-sm focus:border-purple-500/50 focus:ring-1 focus:ring-purple-500/50 focus:outline-none placeholder:text-slate-400" placeholder="data-team" />
							</div>
							<div>
								<label class="block text-xs text-slate-400 mb-1">권한 유형</label>
								<select bind:value={newPermission.permission_type} class="w-full px-3 py-2 bg-slate-800/50 border border-slate-700/50 rounded-lg text-white text-sm focus:border-purple-500/50 focus:ring-1 focus:ring-purple-500/50 focus:outline-none">
									<option value="read">읽기 (read)</option>
									<option value="write">쓰기 (write)</option>
									<option value="admin">관리자 (admin)</option>
								</select>
							</div>
						</div>
						<p class="text-xs text-slate-400 mb-3">* 사용자 ID 또는 그룹 ID 중 하나는 필수입니다.</p>
						<button on:click={addPermission} class="px-4 py-2 bg-purple-600 hover:bg-purple-500 text-white rounded-lg text-sm transition-colors">
							권한 추가
						</button>
					</div>

					<!-- Permissions List -->
					{#if permissionsData && permissionsData.permissions && permissionsData.permissions.length > 0}
						<div class="overflow-x-auto bg-slate-800/50 rounded-lg border border-slate-700/50">
							<table class="w-full text-sm">
								<thead>
									<tr class="bg-slate-800/50 border-b border-slate-700/50">
										<th class="text-left py-2 px-3 text-white uppercase tracking-wider text-xs font-medium">대상</th>
										<th class="text-left py-2 px-3 text-white uppercase tracking-wider text-xs font-medium">유형</th>
										<th class="text-left py-2 px-3 text-white uppercase tracking-wider text-xs font-medium">권한</th>
										<th class="text-left py-2 px-3 text-white uppercase tracking-wider text-xs font-medium">부여일</th>
										<th class="text-right py-2 px-3 text-white uppercase tracking-wider text-xs font-medium">작업</th>
									</tr>
								</thead>
								<tbody>
									{#each permissionsData.permissions as perm}
										<tr class="border-b border-slate-800/50 hover:bg-slate-800/80 hover:border-purple-500/50 transition-all duration-200">
											<td class="py-2 px-3 text-white">
												{perm.user_id || perm.group_id || '-'}
											</td>
											<td class="py-2 px-3">
												<span class="text-xs px-2 py-0.5 rounded {perm.user_id ? 'bg-blue-500/20 text-blue-400 border border-blue-500/30' : 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'}">
													{perm.user_id ? '사용자' : '그룹'}
												</span>
											</td>
											<td class="py-2 px-3">
												<span class="text-xs px-2 py-0.5 rounded {perm.permission_type === 'admin' ? 'bg-red-500/20 text-red-400 border border-red-500/30' : perm.permission_type === 'write' ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30' : 'bg-slate-500/20 text-slate-400 border border-slate-500/30'}">
													{perm.permission_type}
												</span>
											</td>
											<td class="py-2 px-3 text-slate-400 text-xs">
												{perm.created_at ? new Date(perm.created_at).toLocaleDateString('ko-KR') : '-'}
											</td>
											<td class="py-2 px-3 text-right">
												<button on:click={() => deletePermission(perm.id)} class="p-1 text-slate-400 hover:text-red-400 hover:bg-red-500/20 rounded-lg transition-colors">
													<GarbageBin class="size-4" />
												</button>
											</td>
										</tr>
									{/each}
								</tbody>
							</table>
						</div>
					{:else}
						<div class="bg-slate-800/50 border border-slate-700/50 rounded-xl p-12 text-center">
							<p class="text-slate-400">등록된 권한이 없습니다. 위 폼에서 권한을 추가하세요.</p>
						</div>
					{/if}
				{/if}
			</div>
		</div>
	</div>
{/if}
