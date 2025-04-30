#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import logging
import argparse
from pathlib import Path
from dotenv import load_dotenv

from database.json_db_manager import JsonDatabaseManager

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def setup_json_database(data_dir=None):
    """
    Set up the JSON database files.

    Args:
        data_dir (str, optional): Directory to store JSON files.
                                  Defaults to None (use from environment or default 'data').

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Load environment variables
        env_path = Path(__file__).parent / ".env"
        load_dotenv(dotenv_path=env_path)

        # Get data directory from environment if not provided
        if data_dir is None:
            data_dir = os.getenv("DATA_DIR", "data")

        logger.info(f"Setting up JSON database in directory: {data_dir}")

        # Create database manager and initialize files
        db_manager = JsonDatabaseManager(data_dir)
        success = db_manager.create_tables()

        # Add a sample location
        sample_location = {"name": "Malibu", "country": "USA", "region": "California"}
        db_manager.create_location(**sample_location)

        # Add a sample property
        sample_property = {
            "stayvista_id": "sv001",
            "name": "Malibu Beach House",
            "description": "Beautiful beach house with ocean views",
            "property_type": "villa",
            "max_guests": 8,
            "bedrooms": 4,
            "bathrooms": 3,
            "beds": 5,
            "base_price": 350.00,
            "cleaning_fee": 150.00,
            "service_fee": 50.00,
            "minimum_stay": 2,
            "amenities": ["beach access", "pool", "wifi", "kitchen", "parking"],
            "thumbnail_url": "https://example.com/thumbnail.jpg",
            "photo_urls": [
                "https://example.com/photo1.jpg",
                "https://example.com/photo2.jpg",
            ],
            "rating": 4.8,
            "num_reviews": 25,
            "location": {"name": "Malibu", "country": "USA", "region": "California"},
        }
        db_manager.create_or_update_property(sample_property)

        logger.info("Sample data added to JSON database")
        return success
    except Exception as e:
        logger.error(f"Failed to set up JSON database: {e}")
        return False


def parse_args():
    """
    Parse command line arguments.

    Returns:
        argparse.Namespace: Parsed arguments
    """
    parser = argparse.ArgumentParser(description="Set up StayVista JSON database")
    parser.add_argument(
        "--data-dir",
        help="Directory to store JSON data files (defaults to DATA_DIR environment variable or 'data')",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    success = setup_json_database(args.data_dir)

    if success:
        print("JSON database set up successfully")
    else:
        print("Failed to set up JSON database")
        exit(1)
