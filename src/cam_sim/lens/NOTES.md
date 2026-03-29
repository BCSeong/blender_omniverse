# lens 모듈 개발 노트

> SP1: Zemax/CodeV 렌즈 데이터 파싱 및 카메라 모델 생성

## 현재 상태

- [ ] L1: PinholeLens 구현
- [ ] L2: Brown-Conrady distortion 구현
- [ ] L3: Zemax PSF/distortion 데이터 추출
- [ ] L4: Full ray-traced 시뮬레이션

## 설계 결정 사항

| 날짜 | 결정 | 이유 |
|------|------|------|
| 2026-03-26 | L1 pinhole부터 시작 | Zemax/CodeV 파일 보유하나 MVP 검증 우선 |
| 2026-03-26 | Brown-Conrady 왜곡 모델 채택 | OpenCV 호환, field별 계수 fitting 가능 |

## 주요 파라미터 (타겟 광학계 기준)

- NA: ~0.5 (paraxial approximation 부족 → L2 이상 필요)
- 렌즈 종류: telecentric, hypercentric
- 왜곡 데이터 출처: Zemax field별 distortion grid

## TODO

- [ ] `PinholeLens.fov_h_deg` 구현
- [ ] `PinholeLens.pixel_size_mm` 구현
- [ ] Zemax .zmx 파일로 파서 테스트
- [ ] distortion 계수 fitting 검증

## 이슈 / 메모
