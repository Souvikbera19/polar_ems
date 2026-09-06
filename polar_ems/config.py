from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class StationConfig:
    """All units are kW, kWh, litres, degrees C, or fractions as named."""

    interval_minutes: int = 15
    horizon_steps: int = 96

    battery_capacity_kwh: float = 500.0
    battery_initial_soc: float = 0.62
    battery_soc_min: float = 0.30
    battery_soc_max: float = 0.90
    battery_charge_limit_kw: float = 100.0
    battery_discharge_limit_kw: float = 120.0
    charge_efficiency: float = 0.94
    discharge_efficiency: float = 0.94

    generator_min_kw: float = 40.0
    generator_max_kw: float = 150.0
    generator_idle_lph: float = 3.0
    generator_marginal_l_per_kwh: float = 0.245

    fuel_capacity_litres: float = 4000.0
    fuel_initial_litres: float = 1420.0
    fuel_emergency_reserve_litres: float = 800.0
    fuel_stress_hours: int = 48

    pv_capacity_kw: float = 120.0
    wind_capacity_kw: float = 180.0
    heating_setpoint_c: float = 18.0
    heat_loss_kw_per_c: float = 1.25
    heating_cop: float = 1.8

    @property
    def dt_hours(self) -> float:
        return self.interval_minutes / 60.0

    @property
    def battery_min_kwh(self) -> float:
        return self.battery_capacity_kwh * self.battery_soc_min

    @property
    def battery_max_kwh(self) -> float:
        return self.battery_capacity_kwh * self.battery_soc_max
