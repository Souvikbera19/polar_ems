from __future__ import annotations

import argparse

from .config import StationConfig
from .controller import Orchestrator, SimGateway
from .data_pipeline import TelemetryProcessor
from .digital_twin import StationTwin
from .forecasting import SimpleForecaster
from .monitoring import Monitor
from .optimization import SimpleMPCPlanner
from .safety import SafetyValidator
from .simulation import SimulatedStation


def make_orchestrator(seed: int = 7) -> Orchestrator:
    config = StationConfig()
    station = SimulatedStation(config, seed=seed)
    twin = StationTwin(config)
    return Orchestrator(
        gateway=SimGateway(station),
        processor=TelemetryProcessor(),
        forecaster=SimpleForecaster(config),
        planner=SimpleMPCPlanner(config, twin),
        safety=SafetyValidator(config, twin),
        monitor=Monitor(config),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the POLAR-EMS V1 closed-loop simulator.")
    parser.add_argument("--steps", type=int, default=24, help="Number of 15-minute control cycles.")
    parser.add_argument("--seed", type=int, default=7, help="Deterministic simulator seed.")
    parser.add_argument("--quiet", action="store_true", help="Print only the final KPI summary.")
    args = parser.parse_args()

    orchestrator = make_orchestrator(seed=args.seed)
    if not args.quiet:
        print("POLAR-EMS V1 | 15-minute cycle | simulator-only")
        print("time     demand  renew  gen  battery   SOC   fuel  flex  safety")

    for _ in range(args.steps):
        record = orchestrator.run_cycle()
        telemetry = record.telemetry
        action = record.action
        total_demand = telemetry.critical_kw + telemetry.heating_kw + telemetry.flexible_requested_kw
        renewable = telemetry.pv_available_kw + telemetry.wind_available_kw
        soc = 100 * record.execution.telemetry_after.battery_energy_kwh / StationConfig().battery_capacity_kwh
        status = "FALLBACK" if record.validation.used_fallback else "approved"
        if not args.quiet:
            print(
                f"{record.timestamp:%H:%M}  {total_demand:6.1f} {renewable:6.1f}"
                f" {action.generator_kw:4.0f} {action.battery_kw:8.1f}"
                f" {soc:5.1f}% {record.execution.telemetry_after.fuel_litres:6.1f}"
                f"  {'on ' if action.flexible_enabled else 'off'}  {status}"
            )

    print("\nSummary")
    for key, value in orchestrator.monitor.summary().items():
        if isinstance(value, float):
            print(f"- {key}: {value:.2f}")
        else:
            print(f"- {key}: {value}")


if __name__ == "__main__":
    main()
