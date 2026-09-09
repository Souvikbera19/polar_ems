from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class PolarStationConfig:
    interval_hours: float = 1.0
    battery_capacity_kwh: float = 1000.0
    battery_min_soc: float = .15
    battery_normal_reserve: float = .20
    battery_max_soc: float = .95
    battery_charge_limit_kw: float = 250.0
    battery_discharge_limit_kw: float = 300.0
    charge_efficiency: float = .94
    discharge_efficiency: float = .94
    thermal_capacity_kwh: float = 2000.0
    thermal_charge_limit_kw: float = 180.0
    thermal_discharge_limit_kw: float = 160.0
    thermal_efficiency: float = .92
    fuel_capacity_litres: float = 60000.0
    emergency_fuel_reserve_litres: float = 5000.0
    generator_count: int = 3
    generator_min_kw: float = 50.0
    generator_max_kw: float = 200.0
    generator_idle_lph: float = 3.5
    generator_l_per_kwh_at_nominal: float = .255
    wind_capacity_kw: float = 300.0
    solar_capacity_kw: float = 150.0
    fuel_weight: float = 1.0
    battery_degradation_weight: float = .02
    critical_load_penalty: float = 1_000_000.0
    curtailment_weight: float = .1
