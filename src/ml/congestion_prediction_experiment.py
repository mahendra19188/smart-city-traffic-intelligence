import os

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
# Normalize columns
# ==================================================

df.columns = df.columns.str.lower()

df["event_timestamp"] = pd.to_datetime(
    df["event_timestamp"]
)

df["incident_flag"] = (
    df["incident_flag"]
    .astype(int)
)

df = df.sort_values(
    "event_timestamp"
).reset_index(
    drop=True
)


print(
    f"Loaded {len(df)} training records."
)


# ==================================================
# Chronological split
# ==================================================

split_index = int(
    len(df) * 0.80
)

train_df = df.iloc[
    :split_index
].copy()

test_df = df.iloc[
    split_index:
].copy()


print(
    "\nTraining period:"
)

print(
    f"{train_df.event_timestamp.min()} "
    f"-> "
    f"{train_df.event_timestamp.max()}"
)

print(
    "\nTesting period:"
)

print(
    f"{test_df.event_timestamp.min()} "
    f"-> "
    f"{test_df.event_timestamp.max()}"
)


# ==================================================
# Build historical traffic baselines
#
# IMPORTANT:
# Baselines are calculated ONLY from the training
# period. This prevents future-data leakage.
# ==================================================

baseline = (
    train_df
    .groupby(
        [
            "road_id",
            "hour_of_day",
        ]
    )
    .agg(
        typical_vehicle_count=(
            "vehicle_count",
            "mean",
        ),

        typical_speed=(
            "average_speed_kmh",
            "mean",
        ),

        typical_occupancy=(
            "occupancy_percent",
            "mean",
        ),
    )
    .reset_index()
)


# ==================================================
# Add historical baseline features
# ==================================================

train_df = train_df.merge(
    baseline,
    on=[
        "road_id",
        "hour_of_day",
    ],
    how="left",
)

test_df = test_df.merge(
    baseline,
    on=[
        "road_id",
        "hour_of_day",
    ],
    how="left",
)


# ==================================================
# Calculate deviation from normal traffic
# ==================================================

for dataset in [
    train_df,
    test_df,
]:

    dataset[
        "vehicle_count_deviation"
    ] = (
        dataset["vehicle_count"]
        - dataset["typical_vehicle_count"]
    )

    dataset[
        "speed_deviation"
    ] = (
        dataset["average_speed_kmh"]
        - dataset["typical_speed"]
    )

    dataset[
        "occupancy_deviation"
    ] = (
        dataset["occupancy_percent"]
        - dataset["typical_occupancy"]
    )


# ==================================================
# Feature sets
# ==================================================

BASE_FEATURES = [
    "vehicle_count",
    "average_speed_kmh",
    "occupancy_percent",
    "rainfall_mm",
    "incident_flag",
    "hour_of_day",
    "day_of_week",
]


ENHANCED_FEATURES = BASE_FEATURES + [
    "typical_vehicle_count",
    "typical_speed",
    "typical_occupancy",
    "vehicle_count_deviation",
    "speed_deviation",
    "occupancy_deviation",
]


TARGET = "future_congestion_label"


X_train_base = train_df[
    BASE_FEATURES
]

X_test_base = test_df[
    BASE_FEATURES
]

X_train_enhanced = train_df[
    ENHANCED_FEATURES
]

X_test_enhanced = test_df[
    ENHANCED_FEATURES
]

y_train = train_df[
    TARGET
]

y_test = test_df[
    TARGET
]


# ==================================================
# Model evaluation helper
# ==================================================

def evaluate_model(
    model_name,
    X_train,
    X_test,
):

    print(
        "\n"
        + "=" * 60
    )

    print(
        model_name
    )

    print(
        "=" * 60
    )

    model = RandomForestClassifier(
        n_estimators=300,
        max_depth=14,
        min_samples_leaf=2,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1,
    )

    print(
        "\nTraining model..."
    )

    model.fit(
        X_train,
        y_train
    )

    predictions = model.predict(
        X_test
    )

    accuracy = accuracy_score(
        y_test,
        predictions
    )

    balanced_accuracy = (
        balanced_accuracy_score(
            y_test,
            predictions
        )
    )

    macro_f1 = f1_score(
        y_test,
        predictions,
        average="macro"
    )

    weighted_f1 = f1_score(
        y_test,
        predictions,
        average="weighted"
    )

    print(
        f"\nAccuracy          : "
        f"{accuracy:.4f}"
    )

    print(
        f"Balanced Accuracy : "
        f"{balanced_accuracy:.4f}"
    )

    print(
        f"Macro F1          : "
        f"{macro_f1:.4f}"
    )

    print(
        f"Weighted F1       : "
        f"{weighted_f1:.4f}"
    )

    print(
        "\nClassification Report:"
    )

    print(
        classification_report(
            y_test,
            predictions,
            target_names=[
                "LOW",
                "MEDIUM",
                "HIGH",
            ],
            digits=2,
            zero_division=0,
        )
    )

    print(
        "Confusion Matrix:"
    )

    print(
        confusion_matrix(
            y_test,
            predictions
        )
    )

    return model


# ==================================================
# Baseline model
# ==================================================

baseline_model = evaluate_model(
    "BASELINE MODEL",
    X_train_base,
    X_test_base,
)


# ==================================================
# Enhanced model
# ==================================================

enhanced_model = evaluate_model(
    "ENHANCED MODEL - ROAD/TIME TRAFFIC BASELINES",
    X_train_enhanced,
    X_test_enhanced,
)


# ==================================================
# Enhanced feature importance
# ==================================================

feature_importance = pd.DataFrame(
    {
        "feature": ENHANCED_FEATURES,
        "importance": (
            enhanced_model.feature_importances_
        ),
    }
).sort_values(
    "importance",
    ascending=False
)


print(
    "\n"
    + "=" * 60
)

print(
    "ENHANCED MODEL FEATURE IMPORTANCE"
)

print(
    "=" * 60
)

print(
    feature_importance.to_string(
        index=False
    )
)


# ==================================================
# Completion
# ==================================================

print(
    "\nExperiment completed successfully."
)

print(
    "No production model was overwritten."
)