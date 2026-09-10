import os
import sys
import joblib
import pandas as pd
import snowflake.connector
from dotenv import load_dotenv

# Add project root to Python path
PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../..")
)
sys.path.insert(0, PROJECT_ROOT)

load_dotenv()

MODEL_PATH = os.path.join(
    PROJECT_ROOT,
    "models",
    "traffic_anomaly_model.pkl"
)

# ---------------------------------------------------------
# Connect to Snowflake
# ---------------------------------------------------------
conn = snowflake.connector.connect(
    account=os.getenv("SNOWFLAKE_ACCOUNT"),
    user=os.getenv("SNOWFLAKE_USER"),
    password=os.getenv("SNOWFLAKE_PASSWORD"),
    warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
    database=os.getenv("SNOWFLAKE_DATABASE"),
    schema="GOLD",
    role=os.getenv("SNOWFLAKE_ROLE")
)

print("Connected to Snowflake successfully.")

# ---------------------------------------------------------
# Load NEW live traffic data from GOLD
# ---------------------------------------------------------
query = """
SELECT
    f.EVENT_ID,
    f.EVENT_TIMESTAMP,
    f.ROAD_ID,
    f.ROAD_NAME,
    f.VEHICLE_COUNT,
    f.AVERAGE_SPEED_KMH,
    f.OCCUPANCY_PERCENT,
    f.RAINFALL_MM,
    f.INCIDENT_FLAG
FROM TRAFFIC_DB.GOLD.FACT_TRAFFIC f
WHERE NOT EXISTS (
    SELECT 1
    FROM TRAFFIC_DB.GOLD.TRAFFIC_ANOMALIES a
    WHERE a.EVENT_ID = f.EVENT_ID
)
ORDER BY f.EVENT_TIMESTAMP
"""

df = pd.read_sql(query, conn)
df.columns = df.columns.str.lower()

loaded_records = len(df)

print(f"Loaded {loaded_records} new GOLD traffic records.")

if df.empty:
    print("No new traffic events to analyze.")
    conn.close()
    sys.exit(0)

# ---------------------------------------------------------
# Load existing Isolation Forest model
# ---------------------------------------------------------
model = joblib.load(MODEL_PATH)

print("Loaded anomaly model successfully.")

# ---------------------------------------------------------
# Prepare ML features
# ---------------------------------------------------------
features = [
    "vehicle_count",
    "average_speed_kmh",
    "occupancy_percent",
    "rainfall_mm"
]

X = df[features]

# ---------------------------------------------------------
# Run anomaly detection
# ---------------------------------------------------------
df["anomaly_flag"] = model.predict(X)

# Isolation Forest:
#   1  = normal
#  -1  = anomaly
#
# Convert to:
#   0 = normal
#   1 = anomaly
df["anomaly_flag"] = df["anomaly_flag"].map({
    1: 0,
    -1: 1
})

df["anomaly_score"] = model.decision_function(X)

anomalies_detected = int((df["anomaly_flag"] == 1).sum())
normal_events = int((df["anomaly_flag"] == 0).sum())

print("\nAnomaly detection summary:")
print(f"  Events analyzed       : {loaded_records}")
print(f"  Normal events         : {normal_events}")
print(f"  Anomalies detected    : {anomalies_detected}")

print("\nLatest anomaly detection results:")
print(
    df[
        [
            "event_id",
            "road_name",
            "vehicle_count",
            "average_speed_kmh",
            "occupancy_percent",
            "anomaly_flag",
            "anomaly_score"
        ]
    ].tail(10)
)

# ---------------------------------------------------------
# Insert anomaly results into Snowflake in one batch
# ---------------------------------------------------------
cursor = conn.cursor()

