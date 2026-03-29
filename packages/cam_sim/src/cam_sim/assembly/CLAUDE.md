# Assembly Module Agent

## Scope
`packages/cam_sim/src/cam_sim/assembly/` 디렉토리만 담당.

## Responsibility
Layer 1/2에서 생성된 asset을 로드하고, 시뮬레이션 scene을 조합한다.
blender_authoring 패키지를 import하지 않음 — manifest YAML만 읽는다.

## Public API
```python
from cam_sim.assembly import load_assembly, AssemblyConfig

assembly = load_assembly(machine_manifest, specimen_manifest, pose)
assembly = swap_specimen(assembly, new_specimen_manifest)
assembly = swap_lens(assembly, new_lens_data)
```

## Files
- `loader.py`: manifest 읽기, AssemblyConfig 생성, headless Blender USD export
- `grouping.py`: asset swap API (specimen 교체, lens 교체 등)

## Blender 의존성
- bpy를 직접 import하지 않음
- USD export 필요 시 subprocess로 headless Blender 호출
- `blender_authoring/scripts/` 의 bpy 스크립트를 subprocess로 실행

## Constraints
- blender_authoring 코드 import 금지
- manifest 스키마: `docs/manifest_schema.md` 준수
