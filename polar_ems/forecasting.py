from __future__ import annotations

from datetime import timedelta
from math import cos, pi, sin

from .config import StationConfig
from .models import ForecastBundle, ForecastStep, TelemetryFrame
from .simulation import pv_power_from_irradiance, wind_power_from_speed


class SimpleForecaster:
    """A transparent baseline forecaster; replace behind this interface later."""

    def __init__(self, config: StationConfig) -> None:
        self.config = config

    def forecast(self, telemetry: TelemetryFrame) -> ForecastBundle:
        steps: list[ForecastStep] = []
        current = telemetry.timestamp

        for index in range(self.config.horizon_steps):
            timestamp = current + timedelta(minutes=self.config.interval_minutes * index)
            hour = timestamp.hour + timestamp.minute / 60

            # Smooth, conservative weather persistence. In V1 there is no data leak
            # from the simulator's future state.
            ambient_c = telemetry.weather.ambient_c - 1.5 * sin(2 * pi * (hour - 5) / 24)
            daylight = max(0.0, sin(pi * (hour - 8) / 8))
            irradiance = 380.0 * daylight * 0.42
            wind_mps = max(2.0, telemetry.weather.wind_mps * (0.94**index) + 1.6 * cos(index / 11))

            critical_kw = 68.0 + 5.0 * sin(2 * pi * (hour - 7) / 24)
            heating_kw = max(
                8.0,
                (self.config.heating_setpoint_c - ambient_c)
                * self.config.heat_loss_kw_per_c
                / self.config.heating_cop,
            )
            flexible_kw = 18.0 if 8 <= hour < 18 else 5.0

            steps.append(
                ForecastStep(
                    timestamp=timestamp,
                    critical_kw=critical_kw,
                    heating_kw=heating_kw,
                    flexible_requested_kw=flexible_kw,
                    pv_available_kw=pv_power_from_irradiance(irradiance, self.config),
                    wind_available_kw=wind_power_from_speed(wind_mps, self.config),
                    ambient_c=ambient_c,
                )
            )

        # The first MPC step is not a prediction: it is the latest measured state.
        # This prevents an avoidable mismatch between the immediate command and
        # live critical demand/renewable output.
        steps[0] = ForecastStep(
            timestamp=telemetry.timestamp,
            critical_kw=telemetry.critical_kw,
            heating_kw=telemetry.heating_kw,
            flexible_requested_kw=telemetry.flexible_requested_kw,
            pv_available_kw=telemetry.pv_available_kw,
            wind_available_kw=telemetry.wind_available_kw,
            ambient_c=telemetry.weather.ambient_c,
        )

        return ForecastBundle(created_at=current, steps=steps)
