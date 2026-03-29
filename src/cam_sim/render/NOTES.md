# render 모듈 개발 노트

> SP6: Omniverse RTX 렌더링 + Python 후처리

## 현재 상태

- [ ] Omniverse 설치 및 Python API 연결
- [ ] USD 씬 로드 및 RTX 렌더링
- [ ] OmniLensDistortion 적용
- [ ] PSF convolution 후처리
- [ ] 노이즈 모델 적용

## 설계 결정 사항

| 날짜 | 결정 | 이유 |
|------|------|------|
| 2026-03-26 | Omniverse RTX 렌더러 사용 | 물리 기반, GPU(RTX 4060) 활용 |
| 2026-03-26 | PSF/노이즈는 Python 후처리 | Omniverse 미지원 → postprocess.py에서 처리 |

## 근사화 레벨별 후처리 계획

| Level | 후처리 내용 | 우선순위 |
|-------|-----------|---------|
| L1 | 없음 (pinhole) | MVP |
| L2 | OmniLensDistortion (Omniverse 내) | Phase 2 |
| L3 | Field-dependent PSF convolution | Phase 4 |
| L3 | 센서 노이즈 (shot/read/dark) | Phase 4 |

## TODO

- [ ] Omniverse Python API 설치 확인 (RTX 4060)
- [ ] `omniverse.py`: USD 씬 열기 + RTX 렌더링 기본 구현
- [ ] `postprocess.py`: PSF convolution (scipy.signal.fftconvolve)
- [ ] 메타데이터 JSON 저장 형식 정의

## 이슈 / 메모
