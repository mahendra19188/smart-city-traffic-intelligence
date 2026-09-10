import csv
import os
import random
import uuid
from datetime import datetime, timedelta


# ==================================================
# Configuration
# ==================================================

OUTPUT_DIR = "data/raw"

OUTPUT_FILE = os.path.join(
    OUTPUT_DIR,
    "historical_traffic_events.csv"
)

DAYS = 3
INTERVAL_MINUTES = 1


# ==================================================
# Hyderabad project road segments
# ==================================================

ROADS = [
    {
        "road_id": "ROAD_001",
        "road_name": "Gachibowli Main Road",
        "latitude": 17.4401,
        "longitude": 78.3489,
        "base_vehicle_count": 110,
        "base_speed": 48,
        "base_occupancy": 35,
    },
    {
        "road_id": "ROAD_002",
        "road_name": "Hitech City Road",
        "latitude": 17.4483,
        "longitude": 78.3915,
        "base_vehicle_count": 125,
        "base_speed": 45,
        "base_occupancy": 40,
    },
    {
        "road_id": "ROAD_003",
        "road_name": "Madhapur Road",
        "latitude": 17.4486,
        "longitude": 78.3908,
        "base_vehicle_count": 105,
        "base_speed": 47,
        "base_occupancy": 34,
    },
    {
        "road_id": "ROAD_004",
        "road_name": "Kondapur Road",
        "latitude": 17.4584,
        "longitude": 78.3697,
        "base_vehicle_count": 100,
        "base_speed": 49,
        "base_occupancy": 32,
    },
    {
        "road_id": "ROAD_005",
        "road_name": "Airport Route",
        "latitude": 17.2403,
        "longitude": 78.4294,
        "base_vehicle_count": 95,
        "base_speed": 52,
        "base_occupancy": 30,
    },
]


# ==================================================
# Weather conditions
# ==================================================

WEATHER_OPTIONS = [
    "Clear",
    "Cloudy",
    "Rain",
]


# ==================================================
# Generate one traffic event
# ==================================================

