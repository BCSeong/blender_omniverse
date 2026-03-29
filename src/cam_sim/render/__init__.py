"""
render: 렌더링 및 후처리 모듈 공용 API

Usage:
    from cam_sim.render import render_scene, postprocess
"""


def render_scene(usd_path: str, render_config: dict) -> list:
    """USD 씬을 렌더링하고 raw 이미지 리스트 반환"""
    raise NotImplementedError


def postprocess(raw_images: list, sensor_model, lens_model) -> list:
    """센서 노이즈, PSF 적용 후 최종 이미지 + 메타데이터 반환"""
    raise NotImplementedError
