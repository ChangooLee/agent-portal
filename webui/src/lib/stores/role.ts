// Role-based navigation store
import { writable, derived, get } from 'svelte/store';
import { browser } from '$app/environment';

export type UserRole = 'use' | 'build' | 'operate';

// Persistent role store
function createRoleStore() {
    const defaultRole: UserRole = 'use';
    const stored = browser ? localStorage.getItem('selectedRole') as UserRole : null;
    const initial = stored && ['use', 'build', 'operate'].includes(stored) ? stored : defaultRole;
    
    const { subscribe, set, update } = writable<UserRole>(initial);

    return {
        subscribe,
        set: (value: UserRole) => {
            if (browser) {
                localStorage.setItem('selectedRole', value);
            }
            set(value);
        },
        update
    };
}

export const selectedRole = createRoleStore();

// Menu structure for each role
export interface MenuItem {
    id: string;
    name: string;
    href: string;
    icon: string;
    status: 'active' | 'coming-soon';
    description?: string;
}

export const roleMenus: Record<UserRole, MenuItem[]> = {
    use: [
        { id: 'today', name: 'Today', href: '/', icon: 'home', status: 'active', description: '오늘의 요약' },
        { id: 'chat', name: 'Chat', href: '/c', icon: 'chat', status: 'active', description: 'AI 채팅' },
        { id: 'agents', name: '에이전트', href: '/use/agents', icon: 'cube', status: 'active', description: 'AI 에이전트 실행' },
        { id: 'datacloud', name: 'Data Cloud', href: '/use/datacloud', icon: 'database', status: 'active', description: '데이터 질의' },
        { id: 'report', name: '보고서', href: '/report', icon: 'document', status: 'coming-soon', description: 'AI 보고서 생성' },
        { id: 'notebook', name: 'Notebook', href: '/notebook', icon: 'book', status: 'coming-soon', description: 'AI 노트북' },
        { id: 'perplexica', name: 'Perplexica', href: '/use/perplexica', icon: 'search', status: 'coming-soon', description: 'AI 검색' },
    ],
    build: [
        { id: 'agents', name: '에이전트', href: '/build/agents', icon: 'cube', status: 'active', description: '에이전트 개발' },
        { id: 'workflows', name: '워크플로우', href: '/build/workflows', icon: 'workflow', status: 'coming-soon', description: '워크플로우 빌더' },
        { id: 'llm', name: 'LLM', href: '/build/llm', icon: 'cpu', status: 'active', description: 'LLM 모델 관리' },
        { id: 'mcp', name: 'MCP', href: '/build/mcp', icon: 'server', status: 'active', description: 'MCP 서버 관리' },
        { id: 'datacloud', name: 'Data Cloud', href: '/build/datacloud', icon: 'database', status: 'active', description: '데이터베이스 연결' },
        { id: 'knowledge', name: 'Knowledge', href: '/build/knowledge', icon: 'book', status: 'coming-soon', description: '지식 베이스' },
        { id: 'guardrails', name: '가드레일', href: '/build/guardrails', icon: 'shield', status: 'active', description: '안전 설정' },
        { id: 'evaluations', name: '리더보드', href: '/build/evaluations', icon: 'chart', status: 'active', description: '모델 평가' },
    ],
    operate: [
        { id: 'monitoring', name: 'Monitoring', href: '/operate/monitoring', icon: 'chart-bar', status: 'active', description: '모니터링 대시보드' },
        { id: 'gateway', name: 'Gateway', href: '/operate/gateway', icon: 'globe', status: 'active', description: 'API 게이트웨이' },
        { id: 'users', name: '사용자관리', href: '/operate/users', icon: 'users', status: 'active', description: '사용자 관리' },
        { id: 'settings', name: '설정', href: '/operate/settings', icon: 'cog', status: 'active', description: '시스템 설정' },
    ]
};

// Get current role based on pathname
export function getRoleFromPath(pathname: string): UserRole {
    // Use role paths
    if (pathname.startsWith('/use/') || pathname === '/' || pathname === '/home' || pathname.startsWith('/c/') || pathname.startsWith('/c') || pathname === '/today' || pathname === '/dart' || pathname.startsWith('/report') || pathname.startsWith('/notebook') || pathname === '/realestate' || pathname === '/health-agent' || pathname === '/legislation') {
        return 'use';
    }
    
    // Build role paths
    if (pathname.startsWith('/build/')) {
        return 'build';
    }
    
    // Operate role paths
    if (pathname.startsWith('/operate/')) {
        return 'operate';
    }
    
    // Legacy admin paths (for backward compatibility)
    if (pathname.startsWith('/admin/')) {
        return 'operate';
    }
    
    // Default fallback
    return 'use';
}

// Derived store for current menu items
export const currentMenuItems = derived(selectedRole, ($role) => roleMenus[$role]);

