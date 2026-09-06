# POLAR-EMS: Hardware & Software Requirements Specification

This document details both the **software requirements** (for development, simulation, and production deployment) and the **hardware requirements** (both the physical microgrid equipment parameters modeled by the system and the physical industrial compute/sensor specifications required for on-station deployment).

---

## 1. Software Requirements

### 1.1 V1 Core Runtime (Simulator & Controller)

The current version (V1) is deliberately designed to be lightweight, auditable, and self-contained with **zero third-party package dependencies**.

| Component | Minimum Specification | Recommended Specification |
| :--- | :--- | :--- |
| **Operating System** | Linux (Ubuntu 20.04+, Debian 11+, RHEL 8+), macOS (12+), or Windows 10/11 (via WSL2 or native PowerShell) | Enterprise Linux (Rocky Linux 9, Debian 12, or Alpine Linux for containers) |
| **Python Version** | Python 3.10+ | Python 3.11, 3.12, or 3.13 |
| **Standard Library Modules Used** | `dataclasses`, `datetime`, `math`, `random`, `typing`, `argparse`, `unittest` | Pure standard library |
| **Third-Party Dependencies** | **None** (0 external pip dependencies required for V1) | None for V1 |
| **Shell Environment** | POSIX-compliant shell (`bash` 4.0+) for virtual environment setup scripts | `bash` or `zsh` |

### 1.2 Development & Simulation Resource Footprint

Running the simulation loop and executing test suites requires minimal compute:

- **CPU:** 1 physical core, 1.0 GHz or higher (x86-64 or ARM64).
- **RAM:** Minimum 128 MB free memory (512 MB recommended).
- **Disk Storage:** < 50 MB total disk space (including `.venv` and git repository).
- **Execution Time:** ~0.02 seconds for unit test suite; < 1 second for a full 96-step (24-hour) simulation run.

### 1.3 Future Upgrade Path (V2+ Production Stack)

When upgrading from the rule-based / heuristic MPC planner to full Mixed-Integer Linear Programming (MILP), machine learning forecasting, and real-time SCADA integration, the following software components will be introduced:

```
+-------------------------------------------------------------------+
|                        POLAR-EMS Software Stack                   |
+-------------------------------------------------------------------+
| API & Web UI       | FastAPI, Uvicorn, Pydantic                    |
| Optimization       | Pyomo, HiGHS solver (highspy) / CBC / GLPK    |
| Analytics & ML     | NumPy, Pandas, Scikit-Learn, XGBoost          |
| Protocols & SCADA  | PyModbus (Modbus TCP/RTU), asyncua (OPC-UA)   |
| Telemetry Database | TimescaleDB / InfluxDB / SQLite               |
| Core Engine        | Python 3.10+ (polar_ems engine & safety gate) |
+-------------------------------------------------------------------+
```

- **Mathematical Solvers:**
  - `pyomo` (v6.6+): High-level algebraic modeling system.
  - `highspy` / `HiGHS`: Fast open-source LP/MIP solver for real-time MPC dispatch.
- **Forecasting & Analytics:**
  - `pandas` (v2.0+) & `numpy` (v1.24+): Timeseries manipulation and rolling aggregations.
  - `scikit-learn` & `xgboost`: Extreme weather forecasting and renewable yield prediction.
- **Communications & Gateway:**
  - `fastapi` & `uvicorn`: RESTful API and WebSocket streaming for station operators.
  - `pymodbus` (v3.5+): Communication with industrial inverters, genset controllers, and power meters.
  - `asyncua`: Integration with station-wide industrial OPC-UA servers.
- **Persistence & Logging:**
  - TimescaleDB, InfluxDB, or local SQLite for persistent time-series telemetry storage (~15–50 MB per operational year at 15-minute resolution).

### 1.4 Architectural & Safety Software Constraints

- **Control Loop Cadence:** Fixed 15-minute dispatch cycle (`interval_minutes: 15`).
- **Look-Ahead Horizon:** 24-hour prediction horizon consisting of 96 discrete steps (`horizon_steps: 96`).
- **Telemetry Validation:** Automated quality scoring (`good`, `degraded`, `bad`) validating finite values and non-negative parameters via `TelemetryProcessor`.
- **Deterministic Safety Gate:** `SafetyValidator` intercepts every dispatch action before execution. It enforces physical asset limits, SOC boundaries, and fuel reserve buffers, falling back to a deterministic safe priority mode if any violation occurs.

---

## 2. Hardware Requirements

Hardware requirements are split into two categories:
1. **Station Microgrid Assets:** Equipment ratings and operational envelopes modeled by POLAR-EMS.
2. **Industrial Control & Edge Hardware:** The physical computing, networking, and sensor infrastructure needed to deploy POLAR-EMS in an isolated polar station.

---

