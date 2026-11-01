import csv
import sqlite3
import numpy as np
from pathlib import Path
import json
import calendar

def load_analysis_data(connection):
    station_rows = connection.execute("""
        SELECT
            station_id,
            name,
            operator,
            power_kw,
            latitude,
            longitude
        FROM stations
        ORDER BY station_id
    """).fetchall()

    session_rows = connection.execute("""
    SELECT
        station_id,
        CAST(strftime('%H', start_time) AS INTEGER),
        CAST(strftime('%d', start_time) AS INTEGER),
        start_time,
        end_time,
        energy_kwh,
        amount_inr,
        session_id,
        CAST(strftime('%w', start_time) AS INTEGER)
    FROM sessions
    ORDER BY session_id
""").fetchall()

    station_ids = np.array([row[0] for row in station_rows])
    station_names = np.array([row[1] for row in station_rows])
    station_operators = np.array([row[2] for row in station_rows])
    session_ids = np.array([row[7] for row in session_rows])
    session_weekdays = np.array(
    [row[8] for row in session_rows],
    dtype=int
    )

    session_weekdays = (session_weekdays + 6) % 7

    station_power = np.array(
        [row[3] for row in station_rows],
        dtype=float
    )

    latitudes = np.array(
        [row[4] for row in station_rows],
        dtype=float
    )

    longitudes = np.array(
        [row[5] for row in station_rows],
        dtype=float
    )

    session_station_ids = np.array([row[0] for row in session_rows])

    session_hours = np.array(
        [row[1] for row in session_rows],
        dtype=int
    )

    session_days = np.array(
        [row[2] for row in session_rows],
        dtype=int
    )

    start_times = np.array([row[3] for row in session_rows])
    end_times = np.array([row[4] for row in session_rows])

    energy = np.array(
        [row[5] for row in session_rows],
        dtype=float
    )

    amounts = np.array(
        [row[6] for row in session_rows],
        dtype=float
    )

    station_indices = np.searchsorted(
        station_ids,
        session_station_ids
    )

    return {
        "station_ids": station_ids,
        "station_names": station_names,
        "station_operators": station_operators,
        "station_power": station_power,
        "latitudes": latitudes,
        "longitudes": longitudes,
        "session_station_ids": session_station_ids,
        "station_indices": station_indices,
        "session_hours": session_hours,
        "session_days": session_days,
        "start_times": start_times,
        "end_times": end_times,
        "energy": energy,
        "amounts": amounts,
        "session_ids": session_ids,
        "session_weekdays": session_weekdays,
    }

def analyze_hourly_usage(data, output_path):
    station_count = len(data["station_ids"])

    usage_matrix = np.zeros(
        (station_count, 24),
        dtype=int
    )

    np.add.at(
        usage_matrix,
        (
            data["station_indices"],
            data["session_hours"]
        ),
        1
    )

    hourly_totals = usage_matrix.sum(axis=0)

    busiest_indices = np.argsort(hourly_totals)[::-1][:3]

    headers = ["hour", "total_sessions"]

    rows = [
        [f"{hour:02d}:00", int(hourly_totals[hour])]
        for hour in range(24)
    ]

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", newline="", encoding="utf-8") as file:

        writer = csv.writer(file)
        writer.writerow(headers)
        writer.writerows(rows)

    print("\nusage hours checking")

    print("usage matrix shape:", usage_matrix.shape)

    print("\nbusiest three hours:")

    for index in busiest_indices:
        print(
            f"{index:02d}:00 - {hourly_totals[index]} sessions"
        )

    print("\ntotal sessions in matrix:", usage_matrix.sum())

    print("hourly report created:", output_path)

    return usage_matrix

