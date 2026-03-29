"""
spec.py: 센서 스펙 정의

지원 센서: GMAX0505 등
파라미터:
    pixel_pitch_um: 픽셀 피치 (um)
    resolution: (width, height) in pixels
    full_well_capacity_e: 포화 전자 수
    read_noise_e: 읽기 노이즈 (e- rms)
    dark_current_e_per_s: 암전류 (e-/s)
    qe_curve: {wavelength_nm: QE} 딕셔너리
"""

# TODO: implement


class SensorSpec:
    def __init__(self, config: dict):
        self.pixel_pitch_um: float = config.get("pixel_pitch_um")
        self.resolution: tuple = tuple(config.get("resolution", [0, 0]))
        self.full_well_capacity_e: float = config.get("full_well_capacity_e")
        self.read_noise_e: float = config.get("read_noise_e")
        self.dark_current_e_per_s: float = config.get("dark_current_e_per_s")
        self.qe_curve: dict = config.get("qe_curve", {})
