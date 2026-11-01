import csv
import sqlite3
from pathlib import Path
from datetime import datetime
from collections import Counter
import math

def initialize_database(db_path):
    db_path = Path(db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path)

    connection.execute("PRAGMA foreign_keys = ON")
    connection.execute("DROP TABLE IF EXISTS sessions")
    connection.execute("DROP TABLE IF EXISTS stations")
    connection.execute("""
        CREATE TABLE stations (
            station_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            operator TEXT,
            connector_type TEXT,
            power_kw REAL,
            latitude REAL,
            longitude REAL
        )
    """)
    connection.execute("""
        CREATE TABLE sessions (
            session_id TEXT PRIMARY KEY,
            station_id TEXT NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            energy_kwh REAL NOT NULL,
            amount_inr REAL,
            FOREIGN KEY (station_id) REFERENCES stations(station_id)
        )
    """)

    connection.commit()

    print("database and tables created successfully.")

    return connection


def load_stations(connection, csv_path):
    with open(csv_path, "r", newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)
        stations = [
            (
                row["station_id"],
                row["name"],
                row["operator"],
                row["connector_type"],
                float(row["power_kw"]),
                float(row["latitude"]),
                float(row["longitude"])
            )
            for row in reader
        ]

    connection.executemany(
        """
        INSERT INTO stations (
            station_id,
            name,
            operator,
            connector_type,
            power_kw,
            latitude,
            longitude
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        stations
    )

    connection.commit()

    print("stations loaded:", len(stations))


def load_sessions(connection, csv_path, rejected_path):
    expected_time_format = "%Y-%m-%d %H:%M:%S"
    station_ids = {
        row[0]
        for row in connection.execute(
            "SELECT station_id FROM stations"
        ).fetchall()
    }

    seen_session_ids = set()

    valid_sessions = []
    rejected_sessions = []

    rejection_reasons = Counter()
    rows_read = 0

    with open(csv_path, "r", newline="", encoding="utf-8-sig") as file:

        reader = csv.DictReader(file)
        original_columns = reader.fieldnames

        for row in reader:

            rows_read += 1

            session_id = row["session_id"].strip()
            station_id = row["station_id"].strip()

            reason = None
            if not session_id:
                reason = "Missing session_id"

            elif session_id in seen_session_ids:
                reason = "Duplicate session_id"

            else:
                seen_session_ids.add(session_id)
            if reason is None and station_id not in station_ids:
                reason = "Unknown station_id"
            if reason is None:

                start_time = row["start_time"].strip()
                end_time = row["end_time"].strip()

                try:
                    start_datetime = datetime.strptime(
                        start_time, expected_time_format
                    )

                    end_datetime = datetime.strptime(
                        end_time, expected_time_format
                    )
                    if (
                        start_datetime.strftime(expected_time_format) != start_time
                        or end_datetime.strftime(expected_time_format) != end_time
                    ):
                        raise ValueError("Incorrect datetime format")

                except ValueError:
                    reason = "Invalid time format"
            if reason is None and end_datetime <= start_datetime:
                reason = "End time must be after start time"
            if reason is None:

                try:
                    energy_kwh = float(row["energy_kwh"])

                    if not math.isfinite(energy_kwh) or energy_kwh <= 0:
                        reason = "Energy must be a positive number"

                except (ValueError, TypeError):
                    reason = "Invalid energy value"
            if reason is None:

                try:
                    amount_inr = float(row["amount_inr"])

                    if not math.isfinite(amount_inr):
                        reason = "Invalid amount value"

                except (ValueError, TypeError):
                    reason = "Invalid amount value"
            if reason is not None:

                rejected_row = dict(row)
                rejected_row["reason"] = reason

                rejected_sessions.append(rejected_row)
                rejection_reasons[reason] += 1

            else:

                valid_sessions.append(
                    (
                        session_id,
                        station_id,
                        start_time,
                        end_time,
                        energy_kwh,
                        amount_inr
                    )
                )
    connection.executemany(
        """
        INSERT INTO sessions (
            session_id,
            station_id,
            start_time,
            end_time,
            energy_kwh,
            amount_inr
        )
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        valid_sessions
    )
    connection.commit()

    rejected_path = Path(rejected_path)
    rejected_path.parent.mkdir(parents=True, exist_ok=True)

    with open(rejected_path, "w", newline="", encoding="utf-8") as file:

        writer = csv.DictWriter(
            file,
            fieldnames=list(original_columns) + ["reason"]
        )

        writer.writeheader()
        writer.writerows(rejected_sessions)

    print("\nsession data started")

    print("rows read:", rows_read)
    print("sessions loaded:", len(valid_sessions))
    print("sessions rejected:", len(rejected_sessions))

    print("\nRejection reasons:")

    for reason, count in rejection_reasons.items():
        print(f"{reason}: {count}")

    print("\nrejected CSV created:", rejected_path)



if __name__ == "__main__":

    db_path = Path("output/ev.db")
    stations_path = Path("output/stations_clean.csv")
    sessions_path = Path("data/charging_sessions.csv")
    rejected_path = Path("output/rejected_sessions.csv")

    connection = initialize_database(db_path)

    try:
        load_stations(connection, stations_path)

        load_sessions(
            connection,
            sessions_path,
            rejected_path
        )
        station_count = connection.execute(
            "SELECT COUNT(*) FROM stations"
        ).fetchone()[0]

        session_count = connection.execute(
            "SELECT COUNT(*) FROM sessions"
        ).fetchone()[0]

        print("\n========== DATABASE VERIFICATION ==========")
        print("Database station count:", station_count)
        print("Database session count:", session_count)

    finally:
        connection.close()