from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal


@dataclass(frozen=True)
class Weather:
    ambient_c: float
    wind_mps: float
    irradiance_w_m2: float


@dataclass(frozen=True)
class TelemetryFrame:
    timestamp: datetime
    weather: Weather
    critical_kw: float
    heating_kw: float
    flexible_requested_kw: float
    pv_available_kw: float
    wind_available_kw: float
    battery_energy_kwh: float
    fuel_litres: float
    generator_available: bool = True
    battery_available: bool = True
    quality: Literal["good", "degraded", "bad"] = "good"

    @property
    def soc(self) -> float:
        # Capacity is intentionally attached by callers where configuration is known.
        return self.battery_energy_kwh


@dataclass(frozen=True)
class ForecastStep:
    timestamp: datetime
    critical_kw: float
    heating_kw: float
    flexible_requested_kw: float
    pv_available_kw: float
    wind_available_kw: float
    ambient_c: float

    @property
    def renewable_available_kw(self) -> float:
        return self.pv_available_kw + self.wind_available_kw

    @property
    def essential_kw(self) -> float:
        return self.critical_kw + self.heating_kw


@dataclass(frozen=True)
class ForecastBundle:
    created_at: datetime
    steps: list[ForecastStep]


@dataclass(frozen=True)
class DispatchAction:
    """Battery power is positive when discharging and negative when charging."""

    generator_kw: float
    battery_kw: float
    flexible_enabled: bool
    reason: str


@dataclass(frozen=True)
class DispatchPlan:
    created_at: datetime
    steps: list[DispatchAction]
    dynamic_fuel_reserve_litres: float
    planner_note: str

    @property
    def first_action(self) -> DispatchAction:
        return self.steps[0]


@dataclass(frozen=True)
class ValidationResult:
    approved: bool
    action: DispatchAction
    reasons: list[str] = field(default_factory=list)
    used_fallback: bool = False


@dataclass(frozen=True)
class Transition:
    battery_energy_kwh: float
    fuel_litres: float
    critical_unserved_kw: float
    renewable_curtailment_kw: float


@dataclass(frozen=True)
class ExecutionResult:
    telemetry_after: TelemetryFrame
    transition: Transition


@dataclass(frozen=True)
class CycleRecord:
    timestamp: datetime
    telemetry: TelemetryFrame
    action: DispatchAction
    validation: ValidationResult
    execution: ExecutionResult
