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
    initial_sidebar_state="expanded",
)


# ============================================================
# ENVIRONMENT
# ============================================================

load_dotenv()


# ============================================================
# MODERN UI STYLES
# ============================================================

st.markdown(
    """
    <style>
        .block-container {
            padding-top: 1.2rem;
            padding-bottom: 2rem;
            max-width: 1500px;
        }

        .hero {
            padding: 1.2rem 1.4rem 1rem 1.4rem;
            border: 1px solid rgba(128,128,128,0.18);
            border-radius: 18px;
            background: linear-gradient(135deg, rgba(250,250,252,0.96), rgba(240,244,248,0.90));
            margin-bottom: 1rem;
        }

        .hero-kicker {
            font-size: 0.78rem;
            font-weight: 700;
            letter-spacing: 0.16em;
            text-transform: uppercase;
            opacity: 0.62;
            margin-bottom: 0.35rem;
        }

        .hero-title {
            font-size: 2.15rem;
            font-weight: 800;
            line-height: 1.08;
            margin: 0;
        }

        .hero-subtitle {
            font-size: 1rem;
            opacity: 0.68;
            margin-top: 0.5rem;
        }

        .live-pill {
            display: inline-block;
            padding: 0.35rem 0.75rem;
            border-radius: 999px;
            border: 1px solid rgba(40,160,90,0.28);
            background: rgba(40,160,90,0.10);
            font-size: 0.78rem;
            font-weight: 700;
        }

        .panel {
            padding: 1rem 1.05rem;
            border: 1px solid rgba(128,128,128,0.16);
            border-radius: 16px;
            background: rgba(255,255,255,0.72);
        }

        .panel-title {
            font-size: 1.12rem;
            font-weight: 750;
            margin-bottom: 0.65rem;
        }

        .panel-caption {
            font-size: 0.84rem;
            opacity: 0.62;
        }

        .risk-card {
            padding: 0.85rem 0.9rem;
            border-radius: 14px;
            border: 1px solid rgba(128,128,128,0.16);
            margin-bottom: 0.55rem;
        }

        .risk-road {
            font-weight: 750;
            font-size: 0.95rem;
        }

        .risk-meta {
            font-size: 0.80rem;
            opacity: 0.66;
            margin-top: 0.2rem;
        }

        .flow-box {
            text-align: center;
            padding: 0.9rem 0.5rem;
            border-radius: 14px;
            border: 1px solid rgba(128,128,128,0.16);
            min-height: 92px;
        }

        .flow-icon {
            font-size: 1.35rem;
        }

        .flow-title {
            font-weight: 750;
            font-size: 0.90rem;
            margin-top: 0.25rem;
        }

        .flow-caption {
            font-size: 0.73rem;
            opacity: 0.60;
        }

        .insight {
            padding: 0.75rem 0.9rem;
            border-left: 4px solid rgba(80,100,180,0.65);
            border-radius: 8px;
            background: rgba(80,100,180,0.06);
            margin-bottom: 0.55rem;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# SNOWFLAKE
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
        role=os.getenv("SNOWFLAKE_ROLE"),
    )


@st.cache_data(ttl=30)
def run_query(query):
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(query)
        rows = cursor.fetchall()
        columns = [column[0] for column in cursor.description]
        return pd.DataFrame(rows, columns=columns)
    finally:
        cursor.close()


# ============================================================
# SIDEBAR
# ============================================================

st.sidebar.title("🚦 Traffic Intelligence")
st.sidebar.caption("Operations dashboard")

st.sidebar.markdown(
    """
    **City:** Hyderabad  
    **Road segments:** 5  
    **Mode:** Near real-time
    """
)

if st.sidebar.button("🔄 Refresh Dashboard", width="stretch"):
    st.cache_data.clear()
    st.rerun()

st.sidebar.divider()

st.sidebar.markdown(
    """
    **Platform**

    Python · Kafka · Snowflake · dbt ·
    Isolation Forest · Random Forest · Streamlit
    """
)

st.sidebar.info("Data refresh uses a ~30 second cache. Use Refresh for an immediate update.")


# ============================================================
# DATA QUERIES
# ============================================================

current_query = """
SELECT
    f.EVENT_TIMESTAMP,
    f.ROAD_ID,
    f.ROAD_NAME,
    f.CITY,
    f.LATITUDE,
    f.LONGITUDE,
    f.VEHICLE_COUNT,
    f.AVERAGE_SPEED_KMH,
    f.OCCUPANCY_PERCENT,
    f.WEATHER_CONDITION,
    f.TEMPERATURE_C,
    f.RAINFALL_MM,
    f.INCIDENT_FLAG,
    f.CONGESTION_LEVEL,
    b.TYPICAL_VEHICLE_COUNT,
    b.TYPICAL_SPEED,
    b.TYPICAL_OCCUPANCY
FROM TRAFFIC_DB.GOLD.FACT_TRAFFIC f
LEFT JOIN TRAFFIC_DB.GOLD.TRAFFIC_ROAD_HOURLY_BASELINES b
    ON f.ROAD_ID = b.ROAD_ID
   AND EXTRACT(HOUR FROM f.EVENT_TIMESTAMP) = b.HOUR_OF_DAY
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY f.ROAD_ID
    ORDER BY f.EVENT_TIMESTAMP DESC
) = 1
ORDER BY f.ROAD_ID
"""

prediction_query = """
SELECT
    ROAD_ID,
    ROAD_NAME,
    PREDICTED_CONGESTION_LEVEL,
    PREDICTION_CONFIDENCE,
    PREDICTION_TIMESTAMP
