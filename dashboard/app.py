import os
import pandas as pd
import streamlit as st
import snowflake.connector

from dotenv import load_dotenv


# ============================================================
# PAGE CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="Smart City Traffic Intelligence",
    page_icon="🚦",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ============================================================
# LOAD ENVIRONMENT VARIABLES
# ============================================================

load_dotenv()


# ============================================================
# CUSTOM CSS
# ============================================================

st.markdown(
    """
    <style>

    .main-title {
        font-size: 38px;
        font-weight: 700;
        margin-bottom: 0px;
    }

    .subtitle {
        font-size: 17px;
        color: #666666;
        margin-top: 0px;
        margin-bottom: 25px;
    }

    .status-card {
        padding: 18px;
        border-radius: 12px;
        border: 1px solid #dddddd;
        text-align: center;
        margin-bottom: 10px;
    }

    .status-title {
        font-size: 14px;
        color: #666666;
    }

    .status-value {
        font-size: 28px;
        font-weight: 700;
        margin-top: 5px;
    }

    .section-title {
        font-size: 25px;
        font-weight: 650;
        margin-top: 15px;
        margin-bottom: 10px;
    }

    </style>
    """,
    unsafe_allow_html=True
)


# ============================================================
# SNOWFLAKE CONNECTION
# ============================================================

@st.cache_resource
def get_connection():

    return snowflake.connector.connect(
        account=os.getenv("SNOWFLAKE_ACCOUNT"),
        user=os.getenv("SNOWFLAKE_USER"),
        password=os.getenv("SNOWFLAKE_PASSWORD"),
        warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
        database=os.getenv("SNOWFLAKE_DATABASE"),
        schema=os.getenv("SNOWFLAKE_SCHEMA"),
        role=os.getenv("SNOWFLAKE_ROLE")
    )


# ============================================================
# QUERY FUNCTION
# ============================================================

@st.cache_data(ttl=30)
def run_query(query):

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute(query)

    rows = cursor.fetchall()

    columns = [column[0] for column in cursor.description]

    cursor.close()

    return pd.DataFrame(rows, columns=columns)


# ============================================================
# REFRESH FUNCTION
# ============================================================

if "refresh_counter" not in st.session_state:
    st.session_state.refresh_counter = 0


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.title("🚦 Traffic Intelligence")

st.sidebar.markdown(
    """
    ### System
    **City:** Hyderabad
    **Platform:** Real-Time Traffic Intelligence

    ### Technology
    - Python
    - Apache Kafka
    - Snowflake
    - Snowflake Streams & Tasks
    - Random Forest
    - Isolation Forest
    - Streamlit
    """
)

st.sidebar.divider()

if st.sidebar.button("🔄 Refresh Dashboard", width="stretch"):

    st.cache_data.clear()

    st.rerun()


st.sidebar.info(
    "Dashboard refresh interval: approximately 30 seconds."
)


# ============================================================
# HEADER
# ============================================================

st.markdown(
    '<div class="main-title">🚦 Real-Time Smart City Traffic Intelligence</div>',
    unsafe_allow_html=True
)

st.markdown(
    '<div class="subtitle">'
    'Hyderabad traffic monitoring, anomaly detection and 15-minute congestion prediction'
    '</div>',
    unsafe_allow_html=True
)


# ============================================================
# CURRENT TRAFFIC QUERY
# ============================================================

current_query = """

SELECT
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
    incident_flag,
    congestion_level

FROM TRAFFIC_DB.GOLD.FACT_TRAFFIC

QUALIFY ROW_NUMBER() OVER (
    PARTITION BY road_id
    ORDER BY event_timestamp DESC
) = 1

ORDER BY road_id

"""

current_df = run_query(current_query)


# ============================================================
# PREDICTION QUERY
# ============================================================

prediction_query = """

SELECT
    road_id,
    road_name,
    predicted_congestion_level,
    prediction_confidence,
    prediction_timestamp

FROM TRAFFIC_DB.GOLD.TRAFFIC_CONGESTION_PREDICTIONS

QUALIFY ROW_NUMBER() OVER (
    PARTITION BY road_id
    ORDER BY prediction_timestamp DESC
) = 1

ORDER BY road_id

"""

