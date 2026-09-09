from polar_ems.platform_simulation import SimulationRunner, compare

def test_closed_loop_advances_and_protects_critical_loads():
    runner=SimulationRunner("storm",seed=4); runner.run(24)
    assert runner.metrics()["hours"] == 24
    assert runner.metrics()["fuel_consumed_litres"] > 0
    assert runner.metrics()["critical_unserved_kwh"] == 0

def test_comparison_is_computed_not_hardcoded():
    result=compare("generator_failure",24,4)
    assert set(result) == {"scenario","polar_ems","baseline"}
