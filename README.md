Real-Time Smart City Traffic Intelligence Platform

A production-style Data Engineering portfolio project that turns continuous traffic events into near-real-time analytics, anomaly detection, short-term congestion predictions, and an operational dashboard.

The project is intentionally Data Engineering-first. Machine Learning is a lightweight intelligence layer rather than the main focus.

Project Overview

Urban traffic changes quickly with vehicle volume, speed, occupancy, weather, incidents, and time-of-day patterns. This project demonstrates how an event-driven data platform can continuously ingest traffic events, process them through layered data models, and expose useful operational intelligence.

The current MVP uses Hyderabad as the project city and five project/simulation road segments:

ROAD_001 — Gachibowli Main Road

ROAD_002 — Hitech City Road

ROAD_003 — Madhapur Road

ROAD_004 — Kondapur Road

ROAD_005 — Airport Route

These are project/simulation road segments and do not represent a claim of live sensor coverage.

What the Platform Does

Generates realistic traffic events continuously with Python.

Publishes events to Apache Kafka.

Consumes Kafka events into Snowflake RAW storage.

Incrementally processes RAW data into STAGING and GOLD layers using Snowflake Streams and Tasks.

Uses dbt for SQL transformations, testing, documentation, and lineage.

Runs Isolation Forest for traffic anomaly detection.

Runs an enhanced Random Forest model for approximately 15-minute congestion prediction.

Automates ML execution through a scheduled Python pipeline.

Exposes current traffic, pipeline health, anomalies, predictions, trends, and road locations through Streamlit.

End-to-End Architecture

                ┌──────────────────────────┐
                │ Python Traffic Generator │
                │ Traffic / Weather /      │
                │ Incident Simulation      │
                └────────────┬─────────────┘
                             │
                             ▼
                    ┌─────────────────┐
                    │ Apache Kafka     │
                    │ traffic-events  │
                    └────────┬────────┘
                             │
                             ▼
              ┌──────────────────────────────┐
              │ Kafka → Snowflake Consumer   │
              └──────────────┬───────────────┘
                             │
                             ▼
                  ┌──────────────────────┐
                  │ Snowflake RAW        │
                  │ TRAFFIC_EVENTS       │
                  └──────────┬───────────┘
                             │
                    Streams + Tasks
                             │
                             ▼
                  ┌──────────────────────┐
                  │ Snowflake STAGING    │
                  │ STG_TRAFFIC          │
                  └──────────┬───────────┘
                             │
                    Streams + Tasks
                             │
                             ▼
                  ┌──────────────────────┐
                  │ Snowflake GOLD       │
                  │ FACT_TRAFFIC         │
                  └──────────┬───────────┘
                             │
                ┌────────────┴─────────────┐
                │                          │
                ▼                          ▼
       ┌──────────────────┐       ┌────────────────────┐
       │ Isolation Forest │       │ Enhanced Random    │
       │ Anomaly Detection│       │ Forest Prediction  │
       └────────┬─────────┘       └─────────┬──────────┘
                │                           │
                ▼                           ▼
       TRAFFIC_ANOMALIES          TRAFFIC_CONGESTION_
                                  PREDICTIONS
                │                           │
                └─────────────┬─────────────┘
                              ▼
                    ┌──────────────────┐
                    │ Streamlit        │
                    │ Dashboard        │
                    └──────────────────┘

Technology Stack

Technology

Role

Python

Event generation, ingestion utilities, ML inference

Apache Kafka

Real-time event streaming and producer/consumer decoupling

Snowflake

Cloud data platform and analytical warehouse

Snowflake Streams

Change tracking for incremental processing

Snowflake Tasks

Scheduled/incremental downstream processing

dbt

SQL transformation, testing, documentation, lineage

Scikit-learn

Isolation Forest and Random Forest

Streamlit

Operational dashboard

Docker

Local Kafka environment

Git / GitHub

Version control and project presentation

Windows Task Scheduler

Local automation of the ML pipeline

Data Architecture

The Snowflake platform is organized into three logical layers.

RAW

TRAFFIC_DB.RAW.TRAFFIC_EVENTS

Stores incoming traffic events close to their original form.

Purpose:

Preserve source data for auditing and troubleshooting.

Provide a durable input for downstream processing.

Enable reprocessing when downstream logic changes.

STAGING

TRAFFIC_DB.STAGING.STG_TRAFFIC

Cleans and standardizes the incoming data and derives fields such as CONGESTION_LEVEL and PROCESSED_AT.

GOLD

TRAFFIC_DB.GOLD.FACT_TRAFFIC

