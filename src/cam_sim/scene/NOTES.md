# scene 모듈 개발 노트

> SP3 + SP4 + SP5: 피사체, 조명, 카메라 배치 및 USD export

## 현재 상태

- [ ] Blender bpy 환경 설정
- [ ] objects.py: 기본 피사체 생성 (cube, sphere)
- [ ] lighting.py: point light 기본 구현
- [ ] camera.py: LensModel → Blender 카메라 변환
- [ ] usd_export.py: USD 내보내기

## 설계 결정 사항

| 날짜 | 결정 | 이유 |
|------|------|------|
| 2026-03-26 | Blender bpy API 사용 | scene authoring 최강, OptiCore Zemax import 가능 |
| 2026-03-26 | USD export로 Omniverse 연동 | 렌더링은 Omniverse RTX에서 수행 |

## 주의사항

- Blender↔USD 변환 시 **센서 크기 단위/fit 문제** 있음 → camera.py에서 명시적 변환 필요
- OmniLensDistortion은 Blender에서 설정 불가 → USD export 후 Omniverse에서 추가

## TODO

- [ ] Blender bpy import 환경 구성 (standalone script 방식)
- [ ] `camera.py`: focal_length, sensor_size → Blender UsdGeomCamera 변환
- [ ] USD export 후 Omniverse에서 열기 테스트

## 이슈 / 메모
