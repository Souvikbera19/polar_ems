from polar_ems.digital_twin_v2 import StationTwinV2
from polar_ems.domain import DispatchActionV2
from polar_ems.platform_simulation import initial_state

def test_generator_minimum_and_fuel_use():
    twin=StationTwinV2(initial_state()); before=twin.state.fuel_litres
    twin.apply_action(DispatchActionV2([10,0,0]))
    assert twin.state.generators[0].output_kw == 50
    assert twin.state.fuel_litres < before
