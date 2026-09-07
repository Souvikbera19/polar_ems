from polar_ems.domain import DispatchActionV2
from polar_ems.platform_simulation import initial_state
from polar_ems.safety_v2 import DeterministicSafetyValidator

def test_safety_rejects_failed_generator_and_battery_conflict():
    state=initial_state(); state.generators[1].available=False
    action,reasons=DeterministicSafetyValidator().validate(state,DispatchActionV2([0,100,0],10,10))
    assert action.generator_kw[1] == 0
    assert not (action.battery_charge_kw and action.battery_discharge_kw)
    assert reasons
