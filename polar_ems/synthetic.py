"""Physics-informed synthetic weather and load source; never represents real telemetry."""
from __future__ import annotations
from datetime import timedelta
from math import pi, sin
from random import Random
from .domain import LoadDemand, StationState, WeatherState
from .station_config import PolarStationConfig

class SyntheticStationSource:
    def __init__(self, seed: int = 7, scenario: str = "normal"):
        self.rng, self.scenario = Random(seed), scenario

    def update(self, state: StationState, step: int) -> None:
        hour, day = state.timestamp.hour, step / 24
        storm = self.scenario == "storm" and 10 <= step < 34
        cold = self.scenario == "extreme_cold" and step >= 8
        surplus = self.scenario == "renewable_surplus"
        wind_loss = self.scenario == "wind_loss" and step < 48
        temp = -19 - 7*sin(2*pi*(hour-4)/24) - (16 if cold else 0) + self.rng.uniform(-1.8, 1.8)
        if storm: temp -= 8
        wind = max(0, 8 + 3*sin(2*pi*day/3) + self.rng.uniform(-2.5, 2.5))
        if surplus: wind += 7
        if storm: wind *= .20
        if wind_loss: wind *= .40
        daylight = max(0, sin(pi*(hour-6)/12))
        solar = daylight * (.35 + .45*self.rng.random()) * (0.15 if storm else 1)
        heating = max(65, 2.4*(18-temp))
        research = 72 + 16*(1 if 8 <= hour < 20 else .25) + self.rng.uniform(-5, 5)
        state.weather = WeatherState(temp, wind, solar, storm)
        state.loads = LoadDemand(80, 70, 60, 45, 20, heating)
        state.wind_kw = self.wind_power(wind)
        state.solar_kw = 150*solar*.82
        if self.scenario == "generator_failure" and step >= 8:
            state.generators[1].available = False
        if self.scenario == "fuel_scarcity": state.fuel_litres = min(state.fuel_litres, 6200)
        if self.scenario == "increased_demand": state.loads.operational_kw *= 1.3

    @staticmethod
    def wind_power(wind: float) -> float:
        if wind < 3 or wind >= 25: return 0
        if wind >= 12: return 300
        return 300*((wind**3-27)/(1728-27))

    def advance(self, state: StationState) -> None:
        state.timestamp += timedelta(hours=1)
