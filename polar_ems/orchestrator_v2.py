from __future__ import annotations
from copy import deepcopy
from .baseline_controller import BaselineController
from .digital_twin_v2 import StationTwinV2
from .domain import StepResult
from .forecasting_engine import StationForecaster
from .mpc_engine import MPCOptimizer
from .risk_engine import assess_risk, operating_mode
from .safety_v2 import DeterministicSafetyValidator
from .station_config import PolarStationConfig
from .synthetic import SyntheticStationSource

class PolarEMSOrchestrator:
    def __init__(self, twin: StationTwinV2, source: SyntheticStationSource, config: PolarStationConfig|None=None, intelligent=True):
        self.twin,self.source,self.config,self.intelligent=twin,source,config or PolarStationConfig(),intelligent
        self.forecaster=StationForecaster(); self.optimizer=MPCOptimizer(self.config); self.safety=DeterministicSafetyValidator(self.config); self.baseline=BaselineController(self.config); self.history=[]; self.step_no=0
    def step(self) -> StepResult:
        state=self.twin.state; self.source.update(state,self.step_no)
        forecast=self.forecaster.predict(state,24,self.source.scenario)
        risk=assess_risk(state,forecast,self.config); state.mode=operating_mode(risk,state)
        proposed=self.optimizer.plan(state,forecast)[0] if self.intelligent else self.baseline.decide(state)
        action,reasons=self.safety.validate(state,proposed)
        if reasons: action.explanation += " Safety: " + "; ".join(reasons)
        critical,curtailment,fuel=self.twin.apply_action(action)
        # Persist a snapshot, rather than a mutable reference to the next twin state.
        result=StepResult(deepcopy(state),deepcopy(action),risk,critical,curtailment,fuel); self.history.append(result)
        self.source.advance(state); self.step_no+=1
        return result