### 2.1 Station Microgrid Equipment Parameters (Modeled Assets)

As configured in `StationConfig` (`polar_ems/config.py`), the station energy system comprises the following plant assets:

```
                    +------------------------------------+
                    |        Polar Microgrid Bus         |
                    +--+-----------+-----------+-------+-+
                       |           |           |       |
            +----------+--+   +----+----+   +--+--+  +-+--------+
            |  Solar PV   |   |  Wind   |   | BESS|  |  Diesel  |
            |   120 kW    |   | 180 kW  |   | 500 |  |  Genset  |
            |             |   |         |   | kWh |  | 40-150 kW|
            +-------------+   +---------+   +-----+  +----+-----+
                                                          |
                                                     +----+----+
                                                     |  4,000 L|
                                                     |Fuel Tank|
                                                     +---------+
```

#### 2.1.1 Diesel Generator System
- **Nameplate Maximum Output:** 150.0 kW
- **Minimum Operational Loading:** 40.0 kW (26.7% minimum load to prevent wet stacking, cylinder glazing, and thermal degradation under sub-zero intake conditions).
- **Fuel Consumption Characteristics:**
  - Idle Fuel Consumption: `3.0 L/h`
  - Marginal Fuel Consumption: `0.245 L/kWh` (~235 g/kWh diesel fuel density equivalent)
- **Controller Interface:** Electronic Governor / Genset Controller (e.g. Deep Sea Electronics, ComAp, or Woodward) capable of remote start/stop, setpoint modulation, and J1939 CAN / Modbus communication.

#### 2.1.2 Battery Energy Storage System (BESS)
- **Nominal Energy Capacity:** 500.0 kWh
- **Usable Operational Range:** 30% to 90% SOC (State of Charge)
  - Minimum Energy Threshold: `150.0 kWh` (30% floor reserved for emergency reserve and cycle life protection).
  - Maximum Energy Threshold: `450.0 kWh` (90% ceiling to avoid overcharge degradation).
- **Power Rating / C-Rate Limits:**
  - Maximum Continuous Charge Rate: `100.0 kW` (~0.2C)
  - Maximum Continuous Discharge Rate: `120.0 kW` (~0.24C)
- **Efficiency:**
  - One-Way Charge Efficiency: 94.0%
  - One-Way Discharge Efficiency: 94.0%
  - Round-Trip Efficiency (RTE): ~88.36%
- **Thermal Conditioning:** Integrated battery enclosure heating/insulation maintaining internal cell temperatures between +10°C and +25°C despite external polar ambient temperatures down to -50°C.

#### 2.1.3 Renewable Generation Assets
- **Solar Photovoltaic (PV) Array:**
  - Installed Capacity: 120.0 kWp
  - De-rating Factor: 0.82 (accounting for low solar angles, snow reflection albedo, inverter losses, and cable losses)
  - Mounting: High-tilt / bifacial ground mount designed to withstand Antarctic katabatic wind gusts up to 55 m/s.
- **Wind Turbines:**
  - Aggregate Installed Capacity: 180.0 kW
  - Cut-In Wind Speed: `3.0 m/s`
  - Rated Wind Speed: `12.0 m/s` (producing full 180 kW)
  - Cut-Out Wind Speed: `25.0 m/s` (automatic aerodynamic furling / mechanical braking to prevent structural failure)
  - Blade De-icing: Active electro-thermal de-icing heating elements.

#### 2.1.4 Fuel Storage Infrastructure
- **Total Tank Capacity:** 4,000.0 litres of Arctic-grade diesel (e.g., Class A2 Arctic Gas Oil or Jet A-1 kerosene blend with cold-flow pour point depressant rated down to -50°C).
- **Hard Emergency Reserve:** 800.0 litres (unconditional reserve dedicated strictly to station life-support preservation).
- **Autonomy Stress Requirement:** Dynamic fuel buffer ensuring minimum 48 hours of baseline station autonomy under zero renewable generation.

#### 2.1.5 Station Loads & Heating Architecture
- **Critical / Essential Electrical Load:** 60 kW to 75 kW diurnal cycle (average ~70 kW base). Supplies non-sheddable station life support, atmospheric life systems, communications, scientific experiments, and lighting.
- **Heating Load:**
  - Indoor Comfort Setpoint: `18.0°C`
  - Building Heat Loss Coefficient: `1.25 kW/°C`
  - Heat Pump / Electric Heating Coefficient of Performance (COP): `1.8`
  - Baseline Electrical Heating Demand: Minimum `8.0 kW` floor; scales dynamically with ambient polar temperature.
- **Flexible / Deferrable Load:** 5.0 kW (unoccupied/night) to 18.0 kW (daytime). Includes rover charging, wastewater processing, auxiliary snow-melters, and non-time-critical lab refrigeration.

---

