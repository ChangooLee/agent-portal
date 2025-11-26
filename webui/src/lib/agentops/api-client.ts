/**
 * AgentOps API Client
 * Enhanced with WebSocket support, session replay, and advanced features
 */

import type {
	Trace,
	TraceDetail,
	Metrics,
	SessionReplay,
	TraceTimeline,
	CostDataPoint,
	TokenDataPoint,
	PerformanceDataPoint,
	AgentFlowGraph,
	TraceFilters,
	ExportOptions,
	ShareLink,
	AgentUsageStats
} from './types';

const API_BASE_URL = 'http://localhost:8000/api/agentops';
const WS_BASE_URL = 'ws://localhost:8000/api/agentops';

// Re-export types for backward compatibility
export type { Trace, TraceDetail, Metrics } from './types';

export async function getTraces(params: {
	project_id: string;
	start_time: string;
	end_time: string;
	page?: number;
	size?: number;
	search?: string;
}): Promise<{ traces: Trace[]; total: number; page: number; size: number }> {
	const queryParams = new URLSearchParams({
		project_id: params.project_id,
		start_time: params.start_time,
		end_time: params.end_time,
		page: String(params.page || 1),
		size: String(params.size || 20)
	});

	if (params.search) {
		queryParams.append('search', params.search);
	}

	const response = await fetch(`${API_BASE_URL}/traces?${queryParams}`);
	if (!response.ok) {
		throw new Error(`Failed to fetch traces: ${response.statusText}`);
	}
	return response.json();
}

export async function getTraceDetail(trace_id: string): Promise<TraceDetail> {
	const response = await fetch(`${API_BASE_URL}/traces/${trace_id}`);
	if (!response.ok) {
		throw new Error(`Failed to fetch trace detail: ${response.statusText}`);
	}
	return response.json();
}

export async function getMetrics(params: {
	project_id: string;
	start_time: string;
	end_time: string;
}): Promise<Metrics> {
	const queryParams = new URLSearchParams({
		project_id: params.project_id,
		start_time: params.start_time,
		end_time: params.end_time
	});

	const response = await fetch(`${API_BASE_URL}/metrics?${queryParams}`);
	if (!response.ok) {
		throw new Error(`Failed to fetch metrics: ${response.statusText}`);
	}
	return response.json();
}

// ============================================================================
// Session Replay API
// ============================================================================

export async function getSessionReplay(trace_id: string): Promise<SessionReplay> {
	const response = await fetch(`${API_BASE_URL}/replay/${trace_id}`);
	if (!response.ok) {
		throw new Error(`Failed to fetch session replay: ${response.statusText}`);
	}
	return response.json();
}

export async function getTraceTimeline(trace_id: string): Promise<TraceTimeline> {
	const response = await fetch(`${API_BASE_URL}/timeline/${trace_id}`);
	if (!response.ok) {
		throw new Error(`Failed to fetch trace timeline: ${response.statusText}`);
	}
	return response.json();
}

// ============================================================================
// Analytics & Charts API
// ============================================================================

export async function getCostTrend(params: {
	project_id: string;
	start_time: string;
	end_time: string;
	interval?: 'hour' | 'day' | 'week';
}): Promise<CostDataPoint[]> {
	const queryParams = new URLSearchParams({
		project_id: params.project_id,
		start_time: params.start_time,
		end_time: params.end_time,
		interval: params.interval || 'day'
	});

	const response = await fetch(`${API_BASE_URL}/analytics/cost-trend?${queryParams}`);
	if (!response.ok) {
		throw new Error(`Failed to fetch cost trend: ${response.statusText}`);
	}
	return response.json();
}

export async function getTokenUsage(params: {
	project_id: string;
	start_time: string;
	end_time: string;
	interval?: 'hour' | 'day' | 'week';
}): Promise<TokenDataPoint[]> {
	const queryParams = new URLSearchParams({
		project_id: params.project_id,
		start_time: params.start_time,
		end_time: params.end_time,
		interval: params.interval || 'day'
	});

	const response = await fetch(`${API_BASE_URL}/analytics/token-usage?${queryParams}`);
	if (!response.ok) {
		throw new Error(`Failed to fetch token usage: ${response.statusText}`);
	}
	return response.json();
}

export async function getPerformanceMetrics(params: {
	project_id: string;
	start_time: string;
	end_time: string;
}): Promise<PerformanceDataPoint[]> {
	const queryParams = new URLSearchParams({
		project_id: params.project_id,
		start_time: params.start_time,
		end_time: params.end_time
	});

	const response = await fetch(`${API_BASE_URL}/analytics/performance?${queryParams}`);
	if (!response.ok) {
		throw new Error(`Failed to fetch performance metrics: ${response.statusText}`);
	}
	return response.json();
}

export async function getAgentFlowGraph(params: {
	project_id: string;
	trace_id?: string;
	start_time?: string;
	end_time?: string;
}): Promise<AgentFlowGraph> {
	const queryParams = new URLSearchParams({
		project_id: params.project_id
	});

	if (params.trace_id) queryParams.append('trace_id', params.trace_id);
	if (params.start_time) queryParams.append('start_time', params.start_time);
	if (params.end_time) queryParams.append('end_time', params.end_time);

	const response = await fetch(`${API_BASE_URL}/analytics/agent-flow?${queryParams}`);
	if (!response.ok) {
		throw new Error(`Failed to fetch agent flow graph: ${response.statusText}`);
	}
	return response.json();
}

