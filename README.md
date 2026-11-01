# EV Charging Network Data Processing and Analysis

## 1. Project Overview

This project processes and analyses an Electric Vehicle (EV) charging network dataset for Chennai.

It uses Python, NumPy and SQLite to clean station data, validate charging sessions, generate SQL reports, perform numerical analysis and conduct geographical station searches.

The project is designed with modular Python components, reusable functions, parameterised SQL queries and vectorised NumPy operations.

## 2. Technologies Used

- **Python 3.14** – Data processing and application logic.
- **NumPy** – Numerical computation and vectorised analysis.
- **SQLite** – Relational database storage and SQL reporting.
- **CSV** – Input datasets and generated reports.
- **GeoJSON** – Geographical station data.
- **Python Standard Library** – CSV, SQLite, JSON, datetime, pathlib, calendar and other built-in modules.

No external data-processing libraries such as pandas are used.

## 3. Project Structure

```
ev-charging-assessment/
data/
    ev_stations_raw.csv
    charging_sessions.csv

 output/
    ev.db
    stations_clean.csv
    stations.geojson
    rejected_sessions.csv
    operator_report.csv
    top_stations.csv
    daily_summary.csv
    hourly_usage.csv
    station_utilisation.csv
    impossible_sessions.csv
    station_distances.csv
    nearby.geojson
    daily_energy.csv
    weekday_hour_usage.csv
    operator_performance.csv

 src/
    __init__.py
    stations.py
    sessions.py
    reports.py
    analysis.py
    main.py

.gitignore
requirements.txt
README.md
```

## 4. Installation and Setup

### Prerequisites

- Python 3.10 or later
- pip
- Windows, Linux or macOS

### Step 1: Clone the repository

```bash
git clone <your-github-repository-url>
cd ev-charging-assessment
```

### Step 2: Create a virtual environment

Windows PowerShell:

```powershell
python -m venv .venv
```

### Step 3: Activate the virtual environment

```powershell
.venv\Scripts\Activate.ps1
```

### Step 4: Install dependencies

```powershell
pip install -r requirements.txt
```

The requirements file contains:

```text
numpy
```

SQLite and the other required modules are included in Python's standard library.

## 5. Running the Project

Run the complete application from the project root directory:

```powershell
python -m src.main
```

The main module orchestrates all processing stages in sequence:

1. Station data cleaning.
2. SQLite database initialization and session validation.
3. SQL report generation.
4. NumPy-based charging network analysis.
5. Geographical station analysis.

All generated reports are saved in the `output/` directory.

**Important:** Each full execution rebuilds the SQLite database from the supplied CSV files because the database initialization process drops and recreates the existing tables.

## 6. Implementation Details

### Part 1 – Station Data Cleaning

Module: `src/stations.py`

- Reads the raw station CSV file.
- Replaces empty station names with `Unnamed Station`.
- Validates latitude and longitude values.
- Skips records with missing, non-numeric or out-of-range coordinates.
- Converts numerical fields into appropriate types.
- Generates a cleaned station CSV file.
- Generates GeoJSON features using the Point geometry format.

GeoJSON coordinates follow the required order:

```json
{
    "type": "Point",
    "coordinates": [80.2167, 12.9915]
}
```

Longitude is stored before latitude.

**Result:**

- Raw records: 80
- Valid records: 73
- Skipped records: 7

### Part 2 – SQLite Database and Session Validation

Module: `src/sessions.py`

Creates an SQLite database containing two relational tables:

**stations**

- station_id (Primary Key)
- name
- operator
- connector_type
- power_kw
- latitude
- longitude

**sessions**

- session_id (Primary Key)
- station_id (Foreign Key)
- start_time
- end_time
- energy_kwh
- amount_inr

Validation includes:

- Duplicate session ID detection.
- Unknown station ID detection.
- Date and time format validation.
- End time must be later than start time.
- Energy consumption must be positive.
- Invalid numerical values are rejected.

Rejected records are exported to `rejected_sessions.csv` with their corresponding rejection reasons.

Parameterized SQL statements are used for database insertion.

**Result:**

- Sessions read: 432
- Valid sessions: 422
- Rejected sessions: 10

### Part 3 – SQL Reports

Module: `src/reports.py`

Generates three SQL-based reports for October 2026.

**1. Operator Report**

- Total sessions per operator.
- Total energy delivered.
- Total revenue.
- Average charging duration.
- Final TOTAL row.
- Revenue-based descending order.

**2. Top Five Stations**

- Identifies the five stations with the highest energy delivery.
- Includes station ID, station name, operator, session count and energy consumption.

**3. Daily Summary**

- Daily session count.
- Daily energy consumption.
- Daily revenue.

The daily report is cross-checked against the operator report to verify session and energy totals.

### Part 4 – NumPy-Based Station Analysis

Module: `src/analysis.py`

**4A. Hourly Usage**

Creates a station-by-24-hour usage matrix and identifies the three busiest charging hours.

**4B. Station Utilisation**

Calculates total charging hours and station utilisation percentages.

The calculation uses 31 days × 24 hours = 744 available hours per station.

**4C. Impossible Energy Detection**

Compares session energy consumption against the theoretical maximum energy based on station power and charging duration.

**4D. Geographical Distance Analysis**

Implements the Haversine formula using Earth's radius of 6,371 km.

