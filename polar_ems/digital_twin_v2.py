"""Physics-aware, cloneable digital twin used by both controllers."""
from __future__ import annotations
from copy import deepcopy
from dataclasses import replace
from .domain import DispatchActionV2, StationState
from .station_config import PolarStationConfig

class StationTwinV2:
    def __init__(self, state: StationState, config: PolarStationConfig | None = None):
        self.state, self.config = state, config or PolarStationConfig()

    def clone(self) -> "StationTwinV2":
        return StationTwinV2(deepcopy(self.state), self.config)

    def apply_action(self, action: DispatchActionV2) -> tuple[float, float, float]:
        """Apply one interval; returns (critical unserved, curtailment, fuel burn)."""
        c, s, dt = self.config, self.state, self.config.interval_hours
        action.battery_charge_kw = min(max(action.battery_charge_kw, 0), c.battery_charge_limit_kw)
        action.battery_discharge_kw = min(max(action.battery_discharge_kw, 0), c.battery_discharge_limit_kw)
        if action.battery_charge_kw and action.battery_discharge_kw:
            action.battery_charge_kw = action.battery_discharge_kw = 0.0
        action.thermal_charge_kw = min(max(action.thermal_charge_kw, 0), c.thermal_charge_limit_kw)
        action.thermal_discharge_kw = min(max(action.thermal_discharge_kw, 0), c.thermal_discharge_limit_kw)
        action.thermal_charge_kw = min(action.thermal_charge_kw, (c.thermal_capacity_kwh-s.thermal_kwh)/(dt*c.thermal_efficiency))
        action.thermal_discharge_kw = min(action.thermal_discharge_kw, s.thermal_kwh*c.thermal_efficiency/dt)
        action.battery_charge_kw = min(action.battery_charge_kw, (c.battery_max_soc*c.battery_capacity_kwh-s.battery_kwh)/(dt*c.charge_efficiency))
        action.battery_discharge_kw = min(action.battery_discharge_kw, (s.battery_kwh-c.battery_min_soc*c.battery_capacity_kwh)*c.discharge_efficiency/dt)
        action.battery_charge_kw, action.battery_discharge_kw = max(0,action.battery_charge_kw), max(0,action.battery_discharge_kw)
        served = s.loads.essential_kw + s.loads.operational_kw + (s.loads.flexible_kw if action.serve_flexible else 0) + (s.loads.deferrable_kw if action.serve_deferrable else 0)
        thermal_heat = min(action.thermal_discharge_kw, s.loads.heating_kw)
        electrical_demand = served - thermal_heat + action.battery_charge_kw + action.thermal_charge_kw
        gen = []
        for i, g in enumerate(s.generators):
            requested = action.generator_kw[i] if i < len(action.generator_kw) else 0
            output = min(c.generator_max_kw, max(0, requested)) if g.available else 0
            if 0 < output < c.generator_min_kw: output = c.generator_min_kw
            if output > 0 and not g.on: g.starts += 1
            g.on, g.output_kw = output > 0, output
            if g.on: g.runtime_hours += dt
            gen.append(output)
        supply = s.wind_kw + s.solar_kw + sum(gen) + action.battery_discharge_kw
        essential_electric = s.loads.essential_kw - thermal_heat
        critical_unserved = max(0, essential_electric - supply)
        curtailment = max(0, supply - electrical_demand)
        fuel = 0.0
        for output in gen:
            if output:
                load_factor = output / c.generator_max_kw
                # Low-load operation incurs a clear efficiency penalty.
                fuel += dt * (c.generator_idle_lph + output * c.generator_l_per_kwh_at_nominal * (1.12 - .18*load_factor))
        s.fuel_litres = max(0, s.fuel_litres-fuel)
        s.battery_kwh += action.battery_charge_kw*c.charge_efficiency*dt - action.battery_discharge_kw*dt/c.discharge_efficiency
        s.battery_kwh = min(c.battery_max_soc*c.battery_capacity_kwh, max(c.battery_min_soc*c.battery_capacity_kwh, s.battery_kwh))
        s.battery_cycles += (action.battery_charge_kw + action.battery_discharge_kw)*dt/(2*c.battery_capacity_kwh)
        s.battery_soh = max(.7, 1-.00025*s.battery_cycles)
        s.thermal_kwh += action.thermal_charge_kw*c.thermal_efficiency*dt - action.thermal_discharge_kw*dt/c.thermal_efficiency
        s.thermal_kwh = max(0, min(c.thermal_capacity_kwh, s.thermal_kwh))
        return critical_unserved*dt, curtailment*dt, fuel
