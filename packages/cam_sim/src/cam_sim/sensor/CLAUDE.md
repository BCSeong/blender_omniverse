# Sensor Module Agent

## Scope
`packages/cam_sim/src/cam_sim/sensor/` 디렉토리만 담당.

## Responsibility
이미지 센서 물리 모델링. 순수 수학 — Blender/bpy 의존 없음.

## Public API
```python
from cam_sim.sensor import load_sensor, SensorModel

sensor = load_sensor(config)
noisy = sensor.apply_noise(image)
```

## Files
- `spec.py`: SensorSpec (pixel_pitch, resolution, QE, full_well, read_noise, dark_current, bit_depth)
- `noise.py`: 노이즈 모델 (shot, read, dark current, quantization)

## Constraints
- 다른 모듈 import 금지
- numpy 사용 가능
