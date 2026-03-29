"""
pinhole.py: Level 1 - Pinhole 카메라 모델

파라미터:
    focal_length_mm: 초점 거리 (mm)
    sensor_width_mm: 센서 가로 크기 (mm)
    sensor_height_mm: 센서 세로 크기 (mm)
    image_width_px: 이미지 가로 해상도 (pixels)
    image_height_px: 이미지 세로 해상도 (pixels)
"""

# TODO: implement


class PinholeLens:
    def __init__(
        self,
        focal_length_mm: float,
        sensor_width_mm: float,
        sensor_height_mm: float,
        image_width_px: int,
        image_height_px: int,
    ):
        self.focal_length_mm = focal_length_mm
        self.sensor_width_mm = sensor_width_mm
        self.sensor_height_mm = sensor_height_mm
        self.image_width_px = image_width_px
        self.image_height_px = image_height_px

    @property
    def fov_h_deg(self) -> float:
        """수평 화각 (degrees)"""
        raise NotImplementedError

    @property
    def pixel_size_mm(self) -> float:
        """픽셀 크기 (mm)"""
        raise NotImplementedError
