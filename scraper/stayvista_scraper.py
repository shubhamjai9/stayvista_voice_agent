#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import json
import time
import logging
import random
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional

import requests
from bs4 import BeautifulSoup
from tqdm import tqdm
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("scraper.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

# Import database modules
import sys

sys.path.append(str(Path(__file__).parent.parent))
from database.json_db_manager import JsonDatabaseManager


class StayVistaScraper:
    """
    Web scraper for StayVista properties.
    """

    BASE_URL = "https://stayvista.com"
    SEARCH_URL = f"{BASE_URL}/search"
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }

    def __init__(self, data_dir=None, use_selenium=True):
        """
        Initialize the scraper.

        Args:
            data_dir (str, optional): Directory to store JSON files.
                                      Defaults to None (use from environment).
            use_selenium (bool, optional): Whether to use Selenium for dynamic content.
                                         Defaults to True.
        """
        # Set up database connection
        if data_dir is None:
            data_dir = os.getenv("DATA_DIR", "data")

        self.db_manager = JsonDatabaseManager(data_dir)

        # Set up Selenium if requested
        self.use_selenium = use_selenium
        self.driver = None

        if use_selenium:
            self._setup_selenium()

    def _setup_selenium(self):
        """Set up Selenium WebDriver."""
        try:
            chrome_options = Options()
            chrome_options.add_argument("--headless")
            chrome_options.add_argument("--no-sandbox")
            chrome_options.add_argument("--disable-dev-shm-usage")

            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            logger.info("Selenium WebDriver initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Selenium WebDriver: {e}")
            self.use_selenium = False

    def _make_request(self, url, params=None):
        """
        Make an HTTP request with error handling and retries.

        Args:
            url (str): URL to request
            params (dict, optional): Query parameters. Defaults to None.

        Returns:
            requests.Response: Response object, or None if failed
        """
        max_retries = 3
        retry_delay = 2

        for attempt in range(max_retries):
            try:
                response = requests.get(
                    url, params=params, headers=self.HEADERS, timeout=10
                )
                response.raise_for_status()
                return response
            except requests.exceptions.RequestException as e:
                logger.warning(
                    f"Request failed (attempt {attempt+1}/{max_retries}): {e}"
                )
                if attempt < max_retries - 1:
                    # Add jitter to retry delay to avoid thundering herd
                    time.sleep(retry_delay + random.uniform(0, 1))
                    retry_delay *= 1.5
                else:
                    logger.error(
                        f"Failed to make request to {url} after {max_retries} attempts"
                    )
                    return None

    def _extract_property_id(self, url):
        """
        Extract property ID from URL.

        Args:
            url (str): Property URL

        Returns:
            str: Property ID, or None if not found
        """
        # Extract property ID from URL like https://stayvista.com/properties/123456
        match = re.search(r"/properties/([a-zA-Z0-9-]+)", url)
        if match:
            return match.group(1)
        return None

    def search_properties(
        self, location=None, check_in=None, check_out=None, guests=None, limit=100
    ):
        """
        Search for properties with specified criteria.

        Args:
            location (str, optional): Location to search in. Defaults to None.
            check_in (str, optional): Check-in date in YYYY-MM-DD format. Defaults to None.
            check_out (str, optional): Check-out date in YYYY-MM-DD format. Defaults to None.
            guests (int, optional): Number of guests. Defaults to None.
            limit (int, optional): Maximum number of properties to fetch. Defaults to 100.

        Returns:
            List[Dict]: List of property data dictionaries
        """
        logger.info(
            f"Searching for properties with criteria: location={location}, "
            + f"check_in={check_in}, check_out={check_out}, guests={guests}"
        )

        # Prepare search parameters
        params = {}
        if location:
            params["location"] = location
        if check_in:
            params["checkin"] = check_in
        if check_out:
            params["checkout"] = check_out
        if guests:
            params["guests"] = str(guests)

        # Use Selenium for dynamic content if available
        if self.use_selenium and self.driver:
            return self._search_properties_selenium(params, limit)
        else:
            return self._search_properties_requests(params, limit)

    def _search_properties_requests(self, params, limit):
        """
        Search for properties using requests.

        Args:
            params (dict): Search parameters
            limit (int): Maximum number of properties to fetch

        Returns:
            List[Dict]: List of property data dictionaries
        """
        # Make request to search page
        response = self._make_request(self.SEARCH_URL, params)
        if not response:
            return []

        # Parse search results
        soup = BeautifulSoup(response.text, "html.parser")

        # Extract property listings
        property_cards = soup.select(
            ".property-card"
        )  # Adjust selector based on actual page structure
        logger.info(f"Found {len(property_cards)} property cards on search page")

        # Extract basic property data from search results
        property_urls = []
        for card in property_cards[:limit]:
            link = card.select_one('a[href^="/properties/"]')
            if link and link.get("href"):
                property_urls.append(self.BASE_URL + link.get("href"))

        # Fetch detailed property information
        properties = []
        for url in tqdm(property_urls, desc="Fetching property details"):
            property_data = self.get_property_details(url)
            if property_data:
                properties.append(property_data)

        return properties

    def _search_properties_selenium(self, params, limit):
        """
        Search for properties using Selenium.

        Args:
            params (dict): Search parameters
            limit (int): Maximum number of properties to fetch

        Returns:
            List[Dict]: List of property data dictionaries
        """
        # Build URL with parameters
        url = self.SEARCH_URL
        if params:
            query_string = "&".join([f"{k}={v}" for k, v in params.items()])
            url = f"{url}?{query_string}"

        try:
            # Navigate to search page
            self.driver.get(url)

            # Wait for results to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".property-card"))
            )

            # Extract property listings
            property_cards = self.driver.find_elements(
                By.CSS_SELECTOR, ".property-card"
            )
            logger.info(f"Found {len(property_cards)} property cards on search page")

            # Extract property URLs
            property_urls = []
            for card in property_cards[:limit]:
                link = card.find_element(By.CSS_SELECTOR, 'a[href^="/properties/"]')
                if link:
                    property_urls.append(self.BASE_URL + link.get_attribute("href"))

            # Fetch detailed property information
            properties = []
            for url in tqdm(property_urls, desc="Fetching property details"):
                property_data = self.get_property_details(url, use_selenium=True)
                if property_data:
                    properties.append(property_data)

            return properties

        except Exception as e:
            logger.error(f"Error searching properties with Selenium: {e}")
            return []

    def get_property_details(self, url, use_selenium=None):
        """
        Get detailed information about a property.

        Args:
            url (str): Property URL
            use_selenium (bool, optional): Whether to use Selenium.
                                         Defaults to None (use instance setting).

        Returns:
            Dict: Property data dictionary, or None if failed
        """
        logger.info(f"Getting details for property: {url}")

        # Extract property ID from URL
        property_id = self._extract_property_id(url)
        if not property_id:
            logger.error(f"Could not extract property ID from URL: {url}")
            return None

        # Use Selenium if specified or if it's the instance default
        if use_selenium is None:
            use_selenium = self.use_selenium

        # Fetch property page
        if use_selenium and self.driver:
            return self._get_property_details_selenium(url, property_id)
        else:
            return self._get_property_details_requests(url, property_id)

    def _get_property_details_requests(self, url, property_id):
        """
        Get property details using requests.

        Args:
            url (str): Property URL
            property_id (str): Property ID

        Returns:
            Dict: Property data dictionary, or None if failed
        """
        # Make request to property page
        response = self._make_request(url)
        if not response:
            return None

        # Parse property page
        soup = BeautifulSoup(response.text, "html.parser")

        # Extract property data
        try:
            # Basic information
            property_data = {
                "stayvista_id": property_id,
                "name": self._extract_text(soup, ".property-title"),
                "description": self._extract_text(soup, ".property-description"),
                "property_type": self._extract_text(soup, ".property-type"),
                # Location
                "location": {
                    "name": self._extract_text(soup, ".property-location .city"),
                    "country": self._extract_text(soup, ".property-location .country"),
                    "region": self._extract_text(soup, ".property-location .region"),
                },
                "address": self._extract_text(soup, ".property-address"),
                # Capacity
                "max_guests": self._extract_number(soup, ".property-capacity .guests"),
                "bedrooms": self._extract_number(soup, ".property-capacity .bedrooms"),
                "bathrooms": self._extract_number(
                    soup, ".property-capacity .bathrooms"
                ),
                "beds": self._extract_number(soup, ".property-capacity .beds"),
                # Pricing
                "base_price": self._extract_price(
                    soup, ".property-pricing .base-price"
                ),
                "cleaning_fee": self._extract_price(
                    soup, ".property-pricing .cleaning-fee"
                ),
                "service_fee": self._extract_price(
                    soup, ".property-pricing .service-fee"
                ),
                # Media
                "thumbnail_url": self._extract_image_url(
                    soup, ".property-images .main-image img"
                ),
                "photo_urls": self._extract_image_urls(
                    soup, ".property-images .gallery img"
                ),
                # Amenities
                "amenities": self._extract_amenities(soup),
                # Ratings
                "rating": self._extract_rating(soup),
                "num_reviews": self._extract_number(soup, ".property-reviews .count"),
            }

            return property_data

        except Exception as e:
            logger.error(f"Error extracting property details from {url}: {e}")
            return None

    def _get_property_details_selenium(self, url, property_id):
        """
        Get property details using Selenium.

        Args:
            url (str): Property URL
            property_id (str): Property ID

        Returns:
            Dict: Property data dictionary, or None if failed
        """
        try:
            # Navigate to property page
            self.driver.get(url)

            # Wait for page to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, ".property-title"))
            )

            # Extract property data
            property_data = {
                "stayvista_id": property_id,
                "name": self._extract_text_selenium(".property-title"),
                "description": self._extract_text_selenium(".property-description"),
                "property_type": self._extract_text_selenium(".property-type"),
                # Location
                "location": {
                    "name": self._extract_text_selenium(".property-location .city"),
                    "country": self._extract_text_selenium(
                        ".property-location .country"
                    ),
                    "region": self._extract_text_selenium(".property-location .region"),
                },
                "address": self._extract_text_selenium(".property-address"),
                # Capacity
                "max_guests": self._extract_number_selenium(
                    ".property-capacity .guests"
                ),
                "bedrooms": self._extract_number_selenium(
                    ".property-capacity .bedrooms"
                ),
                "bathrooms": self._extract_number_selenium(
                    ".property-capacity .bathrooms"
                ),
                "beds": self._extract_number_selenium(".property-capacity .beds"),
                # Pricing
                "base_price": self._extract_price_selenium(
                    ".property-pricing .base-price"
                ),
                "cleaning_fee": self._extract_price_selenium(
                    ".property-pricing .cleaning-fee"
                ),
                "service_fee": self._extract_price_selenium(
                    ".property-pricing .service-fee"
                ),
                # Media
                "thumbnail_url": self._extract_attribute_selenium(
                    ".property-images .main-image img", "src"
                ),
                "photo_urls": self._extract_attributes_selenium(
                    ".property-images .gallery img", "src"
                ),
                # Amenities
                "amenities": self._extract_amenities_selenium(),
                # Ratings
                "rating": self._extract_rating_selenium(),
                "num_reviews": self._extract_number_selenium(
                    ".property-reviews .count"
                ),
            }

            return property_data

        except Exception as e:
            logger.error(
                f"Error extracting property details with Selenium from {url}: {e}"
            )
            return None

    # Helper methods for extracting data from HTML

    def _extract_text(self, soup, selector):
        """Extract text from a BeautifulSoup element."""
        element = soup.select_one(selector)
        return element.get_text().strip() if element else ""

    def _extract_number(self, soup, selector):
        """Extract a number from a BeautifulSoup element."""
        text = self._extract_text(soup, selector)
        try:
            # Extract digits from text
            match = re.search(r"\d+", text)
            if match:
                return int(match.group())
            return None
        except (ValueError, TypeError):
            return None

    def _extract_price(self, soup, selector):
        """Extract a price value from a BeautifulSoup element."""
        text = self._extract_text(soup, selector)
        try:
            # Extract price value (remove currency symbol and commas)
            match = re.search(r"[\d,]+\.?\d*", text)
            if match:
                return float(match.group().replace(",", ""))
            return None
        except (ValueError, TypeError):
            return None

    def _extract_image_url(self, soup, selector):
        """Extract an image URL from a BeautifulSoup element."""
        element = soup.select_one(selector)
        return element.get("src") if element else None

    def _extract_image_urls(self, soup, selector):
        """Extract multiple image URLs from BeautifulSoup elements."""
        elements = soup.select(selector)
        return [element.get("src") for element in elements if element.get("src")]

    def _extract_amenities(self, soup):
        """Extract amenities list from a BeautifulSoup object."""
        elements = soup.select(".property-amenities .amenity")
        return [element.get_text().strip() for element in elements]

    def _extract_rating(self, soup):
        """Extract rating value from a BeautifulSoup object."""
        element = soup.select_one(".property-rating .value")
        if element:
            try:
                return float(element.get_text().strip())
            except (ValueError, TypeError):
                return None
        return None

    # Helper methods for extracting data with Selenium

    def _extract_text_selenium(self, selector):
        """Extract text from a Selenium element."""
        try:
            element = self.driver.find_element(By.CSS_SELECTOR, selector)
            return element.text.strip()
        except:
            return ""

    def _extract_number_selenium(self, selector):
        """Extract a number from a Selenium element."""
        text = self._extract_text_selenium(selector)
        try:
            # Extract digits from text
            match = re.search(r"\d+", text)
            if match:
                return int(match.group())
            return None
        except (ValueError, TypeError):
            return None

    def _extract_price_selenium(self, selector):
        """Extract a price value from a Selenium element."""
        text = self._extract_text_selenium(selector)
        try:
            # Extract price value (remove currency symbol and commas)
            match = re.search(r"[\d,]+\.?\d*", text)
            if match:
                return float(match.group().replace(",", ""))
            return None
        except (ValueError, TypeError):
            return None

    def _extract_attribute_selenium(self, selector, attribute):
        """Extract an attribute from a Selenium element."""
        try:
            element = self.driver.find_element(By.CSS_SELECTOR, selector)
            return element.get_attribute(attribute)
        except:
            return None

    def _extract_attributes_selenium(self, selector, attribute):
        """Extract attributes from multiple Selenium elements."""
        try:
            elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
            return [
                element.get_attribute(attribute)
                for element in elements
                if element.get_attribute(attribute)
            ]
        except:
            return []

    def _extract_amenities_selenium(self):
        """Extract amenities list using Selenium."""
        try:
            elements = self.driver.find_elements(
                By.CSS_SELECTOR, ".property-amenities .amenity"
            )
            return [element.text.strip() for element in elements]
        except:
            return []

    def _extract_rating_selenium(self):
        """Extract rating value using Selenium."""
        try:
            element = self.driver.find_element(
                By.CSS_SELECTOR, ".property-rating .value"
            )
            return float(element.text.strip())
        except:
            return None

    def save_to_database(self, properties):
        """
        Save scraped properties to the database.

        Args:
            properties (List[Dict]): List of property data dictionaries

        Returns:
            int: Number of properties saved
        """
        count = 0
        logger.info(f"Saving {len(properties)} properties to database")

        for property_data in tqdm(properties, desc="Saving to database"):
            # Create or update the property
            property_obj = self.db_manager.create_or_update_property(property_data)
            if property_obj:
                count += 1

        logger.info(f"Successfully saved {count} properties to database")
        return count

    def close(self):
        """Close connections and release resources."""
        if self.driver:
            self.driver.quit()
            self.driver = None


