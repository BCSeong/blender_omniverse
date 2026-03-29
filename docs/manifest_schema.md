# Asset Manifest Schema

Layer 1/2 (blender_authoring) → Layer 3 (cam_sim) 간 교환 형식.
각 asset은 `.blend` + `.manifest.yaml` 쌍으로 저장.

---

## Specimen Manifest

```yaml
format_version: "1.0"
asset_type: specimen
name: <string>                    # asset 이름 (디렉토리명과 동일)
blend_file: <filename>.blend      # 같은 디렉토리 내 .blend 파일
object_name: Specimen             # .blend 내 오브젝트명 (고정)
bounding_box_mm: [x, y, z]       # 바운딩 박스 크기 (mm)
origin: center | bottom_center   # 원점 위치
material_description: <string>    # material 요약 (사람 참고용)
created_by: blender_authoring.specimen
```

**저장 위치**: `assets/specimens/<name>/<name>.manifest.yaml`

---

## Machine Manifest

```yaml
format_version: "1.0"
asset_type: machine
name: <string>
blend_file: <filename>.blend
groups:
  camera_rig:
    objects:
      - name: <string>            # Blender 오브젝트명
        role: camera | sensor | lens_geometry
    camera_params:
      focal_length_mm: <float>
      sensor_width_mm: <float>
      sensor_height_mm: <float>
      image_width_px: <int>
      image_height_px: <int>
      telecentric: <bool>
  lighting_rig:
    objects:
      - name: <string>
        role: ring_light | coaxial | dome | area | point
    lighting_params:              # optional
      intensity: <float>
      color_temperature_k: <float>
lens_data_file: <path> | null     # .zmx 또는 parsed JSON (optional)
created_by: blender_authoring.machine
```

**저장 위치**: `assets/machines/<name>/<name>.manifest.yaml`

---

## Versioning
- `format_version` 필드로 하위 호환성 관리
- 스키마 변경 시 이 문서와 양쪽 패키지의 CLAUDE.md 동시 업데이트 필요
