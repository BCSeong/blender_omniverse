# 설치 가이드

**환경:** Windows 10 / NVIDIA RTX 4060 / 무료 라이선스
**작성일:** 2026-03-26

---

## 중요: NVIDIA Omniverse 정책 변경 (2025년 10월)

> **Omniverse Launcher가 2025년 10월 1일부로 Deprecated 되었습니다.**
> 이후 설치는 **GitHub kit-app-template** 빌드 또는 **Legacy Tools** 직접 다운로드 방식 사용.

---

## 1. Blender 설치

### 버전 선택

| 버전 | 권장 상황 |
|------|----------|
| **Blender 4.5 LTS** | 프로덕션 파이프라인 **(권장)** |
| Blender 4.2 LTS | OptiCore 공식 테스트 버전 |

### 설치

```powershell
# https://www.blender.org/download/lts/4-5/
# Portable (.zip) 권장 - 경로 직접 제어, 여러 버전 병행 가능
# 압축 해제 예: C:\Tools\blender-4.5\

# 버전 확인
"C:\Tools\blender-4.5\blender.exe" --version
```

> Microsoft Store 버전은 파일 경로 접근 제한으로 자동화에 불리. **Portable 사용 권장.**

### OptiCore 애드온 설치

```
# https://github.com/CodeFHD/OptiCore → Code → Download ZIP

# Blender에서 설치:
Edit > Preferences > Add-ons → 우측 ▼ → Install from Disk
→ OptiCore-master.zip 선택 → 체크박스 활성화

# 확인: N 사이드바 → "OptiCore" 탭
```

> 공식 테스트 버전: Blender **4.2.1 LTS**. 4.5에서도 기본 기능 동작하나 호환성 이슈 시 GitHub Issues 확인.

### USD 내보내기

Blender 4.x 기본 내장 (별도 플러그인 불필요)

```
File > Export > Universal Scene Description (.usdc / .usda)

# 권장 설정:
- Format: .usdc (바이너리) 또는 .usda (텍스트, 디버그용)
- Meshes / Cameras / Lights / Materials 체크
- Export Textures 체크
- To USD Preview Surface 체크

# UV 이름 주의: Blender 기본 "UVMap" → Omniverse 호환을 위해 "st"로 변경 권장
```

### 백그라운드 스크립트 실행

```powershell
# GUI 없이 Python 스크립트 실행
"C:\Tools\blender-4.5\blender.exe" -b --python my_script.py

# .blend 파일에 스크립트 적용
"C:\Tools\blender-4.5\blender.exe" -b my_scene.blend --python export_usd.py
```

---

## 2. NVIDIA Omniverse 설치

### 시스템 요구사항 (RTX 4060)

| 항목 | 요구사항 | RTX 4060 상태 |
|------|---------|--------------|
| GPU 아키텍처 | Turing 이상 | Ada Lovelace ✅ |
| VRAM | 8GB+ (12GB+ 권장) | 8GB ⚠️ 단순 씬은 충분 |
| 드라이버 | 551.78 이상 | 업데이트 필요할 수 있음 |

```
# 드라이버 업데이트: https://www.nvidia.com/drivers
# Studio Driver 권장 (안정성 우선)
```

### Omniverse 설치 방법

#### 방법 A: kit-app-template 빌드 (권장)

```powershell
# 사전 요구사항: Git, Git LFS, Python 3.10+
git lfs install
git clone https://github.com/NVIDIA-Omniverse/kit-app-template.git
cd kit-app-template

.\repo.bat setup
.\repo.bat template new   # → "Application" → "USD Composer" 선택
.\repo.bat build
.\repo.bat launch         # 최초 실행: RTX 셰이더 컴파일 5~15분 소요
```

#### 방법 B: Legacy Tools (간단, 업데이트 없음)

```
# https://developer.nvidia.com/omniverse/legacy-tools
# → USD Composer ZIP 다운로드 후 압축 해제 실행
```

### Blender ↔ Omniverse 연결

#### R&D 초기 권장: USD 파일 직접 교환 (Nucleus 불필요)

