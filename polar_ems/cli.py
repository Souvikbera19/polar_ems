from __future__ import annotations
import argparse, json
from .platform_simulation import SCENARIOS, SimulationRunner, compare
from .forecasting_engine import StationForecaster
from .risk_engine import fuel_autonomy

def main():
    p=argparse.ArgumentParser(description="POLAR-EMS predictive polar-station simulator")
    p.add_argument("--scenario",choices=sorted(SCENARIOS),default="normal"); p.add_argument("--hours",type=int,default=24); p.add_argument("--seed",type=int,default=7); p.add_argument("--baseline",action="store_true"); p.add_argument("--compare",action="store_true")
    a=p.parse_args()
    if a.compare: print(json.dumps(compare(a.scenario,a.hours,a.seed),indent=2)); return
    r=SimulationRunner(a.scenario,a.seed,not a.baseline); r.run(a.hours)
    fc=StationForecaster().predict(r.state,24,a.scenario)
    print(json.dumps({"controller":"baseline" if a.baseline else "POLAR-EMS","scenario":a.scenario,"metrics":r.metrics(),"fuel_autonomy":fuel_autonomy(r.state,fc,r.config),"recommendation":r.orchestrator.history[-1].action.explanation},indent=2))
if __name__=="__main__": main()
