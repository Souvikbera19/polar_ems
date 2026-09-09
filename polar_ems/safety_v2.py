from __future__ import annotations
from .domain import DispatchActionV2, StationState
from .station_config import PolarStationConfig

class DeterministicSafetyValidator:
    def __init__(self, config: PolarStationConfig | None=None): self.config=config or PolarStationConfig()
    def validate(self, state: StationState, action: DispatchActionV2) -> tuple[DispatchActionV2, list[str]]:
        c=self.config; reasons=[]
        action.generator_kw=(action.generator_kw+[0]*c.generator_count)[:c.generator_count]
        for i,g in enumerate(state.generators):
            if not g.available and action.generator_kw[i]: action.generator_kw[i]=0; reasons.append(f"{g.id} unavailable")
            if 0<action.generator_kw[i]<c.generator_min_kw: action.generator_kw[i]=c.generator_min_kw; reasons.append(f"{g.id} raised to minimum safe output")
            if action.generator_kw[i]>c.generator_max_kw: action.generator_kw[i]=c.generator_max_kw; reasons.append(f"{g.id} capped at max output")
        if action.battery_charge_kw and action.battery_discharge_kw:
            action.battery_discharge_kw=0; reasons.append("simultaneous battery charge/discharge prohibited")
        if state.battery_soc<=c.battery_min_soc and action.battery_discharge_kw:
            action.battery_discharge_kw=0; reasons.append("minimum battery SOC protected")
        if state.fuel_litres<=c.emergency_fuel_reserve_litres:
            action.serve_flexible=action.serve_deferrable=False; reasons.append("emergency fuel reserve: noncritical loads shed")
        # Guarantee essential load where capacity permits, using available generators.
        need=max(0,state.loads.essential_kw-action.thermal_discharge_kw-state.wind_kw-state.solar_kw-action.battery_discharge_kw-sum(action.generator_kw))
        for i,g in enumerate(state.generators):
            add=min(need, c.generator_max_kw-action.generator_kw[i]) if g.available else 0
            action.generator_kw[i]+=add; need-=add
        if need>1e-6: reasons.append("critical capacity shortfall: physical capacity insufficient")
        return action,reasons