def parse_args():
    """
    Parse command line arguments.

    Returns:
        argparse.Namespace: Parsed arguments
    """
    parser = argparse.ArgumentParser(description="Scrape StayVista property data")

    parser.add_argument("--location", help="Location to search for properties")
    parser.add_argument("--check-in", help="Check-in date in YYYY-MM-DD format")
    parser.add_argument("--check-out", help="Check-out date in YYYY-MM-DD format")
    parser.add_argument("--guests", type=int, help="Number of guests")
    parser.add_argument(
        "--limit", type=int, default=100, help="Maximum number of properties to scrape"
    )
    parser.add_argument(
        "--no-selenium",
        action="store_true",
        help="Disable Selenium and use requests only",
    )
    parser.add_argument(
        "--data-dir",
        help="Directory to store JSON files (defaults to DATA_DIR environment variable)",
    )

    return parser.parse_args()


if __name__ == "__main__":
    # Parse command line arguments
    args = parse_args()

    # Create scraper
    scraper = StayVistaScraper(
        data_dir=args.data_dir, use_selenium=not args.no_selenium
    )

    try:
        # Search for properties
        properties = scraper.search_properties(
            location=args.location,
            check_in=args.check_in,
            check_out=args.check_out,
            guests=args.guests,
            limit=args.limit,
        )

        if properties:
            # Save to database
            count = scraper.save_to_database(properties)
            print(f"Saved {count} properties to database")
        else:
            print("No properties found")

    finally:
        # Close connections
        scraper.close()
