<script lang="ts">
	import ReportTemplateList from '$lib/components/report/ReportTemplateList.svelte';
	import ReportChatPanel from '$lib/components/report/ReportChatPanel.svelte';
	import ReportPreview from '$lib/components/report/ReportPreview.svelte';
	import type { ReportTemplate } from '$lib/components/report/types';
	import { WEBUI_NAME } from '$lib/stores';

	const reportTemplates: ReportTemplate[] = [
		{
			id: 'executive-briefing',
			category: 'Executive',
			title: '임원용 전략 요약',
			description:
				'핵심 KPI, 인사이트, 의사결정 포인트를 2페이지 내로 정리하는 임원용 보고서입니다.',
			tags: ['KPI', 'OKR', 'Quarterly Review'],
			metrics: [
				{ label: '추천 분량', value: '2 pages', accent: 'primary' },
				{ label: '톤', value: 'Concise' },
				{ label: '리더십 만족도', value: '98%', accent: 'accent' }
			],
			previewHtml: `<section>
	<h2>요약</h2>
	<p>이번 분기 AI 도입 프로젝트는 계획 대비 18% 빠른 완성도로 마감했고, 예상 ROI는 142%로 상향 조정되었습니다. 핵심 KPI인 고객 셀프서비스 전환율은 36% 개선되며 목표치를 초과 달성했습니다.</p>
	<ul>
		<li><strong>핵심 하이라이트</strong>: 고객 이탈률 -12%, 신규 리드 -23% → +9%</li>
		<li><strong>리스크</strong>: 데이터 거버넌스 체크리스트 2항목 미충족 → Q1 개선 계획 제출 예정</li>
		<li><strong>다음 단계</strong>: ① AI 기반 사내 교육 확대 ② 외부 파트너 PoC 협업 추진</li>
	</ul>
</section>
<section>
	<h3>주요 KPI</h3>
	<table>
		<thead>
			<tr>
				<th>KPI</th>
				<th>목표</th>
				<th>실적</th>
				<th>비고</th>
			</tr>
		</thead>
		<tbody>
			<tr>
				<td>고객 셀프서비스 비율</td>
				<td>45%</td>
				<td>53%</td>
				<td>+8pp (AI FAQ 봇 정착)</td>
			</tr>
			<tr>
				<td>운영 비용 절감</td>
				<td>-12%</td>
				<td>-15%</td>
				<td>예상 대비 3pp 개선</td>
			</tr>
		</tbody>
	</table>
</section>`
		},
		{
			id: 'product-update',
			category: 'Product',
			title: '제품 업데이트 브리프',
			description: '최근 릴리즈, 핵심 지표, 현황을 제품 리더십 관점에서 정리합니다.',
			tags: ['Product', 'Release', 'Metrics'],
			metrics: [
				{ label: '추천 분량', value: '3 pages', accent: 'secondary' },
				{ label: '협업 팀', value: 'Product · Design · QA' },
				{ label: '출시 주기', value: '매월', accent: 'accent' }
			],
			previewHtml: `<section>
	<h2>최근 출시 현황</h2>
	<p>7월 메이저 릴리즈에서는 A/B Testing Console과 Adaptive Workflow Builder가 정식 배포되었습니다. 베타 고객 42곳에서 평균 27% 업무 효율 개선 효과를 보고했습니다.</p>
</section>
<section>
	<h3>주요 제품 지표</h3>
	<ul>
		<li><strong>일간 활성 사용자</strong>: 186K → 221K (▲19%)</li>
		<li><strong>피쳐 채택률</strong>: Adaptive Workflow Builder 64%</li>
		<li><strong>에러 레이트</strong>: 0.28%로 0.1pp 감소</li>
	</ul>
</section>
<section>
	<h3>차기 스프린트 집중 영역</h3>
	<ol>
		<li>Enterprise 플랜 고도화 (SSO 확장, 감사 로그 강화)</li>
		<li>API 레이트 리밋 완화 및 모니터링 개선</li>
		<li>Beta Feedback 기반 온보딩 플레이북 리빌딩</li>
	</ol>
</section>`
		},
		{
			id: 'research-whitepaper',
			category: 'Research',
			title: '연구 백서',
			description:
				'시장 조사, 인사이트, 전략 제언을 결합한 심층 분석 보고서를 생성합니다.',
			tags: ['Market', 'Insight', 'Strategy'],
			metrics: [
				{ label: '추천 분량', value: '8 pages' },
				{ label: '톤', value: 'Analytical', accent: 'primary' },
				{ label: '데이터 소스', value: '17개', accent: 'secondary' }
			],
			previewHtml: `<section>
	<h2>초록</h2>
	<p>AI 기반 금융 자동화 시장은 2028년까지 연평균 24.1% 성장할 것으로 예상됩니다. 국내 주요 플레이어 4곳의 경쟁 전략을 비교해 비용 구조와 진입 장벽을 분석했습니다.</p>
</section>
<section>
	<h3>핵심 인사이트</h3>
	<ul>
		<li>Premium 고객층은 <em>품질 보증</em> 및 <em>감사 추적성</em>을 최우선 가치로 인식</li>
		<li>가격 민감도가 높은 Mid-market에서는 구독형 패키지보다 <strong>사용량 기반 요금제</strong> 선호</li>
	</ul>
</section>
<section>
	<h3>권장 전략</h3>
	<p>Hybrid 요금제 모델 도입과 함께, 컨설팅 파트너 네트워크를 활용한 공동 세일즈 전략을 추진하는 것이 효과적입니다.</p>
</section>`
		}
	];

	const heroStats = [
		{ label: '평균 작성 시간', value: '7분', hint: '자동 초안 생성 및 정리' },
		{ label: '추천 템플릿', value: '12개', hint: '산업/목적별 큐레이션' },
		{ label: 'PDF / Word', value: '원클릭', hint: '포맷 변환 지원' }
	];

	const firstTemplate = reportTemplates[0] ?? null;
	let selectedTemplateId: string | null = firstTemplate?.id ?? null;
	let selectedTemplate: ReportTemplate | null = firstTemplate;

	const handleSelectTemplate = (event: CustomEvent<{ id: string }>) => {
		selectedTemplateId = event.detail.id;
		selectedTemplate = reportTemplates.find((template) => template.id === event.detail.id) ?? null;
	};

