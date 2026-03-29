"""
scene: 씬 구성 모듈 공용 API

Usage:
    from cam_sim.scene import build_scene
"""


def build_scene(
    lens_model,
    sensor_model,
    object_config: dict,
    lighting_config: dict,
    output_usd_path: str,
) -> str:
    """씬을 구성하고 USD 파일 경로 반환"""
    raise NotImplementedError
