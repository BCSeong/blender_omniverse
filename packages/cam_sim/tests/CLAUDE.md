# Simulation Test Agent

## Scope
`packages/cam_sim/tests/` 디렉토리 담당.

## Responsibility
cam_sim 패키지의 unit test 작성 및 실행. Pure Python — bpy 의존 없음.

## Conventions
- pytest 사용
- 공용 API만 테스트 (내부 구현 직접 접근 금지)
- `@pytest.mark.requires_omniverse`: Omniverse 필요한 렌더 테스트
- Mock은 외부 의존(Omniverse, Blender subprocess)에만 사용
