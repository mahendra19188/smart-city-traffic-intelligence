import json
import os

import snowflake.connector
from dotenv import load_dotenv
from kafka import KafkaConsumer

load_dotenv()

# Kafka configuration
consumer = KafkaConsumer(
    "traffic-events",
    bootstrap_servers=["localhost:9092"],
    group_id="traffic-snowflake-consumer-v1",
    auto_offset_reset="latest",
    enable_auto_commit=True,
    value_deserializer=lambda value: json.loads(value.decode("utf-8"))
)

# Snowflake connection
conn = snowflake.connector.connect(
    account=os.getenv("SNOWFLAKE_ACCOUNT"),
    user=os.getenv("SNOWFLAKE_USER"),
    password=os.getenv("SNOWFLAKE_PASSWORD"),
    warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
    database=os.getenv("SNOWFLAKE_DATABASE"),
    schema=os.getenv("SNOWFLAKE_SCHEMA"),
    role=os.getenv("SNOWFLAKE_ROLE")
)

cursor = conn.cursor()

insert_sql = """
INSERT INTO TRAFFIC_DB.RAW.TRAFFIC_EVENTS (
    event_id,
    event_timestamp,
    road_id,
    road_name,
    city,
    latitude,
    longitude,
    vehicle_count,
    average_speed_kmh,
    occupancy_percent,
    weather_condition,
    temperature_c,
    rainfall_mm,
    incident_flag
)
VALUES (
    %(event_id)s,
    %(event_timestamp)s,
    %(road_id)s,
    %(road_name)s,
    %(city)s,
    %(latitude)s,
    %(longitude)s,
    %(vehicle_count)s,
    %(average_speed_kmh)s,
    %(occupancy_percent)s,
    %(weather_condition)s,
    %(temperature_c)s,
    %(rainfall_mm)s,
    %(incident_flag)s
)
"""

print("Kafka → Snowflake consumer started...")
print("Waiting for traffic events...")

try:
    for message in consumer:
        event = message.value

        cursor.execute(insert_sql, event)
        conn.commit()

        print(
            f"Inserted event: {event['event_id']} | "
            f"{event['road_name']} | "
            f"Vehicles: {event['vehicle_count']} | "
            f"Speed: {event['average_speed_kmh']} km/h"
        )

except KeyboardInterrupt:
    print("\nConsumer stopped.")

finally:
    cursor.close()
    conn.close()
    consumer.close()