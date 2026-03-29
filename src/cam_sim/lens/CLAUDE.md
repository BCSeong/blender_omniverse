# Lens Module Agent

## Scope
이 agent는 `src/cam_sim/lens/` 디렉토리만 담당한다.

## Responsibility
Zemax/CodeV 렌즈 데이터를 파싱하고, 카메라 렌즈 광학 모델을 구현한다.

## Public API (반드시 유지)
```python
from cam_sim.lens import load_lens, LensModel

lens = load_lens(config)            # config dict -> LensModel
pt2d = lens.project(point_3d)       # 3D -> 2D projection
distorted = lens.distort(pt2d)      # undistorted -> distorted (L1+)
psf = lens.get_psf(field_position)  # field-dependent PSF (L2+)
```

## Files
- `pinhole.py`: PinholeLens 구현 (focal_length, sensor_size 기반 projection)
- `distortion.py`: Brown-Conrady distortion model (k1~k6, p1, p2)
- `zemax_parser.py`: .zmx 파일 파싱 -> 렌즈 파라미터 추출
- `__init__.py`: 공용 API, LensModel alias

## Domain Knowledge
- 타겟: 머신비전 + 현미경, NA ~0.5, telecentric/hypercentric
- Paraxial approximation은 부족 -> field-dependent 모델 필요
- Brown-Conrady: OpenCV 호환 (k1~k6, p1, p2)
- Zemax Huygens PSF -> 5x5 field grid 추출 예정 (L2)

## Constraints
- 다른 모듈 import 금지 (sensor, scene, render)
- numpy, opencv 사용 가능
- 외부 API 변경 시 루트 CLAUDE.md의 Module Contracts 업데이트 필요
