# Blender Authoring — Package Orchestrator (Layer 1 + 2)

## Role
Blender MCP 및 bpy 스크립트를 활용한 scene authoring 패키지.
검사기(machine)와 시편(specimen) asset을 생성한다.

## MCP 사용 정책 (Hybrid)
- **자연어 MCP**: interactive 시편 생성, 프리뷰, 탐색적 작업
- **Python bpy 스크립트**: 재현 가능한 검사기 구성, batch import, asset 교체
- `scripts/` 디렉토리에 standalone bpy 스크립트 배치

## Sub-agents

| Module | CLAUDE.md 위치 | 역할 |
|--------|----------------|------|
| specimen | `src/blender_authoring/specimen/CLAUDE.md` | Layer 1: 시편 생성/import |
| machine | `src/blender_authoring/machine/CLAUDE.md` | Layer 2: 검사기 구축 |

## Output Contract
모든 asset은 `.blend` + `.manifest.yaml` 쌍으로 출력한다.
- specimen → `assets/specimens/<name>/`
- machine → `assets/machines/<name>/`
- manifest 스키마: `docs/manifest_schema.md` 참조

## Constraints
- cam_sim 패키지를 import하지 않는다
- bpy 의존 코드는 import guard 적용: `try: import bpy`
- 외부 asset 경로는 절대경로 금지, 프로젝트 root 상대경로 사용

## Launcher / bat 등록 규칙
bat 파일을 새로 만들거나 수정할 때 반드시:
1. `docs/requirements.md`에 해당 launcher의 requirements 추가/업데이트
   - System Python 패키지 (e.g. `cadquery-ocp`)
   - Blender addon (e.g. MCP)
   - 기타 도구 (e.g. `claude` CLI)
2. bat 파일 내에서 critical requirements 체크 + 에러 메시지 출력
3. Blender addon 설정은 context.md 초기 단계에서 MCP로 자동 확인/안내
