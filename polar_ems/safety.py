from __future__ import annotations

from .config import StationConfig
from .digital_twin import StationTwin
from .models import DispatchAction, DispatchPlan, ForecastBundle, ForecastStep, TelemetryFrame, ValidationResult


class SafetyValidator:
    """Hard deterministic guardrail; it never trusts optimizer output blindly."""

    def __init__(self, config: StationConfig, twin: StationTwin) -> None:
        self.config = config
        self.twin = twin

    def validate(
        self,
        telemetry: TelemetryFrame,
        forecast: ForecastBundle,
        plan: DispatchPlan,
    ) -> ValidationResult:
        action = plan.first_action
        reasons: list[str] = []
        current_conditions = ForecastStep(
            timestamp=telemetry.timestamp,
            critical_kw=telemetry.critical_kw,
            heating_kw=telemetry.heating_kw,
            flexible_requested_kw=telemetry.flexible_requested_kw,
            pv_available_kw=telemetry.pv_available_kw,
            wind_available_kw=telemetry.wind_available_kw,
            ambient_c=telemetry.weather.ambient_c,
        )
        projected = self.twin.transition_from_telemetry(telemetry, current_conditions, action)

        if telemetry.quality != "good":
            reasons.append("telemetry quality is not good")
        if not telemetry.generator_available and action.generator_kw > 0:
            reasons.append("generator unavailable")
        if not telemetry.battery_available and abs(action.battery_kw) > 0:
            reasons.append("battery unavailable")
        if action.generator_kw and not (
            self.config.generator_min_kw <= action.generator_kw <= self.config.generator_max_kw
        ):
            reasons.append("generator power outside operating range")
        if action.battery_kw > self.config.battery_discharge_limit_kw:
            reasons.append("battery discharge limit exceeded")
        if -action.battery_kw > self.config.battery_charge_limit_kw:
            reasons.append("battery charge limit exceeded")
        if not (self.config.battery_min_kwh <= projected.battery_energy_kwh <= self.config.battery_max_kwh):
            reasons.append("battery SOC boundary violated")
        if projected.fuel_litres < self.config.fuel_emergency_reserve_litres:
            reasons.append("emergency fuel reserve violated")
        if projected.critical_unserved_kw > 1e-6:
            reasons.append("critical load would not be fully served")

        if not reasons:
            return ValidationResult(approved=True, action=action)

        fallback = self._fallback(telemetry, current_conditions)
        return ValidationResult(
            approved=False,
            action=fallback,
            reasons=reasons,
            used_fallback=True,
        )

    def _fallback(self, telemetry: TelemetryFrame, step) -> DispatchAction:
        """Known safe priority: critical/heating, then generator, then battery."""
        required_kw = max(0.0, step.essential_kw - step.renewable_available_kw)
        available_battery_kw = min(
            self.config.battery_discharge_limit_kw,
            max(0.0, telemetry.battery_energy_kwh - self.config.battery_min_kwh)
            * self.config.discharge_efficiency
            / self.config.dt_hours,
        )
        generator_kw = max(0.0, required_kw - available_battery_kw)
        if 0 < generator_kw < self.config.generator_min_kw:
            generator_kw = self.config.generator_min_kw
        generator_kw = min(generator_kw, self.config.generator_max_kw)
        battery_kw = max(0.0, required_kw - generator_kw)
        return DispatchAction(
            generator_kw=generator_kw,
            battery_kw=battery_kw,
            flexible_enabled=False,
            reason="deterministic safety fallback",
        )
