# Authoring Test Agent

## Scope
`packages/blender_authoring/tests/` 디렉토리 담당.

## Responsibility
blender_authoring 패키지 테스트.

## Test Strategy
1. **Unit tests (bpy mocked)**: CI-friendly, Blender 없이 실행
2. **Integration tests**: Blender 실행 필요
   - `@pytest.mark.requires_blender`
   - `@pytest.mark.mcp` (MCP 도구 사용 테스트)
