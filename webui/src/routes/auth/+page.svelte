<script>
	import { toast } from 'svelte-sonner';

	import { onMount, onDestroy, getContext, tick } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/stores';

	import { getBackendConfig } from '$lib/apis';
	import { ldapUserSignIn, getSessionUser, userSignIn, userSignUp } from '$lib/apis/auths';

	import { WEBUI_API_BASE_URL, WEBUI_BASE_URL } from '$lib/constants';
	import { WEBUI_NAME, config, user, socket } from '$lib/stores';

	import { generateInitialsImage, canvasPixelTest } from '$lib/utils';

	import Spinner from '$lib/components/common/Spinner.svelte';
	import OnBoarding from '$lib/components/OnBoarding.svelte';

	const i18n = getContext('i18n');

	let loaded = false;

	let mode = $config?.features.enable_ldap ? 'ldap' : 'signin';

	let name = '';
	let email = '';
	let password = '';

	let ldapUsername = '';

	let transitioning = false;

	// Hero 메시지 세트 배열 (제목 + 본문)
	const heroSets = [
		{
			title: 'AI 에이전트의 모든 순간을 한곳에서',
			text: ['대화로 시작해 실행으로 이어지는 새로운 업무 공간,', 'SFN AI Portal은 사람과 AI가 함께 일하는 방식을 새롭게 만듭니다.']
		},
		{
			title: '대화만으로 아이디어가 실행됩니다',
			text: ['채팅창에서 아이디어를 나누면 바로 보고서를 만들고,', '필요한 정보를 웹과 사내 시스템에서 찾아볼 수 있습니다.']
		},
		{
			title: '시스템과 데이터를 자유롭게 연결하세요',
			text: ['복잡한 설정 없이도 필요한 정보가 자동으로 연결되고 실행됩니다.', '모든 업무가 하나로 통합됩니다.']
		},
		{
			title: '누구나 자신만의 AI를 만들 수 있습니다',
			text: ['대화로 설계하고 시각적으로 조합해,', '당신의 일에 꼭 맞는 AI를 직접 만들어보세요.']
		},
		{
			title: '운영까지 한눈에 관리됩니다',
			text: ['에이전트의 동작과 결과를 실시간으로 확인하고,', '필요할 땐 즉시 수정하고 다시 실행할 수 있습니다.']
		},
		{
			title: '문서를 올리면 지식이 됩니다',
			text: ['PDF나 이미지를 업로드하면 자동으로 분석되어,', '필요한 정보만 바로 찾아드립니다. 복잡한 문서도 한눈에 이해할 수 있습니다.']
		},
		{
			title: '데이터베이스와 직접 대화하세요',
			text: ['기존 시스템의 데이터를 복사하지 않고도 실시간으로 조회하고 분석할 수 있습니다.', '안전하고 빠른 데이터 접근이 가능합니다.']
		},
		{
			title: '채팅, 보고서, 검색을 자유롭게 전환하세요',
			text: ['같은 대화를 채팅 형식으로 보거나,', '보고서나 검색 결과로 볼 수 있습니다. 상황에 맞는 가장 편한 방식으로 작업하세요.']
		},
		{
			title: 'AI와 함께 일하는 새로운 방식의 시작',
			text: ['SFN AI Portal에서 당신의 AI 파트너를 만나보세요.', '대화가 곧 결과가 됩니다.']
		}
	];

	let heroSetIndex = 0;
	let heroOpacity = 1;
	let heroInterval = null;

	const querystringValue = (key) => {
		const querystring = window.location.search;
		const urlParams = new URLSearchParams(querystring);
		return urlParams.get(key);
	};

	const setSessionUser = async (sessionUser) => {
		if (sessionUser) {
			console.log(sessionUser);
			toast.success($i18n.t(`You're now logged in.`));
			if (sessionUser.token) {
				localStorage.token = sessionUser.token;
			}

			$socket.emit('user-join', { auth: { token: sessionUser.token } });
			await user.set(sessionUser);
			await config.set(await getBackendConfig());

			const redirectPath = querystringValue('redirect') || '/';
			goto(redirectPath);
		}
	};

	const signInHandler = async () => {
		const sessionUser = await userSignIn(email, password).catch((error) => {
			toast.error(`${error}`);
			return null;
		});

		await setSessionUser(sessionUser);
	};

	const signUpHandler = async () => {
		const sessionUser = await userSignUp(name, email, password, generateInitialsImage(name)).catch(
			(error) => {
				toast.error(`${error}`);
				return null;
			}
		);

		await setSessionUser(sessionUser);
	};

	const ldapSignInHandler = async () => {
		const sessionUser = await ldapUserSignIn(ldapUsername, password).catch((error) => {
			toast.error(`${error}`);
			return null;
		});
		await setSessionUser(sessionUser);
	};

	const submitHandler = async () => {
		if (mode === 'ldap') {
			await ldapSignInHandler();
		} else if (mode === 'signin') {
			await signInHandler();
		} else {
			await signUpHandler();
		}
	};

	const switchMode = (newMode) => {
		if (mode === newMode) return;
		transitioning = true;
		setTimeout(() => {
			mode = newMode;
			transitioning = false;
		}, 150);
	};

	const checkOauthCallback = async () => {
		if (!$page.url.hash) {
			return;
		}
		const hash = $page.url.hash.substring(1);
		if (!hash) {
			return;
		}
		const params = new URLSearchParams(hash);
		const token = params.get('token');
		if (!token) {
			return;
		}
		const sessionUser = await getSessionUser(token).catch((error) => {
			toast.error(`${error}`);
			return null;
		});
		if (!sessionUser) {
			return;
		}
		localStorage.token = token;
		await setSessionUser(sessionUser);
	};

	let onboarding = false;

	async function setLogoImage() {
		await tick();
		const logo = document.getElementById('logo');

		if (logo) {
			const isDarkMode = document.documentElement.classList.contains('dark');

			if (isDarkMode) {
				const darkImage = new Image();
				darkImage.src = '/static/favicon-dark.png';

				darkImage.onload = () => {
					logo.src = '/static/favicon-dark.png';
					logo.style.filter = ''; // Ensure no inversion is applied if favicon-dark.png exists
				};

				darkImage.onerror = () => {
					logo.style.filter = 'invert(1)'; // Invert image if favicon-dark.png is missing
				};
			}
		}
	}

	onMount(async () => {
		if ($user !== undefined) {
			const redirectPath = querystringValue('redirect') || '/';
			goto(redirectPath);
		}
		await checkOauthCallback();

		loaded = true;
		setLogoImage();

		if (($config?.features.auth_trusted_header ?? false) || $config?.features.auth === false) {
			await signInHandler();
		} else {
			onboarding = $config?.onboarding ?? false;

			// Hero 메시지 자동 전환 (8초마다)
			heroInterval = setInterval(() => {
				heroOpacity = 0;
				setTimeout(() => {
					heroSetIndex = (heroSetIndex + 1) % heroSets.length;
					heroOpacity = 1;
				}, 500);
			}, 8000);
		}
	});

	onDestroy(() => {
		if (heroInterval !== null) {
			clearInterval(heroInterval);
		}
	});