def generate_event(timestamp, road):

    hour = timestamp.hour

    vehicle_count = road["base_vehicle_count"]
    speed = road["base_speed"]
    occupancy = road["base_occupancy"]

    # --------------------------------------------------
    # Morning peak
    # --------------------------------------------------

    if 7 <= hour < 10:

        vehicle_count *= random.uniform(
            1.55,
            2.20
        )

        speed *= random.uniform(
            0.50,
            0.78
        )

        occupancy *= random.uniform(
            1.55,
            2.10
        )

    # --------------------------------------------------
    # Evening peak
    # --------------------------------------------------

    elif 17 <= hour < 21:

        vehicle_count *= random.uniform(
            1.65,
            2.35
        )

        speed *= random.uniform(
            0.40,
            0.72
        )

        occupancy *= random.uniform(
            1.65,
            2.25
        )

    # --------------------------------------------------
    # Night
    # --------------------------------------------------

    elif hour >= 22 or hour < 6:

        vehicle_count *= random.uniform(
            0.30,
            0.60
        )

        speed *= random.uniform(
            1.05,
            1.20
        )

        occupancy *= random.uniform(
            0.35,
            0.65
        )

    # --------------------------------------------------
    # Normal daytime
    # --------------------------------------------------

    else:

        vehicle_count *= random.uniform(
            0.80,
            1.20
        )

        speed *= random.uniform(
            0.85,
            1.10
        )

        occupancy *= random.uniform(
            0.80,
            1.20
        )

    # ==================================================
    # Weather
    # ==================================================

    weather = random.choices(
        WEATHER_OPTIONS,
        weights=[
            65,   # Clear
            20,   # Cloudy
            15    # Rain
        ],
        k=1
    )[0]

    rainfall = 0.0

    # --------------------------------------------------
    # Rain
    # --------------------------------------------------

    if weather == "Rain":

        rainfall = random.uniform(
            3,
            20
        )

        speed *= random.uniform(
            0.55,
            0.80
        )

        occupancy *= random.uniform(
            1.15,
            1.40
        )

        vehicle_count *= random.uniform(
            1.00,
            1.15
        )

    # --------------------------------------------------
    # Cloudy
    # --------------------------------------------------

    elif weather == "Cloudy":

        rainfall = random.uniform(
            0,
            2
        )

    # ==================================================
    # Traffic incident
    # ==================================================

    incident_flag = random.random() < 0.04

    if incident_flag:

        vehicle_count *= random.uniform(
            1.20,
            1.55
        )

        speed *= random.uniform(
            0.25,
            0.50
        )

        occupancy *= random.uniform(
            1.35,
            1.70
        )

    # ==================================================
    # High congestion event
    #
    # Additional realistic traffic disruption.
    # This is intentionally more likely during peak
    # hours and bad weather.
    # ==================================================

    is_peak_hour = (
        7 <= hour < 10
        or
        17 <= hour < 21
    )

    heavy_traffic_event = False

    if is_peak_hour:

        # Higher probability during peak traffic.
        heavy_traffic_event = (
            random.random() < 0.16
        )

    else:

        # Occasional congestion outside peak hours.
        heavy_traffic_event = (
            random.random() < 0.025
        )

    if heavy_traffic_event:

        vehicle_count *= random.uniform(
            1.25,
            1.55
        )

        speed *= random.uniform(
            0.35,
            0.55
        )

        occupancy *= random.uniform(
            1.25,
            1.55
        )

    # ==================================================
    # Natural randomness
    # ==================================================

    vehicle_count += random.uniform(
        -15,
        15
    )

    speed += random.uniform(
        -5,
        5
    )

    occupancy += random.uniform(
        -5,
        5
    )

    # ==================================================
    # Keep values realistic
    # ==================================================

    vehicle_count = max(
        10,
        int(vehicle_count)
    )

    speed = max(
        5,
        min(
            70,
            round(speed, 2)
        )
    )

    occupancy = max(
        5,
        min(
            98,
            round(occupancy, 2)
        )
    )

    temperature = random.uniform(
        24,
        34
    )

    # ==================================================
    # Return event
    # ==================================================

    return {
        "event_id": (
            f"EVT{uuid.uuid4().hex[:8].upper()}"
        ),

        "event_timestamp": timestamp.strftime(
            "%Y-%m-%d %H:%M:%S"
        ),

        "road_id": road["road_id"],

        "road_name": road["road_name"],

        "city": "Hyderabad",

        "latitude": road["latitude"],

        "longitude": road["longitude"],

        "vehicle_count": vehicle_count,

        "average_speed_kmh": speed,

        "occupancy_percent": occupancy,

        "weather_condition": weather,

        "temperature_c": round(
            temperature,
            2
        ),

        "rainfall_mm": round(
            rainfall,
            2
        ),

        "incident_flag": incident_flag,
    }


# ==================================================
# Main generator
# ==================================================

def main():

    os.makedirs(
        OUTPUT_DIR,
        exist_ok=True
    )

    start_time = datetime(
        2026,
        9,
        1,
        0,
        0,
        0
    )

    end_time = (
        start_time
        + timedelta(days=DAYS)
    )

    current_time = start_time

    records = []

    print(
        "Generating historical traffic data..."
    )

    print(
        f"Start time : {start_time}"
    )

    print(
        f"End time   : {end_time}"
    )

    print(
        f"Roads      : {len(ROADS)}"
    )

    print(
        "Interval   : "
        f"{INTERVAL_MINUTES} minute(s)"
    )

    while current_time < end_time:

        for road in ROADS:

            event = generate_event(
                current_time,
                road
            )

            records.append(event)

        current_time += timedelta(
            minutes=INTERVAL_MINUTES
        )

    # ==================================================
    # Save CSV
    # ==================================================

    fieldnames = [
        "event_id",
        "event_timestamp",
        "road_id",
        "road_name",
        "city",
        "latitude",
        "longitude",
        "vehicle_count",
        "average_speed_kmh",
        "occupancy_percent",
        "weather_condition",
        "temperature_c",
        "rainfall_mm",
        "incident_flag",
    ]

    with open(
        OUTPUT_FILE,
        "w",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames
        )

        writer.writeheader()

        writer.writerows(records)

    print(
        "\nHistorical traffic generation completed."
    )

    print(
        f"Total records generated: "
        f"{len(records)}"
    )

    print(
        "Output file:"
    )

    print(
        OUTPUT_FILE
    )


# ==================================================
# Entry point
# ==================================================

if __name__ == "__main__":
    main()