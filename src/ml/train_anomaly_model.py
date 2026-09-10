import os
import sys
import joblib
import pandas as pd
import snowflake.connector
from dotenv import load_dotenv
from sklearn.ensemble import IsolationForest

# ---------------------------------------------------------
# Project configuration
# ---------------------------------------------------------
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
    schema="RAW",
    role=os.getenv("SNOWFLAKE_ROLE")
)

print("Connected to Snowflake successfully.")

# ---------------------------------------------------------
# Load historical traffic data
# ---------------------------------------------------------
query = """
SELECT
    EVENT_ID,
    EVENT_TIMESTAMP,
    ROAD_ID,
    ROAD_NAME,
    VEHICLE_COUNT,
    AVERAGE_SPEED_KMH,
    OCCUPANCY_PERCENT,
    RAINFALL_MM,
    INCIDENT_FLAG
FROM TRAFFIC_DB.RAW.HISTORICAL_TRAFFIC_EVENTS
ORDER BY EVENT_TIMESTAMP
"""

df = pd.read_sql(query, conn)
df.columns = df.columns.str.lower()

print(f"Loaded {len(df)} historical traffic records.")

if df.empty:
    print("No historical traffic data found.")
    conn.close()
    sys.exit(1)

# ---------------------------------------------------------
# Prepare ML features
# ---------------------------------------------------------
features = [
    "vehicle_count",
    "average_speed_kmh",
    "occupancy_percent",
    "rainfall_mm"
]

X = df[features].copy()

# Ensure numeric values
for column in features:
    X[column] = pd.to_numeric(X[column], errors="coerce")

# Remove incomplete rows
valid_mask = X.notnull().all(axis=1)

X = X.loc[valid_mask]

print(f"Training records after cleaning: {len(X)}")

# ---------------------------------------------------------
# Train Isolation Forest
# ---------------------------------------------------------
model = IsolationForest(
    n_estimators=200,
    contamination=0.05,
    random_state=42,
    n_jobs=-1
)

model.fit(X)

print("Isolation Forest model trained successfully.")

# ---------------------------------------------------------
# Validate anomaly distribution
# ---------------------------------------------------------
predictions = model.predict(X)

anomaly_count = (predictions == -1).sum()
normal_count = (predictions == 1).sum()
total_count = len(predictions)

anomaly_percentage = (
    anomaly_count / total_count * 100
)

normal_percentage = (
    normal_count / total_count * 100
)

print("\nTraining data anomaly distribution:")
print(f"Normal records : {normal_count} ({normal_percentage:.2f}%)")
print(f"Anomalies      : {anomaly_count} ({anomaly_percentage:.2f}%)")
print(f"Total records  : {total_count}")

# ---------------------------------------------------------
# Save trained model
# ---------------------------------------------------------
os.makedirs(
    os.path.dirname(MODEL_PATH),
    exist_ok=True
)

joblib.dump(model, MODEL_PATH)

print("\nModel saved successfully:")
print(MODEL_PATH)

conn.close()

print("\nAnomaly model training completed successfully!")