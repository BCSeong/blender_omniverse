# Test Agent (Evaluator)

## Scope
이 agent는 `tests/` 디렉토리를 담당하며, 모든 모듈의 테스트를 검증한다.

## Responsibility
- 모듈별 unit test 작성 및 실행
- 모듈 간 인터페이스 계약 검증
- 수치 정확도 검증 (ground truth 비교)

## Test Structure
```
tests/
├── test_lens/       # lens 모듈 테스트
├── test_sensor/     # sensor 모듈 테스트
├── test_scene/      # scene 모듈 테스트
├── test_render/     # render 모듈 테스트
└── test_pipeline/   # 통합 테스트 (선택)
```

## Validation Strategy
| Level | 검증 방법 |
|-------|----------|
| L1 Pinhole | 알려진 3D->2D projection과 비교 (analytic solution) |
| L1 Distortion | OpenCV undistort 왕복 검증 (distort -> undistort = identity) |
| L2 PSF | Zemax PSF 데이터와 convolution 결과 비교 |
| Sensor noise | 통계적 검증 (mean, variance가 모델 예측과 일치) |

## Conventions
- pytest 사용
- 테스트 파일명: `test_*.py`
- Fixture는 `conftest.py`에 공용 정의
- 외부 의존 (Blender, Omniverse) 필요한 테스트는 `@pytest.mark.slow` 또는 `@pytest.mark.requires_blender` 마킹

## Constraints
- 테스트에서 모듈 내부 구현 직접 접근 금지 -> 공용 API만 테스트
- Mock은 외부 의존(Blender, Omniverse)에만 사용, 모듈 간 mock 금지
