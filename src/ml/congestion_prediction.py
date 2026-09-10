import os

import joblib
import pandas as pd
import snowflake.connector

from dotenv import load_dotenv

from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
)


# ==================================================
# Load environment variables
# ==================================================

load_dotenv()


# ==================================================
# Configuration
# ==================================================

MODEL_DIR = "models"

MODEL_FILE = os.path.join(
    MODEL_DIR,
    "congestion_prediction_model.pkl"
)

TABLE_NAME = (
    "TRAFFIC_DB.GOLD.TRAFFIC_PREDICTION_TRAINING"
)


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
# Load training data
# ==================================================

query = f"""
SELECT
    EVENT_TIMESTAMP,
    ROAD_ID,
    VEHICLE_COUNT,
    AVERAGE_SPEED_KMH,
    OCCUPANCY_PERCENT,
    RAINFALL_MM,
    INCIDENT_FLAG,
    HOUR_OF_DAY,
    DAY_OF_WEEK,
    FUTURE_CONGESTION_LABEL
FROM {TABLE_NAME}
ORDER BY EVENT_TIMESTAMP
"""

df = pd.read_sql(
    query,
    conn
)

conn.close()


# ==================================================
# Normalize column names
# ==================================================

df.columns = df.columns.str.lower()

print(
    f"Loaded {len(df)} training records."
)


# ==================================================
# Data preparation
# ==================================================

df["event_timestamp"] = pd.to_datetime(
    df["event_timestamp"]
)

df["incident_flag"] = (
    df["incident_flag"]
    .astype(int)
)


# ==================================================
# Sort chronologically
# ==================================================

df = df.sort_values(
    "event_timestamp"
).reset_index(
    drop=True
)


# ==================================================
# Feature selection
# ==================================================

FEATURES = [
    "vehicle_count",
    "average_speed_kmh",
    "occupancy_percent",
    "rainfall_mm",
    "incident_flag",
    "hour_of_day",
    "day_of_week",
]

TARGET = "future_congestion_label"


X = df[FEATURES]

y = df[TARGET]


# ==================================================
# Chronological train/test split
#
# First 80%  -> training
# Last 20%   -> testing
#
# This simulates:
# "Train on past traffic -> predict future traffic"
# ==================================================

split_index = int(
    len(df) * 0.80
)


X_train = X.iloc[
    :split_index
]

X_test = X.iloc[
    split_index:
]

y_train = y.iloc[
    :split_index
]

y_test = y.iloc[
    split_index:
]


train_timestamps = df[
    "event_timestamp"
].iloc[
    :split_index
]

test_timestamps = df[
    "event_timestamp"
].iloc[
    split_index:
]


print(
    f"\nTraining records: {len(X_train)}"
)

print(
    f"Testing records : {len(X_test)}"
)

print(
    "\nTraining period:"
)

print(
    f"{train_timestamps.min()} "
    f"-> "
    f"{train_timestamps.max()}"
)

print(
    "\nTesting period:"
)

print(
    f"{test_timestamps.min()} "
    f"-> "
    f"{test_timestamps.max()}"
)


# ==================================================
# Target distribution
# ==================================================

print(
    "\nTraining target distribution:"
)

print(
    y_train.value_counts()
    .sort_index()
)


print(
    "\nTesting target distribution:"
)

print(
    y_test.value_counts()
    .sort_index()
)


# ==================================================
# Random Forest model
# ==================================================

model = RandomForestClassifier(
    n_estimators=300,
    max_depth=14,
    min_samples_leaf=2,
    class_weight="balanced",
    random_state=42,
    n_jobs=-1,
)


print(
    "\nTraining Random Forest model..."
)

model.fit(
    X_train,
    y_train
)


# ==================================================
# Predictions
# ==================================================

y_pred = model.predict(
    X_test
)


# ==================================================
# Evaluation
# ==================================================

accuracy = accuracy_score(
    y_test,
    y_pred
)

balanced_accuracy = balanced_accuracy_score(
    y_test,
    y_pred
)

macro_f1 = f1_score(
    y_test,
    y_pred,
    average="macro"
)

weighted_f1 = f1_score(
    y_test,
    y_pred,
    average="weighted"
)


print(
    "\n" + "=" * 60
)

print(
    "CHRONOLOGICAL MODEL EVALUATION"
)

print(
    "=" * 60
)

print(
    f"Accuracy          : {accuracy:.4f}"
)

print(
    f"Balanced Accuracy : {balanced_accuracy:.4f}"
)

print(
    f"Macro F1          : {macro_f1:.4f}"
)

print(
    f"Weighted F1       : {weighted_f1:.4f}"
)


# ==================================================
# Classification report
# ==================================================

print(
    "\nClassification Report:"
)

print(
    classification_report(
        y_test,
        y_pred,
        target_names=[
            "LOW",
            "MEDIUM",
            "HIGH",
        ],
        digits=2,
        zero_division=0,
    )
)


# ==================================================
# Confusion matrix
# ==================================================

print(
    "Confusion Matrix:"
)

print(
    confusion_matrix(
        y_test,
        y_pred
    )
)


# ==================================================
# Feature importance
# ==================================================

feature_importance = pd.DataFrame(
    {
        "feature": FEATURES,
        "importance": model.feature_importances_,
    }
).sort_values(
    "importance",
    ascending=False
)


print(
    "\nFeature Importance:"
)

print(
    feature_importance.to_string(
        index=False
    )
)


# ==================================================
# Save model
# ==================================================

os.makedirs(
    MODEL_DIR,
    exist_ok=True
)

joblib.dump(
    model,
    MODEL_FILE
)


print(
    "\nModel saved successfully:"
)

print(
    MODEL_FILE
)


# ==================================================
# Completion
# ==================================================

print(
    "\nCongestion prediction model "
    "training completed successfully!"
)