def analyze_station_utilisation(data, output_path):
    station_count = len(data["station_ids"])

    total_available_hours = 31 * 24

    start_times = data["start_times"].astype("datetime64[s]")
    end_times = data["end_times"].astype("datetime64[s]")

    session_durations = (
        end_times - start_times
    ) / np.timedelta64(1, "h")

    charging_hours = np.bincount(
        data["station_indices"],
        weights=session_durations,
        minlength=station_count
    )

    utilisation = (
        charging_hours / total_available_hours
    ) * 100

    top_indices = np.argsort(utilisation)[::-1][:5]

    rows = []

    for index in range(station_count):

        rows.append([
            data["station_ids"][index],
            data["station_names"][index],
            data["station_operators"][index],
            round(charging_hours[index], 2),
            round(utilisation[index], 2)
        ])

    rows.sort(key=lambda row: row[4], reverse=True)

    headers = [
        "station_id",
        "station_name",
        "operator",
        "charging_hours",
        "utilisation_percentage"
    ]

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", newline="", encoding="utf-8") as file:

        writer = csv.writer(file)
        writer.writerow(headers)
        writer.writerows(rows)

    network_average = np.mean(utilisation)

    print("\nstation utilisation checking")

    print("total available hours per station:", total_available_hours)

    print("\ntop five stations by utilisation:")

    for index in top_indices:

        print(
            f"{data['station_ids'][index]} - "
            f"{charging_hours[index]:.2f} hours - "
            f"{utilisation[index]:.2f}%"
        )

    print(
        "\nnetwork average utilisation:",
        round(network_average, 2),
        "%"
    )

    print("\nstation utilisation report created:", output_path)

    return charging_hours, utilisation

def detect_impossible_sessions(data, output_path):

    start_times = data["start_times"].astype("datetime64[s]")
    end_times = data["end_times"].astype("datetime64[s]")

    session_durations = (
        end_times - start_times
    ) / np.timedelta64(1, "h")

    session_power = data["station_power"][
        data["station_indices"]
    ]

    maximum_energy = session_power * session_durations

    impossible_mask = data["energy"] > maximum_energy

    suspicious_ids = data["session_ids"][impossible_mask]

    suspicious_station_ids = data["session_station_ids"][impossible_mask]

    suspicious_energy = data["energy"][impossible_mask]

    suspicious_maximum = maximum_energy[impossible_mask]

    suspicious_duration = session_durations[impossible_mask]

    suspicious_power = session_power[impossible_mask]

    rows = []

    for i in range(len(suspicious_ids)):

        rows.append([
            suspicious_ids[i],
            suspicious_station_ids[i],
            round(suspicious_duration[i], 2),
            round(suspicious_power[i], 2),
            round(suspicious_energy[i], 2),
            round(suspicious_maximum[i], 2)
        ])

    headers = [
        "session_id",
        "station_id",
        "duration_hours",
        "station_power_kw",
        "recorded_energy_kwh",
        "maximum_possible_energy_kwh"
    ]

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", newline="", encoding="utf-8") as file:

        writer = csv.writer(file)
        writer.writerow(headers)
        writer.writerows(rows)

    print("\nimpossible session checking")

    print("total sessions analysed:", len(data["energy"]))

    print("suspicious sessions detected:", len(suspicious_ids))

    print("valid sessions:", len(data["energy"]) - len(suspicious_ids))

    print("\nsuspicious session IDs:", suspicious_ids.tolist())

    print("\nreport created:", output_path)

    return impossible_mask


def haversine_distance(lat1, lon1, lat2, lon2):
    earth_radius = 6371.0

    lat1 = np.radians(lat1)
    lon1 = np.radians(lon1)

    lat2 = np.radians(lat2)
    lon2 = np.radians(lon2)

    delta_lat = lat2 - lat1
    delta_lon = lon2 - lon1

    a = (
        np.sin(delta_lat / 2) ** 2
        + np.cos(lat1) * np.cos(lat2)
        * np.sin(delta_lon / 2) ** 2
    )

    a = np.clip(a, 0.0, 1.0)

    c = 2 * np.arctan2(
        np.sqrt(a),
        np.sqrt(1 - a)
    )

    return earth_radius * c

