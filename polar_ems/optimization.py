from __future__ import annotations

from dataclasses import replace

from .config import StationConfig
from .digital_twin import StationTwin
from .models import DispatchAction, DispatchPlan, ForecastBundle, ForecastStep, TelemetryFrame


class SimpleMPCPlanner:
    """Small candidate-search planner with a 24-hour fuel/autonomy look-ahead.

    It is deliberately simple and dependency-free. It preserves the same input and
    output interface a future Pyomo MPC implementation will use.
    """

    def __init__(self, config: StationConfig, twin: StationTwin) -> None:
        self.config = config
        self.twin = twin

    def dynamic_fuel_reserve(self, forecast: ForecastBundle) -> float:
        stress_steps = min(
            len(forecast.steps),
            int(self.config.fuel_stress_hours / self.config.dt_hours),
        )
        stress_kw = sum(
            max(0.0, step.essential_kw - 0.35 * step.renewable_available_kw)
            for step in forecast.steps[:stress_steps]
        ) / max(stress_steps, 1)
        stress_litres = stress_kw * self.config.fuel_stress_hours * self.config.generator_marginal_l_per_kwh
        # Keep the V1 reserve bounded; an impossible reserve should create an alert,
        # not make every schedule meaningless.
        return min(
            self.config.fuel_capacity_litres,
            self.config.fuel_emergency_reserve_litres + 0.35 * stress_litres,
        )

    def plan(self, telemetry: TelemetryFrame, forecast: ForecastBundle) -> DispatchPlan:
        reserve = self.dynamic_fuel_reserve(forecast)
        energy = telemetry.battery_energy_kwh
        fuel = telemetry.fuel_litres
        actions: list[DispatchAction] = []

        for index, step in enumerate(forecast.steps):
            target_soc = self._target_soc(index, forecast, reserve, fuel)
            action = self._choose_action(energy, fuel, step, target_soc, reserve)
            transition = self.twin.step(energy, fuel, step, action)
            energy, fuel = transition.battery_energy_kwh, transition.fuel_litres
            actions.append(action)

        note = (
            "Fuel-autonomy reserve protected" if telemetry.fuel_litres >= reserve
            else "Fuel below dynamic reserve: flexible demand is deprioritized"
        )
        return DispatchPlan(
            created_at=telemetry.timestamp,
            steps=actions,
            dynamic_fuel_reserve_litres=reserve,
            planner_note=note,
        )

    def _target_soc(
        self, index: int, forecast: ForecastBundle, reserve: float, fuel: float
    ) -> float:
        lookahead = forecast.steps[index : min(index + 24, len(forecast.steps))]
        mean_renewable = sum(s.renewable_available_kw for s in lookahead) / max(len(lookahead), 1)
        mean_essential = sum(s.essential_kw for s in lookahead) / max(len(lookahead), 1)
        risk_boost = 0.15 if mean_renewable < 0.35 * mean_essential else 0.0
        autonomy_boost = 0.10 if fuel < reserve else 0.0
        return min(self.config.battery_soc_max - 0.05, 0.55 + risk_boost + autonomy_boost)

    def _choose_action(
        self,
        battery_energy_kwh: float,
        fuel_litres: float,
        step: ForecastStep,
        target_soc: float,
        reserve: float,
    ) -> DispatchAction:
        candidates: list[DispatchAction] = []
        generator_levels = [0.0, self.config.generator_min_kw, 65.0, 95.0, 120.0, self.config.generator_max_kw]

        for flexible_enabled in (False, True):
            flexible_kw = step.flexible_requested_kw if flexible_enabled else 0.0
            net_demand_kw = step.essential_kw + flexible_kw - step.renewable_available_kw
            for generator_kw in generator_levels:
                if generator_kw > 0 and generator_kw < self.config.generator_min_kw:
                    continue
                battery_kw = net_demand_kw - generator_kw
                battery_kw = max(
                    -self.config.battery_charge_limit_kw,
                    min(self.config.battery_discharge_limit_kw, battery_kw),
                )
                candidates.append(
                    DispatchAction(
                        generator_kw=generator_kw,
                        battery_kw=battery_kw,
                        flexible_enabled=flexible_enabled,
                        reason="candidate",
                    )
                )

        def score(action: DispatchAction) -> float:
            transition = self.twin.step(battery_energy_kwh, fuel_litres, step, action)
            soc = transition.battery_energy_kwh / self.config.battery_capacity_kwh
            fuel_burn = fuel_litres - transition.fuel_litres
            critical_penalty = 1_000_000 * transition.critical_unserved_kw
            reserve_penalty = 2_000 * max(0.0, reserve - transition.fuel_litres)
            soc_penalty = 3_000 * max(0.0, target_soc - soc)
            battery_penalty = 0.08 * abs(action.battery_kw)
            flexible_reward = 0.4 * step.flexible_requested_kw if action.flexible_enabled else 0.0
            return critical_penalty + reserve_penalty + soc_penalty + 10 * fuel_burn + battery_penalty - flexible_reward

        best = min(candidates, key=score)
        mode = "protecting SOC/fuel reserve" if not best.flexible_enabled else "serving flexible demand"
        return replace(best, reason=mode)