Contains business-ready traffic measurements used by analytics, ML inference, and the dashboard.

Additional GOLD outputs include:

TRAFFIC_ANOMALIES

TRAFFIC_CONGESTION_PREDICTIONS

TRAFFIC_ROAD_HOURLY_BASELINES

VW_PIPELINE_HEALTH

Incremental Processing

The project avoids repeatedly processing the full traffic dataset.

The flow is:

RAW table
   ↓
RAW Stream
   ↓
STAGING Task
   ↓
STAGING Stream
   ↓
GOLD Task
   ↓
FACT_TRAFFIC

The downstream tasks use stream change detection and duplicate-protection logic so newly arriving events can be processed incrementally.

dbt

dbt is used for the governed SQL transformation layer.

Current dbt models include:

stg_traffic_events

int_traffic_enriched

fct_traffic

dbt also provides:

source definitions

column descriptions

data tests

generated documentation

model lineage

The project has been validated with passing dbt tests and generated documentation.

Machine Learning

The AI layer is deliberately lightweight.

1. Traffic Anomaly Detection

Model: Isolation Forest

Features:

vehicle count

average speed

occupancy

rainfall

The model classifies each newly analyzed event as either:

0 = Normal
1 = Anomaly

Every analyzed event is stored in TRAFFIC_ANOMALIES, including normal observations. This preserves an audit trail of which traffic events were analyzed.

The model is run incrementally against new GOLD events and uses event IDs to prevent duplicate processing.

2. 15-Minute Congestion Prediction

Model: Enhanced Random Forest classifier

Prediction classes:

LOW
MEDIUM
HIGH

The production model uses current traffic features plus road/hour historical baselines and deviation features:

vehicle count

average speed

occupancy

rainfall

incident flag

hour of day

day of week

typical vehicle count

typical speed

typical occupancy

vehicle count deviation

speed deviation

occupancy deviation

The road/hour baselines are calculated from the training period so future-test information is not leaked into training.

Model Evaluation Snapshot

The chronological production-model evaluation achieved approximately:

Metric

Result

Accuracy

70.38%

Balanced Accuracy

57.41%

Macro F1

57.14%

Weighted F1

69.06%

Class-level performance showed that LOW congestion is easier to classify than MEDIUM/HIGH congestion. This is an expected limitation of the current small/simulated training dataset and is documented rather than hidden.

Data Quality and Reliability

The project includes explicit validation for:

duplicate event IDs

null event IDs

null timestamps

null road IDs

negative vehicle counts

negative speeds

invalid occupancy values

negative rainfall

A validation snapshot produced:

GOLD events       : 5,027
Unique events     : 5,027
Duplicate events  : 0

Null event IDs    : 0
Null timestamps   : 0
Null road IDs     : 0
Negative vehicles : 0
Negative speeds   : 0
Invalid occupancy : 0
Negative rainfall : 0

Pipeline Health

TRAFFIC_DB.GOLD.VW_PIPELINE_HEALTH provides operational metrics including:

RAW event count

STAGING event count

GOLD event count

anomaly-analysis count

prediction count

latest RAW event

latest STAGING event

latest GOLD event

latest anomaly detection

latest prediction

RAW → GOLD processing lag

overall pipeline status

The pipeline status is classified as:

HEALTHY
WARNING
CRITICAL

The RAW → GOLD lag is calculated as:

Latest RAW event timestamp
        -
Latest GOLD event timestamp

so a positive value represents downstream processing delay.

ML Automation

The ML pipeline is orchestrated by:

src/ml/ml_pipeline_runner.py

It executes:

anomaly_detection.py
        ↓
generate_congestion_predictions.py

The pipeline is scheduled locally through Windows Task Scheduler.

The task launches the project's virtual-environment Python interpreter and runs the ML pipeline approximately every five minutes.

The runner records:

pipeline start

child process start

child process success/failure

execution duration

overall pipeline status

Dashboard

The Streamlit dashboard provides:

Current Traffic Overview

total vehicles

average speed

average occupancy

congested roads

anomaly count

Pipeline Health

RAW events

STAGING events

GOLD events

anomaly-analysis results

predictions

pipeline status

RAW → GOLD lag

freshness timestamps

Current Road Status

Displays the latest traffic state for each project road segment.

15-Minute Prediction

Shows:

road

predicted congestion

confidence

prediction time

Anomalies

Shows recent anomalous traffic observations with:

event time

road

vehicles

average speed

occupancy

anomaly score

Traffic Trends

