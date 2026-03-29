# Blender MCP 설정 가이드

**작성일:** 2026-03-29
**검증 환경:** Windows 11 Pro / Blender 4.5 LTS / Claude Code (VSCode Extension)

---

## 개요

Blender MCP(Model Context Protocol)는 Claude Code에서 Blender를 직접 제어할 수 있게 해주는 브릿지이다.
Python 코드 실행, 씬 조회, 스크린샷 캡처, 3D 모델 생성 등을 대화형으로 수행할 수 있다.

```
┌──────────────┐     MCP (stdio)     ┌──────────────────┐     TCP 9876     ┌──────────────┐
│  Claude Code  │ ◄──────────────► │  blender-mcp      │ ◄────────────► │   Blender     │
│  (VSCode)     │                    │  (uvx Python)     │                  │   (Addon)     │
└──────────────┘                    └──────────────────┘                  └──────────────┘
```

**동작 흐름:**
1. Claude Code가 MCP 서버(blender-mcp)를 stdio로 실행
2. blender-mcp 서버가 Blender 내 애드온과 TCP(포트 9876)로 통신
3. Blender 애드온이 Python 코드를 실행하고 결과를 반환

---

## 1. 사전 요구사항

| 항목 | 버전 | 설치 확인 |
|------|------|----------|
| **Blender** | 4.5 LTS (Portable 권장) | `blender --version` |
| **Python** | 3.12 (uvx에서 사용) | `python --version` |
| **uv** (Python 패키지 매니저) | 최신 | `uv --version` |
| **Claude Code** | VSCode Extension 또는 CLI | VSCode 확인 |

### uv 설치 (없는 경우)

```powershell
# Windows (PowerShell)
irm https://astral.sh/uv/install.ps1 | iex

# 확인
uv --version
uvx --version
```

> `uvx`는 `uv tool run`의 별칭으로, uv 설치 시 함께 제공된다.
> 경로: `C:\Users\<USERNAME>\.local\bin\uvx.exe`

---

## 2. Blender 애드온 설치 (BlenderMCP)

### 방법 A: pip install (권장)

blender-mcp PyPI 패키지를 설치하면 Blender 애드온이 포함되어 있다.

```powershell
# uvx로 blender-mcp 한 번 실행하면 자동 설치됨
uvx --python 3.12 blender-mcp
# Ctrl+C로 종료 (설치 확인용)
```

### 방법 B: Blender에서 직접 애드온 설치

1. blender-mcp GitHub에서 addon ZIP 다운로드
2. Blender > Edit > Preferences > Add-ons > Install from Disk
3. `addon.zip` 선택 > 체크박스 활성화

### 애드온 활성화 확인

```
Blender 실행 후:
1. Edit > Preferences > Add-ons
2. "BlenderMCP" 또는 "Blender MCP" 검색
3. 체크박스 활성화 확인

4. 3D Viewport > N키 (사이드바) > "BlenderMCP" 탭 확인
```

---

## 3. Claude Code MCP 설정

### 프로젝트별 설정 (`.mcp.json`)

프로젝트 루트에 `.mcp.json` 파일을 생성한다:

```json
{
  "mcpServers": {
    "blender": {
      "type": "stdio",
      "command": "cmd",
      "args": [
        "/c",
        "C:\\Users\\<USERNAME>\\.local\\bin\\uvx.exe",
        "--python",
        "3.12",
        "blender-mcp"
      ],
      "env": {
        "DISABLE_TELEMETRY": "true"
      }
    }
  }
}
```

> **경로 수정 필수**: `<USERNAME>`을 실제 Windows 사용자 이름으로 교체한다.
> 예: `C:\\Users\\Z4G5\\.local\\bin\\uvx.exe`

### uvx.exe 경로 확인

```powershell
# uvx 경로 확인
where uvx
# 또는
(Get-Command uvx).Source
```

### 글로벌 설정 (선택)

모든 프로젝트에서 사용하려면 `~/.claude/settings.json`에 설정:

```json
{
  "mcpServers": {
    "blender": {
      "type": "stdio",
      "command": "cmd",
      "args": ["/c", "C:\\Users\\<USERNAME>\\.local\\bin\\uvx.exe", "--python", "3.12", "blender-mcp"],
      "env": { "DISABLE_TELEMETRY": "true" }
    }
  }
}
```

---

## 4. 연결 및 실행

### Step 1: Blender 실행

Blender를 먼저 실행하고 BlenderMCP 패널을 확인한다.

```
3D Viewport > N키 > BlenderMCP 탭
- Port: 9876 (기본값)
- "Connect to MCP server" 또는 자동 연결 상태 확인
```

### Step 2: Claude Code에서 MCP 연결

Claude Code (VSCode Extension)를 열면 `.mcp.json`이 자동 감지된다.
MCP 서버가 연결되면 Blender 관련 도구들이 사용 가능해진다.

### Step 3: 연결 확인

