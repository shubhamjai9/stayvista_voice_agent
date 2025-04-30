#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
import logging
import uuid
from datetime import datetime, timedelta
import argparse
from pathlib import Path
import random

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def ensure_directory(directory):
    """Ensure a directory exists"""
    os.makedirs(directory, exist_ok=True)
    logger.info(f"Directory ensured: {directory}")


def create_empty_json_file(file_path, default_data=None):
    """Create an empty JSON file if it doesn't exist"""
    if default_data is None:
        default_data = []

    if not os.path.exists(file_path):
        with open(file_path, "w") as f:
            json.dump(default_data, f, indent=2)
        logger.info(f"Created empty JSON file: {file_path}")
    else:
        logger.info(f"JSON file already exists: {file_path}")


def generate_sample_data():
    """Generate sample data for the database"""
    # Sample locations
    locations = [
        {
            "id": str(uuid.uuid4()),
            "name": "Malibu",
            "region": "California",
            "country": "USA",
            "latitude": 34.0259,
            "longitude": -118.7798,
            "description": "A beach city in Los Angeles County, California",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Miami Beach",
            "region": "Florida",
            "country": "USA",
            "latitude": 25.7907,
            "longitude": -80.1300,
            "description": "A coastal resort city in Miami-Dade County, Florida",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Aspen",
            "region": "Colorado",
            "country": "USA",
            "latitude": 39.1911,
            "longitude": -106.8175,
            "description": "A ski resort town in the Rocky Mountains",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Santorini",
            "region": "Cyclades",
            "country": "Greece",
            "latitude": 36.3932,
            "longitude": 25.4615,
            "description": "A stunning island in the Aegean Sea",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Bali",
            "region": "Bali Province",
            "country": "Indonesia",
            "latitude": -8.3405,
            "longitude": 115.0920,
            "description": "A beautiful island known for its beaches and temples",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        },
    ]

    # Sample properties with enhanced details
    properties = []
    property_types = [
        "Villa",
        "Apartment",
        "House",
        "Condo",
        "Cabin",
        "Cottage",
        "Penthouse",
        "Bungalow",
    ]
    luxury_features = [
        "Infinity pool",
        "Ocean view",
        "Private chef",
        "Home theater",
        "Wine cellar",
        "Sauna",
        "Terrace",
        "Game room",
        "Gym",
        "Jacuzzi",
        "Private beach access",
        "Fireplace",
        "Heated floors",
        "Smart home system",
        "Concierge service",
    ]
    basic_amenities = [
        "Wifi",
        "Air conditioning",
        "Kitchen",
        "TV",
        "Washer",
        "Dryer",
        "Free parking",
        "Pool",
        "Hot tub",
        "BBQ grill",
        "Gym",
        "Workspace",
        "Breakfast",
        "Hair dryer",
        "Iron",
        "Smoke alarm",
        "First aid kit",
        "Fire extinguisher",
    ]

    for i in range(20):  # Generate 20 properties
        location = random.choice(locations)
        property_type = random.choice(property_types)
        bedrooms = random.randint(1, 6)
        bathrooms = random.randint(1, bedrooms + 1)
        max_guests = bedrooms * 2 + random.randint(0, 2)
        base_price = (
            random.randint(100, 800)
            if property_type != "Villa"
            else random.randint(500, 2000)
        )

        # Select amenities
        num_amenities = random.randint(8, 15)
        amenities = random.sample(
            basic_amenities, min(num_amenities, len(basic_amenities))
        )

        # Add luxury features for higher-priced properties
        if base_price > 300:
            num_luxury = random.randint(2, 6)
            amenities.extend(
                random.sample(luxury_features, min(num_luxury, len(luxury_features)))
            )

        # Create detailed descriptions
        titles = [
            f"Luxurious {property_type} with {bedrooms} bedrooms",
            f"Beautiful {property_type} in {location['name']}",
            f"Stunning {property_type} with views",
            f"Modern {property_type} near {location['name']} center",
            f"Cozy {property_type} perfect for families",
            f"Elegant {property_type} with pool",
        ]

        descriptions = [
            f"Experience luxury living in this stunning {property_type.lower()} located in beautiful {location['name']}. With {bedrooms} spacious bedrooms and {bathrooms} modern bathrooms, this property comfortably accommodates up to {max_guests} guests. The property features {', '.join(amenities[:3])}, and more.",
            f"Welcome to your dream vacation home in {location['name']}! This exquisite {property_type.lower()} offers {bedrooms} bedrooms and {bathrooms} bathrooms, perfect for groups of up to {max_guests} people. Enjoy amenities like {', '.join(amenities[:3])} and many more luxury features.",
            f"Nestled in the heart of {location['name']}, this {property_type.lower()} provides the perfect blend of comfort and luxury. With {bedrooms} bedrooms and {bathrooms} bathrooms, it can host up to {max_guests} guests. The property includes {', '.join(amenities[:3])} among other premium amenities.",
            f"This breathtaking {property_type.lower()} in {location['name']} offers {bedrooms} bedrooms and {bathrooms} bathrooms, accommodating up to {max_guests} guests. You'll love the {', '.join(amenities[:3])} and all the other thoughtful touches throughout this stunning property.",
        ]

        # Sample image URLs (placeholder for now)
        photo_urls = [
            f"https://source.unsplash.com/random/800x600?{property_type.lower()},{i}",
            f"https://source.unsplash.com/random/800x600?{location['name'].lower()},{i+1}",
            f"https://source.unsplash.com/random/800x600?villa,{i+2}",
            f"https://source.unsplash.com/random/800x600?luxury,{i+3}",
            f"https://source.unsplash.com/random/800x600?house,{i+4}",
        ]

        # Create property object
        property_obj = {
            "id": str(uuid.uuid4()),
            "name": random.choice(titles),
            "description": random.choice(descriptions),
            "property_type": property_type,
            "bedrooms": bedrooms,
            "bathrooms": bathrooms,
            "max_guests": max_guests,
            "base_price": base_price,
            "cleaning_fee": int(base_price * 0.1),
            "service_fee": int(base_price * 0.15),
            "check_in_time": "15:00",
            "check_out_time": "11:00",
            "location_id": location["id"],
            "location": location,
            "amenities": amenities,
            "is_available": True,
            "rating": round(random.uniform(3.5, 5.0), 1),
            "num_reviews": random.randint(5, 100),
            "thumbnail_url": photo_urls[0],
            "photo_urls": photo_urls,
            "square_feet": random.randint(800, 3000),
            "minimum_stay": random.randint(1, 3),
            "house_rules": [
                "No smoking",
                "No parties or events",
                "Check-in is anytime after 3PM",
                "Check out by 11AM",
                "Self check-in with keypad",
            ],
            "cancellation_policy": random.choice(
                ["Flexible", "Moderate", "Strict", "Super Strict"]
            ),
            "host": {
                "id": str(uuid.uuid4()),
                "name": f"Host {i+1}",
                "response_rate": random.randint(85, 100),
                "response_time": random.choice(
                    ["within an hour", "within a few hours", "within a day"]
                ),
                "is_superhost": random.choice([True, False]),
                "joined_date": (
                    datetime.now() - timedelta(days=random.randint(100, 2000))
                ).isoformat(),
            },
            "availability": {
                "calendar_updated_at": datetime.now().isoformat(),
                "unavailable_dates": [],
            },
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }

        properties.append(property_obj)

    # Sample users
    users = [
        {
            "id": str(uuid.uuid4()),
            "name": "John Doe",
            "email": "john.doe@example.com",
            "phone_number": "+1234567890",
            "preferences": {
                "preferred_locations": ["Malibu", "Miami Beach"],
                "preferred_amenities": ["Pool", "Wifi", "Kitchen"],
            },
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        },
        {
            "id": str(uuid.uuid4()),
            "name": "Jane Smith",
            "email": "jane.smith@example.com",
            "phone_number": "+1987654321",
            "preferences": {
                "preferred_locations": ["Aspen", "Bali"],
                "preferred_amenities": ["Hot tub", "Wifi", "Air conditioning"],
            },
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        },
    ]

    # Sample bookings
    bookings = [
        {
            "id": str(uuid.uuid4()),
            "property_id": properties[0]["id"],
            "user_id": users[0]["id"],
            "check_in_date": (datetime.now() + timedelta(days=30)).isoformat(),
            "check_out_date": (datetime.now() + timedelta(days=35)).isoformat(),
            "num_guests": 2,
            "total_price": properties[0]["base_price"] * 5
            + properties[0]["cleaning_fee"]
            + properties[0]["service_fee"],
            "status": "confirmed",
            "confirmation_code": f"BK{uuid.uuid4().hex[:8].upper()}",
            "special_requests": "Late check-in, around 7 PM",
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
    ]

    # Sample conversation logs
    conversation_logs = [
        {
            "id": str(uuid.uuid4()),
            "user_id": users[0]["id"],
            "session_id": str(uuid.uuid4()),
            "call_sid": "CA" + uuid.uuid4().hex[:20],
            "conversation": [
                {
                    "timestamp": (datetime.now() - timedelta(minutes=10)).isoformat(),
                    "speaker": "system",
                    "text": "Hello and welcome to StayVista! How can I help you today?",
                },
                {
                    "timestamp": (
                        datetime.now() - timedelta(minutes=9, seconds=45)
                    ).isoformat(),
                    "speaker": "user",
                    "text": "I'm looking for a place in Malibu for next week",
                },
                {
                    "timestamp": (
                        datetime.now() - timedelta(minutes=9, seconds=30)
                    ).isoformat(),
                    "speaker": "system",
                    "text": "Great! I can help you find a place in Malibu. How many people will be staying?",
                },
                {
                    "timestamp": (
                        datetime.now() - timedelta(minutes=9, seconds=15)
                    ).isoformat(),
                    "speaker": "user",
                    "text": "Just 2 people",
                },
                {
                    "timestamp": (datetime.now() - timedelta(minutes=9)).isoformat(),
                    "speaker": "system",
                    "text": "Perfect. And when would you like to check in and check out?",
                },
                {
                    "timestamp": (
                        datetime.now() - timedelta(minutes=8, seconds=45)
                    ).isoformat(),
                    "speaker": "user",
                    "text": "Check in on Friday and check out on Monday",
                },
                {
                    "timestamp": (
                        datetime.now() - timedelta(minutes=8, seconds=30)
                    ).isoformat(),
                    "speaker": "system",
                    "text": "I found 3 properties in Malibu for 2 guests from Friday to Monday. Would you like to hear about them?",
                },
            ],
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
        }
    ]

    return {
        "properties": properties,
        "locations": locations,
        "users": users,
        "bookings": bookings,
        "conversation_logs": conversation_logs,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Initialize JSON database for StayVista voice agent"
    )
    parser.add_argument(
        "--data-dir", type=str, default="data", help="Directory to store JSON files"
    )
    args = parser.parse_args()

    # Ensure data directory exists
    ensure_directory(args.data_dir)

    # Define file paths
    properties_file = os.path.join(args.data_dir, "properties.json")
    locations_file = os.path.join(args.data_dir, "locations.json")
    users_file = os.path.join(args.data_dir, "users.json")
    bookings_file = os.path.join(args.data_dir, "bookings.json")
    conversation_logs_file = os.path.join(args.data_dir, "conversation_logs.json")

    # Generate sample data
    sample_data = generate_sample_data()

    # Create JSON files
    with open(properties_file, "w") as f:
        json.dump(sample_data["properties"], f, indent=2)
    logger.info(
        f"Created properties file with {len(sample_data['properties'])} records: {properties_file}"
    )

    with open(locations_file, "w") as f:
        json.dump(sample_data["locations"], f, indent=2)
    logger.info(
        f"Created locations file with {len(sample_data['locations'])} records: {locations_file}"
    )

    with open(users_file, "w") as f:
        json.dump(sample_data["users"], f, indent=2)
    logger.info(
        f"Created users file with {len(sample_data['users'])} records: {users_file}"
    )

    with open(bookings_file, "w") as f:
        json.dump(sample_data["bookings"], f, indent=2)
    logger.info(
        f"Created bookings file with {len(sample_data['bookings'])} records: {bookings_file}"
    )

    with open(conversation_logs_file, "w") as f:
        json.dump(sample_data["conversation_logs"], f, indent=2)
    logger.info(
        f"Created conversation logs file with {len(sample_data['conversation_logs'])} records: {conversation_logs_file}"
    )

    logger.info("JSON database initialization complete!")


if __name__ == "__main__":
    main()
