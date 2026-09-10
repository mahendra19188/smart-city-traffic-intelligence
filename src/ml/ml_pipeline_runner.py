import os
import sys
import subprocess
import logging
from datetime import datetime


# ---------------------------------------------------------
# Project root
# ---------------------------------------------------------

PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../..")
)

PYTHON_EXECUTABLE = sys.executable


# ---------------------------------------------------------
# Logging configuration
# ---------------------------------------------------------

LOG_DIR = os.path.join(PROJECT_ROOT, "logs")

os.makedirs(LOG_DIR, exist_ok=True)

LOG_FILE = os.path.join(
    LOG_DIR,
    "ml_pipeline.log"
)


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------
# Run individual ML pipeline
# ---------------------------------------------------------

def run_pipeline(script_name):

    script_path = os.path.join(
        PROJECT_ROOT,
        "src",
        "ml",
        script_name
    )

    logger.info("=" * 60)
    logger.info("STARTING: %s", script_name)
    logger.info("=" * 60)

    start_time = datetime.now()

    result = subprocess.run(
        [PYTHON_EXECUTABLE, script_path],
        cwd=PROJECT_ROOT
    )

    end_time = datetime.now()

    duration = end_time - start_time

    if result.returncode != 0:

        logger.error(
            "FAILED: %s | Exit code: %s | Duration: %s",
            script_name,
            result.returncode,
            duration
        )

        return False

    logger.info(
        "SUCCESS: %s | Duration: %s",
        script_name,
        duration
    )

    return True


# ---------------------------------------------------------
# Main ML pipeline
# ---------------------------------------------------------

def main():

    pipeline_start = datetime.now()

    logger.info("=" * 60)
    logger.info("SMART CITY TRAFFIC ML PIPELINE")
    logger.info("=" * 60)

    logger.info(
        "Project root: %s",
        PROJECT_ROOT
    )

    logger.info(
        "Python executable: %s",
        PYTHON_EXECUTABLE
    )


    # -----------------------------------------------------
    # 1. Anomaly Detection
    # -----------------------------------------------------

    anomaly_success = run_pipeline(
        "anomaly_detection.py"
    )


    # -----------------------------------------------------
    # 2. Congestion Prediction
    # -----------------------------------------------------

    prediction_success = run_pipeline(
        "generate_congestion_predictions.py"
    )


    # -----------------------------------------------------
    # Final summary
    # -----------------------------------------------------

    pipeline_end = datetime.now()

    total_duration = pipeline_end - pipeline_start

    logger.info("=" * 60)
    logger.info("ML PIPELINE SUMMARY")
    logger.info("=" * 60)

    logger.info(
        "Anomaly Detection: %s",
        "SUCCESS" if anomaly_success else "FAILED"
    )

    logger.info(
        "Congestion Prediction: %s",
        "SUCCESS" if prediction_success else "FAILED"
    )

    logger.info(
        "Total Duration: %s",
        total_duration
    )

    logger.info("=" * 60)


    if not anomaly_success or not prediction_success:

        logger.error(
            "ML pipeline completed with errors."
        )

        sys.exit(1)


    logger.info(
        "ML pipeline completed successfully."
    )


# ---------------------------------------------------------
# Entry point
# ---------------------------------------------------------

if __name__ == "__main__":
    main()