prediction_df = run_query(prediction_query)


# ============================================================
# ANOMALY QUERY
# ============================================================

anomaly_query = """

SELECT
    event_id,
    event_timestamp,
    road_id,
    road_name,
    vehicle_count,
    average_speed_kmh,
    occupancy_percent,
    anomaly_flag,
    anomaly_score

FROM TRAFFIC_DB.GOLD.TRAFFIC_ANOMALIES

WHERE anomaly_flag = 1

ORDER BY event_timestamp DESC

LIMIT 20

"""

anomaly_df = run_query(anomaly_query)

# Total anomaly count for KPI (separate from the 20-row display query)
anomaly_count_query = """
SELECT COUNT(*) AS TOTAL_ANOMALIES
FROM TRAFFIC_DB.GOLD.TRAFFIC_ANOMALIES
WHERE ANOMALY_FLAG = 1
"""

anomaly_count_df = run_query(anomaly_count_query)

total_anomalies = (
    int(anomaly_count_df["TOTAL_ANOMALIES"].iloc[0])
    if not anomaly_count_df.empty
    else 0
)


# ============================================================
# PIPELINE HEALTH QUERY
# ============================================================

pipeline_health_query = """
SELECT
    CHECKED_AT,
    RAW_EVENTS,
    STAGING_EVENTS,
    GOLD_EVENTS,
    ANOMALY_RESULTS,
    PREDICTIONS,
    LATEST_RAW_EVENT,
    LATEST_STAGING_EVENT,
    LATEST_GOLD_EVENT,
    LATEST_ANOMALY_DETECTION,
    LATEST_PREDICTION,
    RAW_TO_GOLD_LAG_SECONDS,
    PIPELINE_STATUS
FROM TRAFFIC_DB.GOLD.VW_PIPELINE_HEALTH
"""

pipeline_health_df = run_query(pipeline_health_query)


# ============================================================
# CHECK DATA
# ============================================================

if current_df.empty:

    st.warning(
        "No current traffic data is available in "
        "TRAFFIC_DB.GOLD.FACT_TRAFFIC."
    )

    st.stop()


# ============================================================
# KPI CALCULATIONS
# ============================================================

total_vehicles = int(
    current_df["VEHICLE_COUNT"].sum()
)

average_speed = round(
    current_df["AVERAGE_SPEED_KMH"].mean(),
    2
)

average_occupancy = round(
    current_df["OCCUPANCY_PERCENT"].mean(),
    2
)

congested_roads = int(
    current_df["CONGESTION_LEVEL"]
    .isin(["MEDIUM", "HIGH"])
    .sum()
)

high_congestion_roads = int(
    (current_df["CONGESTION_LEVEL"] == "HIGH")
    .sum()
)

anomaly_count_query = """
SELECT COUNT(*) AS TOTAL_ANOMALIES
FROM TRAFFIC_DB.GOLD.TRAFFIC_ANOMALIES
WHERE ANOMALY_FLAG = 1
"""

anomaly_count_df = run_query(anomaly_count_query)

total_anomalies = (
    int(anomaly_count_df["TOTAL_ANOMALIES"].iloc[0])
    if not anomaly_count_df.empty
    else 0
)


# ============================================================
# KPI SECTION
# ============================================================

st.markdown(
    '<div class="section-title">📊 Current Traffic Overview</div>',
    unsafe_allow_html=True
)

col1, col2, col3, col4, col5 = st.columns(5)


with col1:

    st.metric(
        "🚗 Total Vehicles",
        f"{total_vehicles:,}"
    )


with col2:

    st.metric(
        "⚡ Average Speed",
        f"{average_speed} km/h"
    )


with col3:

    st.metric(
        "📊 Avg Occupancy",
        f"{average_occupancy}%"
    )


