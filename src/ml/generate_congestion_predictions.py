import os
import uuid
import joblib
import pandas as pd
import snowflake.connector

from datetime import datetime
from dotenv import load_dotenv


# ==================================================
# 1. Load environment variables
# ==================================================

load_dotenv()


# ==================================================
# 2. Configuration
# ==================================================

MODEL_PATH = (
    "models/congestion_prediction_model.pkl"
)

BASELINE_TABLE = (
    "TRAFFIC_DB.GOLD.TRAFFIC_ROAD_HOURLY_BASELINES"
)

PREDICTION_TABLE = (
    "TRAFFIC_DB.GOLD.TRAFFIC_CONGESTION_PREDICTIONS"
)


# ==================================================
# 3. Load trained Random Forest model
# ==================================================

model = joblib.load(
    MODEL_PATH
)

print(
    "Enhanced Random Forest model loaded successfully."
)


# ==================================================
# 4. Connect to Snowflake
# ==================================================

conn = snowflake.connector.connect(
    account=os.getenv("SNOWFLAKE_ACCOUNT"),
    user=os.getenv("SNOWFLAKE_USER"),
    password=os.getenv("SNOWFLAKE_PASSWORD"),
    warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
    database=os.getenv("SNOWFLAKE_DATABASE"),
    schema=os.getenv("SNOWFLAKE_SCHEMA"),
    role=os.getenv("SNOWFLAKE_ROLE")
)

print(
    "Connected to Snowflake successfully."
)


# ==================================================
# 5. Read latest unpredicted traffic event
#    for each road
#
#    Also join road/hour traffic baselines.
# ==================================================

query = f"""
SELECT
    f.EVENT_ID,
    f.EVENT_TIMESTAMP,
    f.ROAD_ID,
    f.ROAD_NAME,
    f.VEHICLE_COUNT,
    f.AVERAGE_SPEED_KMH,
    f.OCCUPANCY_PERCENT,
    f.RAINFALL_MM,
    f.INCIDENT_FLAG,

    EXTRACT(
        HOUR FROM f.EVENT_TIMESTAMP
    ) AS HOUR_OF_DAY,

    DAYOFWEEK(
        f.EVENT_TIMESTAMP
    ) AS DAY_OF_WEEK,

    b.TYPICAL_VEHICLE_COUNT,
    b.TYPICAL_SPEED,
    b.TYPICAL_OCCUPANCY

FROM TRAFFIC_DB.GOLD.FACT_TRAFFIC f

LEFT JOIN {BASELINE_TABLE} b
    ON f.ROAD_ID = b.ROAD_ID
    AND EXTRACT(
        HOUR FROM f.EVENT_TIMESTAMP
    ) = b.HOUR_OF_DAY

WHERE NOT EXISTS (

    SELECT 1

    FROM {PREDICTION_TABLE} p

    WHERE p.SOURCE_EVENT_ID = f.EVENT_ID
)

QUALIFY ROW_NUMBER() OVER (
    PARTITION BY f.ROAD_ID
    ORDER BY f.EVENT_TIMESTAMP DESC
) = 1

ORDER BY f.ROAD_ID
"""


df = pd.read_sql(
    query,
    conn
)


# ==================================================
# 6. Normalize column names
# ==================================================

df.columns = (
    df.columns.str.lower()
)

loaded_records = len(df)

print(
    f"Loaded {loaded_records} new traffic records "
    "for prediction."
)


# ==================================================
# 7. Handle no new traffic events
# ==================================================

if df.empty:

    print(
        "No new traffic events available "
        "for prediction."
    )

    conn.close()

    raise SystemExit(0)


# ==================================================
# 8. Validate baseline availability
# ==================================================

baseline_columns = [
    "typical_vehicle_count",
    "typical_speed",
    "typical_occupancy",
]


missing_baseline_rows = df[
    df[baseline_columns]
    .isnull()
    .any(axis=1)
]


if not missing_baseline_rows.empty:

    print(
        "\nWARNING:"
    )

    print(
        f"{len(missing_baseline_rows)} traffic "
        "records do not have matching road/hour "
        "baseline values."
    )

    print(
        missing_baseline_rows[
            [
                "event_id",
                "road_id",
                "hour_of_day",
            ]
        ].to_string(
            index=False
        )
    )

    conn.close()

    raise ValueError(
        "Missing traffic baseline values. "
        "Prediction stopped to prevent "
        "invalid model inputs."
    )


# ==================================================
# 9. Calculate deviation features
# ==================================================

df[
    "vehicle_count_deviation"
] = (
    df["vehicle_count"]
    - df["typical_vehicle_count"]
)


df[
    "speed_deviation"
] = (
    df["average_speed_kmh"]
    - df["typical_speed"]
)


df[
    "occupancy_deviation"
] = (
    df["occupancy_percent"]
    - df["typical_occupancy"]
)


# ==================================================
# 10. Prepare model features
#
#     IMPORTANT:
#     These features MUST match the
#     production model training order.
# ==================================================

features = [
    "vehicle_count",
    "average_speed_kmh",
    "occupancy_percent",
    "rainfall_mm",
    "incident_flag",
    "hour_of_day",
    "day_of_week",

    "typical_vehicle_count",
    "typical_speed",
    "typical_occupancy",

    "vehicle_count_deviation",
    "speed_deviation",
    "occupancy_deviation",
]


X = df[
    features
].copy()


# ==================================================
# 11. Convert data types
# ==================================================

X["incident_flag"] = (
    X["incident_flag"]
    .astype(int)
)


