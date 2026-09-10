import random
import time
from datetime import datetime


ROADS = [
    {
        "road_id": "ROAD_001",
        "road_name": "Gachibowli Main Road",
        "latitude": 17.4401,
        "longitude": 78.3489
    },
    {
        "road_id": "ROAD_002",
        "road_name": "Hitech City Road",
        "latitude": 17.4435,
        "longitude": 78.3772
    },
    {
        "road_id": "ROAD_003",
        "road_name": "Madhapur Road",
        "latitude": 17.4483,
        "longitude": 78.3915
    },
    {
        "road_id": "ROAD_004",
        "road_name": "Kondapur Road",
        "latitude": 17.4580,
        "longitude": 78.3660
    },
    {
        "road_id": "ROAD_005",
        "road_name": "Airport Route",
        "latitude": 17.2403,
        "longitude": 78.4294
    }
]


def get_traffic_level():
    """
    Determine traffic level based on current hour.
    """

    hour = datetime.now().hour

    # Morning peak
    if 8 <= hour <= 10:
        return "HIGH"

    # Evening peak
    elif 17 <= hour <= 20:
        return "HIGH"

    # Midday
    elif 11 <= hour <= 16:
        return "MEDIUM"

    # Night / early morning
    else:
        return "LOW"


def generate_weather():
    """
    Generate realistic weather conditions.
    """

    weather_options = [
        "Sunny",
        "Cloudy",
        "Rain"
    ]

    weather = random.choices(
        weather_options,
        weights=[60, 25, 15]
    )[0]

    if weather == "Sunny":
        temperature = round(random.uniform(27, 34), 1)
        rainfall = 0.0

    elif weather == "Cloudy":
        temperature = round(random.uniform(25, 31), 1)
        rainfall = round(random.uniform(0, 1), 1)

    else:
        temperature = round(random.uniform(23, 29), 1)
        rainfall = round(random.uniform(1, 10), 1)

    return weather, temperature, rainfall


def generate_traffic_event():
    """
    Generate one realistic traffic event.
    """

    road = random.choice(ROADS)

    traffic_level = get_traffic_level()

    # Base values based on traffic level
    if traffic_level == "HIGH":
        vehicle_count = random.randint(150, 300)
        speed = random.uniform(15, 40)
        occupancy = random.uniform(65, 95)

    elif traffic_level == "MEDIUM":
        vehicle_count = random.randint(80, 180)
        speed = random.uniform(30, 55)
        occupancy = random.uniform(40, 70)

    else:
        vehicle_count = random.randint(30, 100)
        speed = random.uniform(45, 70)
        occupancy = random.uniform(15, 45)

    weather, temperature, rainfall = generate_weather()

    # Rain reduces speed
    if weather == "Rain":
        speed *= random.uniform(0.70, 0.90)

    # Random traffic incident
    incident_flag = random.random() < 0.05

    # Incident causes sudden congestion
    if incident_flag:
        vehicle_count += random.randint(30, 80)
        speed *= random.uniform(0.40, 0.65)
        occupancy = min(100, occupancy + random.uniform(10, 25))

    event = {
        "event_id": f"EVT{random.randint(100000, 999999)}",
        "event_timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "road_id": road["road_id"],
        "road_name": road["road_name"],
        "city": "Hyderabad",
        "latitude": road["latitude"],
        "longitude": road["longitude"],
        "vehicle_count": vehicle_count,
        "average_speed_kmh": round(speed, 2),
        "occupancy_percent": round(occupancy, 2),
        "weather_condition": weather,
        "temperature_c": temperature,
        "rainfall_mm": rainfall,
        "incident_flag": incident_flag
    }

    return event


if __name__ == "__main__":

    print("Smart City Traffic Event Generator")
    print("-----------------------------------")

    while True:

        event = generate_traffic_event()

        print(event)

        time.sleep(2)