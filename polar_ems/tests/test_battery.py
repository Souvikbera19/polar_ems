from polar_ems.digital_twin_v2 import StationTwinV2
from polar_ems.domain import DispatchActionV2
from polar_ems.platform_simulation import initial_state

def test_battery_charge_and_boundaries():
    twin=StationTwinV2(initial_state()); twin.state.wind_kw=500; twin.state.solar_kw=0
    twin.apply_action(DispatchActionV2([0,0,0],battery_charge_kw=250,serve_flexible=False,serve_deferrable=False))
    assert .15 <= twin.state.battery_soc <= .95

def test_battery_never_charges_and_discharges_together():
    twin=StationTwinV2(initial_state())
    twin.apply_action(DispatchActionV2([0,0,0],battery_charge_kw=100,battery_discharge_kw=100))
    assert twin.state.battery_kwh >= 600
