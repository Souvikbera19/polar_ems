"""Run with: streamlit run polar_ems/dashboard/app.py (from repository parent)."""
import streamlit as st
import pandas as pd
import plotly.express as px
from polar_ems.platform_simulation import SimulationRunner, compare
from polar_ems.forecasting_engine import StationForecaster
from polar_ems.risk_engine import assess_risk, fuel_autonomy

st.set_page_config(page_title="POLAR ENERGY COMMAND",layout="wide")
st.title("POLAR ENERGY COMMAND")
scenario=st.sidebar.selectbox("Scenario",["normal","renewable_surplus","storm","extreme_cold","generator_failure","fuel_scarcity"])
hours=st.sidebar.slider("Simulation hours",6,168,48)
if st.sidebar.button("Run POLAR-EMS") or "runner" not in st.session_state:
    st.session_state.runner=SimulationRunner(scenario); st.session_state.runner.run(hours)
r=st.session_state.runner; state=r.state; forecast=StationForecaster().predict(state,24,r.scenario); risk=assess_risk(state,forecast,r.config); autonomy=fuel_autonomy(state,forecast,r.config)
a,b,c,d=st.columns(4); a.metric("PERI",f"{risk.score}/100",risk.band); b.metric("Fuel autonomy",f"{autonomy['operational_autonomy_days']} days"); c.metric("Battery SOC",f"{state.battery_soc:.0%}"); d.metric("Mode",state.mode)
st.subheader("Current energy state")
st.write({"wind_kw":round(state.wind_kw,1),"solar_kw":round(state.solar_kw,1),"generators_kw":round(sum(g.output_kw for g in state.generators),1),"loads_kw":round(state.loads.total_kw,1),"thermal_storage_kwh":round(state.thermal_kwh,1)})
st.subheader("Optimizer recommendation")
st.info(r.orchestrator.history[-1].action.explanation if r.orchestrator.history else "Run a simulation.")
st.write({"risk_contributors":risk.contributors,"fuel_autonomy":autonomy})
df=pd.DataFrame([x.__dict__ for x in forecast]); st.plotly_chart(px.line(df,x="timestamp",y=["load_kw","heating_kw","wind_kw","solar_kw"],title="24-hour forecast"),use_container_width=True)
history=pd.DataFrame([{"time":x.state.timestamp,"soc":x.state.battery_soc*100,"fuel":x.state.fuel_litres,"risk":x.risk.score} for x in r.orchestrator.history])
if not history.empty: st.plotly_chart(px.line(history,x="time",y=["soc","risk"],title="Battery SOC and risk"),use_container_width=True)
st.subheader("Baseline vs POLAR-EMS")
st.dataframe(pd.DataFrame(compare(scenario,hours).items(),columns=["controller","metrics"]))
