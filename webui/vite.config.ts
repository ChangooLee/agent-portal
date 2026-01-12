import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

import { viteStaticCopy } from 'vite-plugin-static-copy';

// /** @type {import('vite').Plugin} */
// const viteServerConfig = {
// 	name: 'log-request-middleware',
// 	configureServer(server) {
// 		server.middlewares.use((req, res, next) => {
// 			res.setHeader('Access-Control-Allow-Origin', '*');
// 			res.setHeader('Access-Control-Allow-Methods', 'GET');
// 			res.setHeader('Cross-Origin-Opener-Policy', 'same-origin');
// 			res.setHeader('Cross-Origin-Embedder-Policy', 'require-corp');
// 			next();
// 		});
// 	}
// };

const devPort = Number(process.env.VITE_DEV_PORT ?? '3001');
// Single Port Architecture: 모든 API 요청을 BFF (포트 3010)로 프록시
// BFF가 WebUI Backend, Kong Gateway 등을 프록시합니다.
const bffTarget = process.env.DOCKER_ENV ? 'http://backend:3010' : 'http://localhost:3010';

export default defineConfig({
	plugins: [
		sveltekit(),
		viteStaticCopy({
			targets: [
				{
					src: 'node_modules/onnxruntime-web/dist/*.jsep.*',

					dest: 'wasm'
				}
			]
		})
	],
	define: {
		APP_VERSION: JSON.stringify(process.env.npm_package_version),
		APP_BUILD_HASH: JSON.stringify(process.env.APP_BUILD_HASH || 'dev-build')
	},
	build: {
		sourcemap: true
	},
	worker: {
		format: 'es'
	},
	server: {
		host: '0.0.0.0', // Docker 내부에서 접근 가능하도록
		port: devPort, // 기본 3001, 필요 시 VITE_DEV_PORT로 오버라이드
		proxy: {
			// Single Port Architecture: 모든 API 요청을 BFF (포트 3010)로 프록시
			// BFF가 WebUI Backend, Kong Gateway 등을 프록시합니다.
			// Proxy API (Langflow, Flowise, AutoGen) → FastAPI BFF (포트 3010)
			'/api/proxy': {
				target: bffTarget,
				changeOrigin: true
			},
			// News API → FastAPI BFF (포트 3010)
			'/api/news': {
				target: bffTarget,
				changeOrigin: true
			},
			// DataCloud API → FastAPI BFF (포트 3010)
			'/api/datacloud': {
				target: bffTarget,
				changeOrigin: true,
				rewrite: (path) => path.replace(/^\/api\/datacloud/, '/datacloud')
			},
			// MCP API → FastAPI BFF (포트 3010)
			'/api/mcp': {
				target: bffTarget,
				changeOrigin: true,
				rewrite: (path) => path.replace(/^\/api\/mcp/, '/mcp')
			},
			// Gateway API → FastAPI BFF (포트 3010)
			'/api/gateway': {
				target: bffTarget,
				changeOrigin: true,
				rewrite: (path) => path.replace(/^\/api\/gateway/, '/gateway')
			},
			// Monitoring API → FastAPI BFF (포트 3010)
			'/api/monitoring': {
				target: bffTarget,
				changeOrigin: true,
				ws: true
			},
			// Projects API → FastAPI BFF (포트 3010)
			'/api/projects': {
				target: bffTarget,
				changeOrigin: true
			},
			// LLM Management API → FastAPI BFF (포트 3010)
			'/api/llm': {
				target: bffTarget,
				changeOrigin: true,
				rewrite: (path) => path.replace(/^\/api\/llm/, '/llm')
			},
			// Perplexica API → FastAPI BFF (포트 3010)
			'/api/perplexica': {
				target: bffTarget,
				changeOrigin: true,
				rewrite: (path) => path.replace(/^\/api\/perplexica/, '/proxy/perplexica/api')
			},
			// Embed Proxy (Kong Admin) → FastAPI BFF (포트 3010)
			'/api/embed': {
				target: bffTarget,
				changeOrigin: true,
				rewrite: (path) => path.replace(/^\/api\/embed/, '/embed')
			},
			// LangGraph Text-to-SQL Agent API → FastAPI BFF (포트 3010)
			'/api/text2sql': {
				target: bffTarget,
				changeOrigin: true,
				rewrite: (path) => path.replace(/^\/api\/text2sql/, '/text2sql')
			},
			// DART 기업공시분석 Agent API → FastAPI BFF (포트 3010)
			// SSE 스트리밍을 위해 타임아웃을 10분으로 설정
			'/api/dart': {
				target: bffTarget,
				changeOrigin: true,
				rewrite: (path) => path.replace(/^\/api\/dart/, '/dart'),
				timeout: 600000,  // 10분 타임아웃
				proxyTimeout: 600000  // 프록시 타임아웃 10분
			},
			// RealEstate 부동산 Agent API → FastAPI BFF (포트 3010)
			'/api/realestate': {
				target: bffTarget,
				changeOrigin: true,
				rewrite: (path) => path.replace(/^\/api\/realestate/, '/realestate'),
				timeout: 600000,
				proxyTimeout: 600000
			},
			// Health 건강/의료 Agent API → FastAPI BFF (포트 3010)
			'/api/health-agent': {
				target: bffTarget,
				changeOrigin: true,
				rewrite: (path) => path.replace(/^\/api\/health-agent/, '/health-agent'),
				timeout: 600000,
				proxyTimeout: 600000
			},
			// Legislation 법률 Agent API → FastAPI BFF (포트 3010)
			'/api/legislation': {
				target: bffTarget,
				changeOrigin: true,
				rewrite: (path) => path.replace(/^\/api\/legislation/, '/legislation'),
				timeout: 600000,
				proxyTimeout: 600000
			},
			// WebUI Backend API → FastAPI BFF (포트 3010) → WebUI Backend (8080)
			// BFF의 /api/webui/* 라우터가 WebUI Backend로 프록시합니다.
			// WebUI Backend의 /api/config, /api/v1/* 등을 /api/webui/*로 리라이트
			'/api/config': {
				target: bffTarget,
				changeOrigin: true,
				rewrite: (path) => path.replace(/^\/api\/config/, '/api/webui/config')
			},
			'/api/v1': {
				target: bffTarget,
				changeOrigin: true,
				rewrite: (path) => path.replace(/^\/api\/v1/, '/api/webui/v1')
			},
			'/api/models': {
				target: bffTarget,
				changeOrigin: true,
				rewrite: (path) => path.replace(/^\/api\/models/, '/api/webui/models')
			},
			'/api/chat': {
				target: bffTarget,
				changeOrigin: true,
				rewrite: (path) => path.replace(/^\/api\/chat/, '/api/webui/chat')
			},
			'/api/tasks': {
				target: bffTarget,
				changeOrigin: true,
				rewrite: (path) => path.replace(/^\/api\/tasks/, '/api/webui/tasks')
			},
			'/api/changelog': {
				target: bffTarget,
				changeOrigin: true,
				rewrite: (path) => path.replace(/^\/api\/changelog/, '/api/webui/changelog')
			},
			'/api/version': {
				target: bffTarget,
				changeOrigin: true,
				rewrite: (path) => path.replace(/^\/api\/version/, '/api/webui/version')
			},
			'/api/webhook': {
				target: bffTarget,
				changeOrigin: true,
				rewrite: (path) => path.replace(/^\/api\/webhook/, '/api/webui/webhook')
			},
			'/api/community_sharing': {
				target: bffTarget,
				changeOrigin: true,
				rewrite: (path) => path.replace(/^\/api\/community_sharing/, '/api/webui/community_sharing')
			},
			// 기타 /api/* 요청도 BFF로 프록시 (나중에 처리)
			'/api': {
				target: bffTarget,
				changeOrigin: true,
				ws: true
			},
			// WebUI Backend 직접 경로도 BFF를 통해 프록시
			'/ollama': {
				target: bffTarget,
				changeOrigin: true
			},
			'/openai': {
				target: bffTarget,
				changeOrigin: true
			}
			// Note: /health endpoint is NOT proxied here to avoid conflict with /health-agent route
			// BFF's /health endpoint is accessed directly when needed
		},
		hmr: false,  // Single Port Architecture에서 BFF를 통한 WebSocket 프록시가 복잡하므로 HMR 비활성화
		// 파일 변경 감지는 watch 옵션으로 처리되며, 개발자는 수동으로 새로고침하면 됩니다
		// 또는 나중에 WebSocket 프록시가 완벽하게 구현되면 다시 활성화할 수 있습니다
		watch: {
			// 파일 변경 감지 최적화
			usePolling: true
		}
	}
});