// ============================================================================
// Export & Share API
// ============================================================================

export async function exportTraces(
	project_id: string,
	options: ExportOptions
): Promise<Blob> {
	const response = await fetch(`${API_BASE_URL}/export`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json'
		},
		body: JSON.stringify({
			project_id,
			...options
		})
	});

	if (!response.ok) {
		throw new Error(`Failed to export traces: ${response.statusText}`);
	}

	return response.blob();
}

export async function createShareLink(trace_id: string, expires_in_days: number = 7): Promise<ShareLink> {
	const response = await fetch(`${API_BASE_URL}/share`, {
		method: 'POST',
		headers: {
			'Content-Type': 'application/json'
		},
		body: JSON.stringify({
			trace_id,
			expires_in_days
		})
	});

	if (!response.ok) {
		throw new Error(`Failed to create share link: ${response.statusText}`);
	}

	return response.json();
}

// ============================================================================
// WebSocket Client
// ============================================================================

export class AgentOpsWebSocket {
	private ws: WebSocket | null = null;
	private reconnectAttempts = 0;
	private maxReconnectAttempts = 5;
	private reconnectDelay = 1000;
	private listeners: Map<string, Set<(data: any) => void>> = new Map();

	connect(project_id: string): void {
		if (this.ws?.readyState === WebSocket.OPEN) {
			console.warn('WebSocket already connected');
			return;
		}

		try {
			this.ws = new WebSocket(`${WS_BASE_URL}/ws/${project_id}`);

			this.ws.onopen = () => {
				console.log('AgentOps WebSocket connected');
				this.reconnectAttempts = 0;
				this.emit('connected', { project_id });
			};

			this.ws.onmessage = (event) => {
				try {
					const message = JSON.parse(event.data);
					this.emit(message.type, message.data);
				} catch (error) {
					console.error('Failed to parse WebSocket message:', error);
				}
			};

			this.ws.onerror = (error) => {
				console.error('WebSocket error:', error);
				this.emit('error', error);
			};

			this.ws.onclose = () => {
				console.log('WebSocket closed');
				this.emit('disconnected', {});
				this.attemptReconnect(project_id);
			};
		} catch (error) {
			console.error('Failed to create WebSocket:', error);
			this.attemptReconnect(project_id);
		}
	}

	private attemptReconnect(project_id: string): void {
		if (this.reconnectAttempts >= this.maxReconnectAttempts) {
			console.error('Max reconnect attempts reached');
			return;
		}

		this.reconnectAttempts++;
		const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);

		console.log(`Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`);

		setTimeout(() => {
			this.connect(project_id);
		}, delay);
	}

	on(event: string, callback: (data: any) => void): void {
		if (!this.listeners.has(event)) {
			this.listeners.set(event, new Set());
		}
		this.listeners.get(event)!.add(callback);
	}

	off(event: string, callback: (data: any) => void): void {
		const listeners = this.listeners.get(event);
		if (listeners) {
			listeners.delete(callback);
		}
	}

	private emit(event: string, data: any): void {
		const listeners = this.listeners.get(event);
		if (listeners) {
			listeners.forEach((callback) => callback(data));
		}
	}

	disconnect(): void {
		if (this.ws) {
			this.ws.close();
			this.ws = null;
		}
		this.listeners.clear();
		this.reconnectAttempts = 0;
	}

	send(message: any): void {
		if (this.ws?.readyState === WebSocket.OPEN) {
			this.ws.send(JSON.stringify(message));
		} else {
			console.warn('WebSocket not connected, cannot send message');
		}
	}
}

// Singleton instance for convenience
export const agentOpsWS = new AgentOpsWebSocket();

// ============================================================================
// Agent Usage Stats API
// ============================================================================

export async function getAgentUsageStats(params: {
	project_id: string;
	start_time: string;
	end_time: string;
}): Promise<AgentUsageStats[]> {
	const queryParams = new URLSearchParams({
		project_id: params.project_id,
		start_time: params.start_time,
		end_time: params.end_time
	});

	const response = await fetch(`${API_BASE_URL}/agents/usage?${queryParams}`);
	if (!response.ok) {
		throw new Error(`Failed to fetch agent usage stats: ${response.statusText}`);
	}
	return response.json();
}

// ============================================================================
// Guardrail Stats API
// ============================================================================

export interface GuardrailStats {
	total_requests: number;
	guardrail_applied: number;
	blocked_requests: number;
	block_rate: number;
	input_guardrail: {
		checks: number;
		blocks: number;
		block_rate: number;
	};
	output_guardrail: {
		checks: number;
		blocks: number;
		block_rate: number;
	};
	token_usage: {
		prompt: number;
		completion: number;
		total: number;
	};
	avg_latency_ms: number;
}

export async function getGuardrailStats(params: {
	project_id: string;
	start_time: string;
	end_time: string;
}): Promise<GuardrailStats> {
	const queryParams = new URLSearchParams({
		project_id: params.project_id,
		start_time: params.start_time,
		end_time: params.end_time
	});

	const response = await fetch(`${API_BASE_URL}/analytics/guardrails?${queryParams}`);
	if (!response.ok) {
		throw new Error(`Failed to fetch guardrail stats: ${response.statusText}`);
	}
	return response.json();
}