# ==================================================
# 12. Generate predictions
# ==================================================

predictions = model.predict(
    X
)


prediction_probabilities = (
    model.predict_proba(X)
)


confidence_scores = (
    prediction_probabilities.max(
        axis=1
    )
)


# ==================================================
# 13. Convert prediction labels
# ==================================================

def congestion_level(label):

    if label == 0:
        return "LOW"

    elif label == 1:
        return "MEDIUM"

    else:
        return "HIGH"


df[
    "predicted_congestion_level"
] = [
    congestion_level(label)
    for label in predictions
]


df[
    "prediction_confidence"
] = confidence_scores


# ==================================================
# 14. Prediction summary before insert
# ==================================================

prediction_distribution = (
    df["predicted_congestion_level"]
    .value_counts()
    .to_dict()
)

high_predictions = prediction_distribution.get(
    "HIGH",
    0
)

medium_predictions = prediction_distribution.get(
    "MEDIUM",
    0
)

low_predictions = prediction_distribution.get(
    "LOW",
    0
)

print("\nPrediction generation summary:")
print(
    f"  Events selected        : {loaded_records}"
)
print(
    f"  LOW predictions        : {low_predictions}"
)
print(
    f"  MEDIUM predictions     : {medium_predictions}"
)
print(
    f"  HIGH predictions       : {high_predictions}"
)


# ==================================================
# 15. Generate prediction timestamp
# ==================================================

prediction_time = datetime.now()


# ==================================================
# 16. Prepare records
# ==================================================

records = []


for _, row in df.iterrows():

    records.append({

        "prediction_id":
            str(uuid.uuid4()),

        "prediction_timestamp":
            prediction_time.strftime(
                "%Y-%m-%d %H:%M:%S"
            ),

        "source_event_id":
            row["event_id"],

        "road_id":
            row["road_id"],

        "road_name":
            row["road_name"],

        "vehicle_count":
            int(
                row["vehicle_count"]
            ),

        "average_speed_kmh":
            float(
                row["average_speed_kmh"]
            ),

        "occupancy_percent":
            float(
                row["occupancy_percent"]
            ),

        "rainfall_mm":
            float(
                row["rainfall_mm"]
            ),

        "incident_flag":
            bool(
                row["incident_flag"]
            ),

        "hour_of_day":
            int(
                row["hour_of_day"]
            ),

        "day_of_week":
            int(
                row["day_of_week"]
            ),

        "predicted_congestion_level":
            row[
                "predicted_congestion_level"
            ],

        "prediction_confidence":
            float(
                row["prediction_confidence"]
            ),
    })


# ==================================================
# 17. Insert predictions into Snowflake
# ==================================================

insert_sql = f"""
INSERT INTO {PREDICTION_TABLE} (

    prediction_id,
    prediction_timestamp,
    source_event_id,
    road_id,
    road_name,

    vehicle_count,
    average_speed_kmh,
    occupancy_percent,
    rainfall_mm,
    incident_flag,

    hour_of_day,
    day_of_week,

    predicted_congestion_level,
    prediction_confidence
)

SELECT

    %(prediction_id)s,

    TO_TIMESTAMP(
        %(prediction_timestamp)s
    ),

    %(source_event_id)s,

    %(road_id)s,

    %(road_name)s,

    %(vehicle_count)s,

    %(average_speed_kmh)s,

    %(occupancy_percent)s,

    %(rainfall_mm)s,

    %(incident_flag)s,

    %(hour_of_day)s,

    %(day_of_week)s,

    %(predicted_congestion_level)s,

    %(prediction_confidence)s

WHERE NOT EXISTS (

    SELECT 1

    FROM {PREDICTION_TABLE} p

    WHERE p.SOURCE_EVENT_ID =
        %(source_event_id)s
)
"""


cursor = conn.cursor()

inserted_count = 0
duplicate_count = 0


try:

    for record in records:

        cursor.execute(
            insert_sql,
            record
        )

        rows_affected = cursor.rowcount

        if rows_affected == 1:
            inserted_count += 1
        else:
            duplicate_count += 1

    conn.commit()

except Exception:

    conn.rollback()

    raise

finally:

    cursor.close()
    conn.close()


# ==================================================
# 18. Display prediction results
# ==================================================

print(
    f"\nNew predictions inserted: "
    f"{inserted_count}"
)

print(
    f"Duplicate records skipped: "
    f"{duplicate_count}"
)


print(
    "\n========================================"
)

print(
    "15-MINUTE CONGESTION PREDICTIONS"
)

print(
    "========================================"
)


display_columns = [
    "event_id",
    "road_id",
    "road_name",
    "predicted_congestion_level",
    "prediction_confidence",
]


print(
    df[
        display_columns
    ].to_string(
        index=False
    )
)


print(
    "\n========================================"
)

print(
    "CONGESTION PREDICTION SUMMARY"
)

print(
    "========================================"
)

print(
    f"Events selected        : {loaded_records}"
)

print(
    f"Predictions generated  : {len(predictions)}"
)

print(
    f"LOW predictions        : {low_predictions}"
)

print(
    f"MEDIUM predictions     : {medium_predictions}"
)

print(
    f"HIGH predictions       : {high_predictions}"
)

print(
    f"Records inserted       : {inserted_count}"
)

print(
    f"Duplicates skipped     : {duplicate_count}"
)


print(
    "\nPredictions saved to Snowflake successfully."
)


print(
    f"Table: {PREDICTION_TABLE}"
)


print(
    "\nEnhanced congestion prediction "
    "pipeline completed successfully!"
)