with col4:

    st.metric(
        "🚦 Congested Roads",
        congested_roads
    )


with col5:

    st.metric(
        "🚨 Anomalies",
        total_anomalies
    )


st.divider()


# ============================================================
# PIPELINE HEALTH
# ============================================================

st.markdown(
    '<div class="section-title">⚙️ Pipeline Health</div>',
    unsafe_allow_html=True
)

if not pipeline_health_df.empty:

    health = pipeline_health_df.iloc[0]

    health_col1, health_col2, health_col3, health_col4, health_col5 = st.columns(5)

    with health_col1:
        st.metric(
            "RAW Events",
            f"{int(health['RAW_EVENTS']):,}"
        )

    with health_col2:
        st.metric(
            "STAGING Events",
            f"{int(health['STAGING_EVENTS']):,}"
        )

    with health_col3:
        st.metric(
            "GOLD Events",
            f"{int(health['GOLD_EVENTS']):,}"
        )

    with health_col4:
        st.metric(
            "Anomaly Results",
            f"{int(health['ANOMALY_RESULTS']):,}"
        )

    with health_col5:
        st.metric(
            "Predictions",
            f"{int(health['PREDICTIONS']):,}"
        )

    # Pipeline status and RAW → GOLD lag
    status = str(health["PIPELINE_STATUS"])
    lag_seconds = health["RAW_TO_GOLD_LAG_SECONDS"]

    if pd.isna(lag_seconds):
        lag_display = "N/A"
    else:
        # Lag represents how far GOLD is behind RAW.
        # Never display a negative lag to dashboard users.
        lag_seconds = max(0, int(lag_seconds))
        lag_display = f"{lag_seconds:,} sec"

    status_col, lag_col = st.columns(2)

    with status_col:
        if status == "HEALTHY":
            st.success(f"**Pipeline Status:** {status}")
        elif status == "WARNING":
            st.warning(f"**Pipeline Status:** {status}")
        else:
            st.error(f"**Pipeline Status:** {status}")

    with lag_col:
        st.info(
            f"**RAW → GOLD Lag:** {lag_display}"
        )

    st.write("### Pipeline Freshness")

    freshness_col1, freshness_col2, freshness_col3 = st.columns(3)

    with freshness_col1:

        st.info(
            f"**Latest RAW Event**\n\n"
            f"{health['LATEST_RAW_EVENT']}"
        )

    with freshness_col2:

        st.info(
            f"**Latest STAGING Event**\n\n"
            f"{health['LATEST_STAGING_EVENT']}"
        )

    with freshness_col3:

        st.info(
            f"**Latest GOLD Event**\n\n"
            f"{health['LATEST_GOLD_EVENT']}"
        )

    ml_col1, ml_col2 = st.columns(2)

    with ml_col1:

        st.info(
            f"**Latest Anomaly Detection**\n\n"
            f"{health['LATEST_ANOMALY_DETECTION']}"
        )

    with ml_col2:

        st.info(
            f"**Latest Prediction**\n\n"
            f"{health['LATEST_PREDICTION']}"
        )

else:

    st.warning("Pipeline health information is currently unavailable.")


st.divider()


# ============================================================
# ROAD STATUS
# ============================================================


# ============================================================
# ROAD STATUS
# ============================================================

st.markdown(
    '<div class="section-title">🛣️ Current Road Status</div>',
    unsafe_allow_html=True
)


road_display = current_df[
    [
        "ROAD_ID",
        "ROAD_NAME",
        "VEHICLE_COUNT",
        "AVERAGE_SPEED_KMH",
        "OCCUPANCY_PERCENT",
        "WEATHER_CONDITION",
        "INCIDENT_FLAG",
        "CONGESTION_LEVEL"
    ]
].copy()


road_display.columns = [
    "Road ID",
    "Road Name",
    "Vehicles",
    "Avg Speed (km/h)",
    "Occupancy (%)",
    "Weather",
    "Incident",
    "Congestion"
]


st.dataframe(
    road_display,
    width=1200,
    height=300,
    hide_index=True
)