try:
    # Create a temporary table for this analysis batch
    cursor.execute("""
    CREATE OR REPLACE TEMPORARY TABLE TRAFFIC_ANOMALY_BATCH (
        EVENT_ID VARCHAR,
        EVENT_TIMESTAMP TIMESTAMP,
        ROAD_ID VARCHAR,
        ROAD_NAME VARCHAR,
        VEHICLE_COUNT INTEGER,
        AVERAGE_SPEED_KMH FLOAT,
        OCCUPANCY_PERCENT FLOAT,
        RAINFALL_MM FLOAT,
        INCIDENT_FLAG BOOLEAN,
        ANOMALY_FLAG INTEGER,
        ANOMALY_SCORE FLOAT
    )
    """)

    # -----------------------------------------------------
    # Prepare batch data
    # -----------------------------------------------------
    batch_data = []

    for _, row in df.iterrows():
        batch_data.append((
            row["event_id"],
            str(row["event_timestamp"]),
            row["road_id"],
            row["road_name"],
            int(row["vehicle_count"]),
            float(row["average_speed_kmh"]),
            float(row["occupancy_percent"]),
            float(row["rainfall_mm"]),
            bool(row["incident_flag"]),
            int(row["anomaly_flag"]),
            float(row["anomaly_score"])
        ))

    # -----------------------------------------------------
    # Load all results into temporary table
    # -----------------------------------------------------
    cursor.executemany("""
    INSERT INTO TRAFFIC_ANOMALY_BATCH (
        EVENT_ID,
        EVENT_TIMESTAMP,
        ROAD_ID,
        ROAD_NAME,
        VEHICLE_COUNT,
        AVERAGE_SPEED_KMH,
        OCCUPANCY_PERCENT,
        RAINFALL_MM,
        INCIDENT_FLAG,
        ANOMALY_FLAG,
        ANOMALY_SCORE
    )
    VALUES (
        %s,
        TO_TIMESTAMP(%s),
        %s,
        %s,
        %s,
        %s,
        %s,
        %s,
        %s,
        %s,
        %s
    )
    """, batch_data)

    # -----------------------------------------------------
    # Insert only events that do not already exist
    # -----------------------------------------------------
    cursor.execute("""
    INSERT INTO TRAFFIC_DB.GOLD.TRAFFIC_ANOMALIES (
        EVENT_ID,
        EVENT_TIMESTAMP,
        ROAD_ID,
        ROAD_NAME,
        VEHICLE_COUNT,
        AVERAGE_SPEED_KMH,
        OCCUPANCY_PERCENT,
        RAINFALL_MM,
        INCIDENT_FLAG,
        ANOMALY_FLAG,
        ANOMALY_SCORE
    )
    SELECT
        b.EVENT_ID,
        b.EVENT_TIMESTAMP,
        b.ROAD_ID,
        b.ROAD_NAME,
        b.VEHICLE_COUNT,
        b.AVERAGE_SPEED_KMH,
        b.OCCUPANCY_PERCENT,
        b.RAINFALL_MM,
        b.INCIDENT_FLAG,
        b.ANOMALY_FLAG,
        b.ANOMALY_SCORE
    FROM TRAFFIC_ANOMALY_BATCH b
    WHERE NOT EXISTS (
        SELECT 1
        FROM TRAFFIC_DB.GOLD.TRAFFIC_ANOMALIES a
        WHERE a.EVENT_ID = b.EVENT_ID
    )
    """)

    inserted = cursor.rowcount

    conn.commit()

except Exception:
    conn.rollback()
    raise

finally:
    cursor.close()
    conn.close()

# ---------------------------------------------------------
# Final pipeline summary
# ---------------------------------------------------------
print("\n========================================")
print("ANOMALY DETECTION SUMMARY")
print("========================================")
print(f"Gold events loaded       : {loaded_records}")
print(f"Events analyzed          : {loaded_records}")
print(f"Normal events            : {normal_events}")
print(f"Anomalies detected       : {anomalies_detected}")
print(f"Records inserted         : {inserted}")
print("Anomaly detection completed successfully!")