</script>

<svelte:head>
	<title>보고서 | {$WEBUI_NAME}</title>
</svelte:head>

<div class="min-h-full bg-gray-950 text-slate-50">
	<!-- Hero Section -->
	<div class="relative overflow-hidden border-b border-slate-800/50">
		<div class="absolute inset-0 bg-gradient-to-br from-indigo-600/5 via-transparent to-purple-600/5"></div>
		<div class="absolute inset-0 bg-[linear-gradient(rgba(99,102,241,0.03)_1px,transparent_1px),linear-gradient(90deg,rgba(99,102,241,0.03)_1px,transparent_1px)] bg-[size:64px_64px]"></div>
		
		<div class="relative px-6 py-8 text-center">
			<h1 class="text-3xl md:text-4xl font-medium mb-3 text-white">
				📊 AI 보고서
			</h1>
			<p class="text-base text-indigo-200/80">
				템플릿 선택 → 요구사항 입력 → HTML 프리뷰까지 한 화면에서 확인할 수 있도록 구성했습니다. 보고서 초안, 임원용 요약, 시장 분석 등 목적에 맞는 템플릿으로 빠르게 시작해보세요.
			</p>
		</div>

		<!-- Stats Cards -->
		<div class="relative px-6 pb-8">
			<div class="grid grid-cols-3 gap-4 max-w-4xl mx-auto">
				{#each heroStats as stat}
					<div class="bg-slate-900/80 border border-slate-800/50 rounded-xl p-4 shadow-lg shadow-black/20 hover:shadow-xl hover:shadow-black/30 hover:bg-slate-800/80 hover:border-indigo-500/50 hover:-translate-y-1 transition-all duration-300">
						<div class="text-xs font-medium uppercase tracking-wide text-indigo-400 mb-1">
							{stat.label}
						</div>
						<div class="text-2xl font-medium text-white mb-1">
							{stat.value}
						</div>
						<div class="text-xs text-slate-400">{stat.hint}</div>
					</div>
				{/each}
			</div>
		</div>
	</div>

	<!-- Content Section -->
	<div class="px-6 py-8">
		<div class="flex flex-col gap-6 xl:flex-row">

			<div class="flex w-full flex-col gap-6 xl:w-[56%]">
				<ReportTemplateList
					templates={reportTemplates}
					selectedId={selectedTemplateId}
					on:select={handleSelectTemplate}
				/>

				<ReportChatPanel />
			</div>

			<div class="flex w-full flex-1">
				<ReportPreview template={selectedTemplate} />
			</div>
		</div>
	</div>
</div>