# ============================================================
# STATUS SUMMARY
# ============================================================

st.markdown(
    '<div class="section-title">🚦 Congestion Status</div>',
    unsafe_allow_html=True
)


status_counts = (
    current_df["CONGESTION_LEVEL"]
    .value_counts()
    .to_dict()
)


status_col1, status_col2, status_col3 = st.columns(3)


with status_col1:

    st.markdown(
        f"""
        <div class="status-card">
            <div class="status-title">🟢 LOW</div>
            <div class="status-value">
                {status_counts.get("LOW", 0)}
            </div>
            <div class="status-title">Roads</div>
        </div>
        """,
        unsafe_allow_html=True
    )


with status_col2:

    st.markdown(
        f"""
        <div class="status-card">
            <div class="status-title">🟡 MEDIUM</div>
            <div class="status-value">
                {status_counts.get("MEDIUM", 0)}
            </div>
            <div class="status-title">Roads</div>
        </div>
        """,
        unsafe_allow_html=True
    )


with status_col3:

    st.markdown(
        f"""
        <div class="status-card">
            <div class="status-title">🔴 HIGH</div>
            <div class="status-value">
                {status_counts.get("HIGH", 0)}
            </div>
            <div class="status-title">Roads</div>
        </div>
        """,
        unsafe_allow_html=True
    )


# ============================================================
# TABS
# ============================================================

tab1, tab2, tab3, tab4 = st.tabs(
    [
        "🔮 15-Min Prediction",
        "🚨 Anomalies",
        "📈 Traffic Trends",
        "🗺️ Traffic Map"
    ]
)


# ============================================================
# TAB 1 — PREDICTION
# ============================================================

with tab1:

    st.markdown(
        '<div class="section-title">'
        '🔮 15-Minute Congestion Prediction'
        '</div>',
        unsafe_allow_html=True
    )

    if prediction_df.empty:

        st.warning(
            "No congestion predictions are currently available."
        )

    else:

        display_prediction = prediction_df.copy()

        display_prediction[
            "PREDICTION_CONFIDENCE"
        ] = (
            display_prediction[
                "PREDICTION_CONFIDENCE"
            ] * 100
        ).round(2)

        display_prediction[
            "PREDICTION_TIMESTAMP"
        ] = pd.to_datetime(
            display_prediction[
                "PREDICTION_TIMESTAMP"
            ]
        ).dt.strftime("%Y-%m-%d %H:%M:%S")

        display_prediction = display_prediction[
            [
                "ROAD_ID",
                "ROAD_NAME",
                "PREDICTED_CONGESTION_LEVEL",
                "PREDICTION_CONFIDENCE",
                "PREDICTION_TIMESTAMP"
            ]
        ]

        display_prediction.columns = [
            "Road ID",
            "Road Name",
            "Predicted Congestion",
            "Confidence (%)",
            "Prediction Time"
        ]

        st.dataframe(
            display_prediction,
            width=1200,
            height=300,
            hide_index=True
        )

        st.caption(
            "The Random Forest model predicts the expected "
            "congestion class approximately 15 minutes ahead."
        )


# ============================================================
# TAB 2 — ANOMALIES
# ============================================================

with tab2:

    st.markdown(
        '<div class="section-title">'
        '🚨 Recent Traffic Anomalies'
        '</div>',
        unsafe_allow_html=True
    )

    if anomaly_df.empty:

        st.success(
            "No traffic anomalies detected."
        )

    else:

        display_anomalies = anomaly_df[
            [
                "EVENT_TIMESTAMP",
                "ROAD_ID",
                "ROAD_NAME",
                "VEHICLE_COUNT",
                "AVERAGE_SPEED_KMH",
                "OCCUPANCY_PERCENT",
                "ANOMALY_SCORE"
            ]
        ].copy()

        display_anomalies[
            "EVENT_TIMESTAMP"
        ] = pd.to_datetime(
            display_anomalies[
                "EVENT_TIMESTAMP"
            ]
        ).dt.strftime("%Y-%m-%d %H:%M:%S")

        display_anomalies.columns = [
            "Event Time",
            "Road ID",
            "Road Name",
            "Vehicles",
            "Avg Speed",
            "Occupancy (%)",
            "Anomaly Score"
        ]

        st.dataframe(
            display_anomalies,
            width=1200,
            height=450,
            hide_index=True
        )

        st.caption(
            "Isolation Forest identifies traffic observations "
            "that differ significantly from normal traffic patterns."
        )


