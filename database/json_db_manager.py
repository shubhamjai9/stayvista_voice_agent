#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple, Union
import shutil

logger = logging.getLogger(__name__)


class JsonDatabaseManager:
    """
    Database manager for StayVista voice agent using JSON files.
    Handles all database operations using local JSON files.
    """

    def __init__(self, data_dir="data"):
        """
        Initialize the database manager.

        Args:
            data_dir (str): Directory to store JSON files
        """
        self.data_dir = data_dir
        self.ensure_data_dir()

        # Define file paths
        self.properties_file = os.path.join(data_dir, "properties.json")
        self.locations_file = os.path.join(data_dir, "locations.json")
        self.users_file = os.path.join(data_dir, "users.json")
        self.bookings_file = os.path.join(data_dir, "bookings.json")
        self.conversation_logs_file = os.path.join(data_dir, "conversation_logs.json")

        # Initialize data files if they don't exist
        self.initialize_data_files()

        logger.info("JSON Database initialized at: {}".format(data_dir))

    def ensure_data_dir(self):
        """Ensure data directory exists"""
        os.makedirs(self.data_dir, exist_ok=True)
        logger.info(f"Data directory ensured at: {self.data_dir}")

    def initialize_data_files(self):
        """Initialize JSON data files if they don't exist"""
        data_files = {
            self.properties_file: [],
            self.locations_file: [],
            self.users_file: [],
            self.bookings_file: [],
            self.conversation_logs_file: [],
        }

        for file_path, default_data in data_files.items():
            if not os.path.exists(file_path):
                with open(file_path, "w") as f:
                    json.dump(default_data, f)
                logger.info(f"Initialized empty data file: {file_path}")

    def read_json_file(self, file_path):
        """
        Read data from a JSON file.

        Args:
            file_path (str): Path to JSON file

        Returns:
            list or dict: Data from JSON file
        """
        try:
            with open(file_path, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            logger.error(f"File not found: {file_path}")
            return []
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON in file: {file_path}")
            return []

    def write_json_file(self, file_path, data):
        """
        Write data to a JSON file.

        Args:
            file_path (str): Path to JSON file
            data (list or dict): Data to write

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Create a backup of the original file
            if os.path.exists(file_path):
                backup_path = f"{file_path}.bak"
                shutil.copy2(file_path, backup_path)

            with open(file_path, "w") as f:
                json.dump(data, f, indent=2, default=self._json_serializer)
            return True
        except Exception as e:
            logger.error(f"Error writing to file {file_path}: {e}")
            # Restore from backup if available
            if os.path.exists(f"{file_path}.bak"):
                shutil.copy2(f"{file_path}.bak", file_path)
            return False

    def _json_serializer(self, obj):
        """
        JSON serializer for objects not serializable by default json code.

        Args:
            obj: Object to serialize

        Returns:
            str: Serialized representation
        """
        if isinstance(obj, datetime):
            return obj.isoformat()
        raise TypeError(f"Type {type(obj)} not serializable")

    def create_tables(self):
        """
        Create all data files if they don't exist.

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            self.initialize_data_files()
            return True
        except Exception as e:
            logger.error(f"Failed to create data files: {e}")
            return False

    # Location operations

    def get_location_by_name(self, name: str, country: str = None) -> Optional[Dict]:
        """
        Get a location by name.

        Args:
            name (str): Location name
            country (str, optional): Country name. Defaults to None.

        Returns:
            dict: Location data if found, None otherwise
        """
        locations = self.read_json_file(self.locations_file)
        name = name.lower() if name else ""

        for location in locations:
            location_name = location.get("name", "").lower()

            if location_name == name:
                if country:
                    location_country = location.get("country", "").lower()
                    if location_country == country.lower():
                        return location
                else:
                    return location

        return None

    def create_location(
        self, name: str, country: str, region: str = None
    ) -> Optional[Dict]:
        """
        Create a new location.

        Args:
            name (str): Location name
            country (str): Country name
            region (str, optional): Region name. Defaults to None.

        Returns:
            dict: Created location data if successful, None otherwise
        """
        # Check if location already exists
        existing = self.get_location_by_name(name, country)
        if existing:
            return existing

        locations = self.read_json_file(self.locations_file)

        # Create new location with a unique ID
        new_location = {
            "id": len(locations) + 1,
            "name": name,
            "country": country,
            "region": region,
        }

        locations.append(new_location)

        if self.write_json_file(self.locations_file, locations):
            logger.info(f"Created location: {name}, {country}")
            return new_location

        return None

    # Property operations

    def get_property_by_stayvista_id(self, stayvista_id: str) -> Optional[Dict]:
        """
        Get a property by StayVista ID.

        Args:
            stayvista_id (str): StayVista property ID

        Returns:
            dict: Property data if found, None otherwise
        """
        properties = self.read_json_file(self.properties_file)

        for prop in properties:
            if prop.get("stayvista_id") == stayvista_id:
                return prop

        return None

    def create_or_update_property(
        self, property_data: Dict[str, Any]
    ) -> Optional[Dict]:
        """
        Create or update a property.

        Args:
            property_data (dict): Property data

        Returns:
            dict: Created/updated property data if successful, None otherwise
        """
        # Check if property already exists
        stayvista_id = property_data.get("stayvista_id")
        if not stayvista_id:
            logger.error("Property data missing required field: stayvista_id")
            return None

        properties = self.read_json_file(self.properties_file)

        # Handle location separately
        location_data = property_data.pop("location", None)
        if location_data:
            location = self.get_location_by_name(
                location_data["name"], location_data.get("country")
            )
            if not location:
                location = self.create_location(
                    location_data["name"],
                    location_data.get("country", "Unknown"),
                    location_data.get("region"),
                )
            property_data["location_id"] = location["id"] if location else None

        # Check if property already exists
        property_idx = None
        for idx, prop in enumerate(properties):
            if prop.get("stayvista_id") == stayvista_id:
                property_idx = idx
                break

        if property_idx is not None:
            # Update existing property
            property_data["id"] = properties[property_idx]["id"]
            properties[property_idx].update(property_data)
            property_obj = properties[property_idx]
        else:
            # Create new property with a unique ID
            property_data["id"] = len(properties) + 1
            property_data["created_at"] = datetime.utcnow().isoformat()
            properties.append(property_data)
            property_obj = property_data

        property_obj["updated_at"] = datetime.utcnow().isoformat()

        if self.write_json_file(self.properties_file, properties):
            logger.info(f"Created/updated property: {property_obj.get('name')}")
            return property_obj

        return None

    def search_properties(
        self,
        location: str = None,
        check_in: datetime = None,
        check_out: datetime = None,
        guests: int = None,
        bedrooms: int = None,
        amenities: List[str] = None,
        max_price: float = None,
        limit: int = 10,
    ) -> List[Dict]:
        """
        Search for properties based on criteria.

        Args:
            location (str, optional): Location name. Defaults to None.
            check_in (datetime, optional): Check-in date. Defaults to None.
            check_out (datetime, optional): Check-out date. Defaults to None.
            guests (int, optional): Number of guests. Defaults to None.
            bedrooms (int, optional): Number of bedrooms. Defaults to None.
            amenities (List[str], optional): List of required amenities. Defaults to None.
            max_price (float, optional): Maximum price per night. Defaults to None.
            limit (int, optional): Maximum number of results. Defaults to 10.

        Returns:
            List[Dict]: List of matching properties
        """
        properties = self.read_json_file(self.properties_file)
        locations = self.read_json_file(self.locations_file)
        bookings = self.read_json_file(self.bookings_file)

        # Apply location filter if provided
        if location:
            location_obj = self.get_location_by_name(location)
            if location_obj:
                properties = [
                    p for p in properties if p.get("location_id") == location_obj["id"]
                ]
            else:
                # If location not found, return empty list
                return []

        # Apply date filter if provided
        if check_in and check_out:
            # Find unavailable property IDs based on bookings
            unavailable_property_ids = set()

            for booking in bookings:
                if booking.get("status") == "cancelled":
                    continue

                booking_check_in = datetime.fromisoformat(booking.get("check_in_date"))
                booking_check_out = datetime.fromisoformat(
                    booking.get("check_out_date")
                )

                # Check if booking overlaps with requested dates
                if (
                    (booking_check_in <= check_in and booking_check_out > check_in)
                    or (booking_check_in < check_out and booking_check_out >= check_out)
                    or (booking_check_in >= check_in and booking_check_out <= check_out)
                ):
                    unavailable_property_ids.add(booking.get("property_id"))

            # Filter out unavailable properties
            properties = [
                p for p in properties if p.get("id") not in unavailable_property_ids
            ]

        # Apply guests filter if provided
        if guests:
            properties = [p for p in properties if p.get("max_guests", 0) >= guests]

        # Apply bedrooms filter if provided
        if bedrooms:
            properties = [p for p in properties if p.get("bedrooms", 0) >= bedrooms]

        # Apply amenities filter if provided
        if amenities:
            filtered_properties = []

            for prop in properties:
                prop_amenities = prop.get("amenities", [])

                # Handle string format (JSON string)
                if isinstance(prop_amenities, str):
                    try:
                        prop_amenities = json.loads(prop_amenities)
                    except:
                        prop_amenities = []

                # Check if all required amenities are present
                if all(amenity in prop_amenities for amenity in amenities):
                    filtered_properties.append(prop)

            properties = filtered_properties

        # Apply max_price filter if provided
        if max_price:
            properties = [p for p in properties if p.get("base_price", 0) <= max_price]

        # Apply limit
        properties = properties[:limit]

        # Add location information to each property
        location_map = {loc["id"]: loc for loc in locations}

        for prop in properties:
            location_id = prop.get("location_id")
            if location_id and location_id in location_map:
                prop["location"] = location_map[location_id]

        return properties

    # User operations

    def get_user_by_phone(self, phone_number: str) -> Optional[Dict]:
        """
        Get a user by phone number.

        Args:
            phone_number (str): User's phone number

        Returns:
            dict: User data if found, None otherwise
        """
        users = self.read_json_file(self.users_file)

        for user in users:
            if user.get("phone_number") == phone_number:
                return user

        return None

    def create_or_update_user(self, user_data: Dict[str, Any]) -> Optional[Dict]:
        """
        Create or update a user.

        Args:
            user_data (dict): User data

        Returns:
            dict: Created/updated user data if successful, None otherwise
        """
        users = self.read_json_file(self.users_file)

        # Check for required fields
        phone_number = user_data.get("phone_number")
        email = user_data.get("email")

        if not phone_number and not email:
            logger.error("User data missing required fields: phone_number or email")
            return None

        # Find existing user by phone or email
        user_idx = None
        for idx, user in enumerate(users):
            if (phone_number and user.get("phone_number") == phone_number) or (
                email and user.get("email") == email
            ):
                user_idx = idx
                break

        if user_idx is not None:
            # Update existing user
            user_data["id"] = users[user_idx]["id"]
            users[user_idx].update(user_data)
            user_obj = users[user_idx]
        else:
            # Create new user with a unique ID
            user_data["id"] = len(users) + 1
            user_data["created_at"] = datetime.utcnow().isoformat()
            users.append(user_data)
            user_obj = user_data

        user_obj["updated_at"] = datetime.utcnow().isoformat()

        if self.write_json_file(self.users_file, users):
            logger.info(f"Created/updated user: {user_obj.get('name')}")
            return user_obj

        return None

    # Booking operations

    def create_booking(self, booking_data: Dict[str, Any]) -> Optional[Dict]:
        """
        Create a new booking.

        Args:
            booking_data (dict): Booking data

        Returns:
            dict: Created booking data if successful, None otherwise
        """
        bookings = self.read_json_file(self.bookings_file)

        # Generate a unique confirmation code
        confirmation_code = str(uuid.uuid4())[:8].upper()

        # Set booking defaults
        booking_data["id"] = len(bookings) + 1
        booking_data["status"] = booking_data.get("status", "pending")
        booking_data["confirmation_code"] = confirmation_code
        booking_data["payment_status"] = booking_data.get("payment_status", "unpaid")
        booking_data["created_at"] = datetime.utcnow().isoformat()
        booking_data["updated_at"] = datetime.utcnow().isoformat()

        bookings.append(booking_data)

        if self.write_json_file(self.bookings_file, bookings):
            logger.info(
                f"Created booking for property ID: {booking_data.get('property_id')}"
            )
            return booking_data

        return None

    def get_booking_by_confirmation_code(
        self, confirmation_code: str
    ) -> Optional[Dict]:
        """
        Get a booking by confirmation code.

        Args:
            confirmation_code (str): Booking confirmation code

        Returns:
            dict: Booking data if found, None otherwise
        """
        bookings = self.read_json_file(self.bookings_file)

        for booking in bookings:
            if booking.get("confirmation_code") == confirmation_code:
                return booking

        return None

    # Conversation log operations

    def log_conversation(self, log_data: Dict[str, Any]) -> Optional[Dict]:
        """
        Log a conversation.

        Args:
            log_data (dict): Conversation log data

        Returns:
            dict: Created log data if successful, None otherwise
        """
        logs = self.read_json_file(self.conversation_logs_file)

        # Set log defaults
        log_data["id"] = len(logs) + 1
        log_data["timestamp"] = datetime.utcnow().isoformat()

        logs.append(log_data)

        if self.write_json_file(self.conversation_logs_file, logs):
            logger.info(f"Logged conversation for call SID: {log_data.get('call_sid')}")
            return log_data

        return None

    def get_conversation_history(
        self, call_sid: str = None, user_id: int = None
    ) -> List[Dict]:
        """
        Get conversation history for a call or user.

        Args:
            call_sid (str, optional): Call SID. Defaults to None.
            user_id (int, optional): User ID. Defaults to None.

        Returns:
            List[Dict]: List of conversation logs
        """
        logs = self.read_json_file(self.conversation_logs_file)

        if call_sid:
            logs = [log for log in logs if log.get("call_sid") == call_sid]
        elif user_id:
            logs = [log for log in logs if log.get("user_id") == user_id]

        # Sort by timestamp
        logs.sort(key=lambda x: x.get("timestamp", ""))

        return logs