FROM TRAFFIC_DB.GOLD.TRAFFIC_CONGESTION_PREDICTIONS
QUALIFY ROW_NUMBER() OVER (
    PARTITION BY ROAD_ID
    ORDER BY PREDICTION_TIMESTAMP DESC
) = 1
ORDER BY ROAD_ID
"""

anomaly_query = """
SELECT
    EVENT_TIMESTAMP,
    ROAD_ID,
    ROAD_NAME,
    VEHICLE_COUNT,
    AVERAGE_SPEED_KMH,
    OCCUPANCY_PERCENT,
    ANOMALY_SCORE
FROM TRAFFIC_DB.GOLD.TRAFFIC_ANOMALIES
WHERE ANOMALY_FLAG = 1
ORDER BY EVENT_TIMESTAMP DESC
LIMIT 20
"""

recent_anomaly_query = """
SELECT
    COUNT(*) AS RECENT_ANOMALIES
FROM TRAFFIC_DB.GOLD.TRAFFIC_ANOMALIES
WHERE ANOMALY_FLAG = 1
  AND EVENT_TIMESTAMP >= (
      SELECT DATEADD(
          minute,
          -30,
          MAX(EVENT_TIMESTAMP)
      )
      FROM TRAFFIC_DB.GOLD.FACT_TRAFFIC
  )