def analyze_station_distances(data, output_path):
    station_ids = data["station_ids"]
    station_names = data["station_names"]

    latitudes = data["latitudes"]
    longitudes = data["longitudes"]

    station_count = len(station_ids)

    lat1 = latitudes[:, np.newaxis]
    lon1 = longitudes[:, np.newaxis]

    lat2 = latitudes[np.newaxis, :]
    lon2 = longitudes[np.newaxis, :]

    distance_matrix = haversine_distance(
        lat1,
        lon1,
        lat2,
        lon2
    )

    nearest_matrix = distance_matrix.copy()
    np.fill_diagonal(nearest_matrix, np.inf)

    nearest_indices = np.argmin(nearest_matrix, axis=1)
    nearest_distances = np.min(nearest_matrix, axis=1)

    upper_indices = np.triu_indices(
        station_count,
        k=1
    )

    pair_distances = distance_matrix[upper_indices]

    closest_position = np.argmin(pair_distances)

    closest_i = upper_indices[0][closest_position]
    closest_j = upper_indices[1][closest_position]

    closest_distance = distance_matrix[closest_i, closest_j]

    isolated_index = np.argmax(nearest_distances)

    rows = []

    for index in range(station_count):

        nearest_index = nearest_indices[index]

        rows.append([
            station_ids[index],
            station_names[index],
            station_ids[nearest_index],
            station_names[nearest_index],
            round(nearest_distances[index], 3)
        ])

    rows.sort(key=lambda row: row[4])

    headers = [
        "station_id",
        "station_name",
        "nearest_station_id",
        "nearest_station_name",
        "distance_km"
    ]

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", newline="", encoding="utf-8") as file:

        writer = csv.writer(file)
        writer.writerow(headers)
        writer.writerows(rows)

    print("\nstation distance checking  ")

    print("distance matrix shape:", distance_matrix.shape)

    print("\nclosest station pair:")

    print(
        f"{station_ids[closest_i]} and {station_ids[closest_j]}: "
        f"{closest_distance:.3f} km"
    )

    print("\nmost isolated station:")

    print(
        f"{station_ids[isolated_index]} - "
        f"{nearest_distances[isolated_index]:.3f} km "
        f"from {station_ids[nearest_indices[isolated_index]]}"
    )

    print("\ndistance report created:", output_path)

    return distance_matrix, nearest_distances, nearest_indices


