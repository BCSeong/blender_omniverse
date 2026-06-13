# Project Requirements

Environment, Python packages, and Blender addon requirements for the project.
This document is the single source of truth for what needs to be installed.

---

## Common Requirements

### System
- **Blender 4.x** — path configured in `blender.env`
  ```
  cp blender.env.example blender.env
  # Edit and set: BLENDER_PATH=D:\Tools\blender-4.5.8-windows-x64\blender.exe
  ```
- **Claude Code CLI** — `claude` must be in PATH

### Blender Addons
- **Blender MCP** — must be enabled in Edit > Preferences > Add-ons
  - The MCP addon provides the bridge between Claude and Blender
  - Default port: 9876

---

## Per-Launcher Requirements

### `start_specimen.bat`
Interactive specimen authoring (natural language → Blender model).

| Requirement | Type | Notes |
|---|---|---|
| Blender MCP addon | Blender | Must be running |
| (none extra) | | |

### `start_specimen_with_data.bat`
Height map + texture map → Blender mesh conversion.

| Requirement | Type | Notes |
|---|---|---|
| Blender MCP addon | Blender | Must be running |
| NumPy | Blender Python | Bundled with Blender |

### `start_package_authoring.bat`
Create 3D models of electronic component packages.

| Requirement | Type | Notes |
|---|---|---|
| Blender MCP addon | Blender | Must be running |
| `cadquery-ocp` | System Python | For STEP → STL conversion |
| | | `pip install cadquery-ocp` |

---

## Installing Python Requirements

### System Python (for STEP conversion)
```bash
pip install cadquery-ocp
```

### Blender Python
Most packages (NumPy, etc.) are bundled with Blender. If additional packages
are needed inside Blender:
```python
# From Blender Python console:
import subprocess, sys
subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'package_name'])
```

---

## Blender Addon Setup

The MCP addon can be enabled programmatically:
```python
import bpy
bpy.ops.preferences.addon_enable(module="blender_mcp")
bpy.ops.wm.save_userpref()
```
However, the addon server must also be started manually from the addon panel.
