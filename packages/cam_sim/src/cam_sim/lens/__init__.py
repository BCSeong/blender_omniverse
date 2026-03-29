"""
lens: 렌즈 데이터 모듈 공용 API

Usage:
    from cam_sim.lens import load_lens, LensModel
"""

from cam_sim.lens.pinhole import PinholeLens

# TODO: add distortion, zemax_parser when implemented

LensModel = PinholeLens  # 현재 기본값


def load_lens(config: dict):
    """config dict를 받아 적절한 LensModel 반환"""
    raise NotImplementedError
