# Render Module Agent

## Scope
이 agent는 `src/cam_sim/render/` 디렉토리만 담당한다.

## Responsibility
Omniverse RTX 렌더링 실행 및 Python 후처리 (센서 노이즈, PSF convolution).

## Public API (반드시 유지)
```python
from cam_sim.render import render_scene, postprocess

raw_images = render_scene(usd_path, render_config)
final_images = postprocess(raw_images, sensor_model, lens_model)
```

## Files
- `omniverse.py`: Omniverse RTX 렌더링 (Kit API / Isaac Sim API)
- `postprocess.py`: PSF convolution, 센서 노이즈 적용, 메타데이터 기록
- `__init__.py`: 공용 API

## Domain Knowledge
- Omniverse Kit Python API로 렌더링 제어
- OmniLensDistortion: Omniverse 내장 렌즈 왜곡 (Brown-Conrady 호환)
- Replicator API: batch 이미지 생성, randomization
- 후처리 순서: render -> PSF convolution -> sensor noise -> quantization

## Constraints
- lens, sensor 모듈의 공용 API만 사용
- Omniverse 의존 코드는 import guard 적용
- 외부 API 변경 시 루트 CLAUDE.md의 Module Contracts 업데이트 필요
