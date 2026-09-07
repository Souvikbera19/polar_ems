"""Explainable synthetic/persistence forecasting with sklearn-compatible API."""
from __future__ import annotations
from copy import deepcopy
from datetime import timedelta
from .domain import ForecastPoint, StationState
from .synthetic import SyntheticStationSource

class BaseForecaster:
    def fit(self, data): return self
    def evaluate(self, data): return {"status": "synthetic forecast; no fitted model required"}
    def save(self, path):
        import json; open(path, "w").write(json.dumps({"type": type(self).__name__}))
    @classmethod
    def load(cls, path): return cls()

class StationForecaster(BaseForecaster):
    def __init__(self, seed: int = 99): self.seed = seed
    def predict(self, state: StationState, horizon: int = 24, scenario: str = "normal") -> list[ForecastPoint]:
        twin = deepcopy(state)
        source = SyntheticStationSource(self.seed, scenario)
        result=[]
        for step in range(horizon):
            source.update(twin, step)
            result.append(ForecastPoint(twin.timestamp, twin.loads.total_kw, twin.loads.heating_kw, twin.wind_kw, twin.solar_kw, twin.weather.temperature_c, .85 if twin.weather.storm else .05))
            source.advance(twin)
        return result

class LoadForecaster(StationForecaster): pass
class RenewableForecaster(StationForecaster): pass
class HeatingForecaster(StationForecaster): pass
