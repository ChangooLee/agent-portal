/**
 * AgentOps Type Definitions
 * Complete type system for traces, spans, sessions, and visualizations
 */

// ============================================================================
// Core Trace Types
// ============================================================================

export interface Trace {
	trace_id: string;
	service_name: string;
	span_name: string;
	start_time: string;
	duration: number;
	span_count: number;
	error_count: number;
	tags: string[];
	total_cost: number;
}

export interface TraceDetail {
	trace_id: string;
	project_id: string;
	total_spans?: number;
	total_cost?: number;
	spans: Span[];
	timeline?: TraceTimeline;
}

export interface Span {
	span_id: string;
	parent_span_id: string | null;
	timestamp: string;
	duration: number;
	status_code: string;
	status_message: string | null;
	span_name: string;
	span_kind: string;
	span_attributes: Record<string, any>;
}

// ============================================================================
// Timeline & Hierarchy Types
// ============================================================================

export interface TraceTimeline {
	trace_id: string;
	spans: SpanNode[];
	total_duration: number;
	critical_path: string[];
	start_time: number;
	end_time: number;
}

export interface SpanNode {
	span_id: string;
	parent_span_id: string | null;
	span_name: string;
	start_time: number;
	end_time: number;
	duration: number;
	status: 'OK' | 'ERROR' | 'UNSET';
	children: SpanNode[];
	attributes: Record<string, any>;
	depth: number;
	is_critical_path: boolean;
}

// ============================================================================
// Session Replay Types
// ============================================================================

export interface SessionReplay {
	trace_id: string;
	events: ReplayEvent[];
	timeline: number[];
	total_duration: number;
	start_time: number;
}

export interface ReplayEvent {
	timestamp: number;
	relative_time: number;
	type: 'llm_call' | 'tool_use' | 'error' | 'decision' | 'span_start' | 'span_end';
	span_id: string;
	span_name: string;
	data: LLMCallData | ToolUseData | ErrorData | DecisionData | SpanEventData;
}

export interface LLMCallData {
	model: string;
	prompt: string;
	response: string;
	prompt_tokens: number;
	completion_tokens: number;
	total_tokens: number;
	cost: number;
	latency: number;
}

export interface ToolUseData {
	tool_name: string;
	input: Record<string, any>;
	output: Record<string, any>;
	duration: number;
	status: 'success' | 'error';
}

export interface ErrorData {
	error_type: string;
	error_message: string;
	stack_trace?: string;
	span_id: string;
}

export interface DecisionData {
	decision_type: string;
	reasoning: string;
	selected_option: string;
	alternatives: string[];
}

export interface SpanEventData {
	span_id: string;
	span_name: string;
	status: string;
}

// ============================================================================
// Metrics & Analytics Types
// ============================================================================

export interface Metrics {
	trace_count: number;
	span_count: number;
	error_count: number;
	total_cost: number;
	prompt_tokens: number;
	completion_tokens: number;
	cache_read_input_tokens: number;
	reasoning_tokens: number;
	avg_duration: number;
	p50_duration: number;
	p95_duration: number;
	p99_duration: number;
}

export interface CostDataPoint {
	timestamp: string;
	cost: number;
	model?: string;
}

export interface TokenDataPoint {
	timestamp: string;
	prompt_tokens: number;
	completion_tokens: number;
	cache_hits: number;
}

export interface PerformanceDataPoint {
	timestamp: string;
	duration: number;
	status: 'success' | 'error';
}

// ============================================================================
// Multi-Agent Flow Types
// ============================================================================

export interface AgentFlowGraph {
	nodes: AgentNode[];
	edges: AgentEdge[];
}

export interface AgentNode {
	id: string;
	label: string;
	type: 'agent' | 'tool' | 'llm' | 'stage';
	position: { x: number; y: number };
	data: {
		agent_name?: string;
		stage_name?: string;
		call_count?: number;
		total_calls?: number;
		total_cost: number;
		avg_duration?: number;
		avg_latency_ms?: number;
		total_tokens?: number;
		prompt_tokens?: number;
		completion_tokens?: number;
		error_count?: number;
		guardrail_applied?: number;
		color?: string;
		is_guardrail?: boolean;
	};
}

export interface AgentEdge {
	id: string;
	source: string;
	target: string;
	label?: string;
	animated?: boolean;
	data: {
		message_count?: number;
		total_tokens?: number;
		label?: string;
		blocked?: boolean;
	};
}

// ============================================================================
// Filter & Search Types
// ============================================================================

export interface TraceFilters {
	start_time: string;
	end_time: string;
	status?: ('success' | 'error' | 'running')[];
	models?: string[];
	min_cost?: number;
	max_cost?: number;
	min_duration?: number;
	max_duration?: number;
	tags?: string[];
	search?: string;
}

export interface FilterPreset {
	id: string;
	name: string;
	filters: TraceFilters;
	created_at: string;
}

// ============================================================================
// WebSocket Types
// ============================================================================

export interface WebSocketMessage {
	type: 'trace_update' | 'trace_new' | 'metrics_update' | 'error';
	data: any;
	timestamp: number;
}

export interface TraceUpdate {
	trace_id: string;
	status: string;
	duration?: number;
	cost?: number;
}

// ============================================================================
// Export Types
// ============================================================================

export interface ExportOptions {
	format: 'csv' | 'json' | 'pdf';
	include_spans: boolean;
	include_attributes: boolean;
	date_range: { start: string; end: string };
}

export interface ShareLink {
	link_id: string;
	trace_id: string;
	url: string;
	expires_at: string;
}

// ============================================================================
// Agent Usage Stats
// ============================================================================

export interface AgentUsageStats {
	agent_name: string;
	total_tokens: number;
	total_cost: number;
	event_count: number;
	avg_latency: number;
	error_count: number;
	success_rate: number;
}

