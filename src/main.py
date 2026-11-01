import sqlite3

from src.stations import clean_stations
from src.sessions import (
    initialize_database,
    load_stations,
    load_sessions
)
from src.reports import generate_reports
from src.analysis import (
    load_analysis_data,
    analyze_hourly_usage,
    analyze_station_utilisation,
    detect_impossible_sessions,
    analyze_station_distances,
    find_nearby_stations,
    analyze_daily_energy,
    analyze_weekday_hour_usage,
    analyze_operator_performance,
)


def main():

    print("\nprocess EV data")

    # Part 1 
    clean_stations(
        "data/ev_stations_raw.csv",
        "output/stations_clean.csv"
    )

    # Part 2 
    connection = initialize_database("output/ev.db")

    try:
        load_stations(
            connection,
            "output/stations_clean.csv"
        )

        load_sessions(
            connection,
            "data/charging_sessions.csv",
            "output/rejected_sessions.csv"
        )

    finally:
        connection.close()

    # Part 3 
    generate_reports()

    # Part 4 and Part 5 
    connection = sqlite3.connect("output/ev.db")

    try:
        data = load_analysis_data(connection)

        analyze_hourly_usage(
            data, "output/hourly_usage.csv"
        )

        analyze_station_utilisation(
            data, "output/station_utilisation.csv"
        )

        detect_impossible_sessions(
            data, "output/impossible_sessions.csv"
        )

        analyze_station_distances(
            data, "output/station_distances.csv"
        )

        find_nearby_stations(
            data,
            latitude=13.0418,
            longitude=80.2341,
            radius_km=5,
            min_kw=0,
            output_path="output/nearby.geojson"
        )

        analyze_daily_energy(
            data, "output/daily_energy.csv"
        )

        analyze_weekday_hour_usage(
            data, "output/weekday_hour_usage.csv"
        )

        analyze_operator_performance(
            data, "output/operator_performance.csv"
        )

    finally:
        connection.close()

    print("\nproject completed successfully.")


if __name__ == "__main__":
    main()