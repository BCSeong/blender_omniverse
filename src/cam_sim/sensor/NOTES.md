# sensor 모듈 개발 노트

> SP2: 센서 특성 모델링

## 현재 상태

- [ ] SensorSpec 기본 파라미터 정의
- [ ] GMAX0505 config 파일 작성
- [ ] 노이즈 모델 구현 (shot, read, dark current)
- [ ] QE 스펙트럼 적용

## 설계 결정 사항

| 날짜 | 결정 | 이유 |
|------|------|------|
| 2026-03-26 | config dict 기반 SensorSpec | 센서 교체 시 YAML만 변경하면 됨 |

## 타겟 센서

| 센서 모델 | pixel pitch | 해상도 | 비고 |
|-----------|------------|--------|------|
| GMAX0505 | TBD | TBD | 우선 지원 |

## TODO

- [ ] GMAX0505 datasheet 파라미터 입력 (`configs/sensor_gmax0505.yaml`)
- [ ] `noise.py` 노이즈 모델 구현
- [ ] 노이즈 unit test 작성

## 이슈 / 메모