def find_nearby_stations(
    data,
    latitude,
    longitude,
    radius_km,
    min_kw=0,
    output_path="output/nearby.geojson"
):

    try:
        latitude = float(latitude)
    except (TypeError, ValueError):
        raise ValueError("Latitude must be a number.")

    if not np.isfinite(latitude) or not -90 <= latitude <= 90:
        raise ValueError("Latitude must be between -90 and 90.")

    try:
        longitude = float(longitude)
    except (TypeError, ValueError):
        raise ValueError("Longitude must be a number.")

    if not np.isfinite(longitude) or not -180 <= longitude <= 180:
        raise ValueError("Longitude must be between -180 and 180.")

    try:
        radius_km = float(radius_km)
    except (TypeError, ValueError):
        raise ValueError("radius must be a number.")

    if not np.isfinite(radius_km) or radius_km <= 0:
        raise ValueError("radius must be greater than zero.")

    try:
        min_kw = float(min_kw)
    except (TypeError, ValueError):
        raise ValueError("minimum power must be a number.")

    if not np.isfinite(min_kw) or min_kw < 0:
        raise ValueError("minimum power cannot be negative.")

    distances = haversine_distance(
        latitude,
        longitude,
        data["latitudes"],
        data["longitudes"]
    )

    nearby_mask = (
        (distances <= radius_km)
        & (data["station_power"] >= min_kw)
    )

    nearby_indices = np.where(nearby_mask)[0]

    sorted_order = np.argsort(
        distances[nearby_indices]
    )

    nearby_indices = nearby_indices[sorted_order]

    features = []

    for index in nearby_indices:

        feature = {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [
                    float(data["longitudes"][index]),
                    float(data["latitudes"][index])
                ]
            },
            "properties": {
                "station_id": str(data["station_ids"][index]),
                "name": str(data["station_names"][index]),
                "operator": str(data["station_operators"][index]),
                "power_kw": float(data["station_power"][index]),
                "distance_km": round(float(distances[index]), 3)
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

    print("\nnearby station search checking")

    print("search location:", latitude, longitude)
    print("search radius:", radius_km, "km")
    print("minimum charging power:", min_kw, "kW")

    print("nearby stations found:", len(features))

    print("\nnearby stations:")

    for index in nearby_indices:

        print(
            f"{data['station_ids'][index]} - "
            f"{distances[index]:.3f} km - "
            f"{data['station_power'][index]} kW"
        )

    print("\nGeoJSON created:", output_path)

    return features

def analyze_daily_energy(data, output_path):
    daily_energy = np.bincount(
        data["session_days"],
        weights=data["energy"],
        minlength=32
    )[1:32]

    trailing_average = np.full(31, np.nan)

    seven_day_average = np.convolve(
        daily_energy,
        np.ones(7) / 7,
        mode="valid"
    )

    trailing_average[6:] = seven_day_average

    headers = [
        "date",
        "daily_energy_kwh",
        "seven_day_trailing_average_kwh"
    ]

    rows = []

    for index in range(31):

        date = f"2026-10-{index + 1:02d}"

        average = (
            round(trailing_average[index], 2)
            if not np.isnan(trailing_average[index])
            else ""
        )

        rows.append([
            date,
            round(daily_energy[index], 2),
            average
        ])

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", newline="", encoding="utf-8") as file:

        writer = csv.writer(file)
        writer.writerow(headers)
        writer.writerows(rows)

    print("\ndaily energy checking")

    print("total days analysed:", len(daily_energy))

    print("total energy consumed:", round(daily_energy.sum(), 2), "kWh")

    print("\nfirst seven days:")

    for index in range(7):

        print(
            f"October {index + 1}: "
            f"{daily_energy[index]:.2f} kWh"
        )

    print("\nseven-day trailing average:")

    print(f"October 7: {trailing_average[6]:.2f} kWh")

    print("\ndaily energy report created:", output_path)

    return daily_energy, trailing_average



def analyze_weekday_hour_usage(data, output_path):
    weekday_names = [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday"
    ]

    usage_matrix = np.zeros(
        (7, 24),
        dtype=int
    )

    np.add.at(
        usage_matrix,
        (
            data["session_weekdays"],
            data["session_hours"]
        ),
        1
    )

    weekday_totals = usage_matrix.sum(axis=1)

    year = 2026
    month = 10

    first_weekday, days_in_month = calendar.monthrange(
        year,
        month
    )

    calendar_weekdays = (
        first_weekday + np.arange(days_in_month)
    ) % 7

    weekday_occurrences = np.bincount(
        calendar_weekdays,
        minlength=7
    )

    average_sessions = (
        weekday_totals / weekday_occurrences
    )

    busiest_index = np.argmax(average_sessions)

    weekday_average = (
        weekday_totals[:5].sum()
        / weekday_occurrences[:5].sum()
    )

    weekend_average = (
        weekday_totals[5:].sum()
        / weekday_occurrences[5:].sum()
    )

    headers = (
        ["weekday"]
        + [f"{hour:02d}:00" for hour in range(24)]
        + [
            "total_sessions",
            "days_in_month",
            "average_sessions_per_day"
        ]
    )

    rows = []

    for index in range(7):

        rows.append(
            [weekday_names[index]]
            + usage_matrix[index].tolist()
            + [
                int(weekday_totals[index]),
                int(weekday_occurrences[index]),
                round(average_sessions[index], 2)
            ]
        )

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", newline="", encoding="utf-8") as file:

        writer = csv.writer(file)
        writer.writerow(headers)
        writer.writerows(rows)

    print("\nweekday-hour usage checking    ")

    print("usage matrix shape:", usage_matrix.shape)

    print("\nweekday session summary:")

    for index in range(7):

        print(
            f"{weekday_names[index]}: "
            f"{weekday_totals[index]} sessions, "
            f"{weekday_occurrences[index]} occurrences, "
            f"average {average_sessions[index]:.2f} sessions/day"
        )

    print("\nbusiest weekday:")

    print(
        f"{weekday_names[busiest_index]} - "
        f"{average_sessions[busiest_index]:.2f} sessions/day"
    )

    print("\nweekday vs weekend comparison:")

    print(f"weekday average: {weekday_average:.2f} sessions/day")
    print(f"weekend average: {weekend_average:.2f} sessions/day")

    print("\ntotal sessions in matrix:", usage_matrix.sum())

    print("\nWeekday-hour report created:", output_path)

    return usage_matrix, weekday_totals, average_sessions


def analyze_operator_performance(data, output_path):

    session_operators = data["station_operators"][
        data["station_indices"]
    ]

    unique_operators, inverse_indices = np.unique(
        session_operators,
        return_inverse=True
    )

    operator_count = len(unique_operators)

    session_counts = np.bincount(
        inverse_indices,
        minlength=operator_count
    )

    operator_revenue = np.bincount(
        inverse_indices,
        weights=data["amounts"],
        minlength=operator_count
    )

    revenue_per_session = (
        operator_revenue / session_counts
    )

    sorted_indices = np.argsort(operator_revenue)[::-1]

    headers = [
        "operator",
        "total_sessions",
        "total_revenue_inr",
        "revenue_per_session_inr"
    ]

    rows = []

    for index in sorted_indices:

        rows.append([
            unique_operators[index],
            int(session_counts[index]),
            round(operator_revenue[index], 2),
            round(revenue_per_session[index], 2)
        ])

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", newline="", encoding="utf-8") as file:

        writer = csv.writer(file)
        writer.writerow(headers)
        writer.writerows(rows)

    print("\noperator performance checking  ")

    print("total operators:", operator_count)

    print("\noperator performance:")

    for index in sorted_indices:

        print(
            f"{unique_operators[index]} - "
            f"{session_counts[index]} sessions - "
            f"₹{operator_revenue[index]:.2f} revenue - "
            f"₹{revenue_per_session[index]:.2f} per session"
        )

    print("\ntotal sessions:", session_counts.sum())

    print("total revenue:", round(operator_revenue.sum(), 2))

    print("\ntotal operator report created:", output_path)

    return (
        unique_operators,
        session_counts,
        operator_revenue,
        revenue_per_session
    )

if __name__ == "__main__":

    connection = sqlite3.connect("output/ev.db")

    try:

        data = load_analysis_data(connection)

        # Part 4A 
        usage_matrix = analyze_hourly_usage(
            data,
            "output/hourly_usage.csv"
        )

        # Part 4B 
        charging_hours, utilisation = analyze_station_utilisation(
            data,
            "output/station_utilisation.csv"
        )

        # Part 4C 
        impossible_mask = detect_impossible_sessions(
            data,
            "output/impossible_sessions.csv"
        )

        # Part 4D 
        distance_matrix, nearest_distances, nearest_indices = (
            analyze_station_distances(
                data,
                "output/station_distances.csv"
            )
        )
        # Part 4E 
        nearby_stations = find_nearby_stations(
            data,
            latitude=13.0418,
            longitude=80.2341,
            radius_km=5,
            min_kw=0,
            output_path="output/nearby.geojson"
        )

        # Part 5A 
        daily_energy, trailing_average = analyze_daily_energy(
        data,
        "output/daily_energy.csv"
        )
        # Part 5B 
        weekday_matrix, weekday_totals, weekday_averages = (
        analyze_weekday_hour_usage(
        data,
        "output/weekday_hour_usage.csv"
        )
        )
        # Part 5C 
        (
            unique_operators,
            operator_sessions,
            operator_revenue,
            revenue_per_session
        ) = analyze_operator_performance(
            data,
            "output/operator_performance.csv"
        )
    finally:
        connection.close()