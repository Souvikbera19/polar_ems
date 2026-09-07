"""Small SQLite repository; SQLite can be replaced by a repository implementation later."""
from __future__ import annotations
import json, sqlite3
from pathlib import Path

class SQLiteRepository:
    def __init__(self,path="data/polar_ems.sqlite3"):
        Path(path).parent.mkdir(parents=True,exist_ok=True); self.conn=sqlite3.connect(path)
        self.conn.execute("CREATE TABLE IF NOT EXISTS simulation_runs (id INTEGER PRIMARY KEY, scenario TEXT, controller TEXT, metrics_json TEXT)")
        self.conn.execute("CREATE TABLE IF NOT EXISTS station_states (id INTEGER PRIMARY KEY, run_id INTEGER, state_json TEXT)")
        self.conn.execute("CREATE TABLE IF NOT EXISTS forecasts (id INTEGER PRIMARY KEY, run_id INTEGER, forecast_json TEXT)")
        self.conn.execute("CREATE TABLE IF NOT EXISTS optimization_plans (id INTEGER PRIMARY KEY, run_id INTEGER, plan_json TEXT)")
        self.conn.execute("CREATE TABLE IF NOT EXISTS risk_records (id INTEGER PRIMARY KEY, run_id INTEGER, risk_json TEXT)")
        self.conn.execute("CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY, run_id INTEGER, event_json TEXT)")
        self.conn.commit()
    def save_run(self,scenario,controller,metrics):
        cur=self.conn.execute("INSERT INTO simulation_runs(scenario,controller,metrics_json) VALUES(?,?,?)",(scenario,controller,json.dumps(metrics))); self.conn.commit(); return cur.lastrowid