```
Blender: File > Export > USD → .usdc 저장
Omniverse: File > Open → 같은 .usdc 파일 열기
```

#### Nucleus Connector 애드온 (선택)

```
# NGC Catalog에서 다운로드:
# https://catalog.ngc.nvidia.com/orgs/nvidia/teams/omniverse/collections/omni_connectors

# Blender > Edit > Preferences > Add-ons > Install from Disk
```

### RTX 렌더러 설정

```
# Viewport 렌더러 드롭다운:
# - RTX Real-Time 2.0: 빠름 (개발/디버깅)
# - RTX Interactive (Path Tracing): 정확함 (최종 렌더링)

# RTX 4060 권장: DLSS 활성화
# Viewport > Renderer Settings > DLSS
```

### Replicator 설치 확인

```python
# USD Composer Script Editor:
import omni.replicator.core as rep
print(rep.__version__)
```

---

## 3. Python 환경 설정

### 가상환경 활성화 (.venv 이미 존재)

```powershell
cd "D:\OneDrive - KohYoung\mygit\blender_omniverse"
.\.venv\Scripts\Activate.ps1

# 확인
python --version  # Python 3.11.x 이어야 함
```

### cam_sim 패키지 설치

```powershell
# 프로젝트 루트에서 venv 생성 (최초 1회)
uv venv --python 3.12

# cam_sim (시뮬레이션) 패키지 설치
uv pip install -e packages/cam_sim
uv pip install -e "packages/cam_sim[dev]"

# 설치 확인
python -c "from cam_sim.lens import load_lens; print('ok')"
```

### Blender Python과 연결

```python
# Blender Script Editor에서 외부 패키지 경로 추가:
import sys
sys.path.insert(0, r"D:\OneDrive - KohYoung\mygit\blender_omniverse\.venv\Lib\site-packages")
import cam_sim  # 외부 패키지 사용 가능
```

---

## 설치 검증 체크리스트

```
[ ] Blender 4.5 LTS 실행 확인
[ ] OptiCore 애드온 활성화 확인 (N 사이드바 OptiCore 탭)
[ ] USD 내보내기 동작 확인 (큐브 → .usdc 저장)
[ ] NVIDIA 드라이버 551.78 이상 확인
[ ] Omniverse USD Composer 실행 확인
[ ] USD Composer에서 .usdc 파일 열기 확인
[ ] RTX 렌더러 동작 확인
[ ] .venv 활성화 및 pip install -e ".[dev]" 성공
[ ] python -c "import cam_sim" 성공
[ ] Blender 백그라운드 스크립트 실행 확인
```

---

## 흔한 오류

| 오류 | 원인 | 해결 |
|------|------|------|
| USD 내보내기 텍스처 누락 | 텍스처 packed 상태 | Unpack 후 재시도 |
| OptiCore 탭 없음 | 애드온 미활성화 | Preferences > Add-ons 체크 |
| RTX 렌더러 느림 | VRAM 부족 | 씬 단순화, DLSS 활성화 |
| kit-app-template 빌드 실패 | Git LFS 미설치 | `git lfs install` 후 재클론 |
| USD Composer 셰이더 대기 | 최초 실행 정상 | 5~15분 대기 (이후 캐시됨) |

---

## 공식 문서 링크

- [Blender 4.5 LTS](https://www.blender.org/download/lts/4-5/)
- [OptiCore GitHub](https://github.com/CodeFHD/OptiCore)
- [Kit App Template GitHub](https://github.com/NVIDIA-Omniverse/kit-app-template)
- [Omniverse Legacy Tools](https://developer.nvidia.com/omniverse/legacy-tools)
- [Omniverse Blender Connector](https://docs.omniverse.nvidia.com/connect/latest/blender.html)
- [Omniverse RTX 렌더러](https://docs.omniverse.nvidia.com/materials-and-rendering/latest/rtx-renderer.html)
- [Omniverse Replicator](https://docs.omniverse.nvidia.com/extensions/latest/ext_replicator.html)