Claude Code에서 다음을 요청하여 확인:

```
"Blender 씬 정보를 알려줘" → get_scene_info 호출
"뷰포트 스크린샷 보여줘"   → get_viewport_screenshot 호출
```

---

## 5. 사용 가능한 기능 (MCP 도구 목록)

### 기본 기능 (항상 사용 가능)

| 도구 | 설명 |
|------|------|
| `execute_blender_code` | Blender에서 Python 코드 직접 실행 |
| `get_scene_info` | 현재 씬의 오브젝트, 머티리얼 등 정보 조회 |
| `get_object_info` | 특정 오브젝트의 상세 정보 조회 |
| `get_viewport_screenshot` | 뷰포트 스크린샷 캡처 (이미지 반환) |

### PolyHaven 에셋 (체크박스 활성화 필요)

| 도구 | 설명 |
|------|------|
| `search_polyhaven_assets` | HDRI, 텍스처, 모델 검색 |
| `download_polyhaven_asset` | 에셋 다운로드 및 import |
| `set_texture` | 오브젝트에 PolyHaven 텍스처 적용 |
| `get_polyhaven_categories` | 카테고리 목록 조회 |

> **활성화**: BlenderMCP 패널 > "Use assets from Poly Haven" 체크

### Sketchfab 모델 (체크박스 + API Key 필요)

| 도구 | 설명 |
|------|------|
| `search_sketchfab_models` | 3D 모델 검색 |
| `get_sketchfab_model_preview` | 모델 미리보기 |
| `download_sketchfab_model` | 모델 다운로드 (크기 지정) |

> **활성화**: BlenderMCP 패널 > "Use assets from Sketchfab" 체크 + API Key 입력

### Hyper3D Rodin (AI 3D 생성, 체크박스 + API Key 필요)

| 도구 | 설명 |
|------|------|
| `generate_hyper3d_model_via_text` | 텍스트 설명으로 3D 모델 생성 |
| `generate_hyper3d_model_via_images` | 이미지로 3D 모델 생성 |
| `poll_rodin_job_status` | 생성 작업 상태 확인 |
| `import_generated_asset` | 생성된 모델 import |

### Hunyuan3D (AI 3D 생성, 체크박스 + API Key 필요)

| 도구 | 설명 |
|------|------|
| `generate_hunyuan3d_model` | 텍스트/이미지로 3D 모델 생성 |
| `poll_hunyuan_job_status` | 생성 작업 상태 확인 |
| `import_generated_asset_hunyuan` | 생성된 모델 import |

---

## 6. 실전 예시

### 6.1 Hello World 텍스트 생성

```python
# execute_blender_code로 실행
import bpy

bpy.ops.object.text_add(location=(0, 0, 0))
text_obj = bpy.context.active_object
text_obj.data.body = "Hello World"
text_obj.name = "HelloWorld"
text_obj.data.align_x = 'CENTER'
text_obj.data.align_y = 'CENTER'
text_obj.data.extrude = 0.1
text_obj.data.size = 1.0
```

### 6.2 프로시저럴 텍스처 적용 (메탈릭 골드-퍼플)

```python
import bpy

text_obj = bpy.data.objects["HelloWorld"]
text_obj.data.materials.clear()

mat = bpy.data.materials.new(name="BeautifulTexture")
mat.use_nodes = True
nodes = mat.node_tree.nodes
links = mat.node_tree.links
nodes.clear()

# Node setup
output = nodes.new('ShaderNodeOutputMaterial')
output.location = (800, 0)

bsdf = nodes.new('ShaderNodeBsdfPrincipled')
bsdf.location = (400, 0)
bsdf.inputs['Metallic'].default_value = 0.8
bsdf.inputs['Roughness'].default_value = 0.2

# Wave Texture → Color Ramp → BSDF
wave = nodes.new('ShaderNodeTexWave')
wave.location = (-400, 100)
wave.wave_type = 'RINGS'
wave.inputs['Scale'].default_value = 3.0
wave.inputs['Distortion'].default_value = 5.0
wave.inputs['Detail'].default_value = 4.0

color_ramp = nodes.new('ShaderNodeValToRGB')
color_ramp.location = (0, 100)
cr = color_ramp.color_ramp
cr.elements[0].color = (0.8, 0.2, 0.0, 1.0)   # Gold
cr.elements[1].color = (0.1, 0.0, 0.8, 1.0)    # Purple
mid = cr.elements.new(0.5)
mid.color = (1.0, 0.6, 0.0, 1.0)               # Bright gold

# Noise → Bump for surface detail
noise = nodes.new('ShaderNodeTexNoise')
noise.location = (-400, -200)
noise.inputs['Scale'].default_value = 8.0

bump = nodes.new('ShaderNodeBump')
bump.location = (200, -200)
bump.inputs['Strength'].default_value = 0.3

tex_coord = nodes.new('ShaderNodeTexCoord')
tex_coord.location = (-700, 0)

# Connect
links.new(tex_coord.outputs['Object'], wave.inputs['Vector'])
links.new(tex_coord.outputs['Object'], noise.inputs['Vector'])
links.new(wave.outputs['Fac'], color_ramp.inputs['Fac'])
links.new(color_ramp.outputs['Color'], bsdf.inputs['Base Color'])
links.new(noise.outputs['Fac'], bump.inputs['Height'])
links.new(bump.outputs['Normal'], bsdf.inputs['Normal'])
links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])

text_obj.data.materials.append(mat)
```