"""

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

current_df = run_query(current_query)
prediction_df = run_query(prediction_query)
anomaly_df = run_query(anomaly_query)
recent_anomaly_df = run_query(recent_anomaly_query)
pipeline_health_df = run_query(pipeline_health_query)


if current_df.empty:
    st.warning("No current traffic data is available in TRAFFIC_DB.GOLD.FACT_TRAFFIC.")
    st.stop()


# ============================================================
# NORMALIZE / DERIVED METRICS
# ============================================================

current_df["SPEED_DEVIATION"] = (
    current_df["AVERAGE_SPEED_KMH"] - current_df["TYPICAL_SPEED"]
)

current_df["VEHICLE_DEVIATION"] = (
    current_df["VEHICLE_COUNT"] - current_df["TYPICAL_VEHICLE_COUNT"]
)

current_df["OCCUPANCY_DEVIATION"] = (
    current_df["OCCUPANCY_PERCENT"] - current_df["TYPICAL_OCCUPANCY"]
)

severity_rank = {"LOW": 1, "MEDIUM": 2, "HIGH": 3}

current_df["SEVERITY_SCORE"] = (
    current_df["CONGESTION_LEVEL"].map(severity_rank).fillna(0)
    + (current_df["SPEED_DEVIATION"] < 0).astype(int) * 0.25
    + (current_df["OCCUPANCY_DEVIATION"] > 0).astype(int) * 0.20
)

total_vehicles = int(current_df["VEHICLE_COUNT"].sum())
average_speed = round(current_df["AVERAGE_SPEED_KMH"].mean(), 2)
average_occupancy = round(current_df["OCCUPANCY_PERCENT"].mean(), 2)

congested_roads = int(
    current_df["CONGESTION_LEVEL"].isin(["MEDIUM", "HIGH"]).sum()
)

high_congestion_roads = int(
    (current_df["CONGESTION_LEVEL"] == "HIGH").sum()
)

prediction_risk_roads = 0
if not prediction_df.empty:
    prediction_risk_roads = int(
        prediction_df["PREDICTED_CONGESTION_LEVEL"]
        .isin(["MEDIUM", "HIGH"])
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

if not recent_anomaly_df.empty:
    recent_anomalies = int(
        recent_anomaly_df["RECENT_ANOMALIES"].iloc[0]
    )
else:
    recent_anomalies = 0


# ============================================================
# HEADER
# ============================================================

latest_gold = current_df["EVENT_TIMESTAMP"].max()

st.markdown(
    f"""
    <div class="hero">
        <div class="hero-kicker">SMART CITY TRAFFIC INTELLIGENCE</div>
        <div style="display:flex;justify-content:space-between;gap:1rem;align-items:flex-start;flex-wrap:wrap;">
            <div>
                <div class="hero-title">Real-Time Mobility Operations</div>
                <div class="hero-subtitle">
                    Hyderabad · 5 project/simulation road segments · traffic, anomaly and 15-minute forecast intelligence
                </div>
            </div>
            <div style="text-align:right;">
                <span class="live-pill">● LIVE</span>
                <div class="panel-caption" style="margin-top:0.45rem;">
                    Latest GOLD event<br>{latest_gold}
                </div>
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# KPI ROW
# ============================================================

st.markdown("### 📊 Current Situation")

k1, k2, k3, k4, k5 = st.columns(5)

with k1:
    st.metric("🚗 Vehicles", f"{total_vehicles:,}", help="Sum of vehicles across the latest event for each monitored road.")

with k2:
    st.metric("⚡ Avg Speed", f"{average_speed} km/h")

with k3:
    st.metric("🛣️ Congested Roads", f"{congested_roads}/{len(current_df)}")

with k4:
    st.metric("🚨 Active Anomalies", f"{total_anomalies:,}", help="Traffic observations classified as anomalies by Isolation Forest.")

with k5:
    st.metric("🔮 15-Min Risk", f"{prediction_risk_roads}/{len(prediction_df)}" if not prediction_df.empty else "N/A")

st.divider()


# ============================================================
# TRAFFIC SITUATION + ROADS TO WATCH
# ============================================================

left, right = st.columns([1.05, 1.25])

with left:
    st.markdown(
        '<div class="panel"><div class="panel-title">🚦 Traffic Situation</div>',
        unsafe_allow_html=True,
    )

    status_counts = (
        current_df["CONGESTION_LEVEL"]
        .value_counts()
        .reindex(["LOW", "MEDIUM", "HIGH"], fill_value=0)
    )

    situation_df = status_counts.rename("Roads").to_frame()
    st.bar_chart(situation_df, horizontal=True, width="stretch")

    st.caption(
        f"{high_congestion_roads} road(s) currently classified HIGH · "
        f"{congested_roads} road(s) at MEDIUM/HIGH."
    )

    st.markdown("</div>", unsafe_allow_html=True)


