import os

import pandas as pd
import snowflake.connector
from dotenv import load_dotenv


# ==================================================
# Load environment variables
# ==================================================

load_dotenv()


# ==================================================
# Configuration
# ==================================================

CSV_FILE = "data/raw/historical_traffic_events.csv"

TABLE_NAME = "TRAFFIC_DB.RAW.HISTORICAL_TRAFFIC_EVENTS"

BATCH_SIZE = 1000


# ==================================================
# Connect to Snowflake
# ==================================================

conn = snowflake.connector.connect(
    account=os.getenv("SNOWFLAKE_ACCOUNT"),
    user=os.getenv("SNOWFLAKE_USER"),
    password=os.getenv("SNOWFLAKE_PASSWORD"),
    warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
    database=os.getenv("SNOWFLAKE_DATABASE"),
    schema=os.getenv("SNOWFLAKE_SCHEMA"),
    role=os.getenv("SNOWFLAKE_ROLE"),
)

print("Connected to Snowflake successfully.")


# ==================================================
# Read CSV
# ==================================================

df = pd.read_csv(CSV_FILE)

print(f"Loaded {len(df)} records from CSV.")


# ==================================================
# Validate CSV
# ==================================================

expected_columns = [
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

missing_columns = [
    column
    for column in expected_columns
    if column not in df.columns
]

if missing_columns:
    raise ValueError(
        f"Missing columns in CSV: {missing_columns}"
    )


# ==================================================
# Convert data types
# ==================================================

df["event_timestamp"] = pd.to_datetime(
    df["event_timestamp"],
    errors="raise"
)

df["incident_flag"] = (
    df["incident_flag"]
    .astype(bool)
)


# ==================================================
# Convert timestamps to strings
# ==================================================

df["event_timestamp"] = (
    df["event_timestamp"]
    .dt.strftime("%Y-%m-%d %H:%M:%S")
)


# ==================================================
# Convert DataFrame to records
# ==================================================

records = df[
    expected_columns
].to_dict("records")


print(
    f"Prepared {len(records)} records for loading."
)


# ==================================================
# SQL
# ==================================================

insert_sql = f"""
INSERT INTO {TABLE_NAME} (
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
    TO_TIMESTAMP(%(event_timestamp)s),
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


# ==================================================
# Insert records
# ==================================================

cursor = conn.cursor()

total_inserted = 0

try:

    for start in range(
        0,
        len(records),
        BATCH_SIZE
    ):

        end = min(
            start + BATCH_SIZE,
            len(records)
        )

        batch = records[start:end]

        print(
            f"Loading records "
            f"{start + 1}-{end} "
            f"of {len(records)}..."
        )

        cursor.executemany(
            insert_sql,
            batch
        )

        conn.commit()

        total_inserted += len(batch)

        print(
            f"Committed batch successfully. "
            f"Total inserted: "
            f"{total_inserted}/{len(records)}"
        )

except Exception as error:

    conn.rollback()

    print(
        "\nERROR while loading historical data:"
    )

    print(error)

    raise

finally:

    cursor.close()
    conn.close()


# ==================================================
# Final result
# ==================================================

print(
    "\nHistorical traffic loading completed successfully!"
)

print(
    f"Total records inserted: {total_inserted}"
)