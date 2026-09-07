from __future__ import annotations
from copy import deepcopy
from datetime import datetime, timezone
from .digital_twin_v2 import StationTwinV2
from .domain import StationState
from .orchestrator_v2 import PolarEMSOrchestrator
from .station_config import PolarStationConfig
from .synthetic import SyntheticStationSource

SCENARIOS = {"normal", "renewable_surplus", "storm", "extreme_cold", "generator_failure", "fuel_scarcity", "wind_loss", "increased_demand"}

def initial_state() -> StationState:
    return StationState(timestamp=datetime(2026,9,7,tzinfo=timezone.utc))

class SimulationRunner:
    def __init__(self, scenario="normal", seed=7, intelligent=True, state: StationState|None=None):
        if scenario not in SCENARIOS: raise ValueError(f"Unknown scenario {scenario}; choose {sorted(SCENARIOS)}")
        self.config=PolarStationConfig(); self.scenario=scenario
        self.orchestrator=PolarEMSOrchestrator(StationTwinV2(deepcopy(state) if state else initial_state(),self.config), SyntheticStationSource(seed,scenario),self.config,intelligent)
    @property
    def state(self): return self.orchestrator.twin.state
    def run(self, hours=24):
        return [self.orchestrator.step() for _ in range(hours)]
    def metrics(self):
        h=self.orchestrator.history
        return {"hours":len(h),"fuel_consumed_litres":round(sum(x.fuel_used_litres for x in h),2),"fuel_remaining_litres":round(self.state.fuel_litres,2),"critical_unserved_kwh":round(sum(x.critical_unserved_kwh for x in h),3),"renewable_curtailment_kwh":round(sum(x.curtailment_kwh for x in h),2),"battery_soc_pct":round(self.state.battery_soc*100,1),"battery_cycles":round(self.state.battery_cycles,3),"generator_runtime_hours":round(sum(g.runtime_hours for g in self.state.generators),1),"generator_starts":sum(g.starts for g in self.state.generators),"risk_score":h[-1].risk.score if h else 0}

def compare(scenario="normal", hours=24, seed=7):
    intelligent=SimulationRunner(scenario,seed,True); intelligent.run(hours)
    baseline=SimulationRunner(scenario,seed,False); baseline.run(hours)
    return {"scenario":scenario,"polar_ems":intelligent.metrics(),"baseline":baseline.metrics()}

def what_if(state: StationState, scenario: str, hours=48, seed=7):
    """Runs on a copied state, so the live station remains untouched."""
    runner=SimulationRunner(scenario,seed,True,state); runner.run(hours)
    return runner.metrics()