### 6.3 조명 설정

```python
import bpy

# Sun light
bpy.ops.object.light_add(type='SUN', location=(3, -3, 5))
sun = bpy.context.active_object
sun.data.energy = 3.0

# Accent point light
bpy.ops.object.light_add(type='POINT', location=(-2, -3, 3))
point = bpy.context.active_object
point.data.energy = 200
point.data.color = (0.5, 0.3, 1.0)

# Material Preview 모드로 전환
for area in bpy.context.screen.areas:
    if area.type == 'VIEW_3D':
        for space in area.spaces:
            if space.type == 'VIEW_3D':
                space.shading.type = 'MATERIAL'
```

---

## 7. 트러블슈팅

### 연결 오류

| 증상 | 원인 | 해결 |
|------|------|------|
| MCP 서버 시작 실패 | uvx 경로 오류 | `where uvx`로 경로 확인 후 `.mcp.json` 수정 |
| Blender 연결 안 됨 | 애드온 미활성화 | Preferences > Add-ons > BlenderMCP 체크 |
| 포트 충돌 | 9876 포트 사용 중 | 다른 Blender 인스턴스 종료 또는 포트 변경 |
| `blender-mcp` 패키지 없음 | Python 3.12 미설치 | `uv python install 3.12` |
| 코드 실행 결과 없음 | Blender가 백그라운드 | GUI 모드로 실행 확인 |

### 포트 확인 (Windows)

```powershell
# 9876 포트 사용 확인
netstat -ano | findstr "9876"

# 프로세스 확인
tasklist | findstr <PID>
```

### Python 3.12 설치 (uv)

```powershell
# uv로 Python 3.12 설치
uv python install 3.12

# 설치 확인
uv python list | findstr 3.12
```

### Blender 애드온 로그 확인

```
Blender > Window > Toggle System Console
# 또는
%APPDATA%\Blender Foundation\Blender\4.5\scripts\addons\
```

---

## 8. PolyHaven 활성화 (텍스처/HDRI/모델)

PolyHaven을 통해 무료 고품질 텍스처, HDRI, 3D 모델을 사용할 수 있다.

```
1. Blender 3D Viewport > N키 > BlenderMCP 탭
2. "Use assets from Poly Haven" 체크박스 활성화
3. MCP 서버 재연결 (Disconnect → Connect)
```

사용 예:
```
"나무 텍스처를 큐브에 적용해줘"
→ search_polyhaven_assets(asset_type="textures", categories="wood")
→ download_polyhaven_asset(asset_id="...", asset_type="textures")
→ set_texture(object_name="Cube", texture_id="...")
```

---

## 9. 다른 PC 환경에서 재현하기

### 최소 설치 순서

```powershell
# 1. uv 설치
irm https://astral.sh/uv/install.ps1 | iex

# 2. Python 3.12 설치
uv python install 3.12

# 3. blender-mcp 설치 확인 (uvx가 자동 관리)
uvx --python 3.12 blender-mcp --help

# 4. Blender 설치 (4.5 LTS Portable)
# https://www.blender.org/download/lts/4-5/

# 5. 프로젝트 clone
git clone <repo-url>
cd blender_omniverse

# 6. .mcp.json의 uvx 경로를 현재 PC에 맞게 수정
# where uvx 로 경로 확인 후 수정
```

### 환경별 차이 체크리스트

```
[ ] uvx.exe 경로 확인 및 .mcp.json 수정
[ ] Python 3.12 설치 확인 (uv python list)
[ ] Blender 설치 및 BlenderMCP 애드온 활성화
[ ] Claude Code (VSCode Extension) 설치
[ ] Blender 실행 > BlenderMCP 패널 > 포트 9876 확인
[ ] Claude Code에서 씬 정보 조회 테스트
```

---

## 10. 참고 링크

- [blender-mcp (PyPI)](https://pypi.org/project/blender-mcp/)
- [blender-mcp (GitHub)](https://github.com/ahujasid/blender-mcp)
- [MCP 프로토콜 명세](https://modelcontextprotocol.io/)
- [uv 설치 가이드](https://docs.astral.sh/uv/getting-started/installation/)
- [PolyHaven](https://polyhaven.com/)
- [Sketchfab](https://sketchfab.com/)
- [Blender Python API](https://docs.blender.org/api/current/)
