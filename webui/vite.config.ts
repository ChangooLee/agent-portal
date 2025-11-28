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
			// Proxy API (Langflow, Flowise, AutoGen) → FastAPI BFF (포트 8000)
			'/api/proxy': {
				target: process.env.DOCKER_ENV ? 'http://backend:8000' : 'http://localhost:8000',
				changeOrigin: true
			},
			// News API → FastAPI BFF (포트 8000)
			// Docker 환경: 컨테이너 이름 사용, 로컬 환경: localhost 사용
			'/api/news': {
				target: process.env.DOCKER_ENV ? 'http://backend:8000' : 'http://localhost:8000',
				changeOrigin: true
			},
			// AgentOps API → FastAPI BFF (포트 8000)
			'/api/agentops': {
				target: process.env.DOCKER_ENV ? 'http://backend:8000' : 'http://localhost:8000',
				changeOrigin: true
			},
			// DataCloud API → FastAPI BFF (포트 8000)
			'/api/datacloud': {
				target: process.env.DOCKER_ENV ? 'http://backend:8000' : 'http://localhost:8000',
				changeOrigin: true,
				rewrite: (path) => path.replace(/^\/api\/datacloud/, '/datacloud')
			},
			// MCP API → FastAPI BFF (포트 8000)
			'/api/mcp': {
				target: process.env.DOCKER_ENV ? 'http://backend:8000' : 'http://localhost:8000',
				changeOrigin: true,
				rewrite: (path) => path.replace(/^\/api\/mcp/, '/mcp')
			},
			// Gateway API → FastAPI BFF (포트 8000)
			'/api/gateway': {
				target: process.env.DOCKER_ENV ? 'http://backend:8000' : 'http://localhost:8000',
				changeOrigin: true,
				rewrite: (path) => path.replace(/^\/api\/gateway/, '/gateway')
			},
			// Monitoring API → FastAPI BFF (포트 8000)
			// Note: Backend router uses /api/monitoring prefix, no rewrite needed
			'/api/monitoring': {
				target: process.env.DOCKER_ENV ? 'http://backend:8000' : 'http://localhost:8000',
				changeOrigin: true,
				ws: true
			},
			// Projects API → FastAPI BFF (포트 8000)
			'/api/projects': {
				target: process.env.DOCKER_ENV ? 'http://backend:8000' : 'http://localhost:8000',
				changeOrigin: true
			},
			// LLM Management API → FastAPI BFF (포트 8000)
			'/api/llm': {
				target: process.env.DOCKER_ENV ? 'http://backend:8000' : 'http://localhost:8000',
				changeOrigin: true,
				rewrite: (path) => path.replace(/^\/api\/llm/, '/llm')
			},
			// 백엔드 API 프록시 (WebUI Backend - 포트 8080)
		// ⚠️ CRITICAL: Docker 환경에서는 localhost (컨테이너 내부 Uvicorn)
			'/api': {
			target: 'http://localhost:8080',
				changeOrigin: true,
				ws: true
			},
			'/ollama': {
			target: 'http://localhost:8080',
				changeOrigin: true
			},
			'/openai': {
			target: 'http://localhost:8080',
				changeOrigin: true
			},
			'/health': {
			target: 'http://localhost:8080',
				changeOrigin: true
			}
		},
		hmr: {
			// Docker 환경에서 HMR이 정상 작동하도록 설정
			clientPort: Number(process.env.VITE_HMR_PORT ?? devPort) // 외부 포트 매핑
		},
		watch: {
			// 파일 변경 감지 최적화
			usePolling: true
		}
	}
});