</script>

<style>
	@keyframes fade-in {
		from {
			opacity: 0;
			transform: translateY(10px);
		}
		to {
			opacity: 1;
			transform: translateY(0);
		}
	}
</style>

<svelte:head>
	<title>SFN AI Portal</title>
</svelte:head>

<OnBoarding
	bind:show={onboarding}
	getStartedHandler={() => {
		onboarding = false;
		mode = $config?.features.enable_ldap ? 'ldap' : 'signup';
	}}
/>

<div class="w-full h-screen max-h-[100dvh] relative overflow-y-auto">
	<!-- Subtle reflective light layer -->
	<div class="absolute inset-0 -z-20 bg-light-overlay"></div>
	<!-- Animated Samsung Blue Multi-Layer Gradient Background -->
	<div class="absolute inset-0 -z-10 bg-animated-samsung"></div>

	<div class="w-full absolute top-0 left-0 right-0 h-8 drag-region z-50" />

	{#if loaded}
		<div
			class="relative w-full flex flex-col items-center font-primary z-40 px-4 py-4 md:py-16 min-h-full md:min-h-screen"
			style="font-family: 'Samsung Gothic', -apple-system, BlinkMacSystemFont, sans-serif;"
		>
			<!-- Logo at top -->
			<div class="mb-4 md:mb-8 mt-2 md:mt-0">
					<img
						id="logo"
						crossorigin="anonymous"
					src="/samsung-financial-networks-logo.webp"
					class="h-10 md:h-16 w-auto"
					alt="Samsung Financial Networks"
					/>
				</div>

			<!-- Hero Section -->
			<div class="w-full max-w-3xl mb-4 md:mb-12 text-center text-white hidden md:block">
				<div
					class="transition-opacity duration-1000 ease-in-out"
					style="opacity: {heroOpacity};"
				>
					<h1 class="text-3xl lg:text-4xl font-extrabold leading-snug mb-4 text-white">
						{heroSets[heroSetIndex].title}
					</h1>
					<p class="text-lg lg:text-xl opacity-90 max-w-2xl mx-auto text-white">
						{heroSets[heroSetIndex].text[0]}<br />
						{heroSets[heroSetIndex].text[1]}
					</p>
			</div>

			<!-- Login Form -->
			<div class="w-full max-w-[400px] mx-auto relative z-50 mb-8 md:mb-0">
				{#if ($config?.features.auth_trusted_header ?? false) || $config?.features.auth === false}
					<div class=" my-auto pb-10 w-full">
						<div
							class="flex items-center justify-center gap-3 text-xl sm:text-2xl text-center font-semibold text-white"
						>
							<div>
								{$i18n.t('Signing in...')}
							</div>

							<div>
								<Spinner />
							</div>
						</div>
					</div>
				{:else}
					<div class="w-full bg-gray-800/50 backdrop-blur-sm rounded-2xl shadow-2xl p-4 md:p-8 transition-all duration-300 text-white {transitioning ? 'opacity-50' : 'opacity-100'}">
						{#if $config?.features.enable_signup && !($config?.onboarding ?? false) && !$config?.features.enable_ldap}
							<!-- Tab Switcher - Stripe style -->
							<div class="flex mb-8 border-b border-gray-600">
								<button
									type="button"
									class="flex-1 pb-3.5 text-sm font-medium transition-all duration-200 border-b-2 {mode === 'signin'
										? 'text-white border-white'
										: 'text-gray-400 border-transparent hover:text-gray-300'}"
									on:click={() => switchMode('signin')}
								>
									{$i18n.t('Sign in')}
								</button>
								<button
									type="button"
									class="flex-1 pb-3.5 text-sm font-medium transition-all duration-200 border-b-2 {mode === 'signup'
										? 'text-white border-white'
										: 'text-gray-400 border-transparent hover:text-gray-300'}"
									on:click={() => switchMode('signup')}
								>
									{$i18n.t('Sign up')}
								</button>
							</div>
						{/if}

						<form
							class="flex flex-col"
							on:submit={(e) => {
								e.preventDefault();
								submitHandler();
							}}
						>
									{#if $config?.onboarding ?? false}
								<div class="mb-6 text-center">
									<div class="text-sm text-gray-300">
										ⓘ {$WEBUI_NAME}
										{$i18n.t(
											'does not make any external connections, and your data stays securely on your locally hosted server.'
										)}
									</div>
									</div>
								{/if}

							{#if $config?.features.enable_login_form || $config?.features.enable_ldap}
								<div class="flex flex-col space-y-5">
									{#if mode === 'signup'}
										<div>
											<label class="block text-sm font-medium text-gray-200 mb-2.5">
												{$i18n.t('Name')}
											</label>
											<input
												bind:value={name}
												type="text"
												class="w-full px-4 py-3.5 text-base rounded-md bg-gray-700 text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-400 transition-all duration-200"
												autocomplete="name"
												placeholder={$i18n.t('Enter Your Full Name')}
												required
											/>
										</div>
									{/if}

									{#if mode === 'ldap'}
										<div>
											<label class="block text-sm font-medium text-gray-200 mb-2.5">
												{$i18n.t('Username')}
											</label>
											<input
												bind:value={ldapUsername}
												type="text"
												class="w-full px-4 py-3.5 text-base rounded-md bg-gray-700 text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-400 transition-all duration-200"
												autocomplete="username"
												name="username"
												placeholder={$i18n.t('Enter Your Username')}
												required
											/>
										</div>
									{:else}
										<div>
											<label class="block text-sm font-medium text-gray-200 mb-2.5">
												{$i18n.t('Email')}
											</label>
											<input
												bind:value={email}
												type="email"
												class="w-full px-4 py-3.5 text-base rounded-md bg-gray-700 text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-400 transition-all duration-200"
												autocomplete="email"
												name="email"
												placeholder={$i18n.t('Enter Your Email')}
												required
											/>
										</div>
									{/if}

									<div>
										<label class="block text-sm font-medium text-gray-200 mb-2.5">
											{$i18n.t('Password')}
										</label>
										<input
											bind:value={password}
											type="password"
											class="w-full px-4 py-3.5 text-base rounded-md bg-gray-700 text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-400 transition-all duration-200"
											placeholder={$i18n.t('Enter Your Password')}
											autocomplete="current-password"
											name="current-password"
											required
										/>
									</div>
								</div>
							{/if}
							<div class="mt-8">
								{#if $config?.features.enable_login_form || $config?.features.enable_ldap}
									{#if mode === 'ldap'}
										<button
											class="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-4 px-4 rounded-md transition-all duration-200"
											type="submit"
										>
											{$i18n.t('Authenticate')}
										</button>
									{:else}
										<button
											class="w-full bg-blue-600 hover:bg-blue-700 text-white font-medium py-4 px-4 rounded-md transition-all duration-200"
											type="submit"
										>
											{mode === 'signin'
												? $i18n.t('Sign in')
												: ($config?.onboarding ?? false)
													? $i18n.t('Create Admin Account')
													: $i18n.t('Create Account')}
										</button>
									{/if}
								{/if}
							</div>
						</form>

						{#if Object.keys($config?.oauth?.providers ?? {}).length > 0}
							<div class="inline-flex items-center justify-center w-full my-8">
								<hr class="flex-1 h-px border-0 bg-gray-600" />
								{#if $config?.features.enable_login_form || $config?.features.enable_ldap}
									<span
										class="px-4 text-sm font-medium text-gray-400 bg-gray-800/95"
										>{$i18n.t('or')}</span
									>
								{/if}

								<hr class="flex-1 h-px border-0 bg-gray-600" />
							</div>
							<div class="flex flex-col space-y-2.5">
								{#if $config?.oauth?.providers?.google}
									<button
										class="flex justify-center items-center bg-gray-700 border border-gray-600 hover:bg-gray-600 text-gray-200 transition-all duration-200 w-full rounded-md font-medium text-sm py-3.5 px-4"
										on:click={() => {
											window.location.href = `${WEBUI_BASE_URL}/oauth/google/login`;
										}}
									>
										<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 48 48" class="size-6 mr-3">
											<path
												fill="#EA4335"
												d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"
											/><path
												fill="#4285F4"
												d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"
											/><path
												fill="#FBBC05"
												d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"
											/><path
												fill="#34A853"
												d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.15 1.45-4.92 2.3-8.16 2.3-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"
											/><path fill="none" d="M0 0h48v48H0z" />
										</svg>
										<span>{$i18n.t('Continue with {{provider}}', { provider: 'Google' })}</span>
									</button>
								{/if}
								{#if $config?.oauth?.providers?.microsoft}
									<button
										class="flex justify-center items-center bg-gray-700 border border-gray-600 hover:bg-gray-600 text-gray-200 transition-all duration-200 w-full rounded-md font-medium text-sm py-3.5 px-4"
										on:click={() => {
											window.location.href = `${WEBUI_BASE_URL}/oauth/microsoft/login`;
										}}
									>
										<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 21 21" class="size-6 mr-3">
											<rect x="1" y="1" width="9" height="9" fill="#f25022" /><rect
												x="1"
												y="11"
												width="9"
												height="9"
												fill="#00a4ef"
											/><rect x="11" y="1" width="9" height="9" fill="#7fba00" /><rect
												x="11"
												y="11"
												width="9"
												height="9"
												fill="#ffb900"
											/>
										</svg>
										<span>{$i18n.t('Continue with {{provider}}', { provider: 'Microsoft' })}</span>
									</button>
								{/if}
								{#if $config?.oauth?.providers?.github}
									<button
										class="flex justify-center items-center bg-gray-700 border border-gray-600 hover:bg-gray-600 text-gray-200 transition-all duration-200 w-full rounded-md font-medium text-sm py-3.5 px-4"
										on:click={() => {
											window.location.href = `${WEBUI_BASE_URL}/oauth/github/login`;
										}}
									>
										<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" class="size-6 mr-3">
											<path
												fill="currentColor"
												d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.92 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57C20.565 21.795 24 17.31 24 12c0-6.63-5.37-12-12-12z"
											/>
										</svg>
										<span>{$i18n.t('Continue with {{provider}}', { provider: 'GitHub' })}</span>
									</button>
								{/if}
								{#if $config?.oauth?.providers?.oidc}
									<button
										class="flex justify-center items-center bg-gray-700 border border-gray-600 hover:bg-gray-600 text-gray-200 transition-all duration-200 w-full rounded-md font-medium text-sm py-3.5 px-4"
										on:click={() => {
											window.location.href = `${WEBUI_BASE_URL}/oauth/oidc/login`;
										}}
									>
										<svg
											xmlns="http://www.w3.org/2000/svg"
											fill="none"
											viewBox="0 0 24 24"
											stroke-width="1.5"
											stroke="currentColor"
											class="size-6 mr-3"
										>
											<path
												stroke-linecap="round"
												stroke-linejoin="round"
												d="M15.75 5.25a3 3 0 0 1 3 3m3 0a6 6 0 0 1-7.029 5.912c-.563-.097-1.159.026-1.563.43L10.5 17.25H8.25v2.25H6v2.25H2.25v-2.818c0-.597.237-1.17.659-1.591l6.499-6.499c.404-.404.527-1 .43-1.563A6 6 0 1 1 21.75 8.25Z"
											/>
										</svg>

										<span
											>{$i18n.t('Continue with {{provider}}', {
												provider: $config?.oauth?.providers?.oidc ?? 'SSO'
											})}</span
										>
									</button>
								{/if}
							</div>
						{/if}

						{#if $config?.features.enable_ldap && $config?.features.enable_login_form}
							<div class="mt-6 text-center">
								<button
									class="text-sm text-gray-300 hover:text-white transition-colors duration-200"
									type="button"
									on:click={() => {
										if (mode === 'ldap')
											mode = ($config?.onboarding ?? false) ? 'signup' : 'signin';
										else mode = 'ldap';
									}}
								>
									<span
										>{mode === 'ldap'
											? $i18n.t('Continue with Email')
											: $i18n.t('Continue with LDAP')}</span
									>
								</button>
							</div>
						{/if}
					</div>
				{/if}
			</div>
		</div>
	{/if}
</div>
