from __future__ import annotations

from .config import StationConfig
from .models import DispatchAction, ForecastStep, TelemetryFrame, Transition


class StationTwin:
    """Simplified station physics used by the planner and safety validator."""

    def __init__(self, config: StationConfig) -> None:
        self.config = config

    def step(
        self,
        battery_energy_kwh: float,
        fuel_litres: float,
        forecast: ForecastStep,
        action: DispatchAction,
    ) -> Transition:
        dt = self.config.dt_hours
        generator_kw = max(0.0, action.generator_kw)
        flexible_kw = forecast.flexible_requested_kw if action.flexible_enabled else 0.0
        renewable_kw = forecast.renewable_available_kw
        demand_kw = forecast.essential_kw + flexible_kw

        proposed_charge_kw = max(0.0, -action.battery_kw)
        proposed_discharge_kw = max(0.0, action.battery_kw)
        energy_after = battery_energy_kwh

        if proposed_charge_kw:
            room_kwh = max(0.0, self.config.battery_max_kwh - energy_after)
            accepted_charge_kw = min(
                proposed_charge_kw,
                self.config.battery_charge_limit_kw,
                room_kwh / (self.config.charge_efficiency * dt) if dt else 0.0,
            )
            energy_after += accepted_charge_kw * self.config.charge_efficiency * dt
        else:
            available_kwh = max(0.0, energy_after - self.config.battery_min_kwh)
            accepted_discharge_kw = min(
                proposed_discharge_kw,
                self.config.battery_discharge_limit_kw,
                available_kwh * self.config.discharge_efficiency / dt if dt else 0.0,
            )
            energy_after -= accepted_discharge_kw * dt / self.config.discharge_efficiency

        supply_kw = renewable_kw + generator_kw + (accepted_discharge_kw if proposed_discharge_kw else 0.0)
        demand_with_charge_kw = demand_kw + (accepted_charge_kw if proposed_charge_kw else 0.0)
        # Flexible work and discretionary charging may be deferred. Critical and
        # heating demand are the non-negotiable safety condition.
        critical_unserved_kw = max(0.0, forecast.essential_kw - supply_kw)
        curtailment_kw = max(0.0, supply_kw - demand_with_charge_kw)

        fuel_burn = 0.0
        if generator_kw > 0:
            fuel_burn = dt * (
                self.config.generator_idle_lph
                + self.config.generator_marginal_l_per_kwh * generator_kw
            )

        return Transition(
            battery_energy_kwh=energy_after,
            fuel_litres=max(0.0, fuel_litres - fuel_burn),
            critical_unserved_kw=critical_unserved_kw,
            renewable_curtailment_kw=curtailment_kw,
        )

    def transition_from_telemetry(
        self, telemetry: TelemetryFrame, forecast: ForecastStep, action: DispatchAction
    ) -> Transition:
        return self.step(telemetry.battery_energy_kwh, telemetry.fuel_litres, forecast, action)
