import unittest

from polar_ems.config import StationConfig
from polar_ems.digital_twin import StationTwin
from polar_ems.main import make_orchestrator
from polar_ems.models import DispatchAction


class PolarEmsV1Tests(unittest.TestCase):
    def test_twin_never_discharges_below_minimum_energy(self):
        config = StationConfig()
        twin = StationTwin(config)
        station = make_orchestrator().gateway.station
        telemetry = station.telemetry()
        forecast = make_orchestrator().forecaster.forecast(telemetry).steps[0]
        action = DispatchAction(0.0, 10_000.0, False, "test")

        result = twin.transition_from_telemetry(telemetry, forecast, action)

        self.assertGreaterEqual(result.battery_energy_kwh, config.battery_min_kwh)

    def test_closed_loop_runs_and_records_all_cycles(self):
        orchestrator = make_orchestrator(seed=11)
        for _ in range(8):
            orchestrator.run_cycle()

        summary = orchestrator.monitor.summary()
        self.assertEqual(summary["cycles"], 8)
        self.assertGreater(summary["ending_fuel_litres"], 0)
        self.assertGreaterEqual(summary["ending_soc_pct"], 30.0)
        self.assertAlmostEqual(summary["critical_unserved_kwh"], 0.0)


if __name__ == "__main__":
    unittest.main()
