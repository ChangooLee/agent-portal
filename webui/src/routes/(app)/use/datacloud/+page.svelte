<script lang="ts">
	import { onMount } from 'svelte';
	import { toast } from 'svelte-sonner';
	import Check from '$lib/components/icons/Check.svelte';
	import XMark from '$lib/components/icons/XMark.svelte';
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
	let showSchemaModal = false;
	let selectedConnection: DBConnection | null = null;
	let schemaData: { tables: TableInfo[] } | null = null;
	let schemaLoading = false;
	let expandedTables: Set<string> = new Set();
	let showQueryModal = false;
	let queryText = '';
	let queryResult: { columns: string[]; rows: any[]; rows_affected: number; execution_time_ms: number } | null = null;
	let queryLoading = false;

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
	<title>Data Cloud | AI Agent Portal</title>
</svelte:head>

<div class="min-h-full bg-gray-950 text-slate-50">
	<!-- Hero Section -->
	<div class="relative overflow-hidden border-b border-slate-800/50">
		<div class="absolute inset-0 bg-gradient-to-br from-cyan-600/5 via-transparent to-blue-600/5"></div>
		<div class="absolute inset-0 bg-[linear-gradient(rgba(6,182,212,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(6,182,212,0.03)_1px,transparent_1px)] bg-[size:64px_64px]"></div>
		
		<div class="relative px-6 py-8 text-center">
			<h1 class="text-3xl md:text-4xl font-medium text-white mb-3">
				Data Cloud
			</h1>
			<p class="text-base text-cyan-200/80">
				데이터 복제 없이 실시간으로 데이터베이스에 연결하여 스키마 조회 및 쿼리를 실행할 수 있습니다.
			</p>
		</div>
	</div>

	<!-- Content Section -->
	<div class="px-6 py-8">
		<!-- Connection List -->
		<div class="bg-slate-900/50 backdrop-blur-xl rounded-xl border border-slate-800/50 overflow-hidden">
			{#if loading}
				<div class="flex items-center justify-center py-12">
					<div class="animate-spin rounded-full h-8 w-8 border-b-2 border-cyan-500"></div>
				</div>
			{:else if connections.length === 0}
				<div class="bg-slate-800/50 border border-slate-700 rounded-xl p-12 text-center">
					<Cube class="size-16 mx-auto text-slate-500 mb-4" />
					<p class="text-slate-400">등록된 연결이 없습니다.</p>
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
