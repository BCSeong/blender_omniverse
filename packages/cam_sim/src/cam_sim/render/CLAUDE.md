# Render Module Agent

## Scope
`packages/cam_sim/src/cam_sim/render/` 디렉토리만 담당.

## Responsibility
Omniverse RTX 렌더링 실행 및 Python 후처리.

## Public API
```python
from cam_sim.render import render_scene, postprocess

raw_images = render_scene(usd_path, render_config)
final_images = postprocess(raw_images, sensor_model, lens_model)
```

## Files
- `omniverse.py`: Omniverse RTX 렌더링 (Kit API / Isaac Sim API)
- `postprocess.py`: PSF convolution, 센서 노이즈 적용, 메타데이터 기록

## Constraints
- lens, sensor 모듈의 공용 API만 사용
- Omniverse 의존 코드는 import guard 적용
