
import csv
from pathlib import Path
import json
import sqlite3


def read_stations(file_path):
    with open(file_path, "r", newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)

        stations = list(reader)

    return stations


def validate_coordinates(row):
    latitude_value = row["latitude"].strip()
    longitude_value = row["longitude"].strip()

    if not latitude_value:
        return False, None, None, "Missing latitude"

    if not longitude_value:
        return False, None, None, "Missing longitude"

    try:
        latitude = float(latitude_value)
    except ValueError:
        return False, None, None, "Latitude is not a number"

    try:
        longitude = float(longitude_value)
    except ValueError:
        return False, None, None, "Longitude is not a number"

    if not -90 <= latitude <= 90:
        return False, None, None, "Latitude outside valid range"

    if not -180 <= longitude <= 180:
        return False, None, None, "Longitude outside valid range"

    return True, latitude, longitude, None



def clean_stations(input_path, output_path):
    stations = read_stations(input_path)

    cleaned_stations = []
    skipped_stations = []

    for row in stations:

        is_valid, latitude, longitude, reason = validate_coordinates(row)

        if not is_valid:
            skipped_stations.append({
                "station_id": row["station_id"],
                "reason": reason
            })
            continue
        name = row["name"].strip()

        if not name:
            name = "Unnamed Station"
        power_kw = float(row["power_kw"])

        cleaned_station = {
            "station_id": row["station_id"],
            "name": name,
            "operator": row["operator"],
            "connector_type": row["connector_type"],
            "power_kw": power_kw,
            "latitude": latitude,
            "longitude": longitude
        }

        cleaned_stations.append(cleaned_station)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "station_id",
        "name",
        "operator",
        "connector_type",
        "power_kw",
        "latitude",
        "longitude"
    ]

    with open(output_path, "w", newline="", encoding="utf-8") as file:

        writer = csv.DictWriter(file, fieldnames=fieldnames)

        writer.writeheader()
        writer.writerows(cleaned_stations)
    print("\nstation data cleaning")

    print("rows read:", len(stations))
    print("rows written:", len(cleaned_stations))
    print("rows skipped:", len(skipped_stations))

    for skipped in skipped_stations:
        print(
            f"station id: {skipped['station_id']} | "
            f"reason: {skipped['reason']}"
        )

    return cleaned_stations, skipped_stations



def generate_geojson(stations, output_path):

    features = []

    for station in stations:

        feature = {
            "type": "Feature",

            "geometry": {
                "type": "Point",
                "coordinates": [
                    station["longitude"],
                    station["latitude"]
                ]
            },

            "properties": {
                "station_id": station["station_id"],
                "name": station["name"],
                "operator": station["operator"],
                "connector_type": station["connector_type"],
                "power_kw": station["power_kw"]
            }
        }

        features.append(feature)

    geojson = {
        "type": "FeatureCollection",
        "features": features
    }

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as file:
        json.dump(geojson, file, indent=4)

    print(f"\nGeoJSON created: {output_path}")
    print("Total GeoJSON features:", len(features))




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
            FOREIGN KEY (station_id)
                REFERENCES stations(station_id)
        )
    """)

    connection.commit()

    return connection


if __name__ == "__main__":

    input_file = Path("data/ev_stations_raw.csv")

    csv_output = Path("output/stations_clean.csv")
    geojson_output = Path("output/stations.geojson")

    cleaned_stations, skipped_stations = clean_stations(
        input_file,
        csv_output
    )

    generate_geojson(
        cleaned_stations,
        geojson_output
    )
