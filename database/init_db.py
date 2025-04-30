#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import logging
import argparse
from pathlib import Path
from dotenv import load_dotenv

# Import the JSON database manager instead of the SQL one
from .json_db_manager import JsonDatabaseManager

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def init_database(data_dir=None):
    """
    Initialize the database by creating JSON data files.

    Args:
        data_dir (str, optional): Directory to store JSON files.
                                  Defaults to None (use from environment or default).

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Load environment variables
        env_path = Path(__file__).parent.parent / ".env"
        load_dotenv(dotenv_path=env_path)

        # Get data directory from environment if not provided
        if data_dir is None:
            data_dir = os.getenv("DATA_DIR", "data")

        # Create database manager
        db_manager = JsonDatabaseManager(data_dir)

        # Create data files
        success = db_manager.create_tables()

        return success
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        return False


def parse_args():
    """
    Parse command line arguments.

    Returns:
        argparse.Namespace: Parsed arguments
    """
    parser = argparse.ArgumentParser(description="Initialize StayVista database")
    parser.add_argument(
        "--data-dir",
        help="Directory to store JSON data files (defaults to DATA_DIR environment variable or 'data')",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    success = init_database(args.data_dir)

    if success:
        print("JSON database initialized successfully")
    else:
        print("Failed to initialize JSON database")
        exit(1)
