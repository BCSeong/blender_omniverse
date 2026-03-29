"""
assembly: Asset 로딩 및 시뮬레이션 scene 조합

Usage:
    from cam_sim.assembly import load_assembly, AssemblyConfig
"""

from dataclasses import dataclass

# TODO: implement


@dataclass
class PoseConfig:
    """시편의 검사기 내 위치/자세"""
    position_mm: tuple[float, float, float] = (0.0, 0.0, 0.0)
    rotation_deg: tuple[float, float, float] = (0.0, 0.0, 0.0)


@dataclass
class AssemblyConfig:
    """시뮬레이션 scene 조합 설정"""
    machine_manifest: str
    specimen_manifest: str
    specimen_pose: PoseConfig
    camera_params: dict
    lighting_params: list[dict]
    usd_export_path: str = ""


def load_assembly(
    machine_manifest: str,
    specimen_manifest: str,
    pose: PoseConfig | None = None,
) -> AssemblyConfig:
    """manifest 파일들을 읽어 AssemblyConfig 반환"""
    raise NotImplementedError