The dashboard visualizes recent traffic movement using 5-minute aggregation to make high-frequency streaming data easier to interpret.

Traffic Map

Displays the five project/simulation road segments on a map.

Project Structure

smart-city-traffic-intelligence/
│
├── config/
├── dashboard/
│   └── app.py
├── data/
│   ├── raw/
│   ├── processed/
│   └── sample/
├── dbt/
│   ├── macros/
│   ├── models/
│   │   ├── staging/
│   │   ├── intermediate/
│   │   └── marts/
│   ├── seeds/
│   └── tests/
├── docs/
│   ├── architecture/
│   └── screenshots/
├── models/
│   ├── traffic_anomaly_model.pkl
│   └── congestion_prediction_model.pkl
├── notebooks/
├── sql/
│   ├── database/
│   ├── queries/
│   ├── tables/
│   └── views/
├── src/
│   ├── ingestion/
│   ├── kafka/
│   ├── ml/
│   ├── snowflake/
│   └── transformations/
├── tests/
├── .env.example
├── .gitignore
├── README.md
├── dbt_project.yml
└── requirements.txt

Setup

1. Clone the repository

git clone <YOUR_GITHUB_REPOSITORY_URL>
cd smart-city-traffic-intelligence

2. Create and activate the virtual environment

python -m venv .venv
.\.venv\Scripts\Activate.ps1

3. Install dependencies

pip install -r requirements.txt

4. Configure environment variables

Copy:

.env.example

to:

.env

and configure the Snowflake connection values.

Never commit .env or credentials to GitHub.

5. Start Kafka

The MVP uses Kafka locally through Docker.

The Kafka topic used by the project is:

traffic-events

6. Start the streaming components

Traffic generation:

.\.venv\Scripts\python.exe src\ingestion\traffic_generator.py

Kafka producer:

.\.venv\Scripts\python.exe -m src.kafka.traffic_producer

Kafka → Snowflake consumer:

.\.venv\Scripts\python.exe src\snowflake\kafka_to_snowflake.py

7. Run dbt

From the project root:

dbt debug
dbt run
dbt test
dbt docs generate

8. Run the ML pipeline

.\.venv\Scripts\python.exe src\ml\ml_pipeline_runner.py

9. Run the dashboard

.\.venv\Scripts\python.exe -m streamlit run dashboard\app.py

Important Project Notes

Data strategy

The MVP uses realistic simulated traffic events so the platform can be demonstrated without depending on unreliable third-party live traffic APIs.

The architecture is designed so public or live sources can be introduced later without changing the downstream analytical pattern.

Scope of AI

The MVP intentionally does not include:

deep learning

LLM chatbots

RAG

AI agents

computer vision

The purpose is to demonstrate strong end-to-end data engineering with a manageable intelligence layer.

Current limitations

Training data is relatively small and partly simulated.

Prediction quality is therefore not representative of a production city's traffic forecasting accuracy.

Only five project/simulation road segments are currently modeled.

Local Windows Task Scheduler is used for automation in the MVP.

Kafka currently runs locally through Docker.

Production deployment would require cloud-native orchestration, monitoring, CI/CD, secret management, and stronger data infrastructure.

Future Improvements

Potential production extensions include:

live traffic and weather source integration

larger historical datasets

richer incident feeds

cloud-native Kafka deployment

cloud orchestration such as Airflow or managed workflows

CI/CD

centralized logging and metrics

data-quality alerting

model monitoring and retraining

stronger forecasting models when justified

broader road/network coverage

role-based access and managed secrets

These are future extensions rather than requirements for the current MVP.

Why This Project Matters for Data Engineering

The domain is traffic, but the main engineering value is the end-to-end architecture:

Event generation
      ↓
Real-time streaming
      ↓
Cloud data ingestion
      ↓
Layered data modeling
      ↓
Incremental processing
      ↓
Transformation + testing
      ↓
Machine learning inference
      ↓
Operational visualization
      ↓
Pipeline monitoring

The project demonstrates practical experience with streaming, cloud warehousing, incremental processing, data quality, SQL transformation, ML integration, automation, and operational dashboards.

Interview Summary

A concise way to describe the project:

Built a near-real-time smart-city traffic intelligence platform using Python, Apache Kafka, Snowflake, dbt, and Scikit-learn. Designed an incremental RAW → STAGING → GOLD pipeline with Snowflake Streams and Tasks, added Isolation Forest anomaly detection and a Random Forest model for 15-minute congestion prediction, automated ML inference, and exposed live operational metrics through Streamlit.

License

Add the repository license you choose for the final GitHub repository.