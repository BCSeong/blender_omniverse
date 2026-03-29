# Sensor Module Agent

## Scope
이 agent는 `src/cam_sim/sensor/` 디렉토리만 담당한다.

## Responsibility
이미지 센서의 물리적 특성을 모델링한다 (pixel pitch, resolution, QE, noise).

## Public API (반드시 유지)
```python
from cam_sim.sensor import load_sensor, SensorModel

sensor = load_sensor(config)              # config dict -> SensorModel
noisy = sensor.apply_noise(image)         # clean image -> noisy image
electrons = sensor.photons_to_electrons(photons)  # QE 적용
dn = sensor.electrons_to_dn(electrons)    # ADC 변환
```

## Files
- `spec.py`: SensorSpec 클래스 (pixel_pitch, resolution, QE, full_well, read_noise, dark_current, bit_depth)
- `noise.py`: 노이즈 모델 (shot noise, read noise, dark current, quantization)
- `__init__.py`: 공용 API, SensorModel alias

## Domain Knowledge
- 기준 센서: GMAX0505 (사용자가 스펙 제공 예정)
- Noise model: shot noise (Poisson), read noise (Gaussian), dark current, quantization noise
- Signal chain: photons -> electrons (QE) -> voltage (gain) -> DN (ADC)

## Constraints
- 다른 모듈 import 금지
- numpy 사용 가능
- 외부 API 변경 시 루트 CLAUDE.md의 Module Contracts 업데이트 필요
