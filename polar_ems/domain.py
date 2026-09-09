"""Core data contracts for the expanded POLAR-EMS MVP."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import IntEnum
from typing import Any


class LoadPriority(IntEnum):
    LIFE_CRITICAL = 1
    MISSION_CRITICAL = 2
    OPERATIONAL = 3
    FLEXIBLE = 4
    DEFERRABLE = 5


@dataclass
class LoadDemand:
    critical_kw: float
    mission_kw: float
    operational_kw: float
    flexible_kw: float
    deferrable_kw: float
    heating_kw: float

    @property
    def essential_kw(self) -> float:
        return self.critical_kw + self.mission_kw + self.heating_kw

    @property
    def total_kw(self) -> float:
        return self.essential_kw + self.operational_kw + self.flexible_kw + self.deferrable_kw

    def served(self, mode: str) -> "LoadDemand":
        if mode == "SURVIVAL":
            return LoadDemand(self.critical_kw, 0, 0, 0, 0, self.heating_kw)
        if mode == "EMERGENCY":
            return LoadDemand(self.critical_kw, self.mission_kw, 0, 0, 0, self.heating_kw)
        if mode == "CONSERVATION":
            return LoadDemand(self.critical_kw, self.mission_kw, self.operational_kw * .8, 0, 0, self.heating_kw)
        return self


@dataclass
class WeatherState:
    temperature_c: float
    wind_mps: float
    solar_factor: float
    storm: bool = False


@dataclass
class GeneratorState:
    id: str
    available: bool = True
    on: bool = False
    output_kw: float = 0.0
    runtime_hours: float = 0.0
    starts: int = 0
    health: float = 1.0


@dataclass
class StationState:
    timestamp: datetime
    battery_kwh: float = 600.0
    battery_soh: float = 1.0
    battery_cycles: float = 0.0
    fuel_litres: float = 42000.0
    thermal_kwh: float = 1000.0
    weather: WeatherState = field(default_factory=lambda: WeatherState(-20, 8, 0))
    loads: LoadDemand = field(default_factory=lambda: LoadDemand(80, 70, 75, 45, 20, 100))
    generators: list[GeneratorState] = field(default_factory=lambda: [GeneratorState(f"GEN-{i}") for i in range(1, 4)])
    wind_kw: float = 0.0
    solar_kw: float = 0.0
    mode: str = "NORMAL"

    @property
    def battery_soc(self) -> float:
        return self.battery_kwh / 1000.0

    @property
    def fuel_pct(self) -> float:
        return self.fuel_litres / 60000.0

    def json(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class DispatchActionV2:
    generator_kw: list[float]
    battery_charge_kw: float = 0.0
    battery_discharge_kw: float = 0.0
    thermal_charge_kw: float = 0.0
    thermal_discharge_kw: float = 0.0
    serve_flexible: bool = True
    serve_deferrable: bool = True
    explanation: str = ""

    @property
    def generator_total_kw(self) -> float:
        return sum(self.generator_kw)


@dataclass
class ForecastPoint:
    timestamp: datetime
    load_kw: float
    heating_kw: float
    wind_kw: float
    solar_kw: float
    temperature_c: float
    storm_probability: float = 0.0


@dataclass
class RiskAssessment:
    score: float
    band: str
    contributors: dict[str, float]


@dataclass
class StepResult:
    state: StationState
    action: DispatchActionV2
    risk: RiskAssessment
    critical_unserved_kwh: float
    curtailment_kwh: float
    fuel_used_litres: float
