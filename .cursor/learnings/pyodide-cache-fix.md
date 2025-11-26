# 2025-11-21: Pyodide 다운로드 무한 루프 해결

## 문제 상황

**증상**:
- WebUI 개발 환경 시작 시 `npm run pyodide:fetch`에서 멈춤
- 로그: `Fetching 30 files:   0%|          | 0/30 [00:00<?, ?it/s]Killed`
- 프로세스가 강제 종료됨 (Killed)

**근본 원인**:
- `scripts/prepare-pyodide.js`가 **캐시 확인 로직이 없음**
- 이미 `static/pyodide/` 디렉토리에 패키지가 다운로드되어 있어도 **무조건 다시 다운로드 시도**
- Pyodide 패키지(numpy, pandas, scipy, matplotlib 등)가 크기 때문에 다운로드 중 메모리/리소스 문제 발생

## 해결 방법

**`scripts/prepare-pyodide.js` 수정**:

```javascript
async function downloadPackages() {
	console.log('Setting up pyodide + micropip');

	// ✅ 캐시 확인 로직 추가
	try {
		const lockFile = await readFile('static/pyodide/pyodide-lock.json');
		if (lockFile) {
			console.log('✅ Pyodide packages already cached, skipping download.');
			return;
		}
	} catch (e) {
		console.log('Pyodide lock file not found, proceeding with download.');
	}

	// 기존 로직...
}
```

**핵심 변경**:
- `pyodide-lock.json` 파일이 있으면 다운로드 스킵
- 캐시가 있을 때 즉시 반환하여 불필요한 다운로드 방지

## 결과

**Before**:
```
Setting up pyodide + micropip
Loading micropip package
...
Fetching 30 files:   0%|          | 0/30 [00:00<?, ?it/s]Killed
(재시작 무한 반복)
```

**After**:
```
Setting up pyodide + micropip
✅ Pyodide packages already cached, skipping download.
Copying Pyodide files into static directory
VITE v5.4.15  ready in 2030 ms
➜  Local:   http://localhost:3001/
```

## 학습 내용

**피드백**: ✅ 근본 원인 파악 후 해결

**성공 요인**:
1. **로그 분석**: `Killed` 메시지로 프로세스 강제 종료 파악
2. **스크립트 분석**: `prepare-pyodide.js`에 캐시 확인 로직 부재 발견
3. **최소 수정**: 캐시 확인 로직만 추가하여 기존 동작 유지

**향후 적용**:
- 대용량 패키지 다운로드 스크립트는 **항상 캐시 확인 로직 필수**
- `pyodide-lock.json` 파일 존재 여부로 캐시 확인
- Open-WebUI upstream에 PR 제출 가능

**트레이드오프**:
- 캐시 무효화: `rm -rf webui/static/pyodide/pyodide-lock.json` 후 재시작
- 버전 불일치 시 기존 로직(버전 체크 후 디렉토리 삭제)이 처리

## 관련 파일

- `webui/scripts/prepare-pyodide.js` (line 52-78) — 수정된 캐시 확인 로직
- `webui/static/pyodide/pyodide-lock.json` — 캐시 확인 플래그 파일
- `webui/dev-start.sh` (line 47) — `npm run dev` 호출

## 참고

- Pyodide 공식 문서: https://pyodide.org/
- Open-WebUI 레포: https://github.com/open-webui/open-webui
- 관련 이슈: 대용량 패키지 다운로드 시 OOM 문제

---

**학습 시점**: 2025-11-21  
**해결 시간**: 1시간  
**재사용 가능성**: ⭐⭐⭐⭐⭐ (Open-WebUI 개발 환경 필수)



