from __future__ import annotations

from .data_pipeline import TelemetryProcessor
from .forecasting import SimpleForecaster
from .models import CycleRecord
from .monitoring import Monitor
from .optimization import SimpleMPCPlanner
from .safety import SafetyValidator
from .simulation import SimulatedStation


class SimGateway:
    def __init__(self, station: SimulatedStation) -> None:
        self.station = station

    def read_telemetry(self):
        return self.station.telemetry()

    def execute(self, action, telemetry):
        return self.station.apply(action, telemetry)


class Orchestrator:
    def __init__(
        self,
        gateway,
        processor: TelemetryProcessor,
        forecaster: SimpleForecaster,
        planner: SimpleMPCPlanner,
        safety: SafetyValidator,
        monitor: Monitor,
    ) -> None:
        self.gateway = gateway
        self.processor = processor
        self.forecaster = forecaster
        self.planner = planner
        self.safety = safety
        self.monitor = monitor

    def run_cycle(self) -> CycleRecord:
        telemetry = self.processor.process(self.gateway.read_telemetry())
        forecast = self.forecaster.forecast(telemetry)
        plan = self.planner.plan(telemetry, forecast)
        validation = self.safety.validate(telemetry, forecast, plan)
        execution = self.gateway.execute(validation.action, telemetry)
        record = CycleRecord(
            timestamp=telemetry.timestamp,
            telemetry=telemetry,
            action=validation.action,
            validation=validation,
            execution=execution,
        )
        self.monitor.record(record)
        return record
