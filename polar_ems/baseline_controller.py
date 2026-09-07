from __future__ import annotations
from .domain import DispatchActionV2, StationState
from .station_config import PolarStationConfig

class BaselineController:
    """Reactive dispatch: deliberately does not use a future forecast."""
    def __init__(self, config: PolarStationConfig | None = None): self.config=config or PolarStationConfig()
    def decide(self, state: StationState) -> DispatchActionV2:
        net=state.loads.total_kw-state.wind_kw-state.solar_kw
        discharge=min(max(0,net), self.config.battery_discharge_limit_kw, max(0,state.battery_kwh-self.config.battery_min_soc*1000)*self.config.discharge_efficiency)
        net-=discharge; generators=[]
        for g in state.generators:
            output=min(self.config.generator_max_kw,max(0,net)) if g.available else 0
            if 0<output<self.config.generator_min_kw: output=self.config.generator_min_kw
            generators.append(output); net-=output
        charge=min(max(0,-net), self.config.battery_charge_limit_kw)
        return DispatchActionV2(generators, charge, discharge, explanation="Reactive baseline: renewables, battery, then diesel.")
