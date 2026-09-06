from __future__ import annotations

from datetime import datetime, timedelta, timezone
from math import exp, sin, pi
from random import Random

from .config import StationConfig
from .models import DispatchAction, ExecutionResult, TelemetryFrame, Transition, Weather


def pv_power_from_irradiance(irradiance_w_m2: float, config: StationConfig) -> float:
    return max(0.0, min(config.pv_capacity_kw, config.pv_capacity_kw * irradiance_w_m2 / 1000.0 * 0.82))


def wind_power_from_speed(wind_mps: float, config: StationConfig) -> float:
    """Simple cut-in/rated/cut-out turbine curve."""
    if wind_mps < 3.0 or wind_mps >= 25.0:
        return 0.0
    if wind_mps >= 12.0:
        return config.wind_capacity_kw
    fraction = (wind_mps**3 - 3.0**3) / (12.0**3 - 3.0**3)
    return config.wind_capacity_kw * max(0.0, min(1.0, fraction))


class SimulatedStation:
    """Ground-truth world for V1. It is intentionally not the same as the forecaster."""

    def __init__(self, config: StationConfig, seed: int = 7) -> None:
        self.config = config
        self.rng = Random(seed)
        self.timestamp = datetime(2026, 9, 6, 10, 0, tzinfo=timezone.utc)
        self.battery_energy_kwh = config.battery_capacity_kwh * config.battery_initial_soc
        self.fuel_litres = config.fuel_initial_litres
        self.wind_mps = 8.4
        self.ambient_c = -19.2
        self.cloud_factor = 0.62
        self.generator_available = True
        self.battery_available = True

    def telemetry(self) -> TelemetryFrame:
        weather = self._weather()
        return TelemetryFrame(
            timestamp=self.timestamp,
            weather=weather,
            critical_kw=self._critical_load_kw(),
            heating_kw=self._heating_load_kw(weather.ambient_c),
            flexible_requested_kw=self._flexible_requested_kw(),
            pv_available_kw=pv_power_from_irradiance(weather.irradiance_w_m2, self.config),
            wind_available_kw=wind_power_from_speed(weather.wind_mps, self.config),
            battery_energy_kwh=self.battery_energy_kwh,
            fuel_litres=self.fuel_litres,
            generator_available=self.generator_available,
            battery_available=self.battery_available,
        )

    def apply(
        self, action: DispatchAction, telemetry_before: TelemetryFrame | None = None
    ) -> ExecutionResult:
        # The controller, safety validator and plant must operate on one sampled
        # control-interval snapshot. Sampling another random load here would create
        # a false plan-versus-execution mismatch.
        telemetry_before = telemetry_before or self.telemetry()
        dt = self.config.dt_hours
        flexible_kw = telemetry_before.flexible_requested_kw if action.flexible_enabled else 0.0
        generator_kw = action.generator_kw if self.generator_available else 0.0
        battery_kw = action.battery_kw if self.battery_available else 0.0

        charge_kw = max(0.0, -battery_kw)
        discharge_kw = max(0.0, battery_kw)
        charge_room = max(0.0, self.config.battery_max_kwh - self.battery_energy_kwh)
        charge_kw = min(
            charge_kw,
            self.config.battery_charge_limit_kw,
            charge_room / (self.config.charge_efficiency * dt),
        )
        available_kwh = max(0.0, self.battery_energy_kwh - self.config.battery_min_kwh)
        discharge_kw = min(
            discharge_kw,
            self.config.battery_discharge_limit_kw,
            available_kwh * self.config.discharge_efficiency / dt,
        )

        self.battery_energy_kwh += charge_kw * self.config.charge_efficiency * dt
        self.battery_energy_kwh -= discharge_kw * dt / self.config.discharge_efficiency

        supply_kw = telemetry_before.pv_available_kw + telemetry_before.wind_available_kw + generator_kw + discharge_kw
        demand_kw = telemetry_before.critical_kw + telemetry_before.heating_kw + flexible_kw + charge_kw
        # A flexible job may be deferred, but a deficit against essential demand is
        # safety-critical and must be surfaced to the validator/monitor.
        essential_kw = telemetry_before.critical_kw + telemetry_before.heating_kw
        critical_unserved_kw = max(0.0, essential_kw - supply_kw)
        curtailment_kw = max(0.0, supply_kw - demand_kw)

        if generator_kw > 0:
            self.fuel_litres = max(
                0.0,
                self.fuel_litres
                - dt
                * (
                    self.config.generator_idle_lph
                    + self.config.generator_marginal_l_per_kwh * generator_kw
                ),
            )

        transition = Transition(
            battery_energy_kwh=self.battery_energy_kwh,
            fuel_litres=self.fuel_litres,
            critical_unserved_kw=critical_unserved_kw,
            renewable_curtailment_kw=curtailment_kw,
        )
        self._advance_weather()
        self.timestamp += timedelta(minutes=self.config.interval_minutes)
        return ExecutionResult(telemetry_after=self.telemetry(), transition=transition)

    def _weather(self) -> Weather:
        hour = self.timestamp.hour + self.timestamp.minute / 60
        daylight = max(0.0, sin(pi * (hour - 8) / 8))
        irradiance = 520.0 * daylight * self.cloud_factor
        return Weather(ambient_c=self.ambient_c, wind_mps=self.wind_mps, irradiance_w_m2=irradiance)

    def _critical_load_kw(self) -> float:
        hour = self.timestamp.hour + self.timestamp.minute / 60
        return 70.0 + 5.5 * sin(2 * pi * (hour - 7) / 24) + self.rng.uniform(-1.5, 1.5)

    def _heating_load_kw(self, ambient_c: float) -> float:
        return max(
            8.0,
            (self.config.heating_setpoint_c - ambient_c)
            * self.config.heat_loss_kw_per_c
            / self.config.heating_cop,
        )

    def _flexible_requested_kw(self) -> float:
        hour = self.timestamp.hour + self.timestamp.minute / 60
        return 18.0 if 8 <= hour < 18 else 5.0

    def _advance_weather(self) -> None:
        hour = self.timestamp.hour + self.timestamp.minute / 60
        target_temp = -20.0 - 2.5 * sin(2 * pi * (hour - 4) / 24)
        self.ambient_c = 0.84 * self.ambient_c + 0.16 * target_temp + self.rng.uniform(-0.45, 0.45)
        self.wind_mps = max(1.0, min(19.0, 0.83 * self.wind_mps + 1.8 + self.rng.uniform(-2.2, 2.2)))
        self.cloud_factor = max(0.15, min(0.95, 0.88 * self.cloud_factor + 0.12 * self.rng.uniform(0.2, 0.9)))
