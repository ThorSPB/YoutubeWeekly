import logging
import os
from datetime import datetime
import json

def setup_logger(config_path="config/settings.json"):
    # Load log folder path from config
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)
    log_folder = config.get("log_folder", "data/logs")

    # Make sure log folder exists
    os.makedirs(log_folder, exist_ok=True)

    # Create log file with timestamp
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_filename = os.path.join(log_folder, f"log_{timestamp}.txt")

    # Configure logger
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler(log_filename, encoding="utf-8"),
            logging.StreamHandler()
        ]
    )

    logging.info("Logger initialized.")