# ============================================================
# TAB 3 — TRAFFIC TRENDS
# ============================================================

with tab3:

    st.markdown(
        '<div class="section-title">'
        '📈 Traffic Trends'
        '</div>',
        unsafe_allow_html=True
    )

    analytics_query = """

    SELECT
        event_timestamp,
        road_name,
        vehicle_count,
        average_speed_kmh,
        occupancy_percent

    FROM TRAFFIC_DB.GOLD.FACT_TRAFFIC

    WHERE event_timestamp >= (
        SELECT DATEADD(
            hour,
            -3,
            MAX(event_timestamp)
        )
        FROM TRAFFIC_DB.GOLD.FACT_TRAFFIC
    )

    ORDER BY event_timestamp

    """

    analytics_df = run_query(
        analytics_query
    )

    if analytics_df.empty:

        st.warning(
            "No traffic trend data is available."
        )

    else:

        analytics_df[
            "EVENT_TIMESTAMP"
        ] = pd.to_datetime(
            analytics_df[
                "EVENT_TIMESTAMP"
            ]
        )

        # --------------------------------------------
        # Vehicle Count
        # --------------------------------------------

        st.write("### 🚗 Vehicle Count Over Time")

        vehicle_chart = (
            analytics_df
            .set_index("EVENT_TIMESTAMP")
            .resample("5min")["VEHICLE_COUNT"]
            .sum()
            .to_frame(name="VEHICLE_COUNT")
        )

        st.line_chart(
            vehicle_chart,
            width="stretch"
        )

        # --------------------------------------------
        # Average Speed
        # --------------------------------------------

        st.write("### ⚡ Average Speed Over Time")

        speed_chart = (
            analytics_df
            .set_index("EVENT_TIMESTAMP")
            .resample("5min")["AVERAGE_SPEED_KMH"]
            .mean()
            .to_frame(name="AVERAGE_SPEED_KMH")
        )

        st.line_chart(
            speed_chart,
            width="stretch"
        )


# ============================================================
# TAB 4 — MAP
# ============================================================

with tab4:

    st.markdown(
        '<div class="section-title">'
        '🗺️ Hyderabad Traffic Road Segments'
        '</div>',
        unsafe_allow_html=True
    )

    map_data = current_df[
        [
            "LATITUDE",
            "LONGITUDE"
        ]
    ].copy()

    map_data.columns = [
        "latitude",
        "longitude"
    ]

    st.map(
        map_data,
        width="stretch"
    )

    st.caption(
        "Map shows the five project/simulation road segments "
        "used by the Smart City Traffic Intelligence platform."
    )


# ============================================================
# SYSTEM INFORMATION
# ============================================================

st.divider()

st.markdown(
    '<div class="section-title">⚙️ System Architecture</div>',
    unsafe_allow_html=True
)

architecture_col1, architecture_col2, architecture_col3, architecture_col4, architecture_col5 = st.columns(5)


with architecture_col1:
    st.info("🐍 Python\n\nTraffic Generation")


with architecture_col2:
    st.info("📨 Kafka\n\nReal-Time Streaming")


with architecture_col3:
    st.info("ℹ️ Snowflake\n\nData Platform")


with architecture_col4:
    st.info("🤖 ML\n\nAI Intelligence")


with architecture_col5:
    st.info("📊 Streamlit\n\nVisualization")


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    "Real-Time Smart City Traffic Intelligence Platform | "
    "Hyderabad | Kafka + Snowflake + Machine Learning + Streamlit"
)