### 2.2 Physical Edge Controller & Station Deployment Requirements

For physical installation at an isolated station or test facility, the computer running the POLAR-EMS supervisor must satisfy the following hardware specifications:

| Category | Specification | Justification |
| :--- | :--- | :--- |
| **Form Factor** | Ruggedized DIN-rail or 19-inch rack-mount Industrial PC (IPC) | Vibration and shock resistance in polar transport and utility plant rooms |
| **Cooling** | Fanless passive cooling design | Eliminates fan failure points and dust/snow ingress |
| **Processor** | Quad-Core x86-64 (e.g., Intel Atom x6425RE, Core i3-1115GRE) or Quad-Core ARM64 (Cortex-A72 / NXP i.MX8) | Provides sufficient compute for V1 rules and V2 MILP solver executions |
| **Memory (RAM)** | 4 GB to 8 GB ECC DDR4 | ECC prevents bit-flip errors in cosmic ray / polar high-latitude environments |
| **Storage** | 32 GB to 64 GB Industrial SLC or pSLC eMMC / NVMe SSD | High endurance (TBW), wide temperature rating |
| **Operating Temperature** | -40°C to +70°C ambient | Operational in cold electrical outbuildings or unconditioned equipment shelters |
| **Power Supply** | Redundant dual 18–36V DC inputs (24V DC nominal) | Powered from station DC bus; immune to single-supply AC failure |
| **UPS Backup** | Dedicated 24V DC DIN-rail buffer / supercapacitor unit | Guaranteed clean shutdown / minimum 30-minute runtime during station blackouts |
| **Watchdog Timer** | Hardware watchdog relay (independent MCU/FPGA) | Automatic hard reset if the OS or control daemon freezes |

### 2.3 Communications & Field Instrumentation Interfaces

| Interface | Standard / Specification | Connected Equipment |
| :--- | :--- | :--- |
| **Ethernet Port 1** | 10/100/1000 Mbps RJ45 (Galvanic isolation 1.5 kV) | Isolated Microgrid Equipment Network (Inverters, BMS, Genset) |
| **Ethernet Port 2** | 10/100/1000 Mbps RJ45 (Galvanic isolation 1.5 kV) | Station SCADA / Satellite telemetry backhaul |
| **Serial Bus 1** | RS-485 (2-wire, isolated, Modbus RTU protocol) | Diesel Generator ECU / Deep Sea controller |
| **Serial Bus 2** | RS-485 (2-wire, isolated, Modbus RTU protocol) | Weather Station & Irradiance Pyranometers |
| **CAN Interface** | 2x CANbus 2.0B / CANopen (ISO 11898-2) | Battery Management System (BMS) & bidirectional inverters |
| **Digital Inputs** | 8x Opto-isolated dry contact inputs (24V DC) | Auto-Transfer Switch (ATS) status, Fire alarm, E-Stop trip status |
| **Digital Outputs** | 4x Form C Relay contacts (250V AC / 5A) | Hardwired fallback triggers, generator remote start, load-shedding contactor |

### 2.4 Field Sensor & Measurement Accuracy

- **Solar Irradiance:** Heated thermopile pyranometer (ISO 9060 Class A / Secondary Standard) with dome heater preventing riming and snow accumulation.
- **Wind Speed & Direction:** Ultrasonic anemometer with internal heating elements (no moving mechanical cups prone to freezing). Range: 0 to 65 m/s, accuracy: ±2%.
- **Ambient Temperature:** 4-wire PT100 Class A Platinum RTD probe with solar radiation shield. Range: -70°C to +40°C.
- **Fuel Level Transmitter:** Hydrostatic pressure transmitter or continuous guided-wave radar (ATEX/IECEx certified for diesel tanks).
- **Microgrid Power Meters:** Bidirectional Class 0.2S three-phase power quality meters monitoring generator output, BESS inverter, solar array, and station distribution feeders.

---

## 3. Summary Compliance Matrix

| Requirement Domain | V1 Simulator Prototype | V2+ Physical Station Target |
| :--- | :--- | :--- |
| **Programming Language** | Python 3.10+ | Python 3.11+ / Rust (for critical microgrid gateway) |
| **External Dependencies** | None (0 packages) | Pyomo, HiGHS, Pandas, Scikit-Learn, PyModbus |
| **Compute Hardware** | Any standard laptop / PC / cloud VM | Industrial Fanless PC (ECC RAM, -40°C to +70°C) |
| **Physical I/O** | Software Mock Gateway (`SimGateway`) | Modbus TCP/RTU, CANbus, Optocoupled digital I/O |
| **Discretionary Demand Control**| Software flag (`flexible_enabled`) | Contactor relays controlling non-critical distribution panels |
| **Fail-Safe Mechanism** | `SafetyValidator` deterministic override | Hardware watchdog + electrical interlock relay to generator |
