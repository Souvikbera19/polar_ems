from polar_ems.forecasting_engine import StationForecaster
from polar_ems.mpc_engine import MPCOptimizer
from polar_ems.platform_simulation import initial_state

def test_storm_plan_prepares_and_is_physically_bounded():
    state=initial_state(); forecast=StationForecaster().predict(state,24,"storm")
    plan=MPCOptimizer().plan(state,forecast)
    assert len(plan)==24
    assert all(sum(a.generator_kw)<=600 for a in plan)
    assert any(not a.serve_flexible for a in plan[:12])
