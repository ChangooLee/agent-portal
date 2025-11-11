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
			}
		}
	},
	plugins: [typography, containerQuries]
};