Uses NumPy broadcasting to calculate the station-to-station distance matrix and identifies:

- Nearest other station for each station.
- Closest station pair.
- Most isolated station.

**4E. Nearby Station Search**

Implements a reusable nearby-station search using vectorised distance calculations.

Supports:

- Latitude and longitude.
- Search radius in kilometres.
- Minimum charging power.
- Distance-based sorting.
- GeoJSON output.

Test location:

- Latitude: 13.0418
- Longitude: 80.2341
- Search radius: 5 km
- Minimum power: 0 kW

### Part 5 – NumPy-Based Network Performance Analysis

**5A. Daily Energy Consumption**

- Calculates daily energy consumption for all 31 days.
- Uses NumPy `bincount`.
- Calculates a seven-day trailing average.
- Leaves the first six days without a rolling average.

**5B. Weekday and Hour Analysis**

- Creates a 7 × 24 weekday-hour usage matrix.
- Calculates average daily sessions for each weekday.
- Adjusts averages based on the actual number of weekday occurrences in October.
- Compares weekday and weekend activity.

**5C. Operator Performance**

Uses NumPy `unique` and `bincount` to calculate:

- Sessions per operator.
- Total revenue per operator.
- Revenue per session.
- Revenue-based operator ranking.

## 7. Results and Observations

The following results were obtained from the supplied datasets.

### Dataset Processing

| Metric            | Result |
| ----------------- | -----: |
| Raw stations      |     80 |
| Clean stations    |     73 |
| Skipped stations  |      7 |
| Raw sessions      |    432 |
| Valid sessions    |    422 |
| Rejected sessions |     10 |

### Network Performance

| Metric                              |       Result |
| ----------------------------------- | -----------: |
| Total charging sessions             |          422 |
| Total energy consumed               | 9,281.21 kWh |
| Total revenue                       |  ₹191,533.83 |
| Number of operators                 |            9 |
| Network average station utilisation |        1.14% |

### Key Observations

1. **Peak charging hours:** 18:00 recorded the highest activity with 32 sessions, followed by 22:00 and 16:00 with 31 sessions each.

2. **Operator revenue:** Zeon recorded the highest total revenue at ₹32,373.42, followed by Tata Power at ₹30,386.09.

3. **Station utilisation:** EV060 recorded the highest utilisation at 2.86%, with 21.27 charging hours during October.

4. **Weekday activity:** Wednesday had the highest average daily session count at 15 sessions per day.

5. **Geographical distribution:** EV065 and EV079 were the closest station pair, approximately 0.162 km apart. EV047 was the most isolated station, approximately 4.470 km from EV007.

6. **Data quality:** One charging session, S00376, exceeded the theoretical energy limit calculated from its station's rated power and session duration. It was flagged for investigation.

### Data Validation

The SQL and NumPy daily energy totals were cross-checked.

| Validation                 | Result       |
| -------------------------- | ------------ |
| SQL daily session count    | 422          |
| SQL operator session count | 422          |
| SQL daily energy           | 9,281.21 kWh |
| NumPy daily energy         | 9,281.21 kWh |
| Session counts match       | Yes          |
| Energy totals match        | Yes          |

## 8. Generated Output Files

| Output file                | Description                            |
| -------------------------- | -------------------------------------- |
| `stations_clean.csv`       | Cleaned station records                |
| `stations.geojson`         | Geographical station features          |
| `rejected_sessions.csv`    | Invalid sessions and rejection reasons |
| `ev.db`                    | SQLite database                        |
| `operator_report.csv`      | Operator-wise SQL report               |
| `top_stations.csv`         | Top five stations by energy            |
| `daily_summary.csv`        | Daily SQL summary                      |
| `hourly_usage.csv`         | Station-hour usage analysis            |
| `station_utilisation.csv`  | Station utilisation report             |
| `impossible_sessions.csv`  | Suspicious energy consumption records  |
| `station_distances.csv`    | Nearest station distances              |
| `nearby.geojson`           | Nearby station search results          |
| `daily_energy.csv`         | Daily energy and rolling average       |
| `weekday_hour_usage.csv`   | Weekday-hour usage matrix              |
| `operator_performance.csv` | NumPy operator performance analysis    |

## 9. Data Quality Notes and Known Limitations

- Station records with invalid geographical coordinates are excluded because reliable geographical calculations require valid latitude and longitude.
- Invalid charging sessions are excluded from the database and retained separately in the rejection report.
- The energy-limit check identifies theoretically suspicious records. A flagged record is not necessarily proof of fraud or an actual charging-system failure.
- Station utilisation is calculated using the full 744-hour October period.
- The nearby-station test location and search radius are currently configured in `main.py`.
- The dataset represents October 2026, and the reports are generated for that period.
- The project uses a full database rebuild during each complete execution rather than incremental updates.
- No external geospatial routing or road-network distance calculation is performed; distances are straight-line Haversine distances.

## 10. Project Completion

The implementation covers:

- CSV data cleaning and validation.
- GeoJSON generation.
- SQLite database creation and relational constraints.
- SQL reporting and aggregation.
- NumPy vectorised numerical analysis.
- Geographical distance calculations.
- Nearby station search.
- Cross-validation of SQL and NumPy results.
- Modular project execution through a single entry point.

**Execution command:**

```powershell
python -m src.main
```

**Final execution status:** Successfully completed all implemented processing and analysis stages.
