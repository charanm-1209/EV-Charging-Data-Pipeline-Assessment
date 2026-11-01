import csv
import sqlite3
from pathlib import Path


def write_csv(file_path, headers, rows):
    file_path = Path(file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)

    with open(file_path, "w", newline="", encoding="utf-8") as file:

        writer = csv.writer(file)

        writer.writerow(headers)
        writer.writerows(rows)

    print("Report created:", file_path)



def generate_operator_report(connection, output_path):

    query = """
        SELECT
            st.operator,
            COUNT(se.session_id) AS total_sessions,
            SUM(se.energy_kwh) AS total_energy,
            SUM(se.amount_inr) AS total_revenue,
            AVG(
                (julianday(se.end_time) - julianday(se.start_time))
                * 24 * 60
            ) AS avg_duration_min

        FROM sessions se

        JOIN stations st
            ON se.station_id = st.station_id

        WHERE date(se.start_time) >= ?
          AND date(se.start_time) <= ?

        GROUP BY st.operator

        ORDER BY total_revenue DESC
    """

    results = connection.execute(
        query,
        ("2026-10-01", "2026-10-31")
    ).fetchall()

    rows = []

    for operator, sessions, energy, revenue, duration in results:

        rows.append([
            operator,
            sessions,
            round(energy, 2),
            round(revenue, 2),
            round(duration, 1)
        ])

    total_sessions = sum(row[1] for row in rows)
    total_energy = sum(row[2] for row in rows)
    total_revenue = sum(row[3] for row in rows)

    if total_sessions > 0:

        weighted_duration = connection.execute(
            """
            SELECT AVG(
                (julianday(end_time) - julianday(start_time))
                * 24 * 60
            )
            FROM sessions
            WHERE date(start_time) >= ?
              AND date(start_time) <= ?
            """,
            ("2026-10-01", "2026-10-31")
        ).fetchone()[0]

    else:
        weighted_duration = 0

    rows.append([
        "TOTAL",
        total_sessions,
        round(total_energy, 2),
        round(total_revenue, 2),
        round(weighted_duration or 0, 1)
    ])

    headers = [
        "operator",
        "total_sessions",
        "total_energy_kwh",
        "total_revenue_inr",
        "avg_duration_min"
    ]

    write_csv(output_path, headers, rows)

    print("Operator report rows:", len(results))

def generate_top_stations_report(connection, output_path):
    query = """
        SELECT
            st.station_id,
            st.name,
            st.operator,
            COUNT(se.session_id) AS total_sessions,
            SUM(se.energy_kwh) AS total_energy

        FROM stations st

        JOIN sessions se
            ON st.station_id = se.station_id

        GROUP BY
            st.station_id,
            st.name,
            st.operator

        ORDER BY total_energy DESC

        LIMIT 5
    """

    results = connection.execute(query).fetchall()

    rows = [
        [
            station_id,
            name,
            operator,
            total_sessions,
            round(total_energy, 2)
        ]
        for station_id, name, operator, total_sessions, total_energy in results
    ]

    headers = [
        "station_id",
        "station_name",
        "operator",
        "total_sessions",
        "total_energy_kwh"
    ]

    write_csv(output_path, headers, rows)

    print("Top stations identified:", len(rows))


def generate_daily_summary(connection, output_path):
    query = """
        SELECT
            date(start_time) AS session_date,
            COUNT(*) AS total_sessions,
            SUM(energy_kwh) AS total_energy,
            SUM(amount_inr) AS total_revenue

        FROM sessions

        WHERE date(start_time) >= ?
          AND date(start_time) <= ?

        GROUP BY date(start_time)

        ORDER BY session_date
    """

    results = connection.execute(
        query,
        ("2026-10-01", "2026-10-31")
    ).fetchall()

    rows = [
        [
            session_date,
            total_sessions,
            round(total_energy, 2),
            round(total_revenue, 2)
        ]
        for session_date, total_sessions, total_energy, total_revenue in results
    ]

    headers = [
        "date",
        "total_sessions",
        "total_energy_kwh",
        "total_revenue_inr"
    ]

    write_csv(output_path, headers, rows)

    print("daily summary rows:", len(rows))

def generate_reports():

    db_path = Path("output/ev.db")
    connection = sqlite3.connect(db_path)

    try:
        generate_operator_report(
            connection,
            "output/operator_report.csv"
        )

        generate_top_stations_report(
            connection,
            "output/top_stations.csv"
        )

        generate_daily_summary(
            connection,
            "output/daily_summary.csv"
        )
        with open(
            "output/daily_summary.csv",
            newline="",
            encoding="utf-8"
        ) as file:
            daily_rows = list(csv.DictReader(file))

        daily_sessions = sum(
            int(row["total_sessions"]) for row in daily_rows
        )

        daily_energy = sum(
            float(row["total_energy_kwh"]) for row in daily_rows
        )

        with open(
            "output/operator_report.csv",
            newline="",
            encoding="utf-8"
        ) as file:
            operator_rows = list(csv.DictReader(file))

        total_row = next(
            row for row in operator_rows
            if row["operator"] == "TOTAL"
        )

        operator_sessions = int(total_row["total_sessions"])
        operator_energy = float(total_row["total_energy_kwh"])

        print("\nreport summary")
        print("daily session total:", daily_sessions)
        print("operator session total:", operator_sessions)
        print("daily energy total:", round(daily_energy, 2))
        print("operator energy total:", operator_energy)

        print(
            "Session counts match:",
            daily_sessions == operator_sessions
        )

        print(
            "Energy totals match (within 0.15 kWh):",
            abs(daily_energy - operator_energy) <= 0.15
        )

    finally:
        connection.close()

if __name__ == "__main__":
    generate_reports()