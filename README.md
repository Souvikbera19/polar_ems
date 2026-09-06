# POLAR-EMS V1

POLAR-EMS V1 is a simulator-first energy-management prototype for an isolated
polar research station. It intentionally uses only the Python standard library
so the first demo is easy to run and inspect.

## What it demonstrates

- Synthetic polar weather, PV, wind, heating and electrical-load telemetry.
- A 24-hour / 15-minute look-ahead forecast.
- A lightweight constrained dispatch planner that protects battery SOC and fuel.
- A deterministic safety gate and an emergency fallback policy.
- A closed feedback loop: telemetry -> forecast -> plan -> safety -> command ->
  simulator -> telemetry.

The planner is intentionally a small, inspectable V1. `optimization/planner.py`
defines a clean interface that can later be replaced with a Pyomo MILP/MPC model.

## Create and use the virtual environment

From this directory:

```bash
bash scripts/create_venv.sh
source .venv/bin/activate
python main.py --steps 96
python -m unittest discover -s tests -v
```

No third-party packages are required for V1. The virtual environment remains
useful because later forecasting and Pyomo dependencies can be installed without
affecting the system Python.

## Read the output

Each cycle prints the actual station load/renewables, the approved action,
battery SOC, fuel and safety result. At the end it prints core V1 KPIs:

- critical-load energy not served (target: zero in normal scenarios),
- fuel consumed,
- renewable curtailment,
- safety fallback count,
- ending battery SOC and fuel.

## Important V1 assumptions

- 15-minute control interval and 24-hour prediction horizon.
- One equivalent diesel generator, not generator synchronisation dynamics.
- Battery uses an energy/SOC model, not electrochemistry.
- Heating is an electrical demand derived from outdoor temperature.
- The simulator is the only command target. This code must not be connected to
  physical equipment without a proper hardware gateway, testing, and review.
