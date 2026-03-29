"""
sensor: 센서 모듈 공용 API

Usage:
    from cam_sim.sensor import load_sensor, SensorModel
"""

from cam_sim.sensor.spec import SensorSpec as SensorModel


def load_sensor(config: dict):
    """config dict를 받아 SensorModel 반환"""
    raise NotImplementedError
