from __future__ import annotations

from dataclasses import replace
from math import isfinite

from .models import TelemetryFrame


class TelemetryProcessor:
    """Small V1 data boundary between a gateway and decision-making code.

    Future versions can add persistence, resampling and feature tables here without
    coupling those concerns to the simulator or planner.
    """

    def process(self, frame: TelemetryFrame) -> TelemetryFrame:
        numeric_values = (
            frame.weather.ambient_c,
            frame.weather.wind_mps,
            frame.weather.irradiance_w_m2,
            frame.critical_kw,
            frame.heating_kw,
            frame.flexible_requested_kw,
            frame.pv_available_kw,
            frame.wind_available_kw,
            frame.battery_energy_kwh,
            frame.fuel_litres,
        )
        if not all(isfinite(value) for value in numeric_values):
            return replace(frame, quality="bad")
        if any(value < 0 for value in numeric_values[1:]):
            return replace(frame, quality="bad")
        return frame
