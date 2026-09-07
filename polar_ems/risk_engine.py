from __future__ import annotations
from .domain import ForecastPoint, RiskAssessment, StationState
from .station_config import PolarStationConfig

def assess_risk(state: StationState, forecast: list[ForecastPoint], config: PolarStationConfig) -> RiskAssessment:
    next6 = forecast[:6] or []
    avg_renew = sum(x.wind_kw+x.solar_kw for x in next6)/max(1,len(next6))
    avg_heat = sum(x.heating_kw for x in next6)/max(1,len(next6))
    contributors = {
      "low_battery": max(0, (.45-state.battery_soc)*60),
      "fuel_reserve": max(0, (.22-state.fuel_pct)*75),
      "poor_renewable_forecast": max(0, (1-avg_renew/220)*16),
      "heating_demand": max(0, (avg_heat-100)/8),
      "storm_forecast": 18 if any(x.storm_probability>.5 for x in next6) else 0,
      "generator_health": sum(1-g.health for g in state.generators)*9 + 8*sum(not g.available for g in state.generators),
      "battery_health": max(0, .9-state.battery_soh)*30,
    }
    score = min(100, round(sum(contributors.values()), 1))
    band = "Green / Normal" if score <=25 else "Blue / Monitor" if score<=50 else "Yellow / Conservation" if score<=70 else "Red / Emergency" if score<=85 else "Black / Survival"
    return RiskAssessment(score, band, {k:round(v,1) for k,v in contributors.items() if v>0})

def fuel_autonomy(state: StationState, forecast: list[ForecastPoint], config: PolarStationConfig) -> dict:
    demand = sum(max(0, x.load_kw-x.wind_kw-x.solar_kw) for x in forecast)/max(1,len(forecast))
    daily_litres = max(1, demand*24*config.generator_l_per_kwh_at_nominal)
    usable = max(0, state.fuel_litres-config.emergency_fuel_reserve_litres)
    days = usable/daily_litres
    return {"fuel_remaining_litres":round(state.fuel_litres,1), "predicted_average_consumption_litres_per_day":round(daily_litres,1), "operational_autonomy_days":round(days,1), "autonomy_risk":"high" if days<7 else "medium" if days<21 else "low"}

def operating_mode(risk: RiskAssessment, state: StationState) -> str:
    if risk.score>85: return "SURVIVAL"
    if risk.score>70: return "EMERGENCY"
    if risk.score>50 or state.fuel_pct<.15: return "CONSERVATION"
    if state.wind_kw+state.solar_kw > state.loads.total_kw: return "RENEWABLE SURPLUS"
    return "NORMAL"
