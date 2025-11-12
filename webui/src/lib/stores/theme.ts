import { writable } from 'svelte/store';
import { browser } from '$app/environment';

export type Theme = 'light' | 'dark';

// 시스템 테마 감지
function getSystemTheme(): Theme {
	if (!browser) return 'light';
	return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

// 로컬 스토리지에서 테마 불러오기
function getStoredTheme(): Theme | null {
	if (!browser) return null;
	const stored = localStorage.getItem('theme');
	return (stored === 'light' || stored === 'dark') ? stored : null;
}

// 초기 테마 설정 (저장된 테마 > 시스템 테마 > 기본값)
const initialTheme = getStoredTheme() || getSystemTheme();

// 테마 스토어 생성
function createThemeStore() {
	const { subscribe, set, update } = writable<Theme>(initialTheme);

	return {
		subscribe,
		set: (theme: Theme) => {
			if (browser) {
				// 로컬 스토리지에 저장
				localStorage.setItem('theme', theme);
				
				// HTML 클래스 업데이트
				if (theme === 'dark') {
					document.documentElement.classList.add('dark');
				} else {
					document.documentElement.classList.remove('dark');
				}
			}
			set(theme);
		},
		toggle: () => {
			update(current => {
				const newTheme = current === 'light' ? 'dark' : 'light';
				if (browser) {
					localStorage.setItem('theme', newTheme);
					if (newTheme === 'dark') {
						document.documentElement.classList.add('dark');
					} else {
						document.documentElement.classList.remove('dark');
					}
				}
				return newTheme;
			});
		},
		init: () => {
			if (browser) {
				// 초기 HTML 클래스 설정
				if (initialTheme === 'dark') {
					document.documentElement.classList.add('dark');
				} else {
					document.documentElement.classList.remove('dark');
				}

				// 시스템 테마 변경 감지
				const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
				const handleChange = (e: MediaQueryListEvent) => {
					// 사용자가 수동으로 테마를 설정한 경우에는 시스템 테마 변경을 무시
					if (getStoredTheme() === null) {
						const newTheme = e.matches ? 'dark' : 'light';
						set(newTheme);
					}
				};
				
				mediaQuery.addEventListener('change', handleChange);
				
				// 클린업 함수 반환
				return () => mediaQuery.removeEventListener('change', handleChange);
			}
		}
	};
}

export const theme = createThemeStore();

