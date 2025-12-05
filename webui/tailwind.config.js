import typography from '@tailwindcss/typography';
import containerQuries from '@tailwindcss/container-queries';

/** @type {import('tailwindcss').Config} */
export default {
	darkMode: 'class',
	content: ['./src/**/*.{html,js,svelte,ts}'],
	safelist: [
		'bg-brand-500',
		'bg-brand-50',
		'text-brand-500',
		'hover:bg-brand-50',
		'hover:text-brand-500',
		'bg-samsung-blue',
		'bg-samsung-blue-light',
		'bg-samsung-blue-dark'
	],
	theme: {
		extend: {
			colors: {
				// 삼성생명 브랜드 컬러 (파란색 계열)
				brand: {
					50: '#e6f2ff',
					100: '#cce5ff',
					200: '#99cbff',
					300: '#66b1ff',
					400: '#3397ff',
					500: '#0066CC', // 메인 브랜드 컬러
					600: '#0052A3',
					700: '#003d7a',
					800: '#002952',
					900: '#001429'
				},
				// 직접 사용을 위한 삼성생명 컬러
				'samsung-blue': {
					DEFAULT: '#0066CC',
					light: '#e6f2ff',
					dark: '#0052A3'
				},
				// Monitoring 스타일 색상
				'monitoring': {
					primary: '#141B34', // Primary font color
					'primary-muted': 'rgba(20, 27, 52, 0.74)', // Secondary font
					icons: 'rgba(20, 27, 52, 0.68)', // Icons color
					border: '#DEE0F4', // Border color
					'icon-white': '#E1E2F2', // Font/Icon white
					success: '#4BC498', // Success green
					warning: '#EDD867', // Warning yellow
					error: '#E65A7E', // Error red
					'action': '#4BC498', // Action event color
					'llm-call': 'rgba(36, 0, 255, 0.7)', // LLM Call event color
					'tool': 'rgba(237, 216, 103, 0.8)', // Tool event color
					'bg-tint': '#E1E3F2', // Background tint (hover state)
					'primary-container': '#EBECF8', // Primary container
				},
				// Glassmorphism 색상 팔레트
				glass: {
					light: 'rgba(255, 255, 255, 0.8)',
					'light-hover': 'rgba(255, 255, 255, 0.9)',
					dark: 'rgba(30, 41, 59, 0.8)',
					'dark-hover': 'rgba(30, 41, 59, 0.9)',
				},
				// 새로운 그라데이션 색상
				primary: {
					DEFAULT: '#3478f6',
					light: '#5b8def',
					dark: '#1e5fd9',
				},
				secondary: {
					DEFAULT: '#9a7ac9',
					light: '#b48eda',
					dark: '#7d5fac',
				},
				accent: {
					DEFAULT: '#49b59c',
					light: '#5dd4bd',
					dark: '#3a9680',
				},
				// 삼성생명 스타일 그레이 스케일 (더 깔끔하고 전문적인 톤)
				gray: {
					50: 'var(--color-gray-50, #f8f9fa)',
					100: 'var(--color-gray-100, #e9ecef)',
					200: 'var(--color-gray-200, #dee2e6)',
					300: 'var(--color-gray-300, #ced4da)',
					400: 'var(--color-gray-400, #adb5bd)',
					500: 'var(--color-gray-500, #6c757d)',
					600: 'var(--color-gray-600, #495057)',
					700: 'var(--color-gray-700, #343a40)',
					800: 'var(--color-gray-800, #212529)',
					850: 'var(--color-gray-850, #1a1d21)',
					900: 'var(--color-gray-900, #0d1117)',
					950: 'var(--color-gray-950, #050608)'
				},
				// 액센트 컬러 (성공, 경고, 에러)
				success: {
					50: '#f0fdf4',
					100: '#dcfce7',
					200: '#bbf7d0',
					300: '#86efac',
					400: '#4ade80',
					500: '#22c55e',
					600: '#16a34a',
					700: '#15803d',
					800: '#166534',
					900: '#14532d'
				},
				warning: {
					50: '#fffbeb',
					100: '#fef3c7',
					200: '#fde68a',
					300: '#fcd34d',
					400: '#fbbf24',
					500: '#f59e0b',
					600: '#d97706',
					700: '#b45309',
					800: '#92400e',
					900: '#78350f'
				},
				error: {
					50: '#fef2f2',
					100: '#fee2e2',
					200: '#fecaca',
					300: '#fca5a5',
					400: '#f87171',
					500: '#ef4444',
					600: '#dc2626',
					700: '#b91c1c',
					800: '#991b1b',
					900: '#7f1d1d'
				}
			},
			typography: {
				DEFAULT: {
					css: {
						pre: false,
						code: false,
						'pre code': false,
						'code::before': false,
						'code::after': false
					}
				}
			},
			padding: {
				'safe-bottom': 'env(safe-area-inset-bottom)'
			},
			animation: {
				'gradient': 'gradient 30s ease-in-out infinite',
				'shimmer': 'shimmer 12s ease-in-out infinite alternate',
				'fade-in': 'fade-in 0.6s ease-out',
				'scale-in': 'scale-in 0.3s ease-out',
				'slide-up': 'slide-up 0.4s ease-out',
				'ripple': 'ripple 0.6s ease-out',
			},
			keyframes: {
				gradient: {
					'0%, 100%': { backgroundPosition: '0% 50%' },
					'50%': { backgroundPosition: '100% 50%' }
				},
				shimmer: {
					'0%': { transform: 'translateX(0px) translateY(0px)', opacity: '0.7' },
					'100%': { transform: 'translateX(40px) translateY(-40px)', opacity: '0.4' }
				},
				'fade-in': {
					'0%': { opacity: '0', transform: 'translateY(10px)' },
					'100%': { opacity: '1', transform: 'translateY(0)' }
				},
				'scale-in': {
					'0%': { opacity: '0', transform: 'scale(0.9)' },
					'100%': { opacity: '1', transform: 'scale(1)' }
				},
				'slide-up': {
					'0%': { opacity: '0', transform: 'translateY(20px)' },
					'100%': { opacity: '1', transform: 'translateY(0)' }
				},
				ripple: {
					'0%': { transform: 'scale(0)', opacity: '1' },
					'100%': { transform: 'scale(4)', opacity: '0' }
				}
			},
			backdropBlur: {
				xs: '2px',
			}
		}
	},
	plugins: [typography, containerQuries]
};
