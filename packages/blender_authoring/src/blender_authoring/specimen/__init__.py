"""
specimen: 시편(검사 대상) asset 생성 모듈

Usage:
    from blender_authoring.specimen import create_specimen, import_specimen
"""

# TODO: implement


def create_specimen(config: dict) -> str:
    """config에 따라 시편 생성, manifest 경로 반환"""
    raise NotImplementedError


def import_specimen(file_path: str, material_config: dict | None = None) -> str:
    """외부 3D 파일 import 후 manifest 경로 반환"""
    raise NotImplementedError