with right:
    st.markdown(
        '<div class="panel"><div class="panel-title">👀 Roads to Watch</div>',
        unsafe_allow_html=True,
    )

    watch_df = (
        current_df[
            [
                "ROAD_NAME",
                "CONGESTION_LEVEL",
                "AVERAGE_SPEED_KMH",
                "SPEED_DEVIATION",
                "OCCUPANCY_PERCENT",
            ]
        ]
        .copy()
    )

    watch_df["SEVERITY_RANK"] = (
        watch_df["CONGESTION_LEVEL"]
        .map(severity_rank)
        .fillna(0)
    )

    watch_df = (
        watch_df
        .sort_values(
            ["SEVERITY_RANK", "SPEED_DEVIATION", "OCCUPANCY_PERCENT"],
            ascending=[False, True, False],
        )
        .head(5)
    )

    for _, row in watch_df.iterrows():
        st.markdown(
            f"""
            <div class="risk-card">
                <div class="risk-road">{row["ROAD_NAME"]} · {row["CONGESTION_LEVEL"]}</div>
                <div class="risk-meta">
                    Speed {row["AVERAGE_SPEED_KMH"]:.1f} km/h ·
                    Occupancy {row["OCCUPANCY_PERCENT"]:.1f}% ·
                    Δ speed vs baseline {row["SPEED_DEVIATION"]:+.1f} km/h
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("</div>", unsafe_allow_html=True)


# ============================================================
# PIPELINE HEALTH
# ============================================================

st.markdown("### ⚙️ Platform Health")

if not pipeline_health_df.empty:

    health = pipeline_health_df.iloc[0]
    status = str(health["PIPELINE_STATUS"])

    if pd.isna(health["RAW_TO_GOLD_LAG_SECONDS"]):
        lag_display = "N/A"
    else:
        lag_display = f"{max(0, int(health['RAW_TO_GOLD_LAG_SECONDS'])):,} sec"

    hp1, hp2, hp3, hp4, hp5 = st.columns(5)

    with hp1:
        st.metric("RAW", f"{int(health['RAW_EVENTS']):,}")

    with hp2:
        st.metric("STAGING", f"{int(health['STAGING_EVENTS']):,}")

    with hp3:
        st.metric("GOLD", f"{int(health['GOLD_EVENTS']):,}")

    with hp4:
        st.metric("Anomaly Results", f"{int(health['ANOMALY_RESULTS']):,}")

    with hp5:
        st.metric("Predictions", f"{int(health['PREDICTIONS']):,}")

    status_col, lag_col = st.columns(2)

    with status_col:
        if status == "HEALTHY":
            st.success(f"**Pipeline Status:** {status}")
        elif status == "WARNING":
            st.warning(f"**Pipeline Status:** {status}")
        else:
            st.error(f"**Pipeline Status:** {status}")

    with lag_col:
        st.info(f"**RAW → GOLD Lag:** {lag_display}")

    flow = st.columns(7)
    flow_items = [
        ("🐍", "Python", "Events"),
        ("📨", "Kafka", "Stream"),
        ("🧊", "RAW", "Landing"),
        ("⚙️", "STAGING", "Clean"),
        ("💎", "GOLD", "Curated"),
        ("🤖", "ML", "Inference"),
        ("📊", "Dashboard", "Insights"),
    ]

    for col, (icon, title, caption) in zip(flow, flow_items):
        with col:
            st.markdown(
                f"""
                <div class="flow-box">
                    <div class="flow-icon">{icon}</div>
                    <div class="flow-title">{title}</div>
                    <div class="flow-caption">{caption}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    f1, f2, f3, f4, f5 = st.columns(5)

    freshness_items = [
        ("RAW", health["LATEST_RAW_EVENT"]),
        ("STAGING", health["LATEST_STAGING_EVENT"]),
        ("GOLD", health["LATEST_GOLD_EVENT"]),
        ("Anomaly", health["LATEST_ANOMALY_DETECTION"]),
        ("Prediction", health["LATEST_PREDICTION"]),
    ]

    for col, (label, value) in zip([f1, f2, f3, f4, f5], freshness_items):
        with col:
            st.caption(label)
            st.write(value)

else:
    st.warning("Pipeline health information is currently unavailable.")


# ============================================================
# ROAD DETAILS
# ============================================================

st.divider()
st.markdown("### 🛣️ Current Road Status")

road_display = current_df[
    [
        "ROAD_ID",
        "ROAD_NAME",
        "VEHICLE_COUNT",
        "AVERAGE_SPEED_KMH",
        "OCCUPANCY_PERCENT",
        "WEATHER_CONDITION",
        "INCIDENT_FLAG",
        "CONGESTION_LEVEL",
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
    "Congestion",
]

st.dataframe(
    road_display,
    width="stretch",
    height=290,
    hide_index=True,
)


# ============================================================
# "WHY IS TRAFFIC CHANGING?"
# ============================================================

st.divider()
st.markdown("### 🔎 Why Is Traffic Changing?")

worst = current_df.sort_values(
    ["SEVERITY_SCORE", "SPEED_DEVIATION", "OCCUPANCY_DEVIATION"],
    ascending=[False, True, False],
).iloc[0]

why1, why2, why3 = st.columns(3)

with why1:
    vehicle_delta = float(worst["VEHICLE_DEVIATION"])
    st.metric(
        "🚗 Vehicle Volume",
        f"{int(worst['VEHICLE_COUNT']):,}",
        f"{vehicle_delta:+.0f} vs baseline",
    )

with why2:
    st.metric(
        "⚡ Speed",
        f"{worst['AVERAGE_SPEED_KMH']:.1f} km/h",
        f"{worst['SPEED_DEVIATION']:+.1f} km/h vs baseline",
    )

with why3:
    st.metric(
        "📊 Occupancy",
        f"{worst['OCCUPANCY_PERCENT']:.1f}%",
        f"{worst['OCCUPANCY_DEVIATION']:+.1f} pts vs baseline",
    )

reason_parts = []

if worst["VEHICLE_DEVIATION"] > 0:
    reason_parts.append(
        f"vehicle volume is {worst['VEHICLE_DEVIATION']:.0f} above the road/hour baseline"
    )

if worst["SPEED_DEVIATION"] < 0:
    reason_parts.append(
        f"speed is {abs(worst['SPEED_DEVIATION']):.1f} km/h below baseline"
    )

if worst["OCCUPANCY_DEVIATION"] > 0:
    reason_parts.append(
        f"occupancy is {worst['OCCUPANCY_DEVIATION']:.1f} percentage points above baseline"
    )

if float(worst["RAINFALL_MM"]) > 0:
    reason_parts.append(
        f"rainfall is {float(worst['RAINFALL_MM']):.1f} mm"
    )

if bool(worst["INCIDENT_FLAG"]):
    reason_parts.append("an incident flag is active")

if reason_parts:
    reason_text = "; ".join(reason_parts)
else:
    reason_text = "Current measurements are close to the historical road/hour baseline."

st.markdown(
    f"""
    <div class="insight">
        <b>{worst["ROAD_NAME"]}</b> is the road with the strongest current watch signal.
        {reason_text.capitalize()}.
    </div>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# TABS
# ============================================================

tab1, tab2, tab3, tab4 = st.tabs(
    [
        "🔮 15-Min Forecast",
        "🚨 Anomaly Monitor",
        "📈 Traffic Trends",
        "🗺️ Traffic Map",
    ]
)


# ============================================================
# TAB 1 — FORECAST
# ============================================================

with tab1:

    st.markdown("#### 🔮 15-Minute Congestion Forecast")

    if prediction_df.empty:

        st.warning("No congestion predictions are currently available.")

    else:

        forecast = prediction_df.copy()

        forecast["CONFIDENCE_%"] = (
            forecast["PREDICTION_CONFIDENCE"] * 100
        ).round(1)

        forecast["PREDICTION_TIMESTAMP"] = pd.to_datetime(
            forecast["PREDICTION_TIMESTAMP"]
        ).dt.strftime("%Y-%m-%d %H:%M:%S")

        forecast_display = forecast[
            [
                "ROAD_ID",
                "ROAD_NAME",
                "PREDICTED_CONGESTION_LEVEL",
                "CONFIDENCE_%",
                "PREDICTION_TIMESTAMP",
            ]
        ].copy()

        forecast_display.columns = [
            "Road ID",
            "Road Name",
            "Predicted Congestion",
            "Confidence (%)",
            "Prediction Time",
        ]

        st.dataframe(
            forecast_display,
            width="stretch",
            height=290,
            hide_index=True,
        )

        risk_count = int(
            forecast["PREDICTED_CONGESTION_LEVEL"]
            .isin(["MEDIUM", "HIGH"])
            .sum()
        )

        if risk_count:
            st.warning(
                f"{risk_count} of {len(forecast)} roads are predicted to be MEDIUM/HIGH "
                "within approximately 15 minutes."
            )
        else:
            st.success(
                "No MEDIUM/HIGH congestion prediction is currently present."
            )

        st.caption(
            "The enhanced Random Forest model uses current traffic conditions, "
            "time context and road/hour historical baselines."
        )


# ============================================================
# TAB 2 — ANOMALIES
# ============================================================

with tab2:

    st.markdown("#### 🚨 Anomaly Monitor")

    anomaly_kpi1, anomaly_kpi2 = st.columns(2)

    with anomaly_kpi1:
        st.metric("Total Classified Anomalies", f"{total_anomalies:,}")

    with anomaly_kpi2:
        st.metric("Anomalies in Recent 30 Min", recent_anomalies)

    if anomaly_df.empty:

        st.success("No traffic anomalies detected.")

    else:

        display_anomalies = anomaly_df.copy()

        display_anomalies["EVENT_TIMESTAMP"] = pd.to_datetime(
            display_anomalies["EVENT_TIMESTAMP"]
        ).dt.strftime("%Y-%m-%d %H:%M:%S")

        display_anomalies.columns = [
            "Event Time",
            "Road ID",
            "Road Name",
            "Vehicles",
            "Avg Speed",
            "Occupancy (%)",
            "Anomaly Score",
        ]

        st.dataframe(
            display_anomalies,
            width="stretch",
            height=420,
            hide_index=True,
        )

        st.caption(
            "Isolation Forest flags traffic observations that differ significantly "
            "from learned normal traffic behavior."
        )


# ============================================================
# TAB 3 — TRENDS
# ============================================================

with tab3:

    st.markdown("#### 📈 Recent Traffic Trends")

    analytics_query = """
    SELECT
        EVENT_TIMESTAMP,
        VEHICLE_COUNT,
        AVERAGE_SPEED_KMH,
        OCCUPANCY_PERCENT
    FROM TRAFFIC_DB.GOLD.FACT_TRAFFIC
    WHERE EVENT_TIMESTAMP >= (
        SELECT DATEADD(
            hour,
            -3,
            MAX(EVENT_TIMESTAMP)
        )
        FROM TRAFFIC_DB.GOLD.FACT_TRAFFIC
    )
    ORDER BY EVENT_TIMESTAMP
    """

    analytics_df = run_query(analytics_query)

    if analytics_df.empty:

        st.warning("No traffic trend data is available.")

    else:

        analytics_df["EVENT_TIMESTAMP"] = pd.to_datetime(
            analytics_df["EVENT_TIMESTAMP"]
        )

        traffic_trend = (
            analytics_df
            .set_index("EVENT_TIMESTAMP")
            .resample("5min")
            .agg(
                {
                    "VEHICLE_COUNT": "sum",
                    "AVERAGE_SPEED_KMH": "mean",
                    "OCCUPANCY_PERCENT": "mean",
                }
            )
            .dropna(how="all")
        )

        trend_left, trend_right = st.columns(2)

        with trend_left:
            st.write("**Vehicle Volume — 5 Minute Windows**")
            st.line_chart(
                traffic_trend[["VEHICLE_COUNT"]],
                width="stretch",
            )

        with trend_right:
            st.write("**Average Speed — 5 Minute Windows**")
            st.line_chart(
                traffic_trend[["AVERAGE_SPEED_KMH"]],
                width="stretch",
            )

        st.write("**Average Occupancy — 5 Minute Windows**")
        st.line_chart(
            traffic_trend[["OCCUPANCY_PERCENT"]],
            width="stretch",
        )


# ============================================================
# TAB 4 — MAP
# ============================================================

with tab4:

    st.markdown("#### 🗺️ Hyderabad Project Road Segments")

    map_data = current_df[
        ["LATITUDE", "LONGITUDE", "ROAD_NAME", "CONGESTION_LEVEL"]
    ].copy()

    map_data.columns = [
        "latitude",
        "longitude",
        "Road Name",
        "Congestion",
    ]

    st.map(
        map_data[
            [
                "latitude",
                "longitude",
            ]
        ],
        width="stretch",
    )

    st.caption(
        "Map shows the five project/simulation road segments used by the platform."
    )


# ============================================================
# FOOTER
# ============================================================

st.divider()

st.caption(
    "Real-Time Smart City Traffic Intelligence Platform · "
    "Hyderabad · Kafka + Snowflake + dbt + Lightweight ML + Streamlit"
)
