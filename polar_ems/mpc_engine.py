"""Small, solver-free MPC optimizer. It evaluates feasible dispatch candidates across a forecast horizon."""
from __future__ import annotations
from .domain import DispatchActionV2, ForecastPoint, StationState
from .station_config import PolarStationConfig

class MPCOptimizer:
    def __init__(self, config: PolarStationConfig | None = None): self.config=config or PolarStationConfig()
    def plan(self, state: StationState, forecast: list[ForecastPoint]) -> list[DispatchActionV2]:
        plan=[]; soc=state.battery_soc
        storm = any(p.storm_probability>.5 for p in forecast[:12])
        reserve_target=.85 if storm else (.65 if state.fuel_pct<.2 else .45)
        for i,p in enumerate(forecast):
            flexible = not (storm or state.fuel_pct<.2)
            deferrable = flexible and p.wind_kw+p.solar_kw>p.load_kw
            demand=p.load_kw-(0 if flexible else state.loads.flexible_kw)-(0 if deferrable else state.loads.deferrable_kw)
            renew=p.wind_kw+p.solar_kw
            future_renew=sum(q.wind_kw+q.solar_kw for q in forecast[i:min(i+6,len(forecast))])/max(1,min(6,len(forecast)-i))
            future_load=sum(q.load_kw for q in forecast[i:min(i+6,len(forecast))])/max(1,min(6,len(forecast)-i))
            prep=storm and i<12
            charge=min(self.config.battery_charge_limit_kw, max(0, renew-demand))
            # During pre-storm surplus, generator charging is allowed only until safe target.
            extra_charge=min(90, max(0, reserve_target-soc)*1000) if prep and soc<reserve_target else 0
            net=demand+charge+extra_charge-renew
            preserve = prep or future_renew < .45*future_load
            discharge=0 if preserve else min(max(0,net), self.config.battery_discharge_limit_kw, max(0,soc-self.config.battery_min_soc)*1000*self.config.discharge_efficiency)
            net-=discharge
            gens=[]
            for g in state.generators:
                output=min(self.config.generator_max_kw,max(0,net)) if g.available else 0
                if 0<output<self.config.generator_min_kw: output=self.config.generator_min_kw
                gens.append(output); net-=output
            # generator surplus can charge battery specifically for storm preparation
            if prep and sum(gens)>0: extra_charge=min(self.config.battery_charge_limit_kw-charge, max(0,sum(gens)-max(0,demand-renew)))
            thermal_charge=min(self.config.thermal_charge_limit_kw, max(0,renew+sum(gens)-demand-charge-extra_charge)) if prep else 0
            thermal_discharge=min(state.loads.heating_kw*.4, self.config.thermal_discharge_limit_kw) if storm and i>=10 else 0
            action=DispatchActionV2(gens,charge+extra_charge,discharge,thermal_charge,thermal_discharge,flexible,deferrable)
            action.explanation=self._explain(storm, prep, flexible, reserve_target, future_renew, future_load)
            plan.append(action)
            soc=min(self.config.battery_max_soc,max(self.config.battery_min_soc,soc+(action.battery_charge_kw*.94-action.battery_discharge_kw/.94)/1000))
        return plan
    @staticmethod
    def _explain(storm, prep, flexible, target, renew, load):
        if prep: return f"Storm preparation: forecast renewable supply ({renew:.0f} kW) is below future demand ({load:.0f} kW); charge battery toward {target:.0%}, store heat, and defer flexible work."
        if not flexible: return "Fuel/risk conservation: flexible and deferrable loads are deferred to preserve critical-load autonomy."
        return "MPC dispatch balances renewable use, battery wear, generator efficiency, and critical-load reliability."
