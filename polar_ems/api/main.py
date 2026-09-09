"""FastAPI application. Install requirements first: pip install -r requirements.txt."""
from __future__ import annotations
from dataclasses import asdict
try:
    from fastapi import FastAPI, HTTPException
    from pydantic import BaseModel
except ImportError as exc:
    raise RuntimeError("FastAPI is optional. Install dependencies with `pip install -r requirements.txt`.") from exc
from ..forecasting_engine import StationForecaster
from ..platform_simulation import SCENARIOS, SimulationRunner, compare, what_if
from ..risk_engine import assess_risk, fuel_autonomy

app=FastAPI(title="POLAR-EMS",version="0.1.0")
runner=SimulationRunner()
class RunRequest(BaseModel): scenario: str="normal"; hours: int=24; seed: int=7
class WhatIfRequest(BaseModel): scenario: str="storm"; hours: int=48; seed: int=7
def payload_state(): return runner.state.json()
@app.get("/health")
def health(): return {"status":"ok","service":"POLAR-EMS"}
@app.get("/station/state")
def station_state(): return payload_state()
@app.get("/station/history")
def station_history(): return [{"state":x.state.json(),"action":asdict(x.action),"risk":asdict(x.risk)} for x in runner.orchestrator.history]
@app.get("/forecast")
def forecast(): return [asdict(x) for x in StationForecaster().predict(runner.state,24,runner.scenario)]
@app.post("/simulation/start")
def start(request:RunRequest):
    global runner
    if request.scenario not in SCENARIOS: raise HTTPException(400,"unknown scenario")
    runner=SimulationRunner(request.scenario,request.seed); runner.run(request.hours); return {"metrics":runner.metrics(),"state":payload_state()}
@app.post("/simulation/step")
def step():
    result=runner.orchestrator.step(); return {"state":payload_state(),"action":asdict(result.action),"risk":asdict(result.risk)}
@app.post("/simulation/reset")
def reset():
    global runner; runner=SimulationRunner(); return payload_state()
@app.get("/simulation/status")
def status(): return {"scenario":runner.scenario,"metrics":runner.metrics()}
@app.get("/optimization/current-plan")
def current_plan(): return [asdict(x) for x in runner.orchestrator.optimizer.plan(runner.state,StationForecaster().predict(runner.state,24,runner.scenario))]
@app.get("/risk")
def risk(): return asdict(assess_risk(runner.state,StationForecaster().predict(runner.state,24,runner.scenario),runner.config))
@app.get("/fuel-autonomy")
def autonomy(): return fuel_autonomy(runner.state,StationForecaster().predict(runner.state,24,runner.scenario),runner.config)
@app.post("/scenario/run")
def scenario(request:RunRequest): return start(request)
@app.post("/what-if/run")
def run_what_if(request:WhatIfRequest): return what_if(runner.state,request.scenario,request.hours,request.seed)
@app.get("/comparison/results")
def comparison(scenario:str="storm",hours:int=48,seed:int=7): return compare(scenario,hours,seed)
