from __future__ import annotations

from .config import StationConfig
from .models import CycleRecord


class Monitor:
    def __init__(self, config: StationConfig) -> None:
        self.config = config
        self.records: list[CycleRecord] = []

    def record(self, record: CycleRecord) -> None:
        self.records.append(record)

    def summary(self) -> dict[str, float | int]:
        if not self.records:
            return {}
        first = self.records[0].telemetry
        last = self.records[-1].execution
        return {
            "cycles": len(self.records),
            "critical_unserved_kwh": sum(
                r.execution.transition.critical_unserved_kw * self.config.dt_hours for r in self.records
            ),
            "fuel_consumed_litres": first.fuel_litres - last.telemetry_after.fuel_litres,
            "renewable_curtailment_kwh": sum(
                r.execution.transition.renewable_curtailment_kw * self.config.dt_hours for r in self.records
            ),
            "safety_fallbacks": sum(1 for r in self.records if r.validation.used_fallback),
            "ending_soc_pct": 100
            * last.telemetry_after.battery_energy_kwh
            / self.config.battery_capacity_kwh,
            "ending_fuel_litres": last.telemetry_after.fuel_litres,
        }
