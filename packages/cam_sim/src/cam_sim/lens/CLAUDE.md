# Lens Module Agent

## Scope
`packages/cam_sim/src/cam_sim/lens/` 디렉토리만 담당.

## Responsibility
렌즈 광학 모델 구현. 순수 수학 — Blender/bpy 의존 없음.

## Public API
```python
from cam_sim.lens import load_lens, LensModel

lens = load_lens(config)
pt2d = lens.project(point_3d)
distorted = lens.distort(pt2d)
psf = lens.get_psf(field_position)  # L2+
```

## Files
- `pinhole.py`: PinholeLens (focal_length, sensor_size 기반 projection)
- `distortion.py`: Brown-Conrady distortion (k1~k6, p1, p2, OpenCV 호환)
- `zemax_parser.py`: .zmx 파싱 → 렌즈 파라미터 추출

## Constraints
- 다른 모듈 import 금지
- numpy, opencv 사용 가능
