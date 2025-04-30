#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
import logging
import random
import string
from pathlib import Path
from datetime import datetime, timedelta
from typing import Any, Text, Dict, List, Optional

from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet, AllSlotsReset, FollowupAction

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Import database manager
import sys

sys.path.append(str(Path(__file__).parent.parent.parent))
from database.json_db_manager import JsonDatabaseManager

# Load environment variables
from dotenv import load_dotenv

env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

# Initialize database manager
db_manager = JsonDatabaseManager(os.getenv("DATA_DIR", "data"))


def parse_date(date_str: str) -> Optional[datetime]:
    """
    Parse date string into datetime object.

    Args:
        date_str (str): Date string from user input

    Returns:
        datetime: Parsed datetime object, or None if parsing fails
    """
    try:
        # Try common date formats
        formats = [
            "%Y-%m-%d",  # 2023-06-15
            "%B %d",  # June 15
            "%b %d",  # Jun 15
            "%d %B",  # 15 June
            "%d %b",  # 15 Jun
            "%B %d, %Y",  # June 15, 2023
            "%d/%m/%Y",  # 15/06/2023
            "%m/%d/%Y",  # 06/15/2023
        ]

        for fmt in formats:
            try:
                date_obj = datetime.strptime(date_str, fmt)
                # Add current year if year not provided
                if "%Y" not in fmt and date_obj.year == 1900:
                    date_obj = date_obj.replace(year=datetime.now().year)
                return date_obj
            except ValueError:
                continue

        # If all formats fail, return None
        logger.warning(f"Failed to parse date: {date_str}")
        return None

    except Exception as e:
        logger.error(f"Error parsing date: {e}")
        return None


class ActionSearchProperties(Action):
    """Action to search for properties based on user criteria."""

    def name(self) -> Text:
        return "action_search_properties"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:

        try:
            # Extract search criteria from slots
            location = tracker.get_slot("location")
            check_in_date_str = tracker.get_slot("check_in_date")
            check_out_date_str = tracker.get_slot("check_out_date")
            guests = tracker.get_slot("number_of_guests")
            bedrooms = tracker.get_slot("number_of_rooms")
            amenities = tracker.get_slot("amenities")
            max_price = tracker.get_slot("max_price")

            # Convert string dates to datetime objects
            check_in_date = parse_date(check_in_date_str) if check_in_date_str else None
            check_out_date = (
                parse_date(check_out_date_str) if check_out_date_str else None
            )

            # Validate search criteria
            if not location:
                dispatcher.utter_message(
                    text="I need to know where you'd like to stay."
                )
                return [FollowupAction("utter_ask_location")]

            # Search for properties
            properties = db_manager.search_properties(
                location=location,
                check_in=check_in_date,
                check_out=check_out_date,
                guests=guests,
                bedrooms=bedrooms,
                amenities=amenities,
                max_price=max_price,
            )

            # Handle search results
            if not properties:
                dispatcher.utter_message(
                    text=f"I'm sorry, I couldn't find any properties in {location} that match your criteria."
                )
                return []

            # Store search results in a slot
            properties_data = []
            for prop in properties[
                :5
            ]:  # Limit to top 5 properties for voice interaction
                property_data = {
                    "id": prop.id,
                    "name": prop.name,
                    "location": prop.location.name if prop.location else "Unknown",
                    "price": prop.base_price,
                    "bedrooms": prop.bedrooms,
                    "bathrooms": prop.bathrooms,
                    "max_guests": prop.max_guests,
                    "amenities": prop.amenities_list,
                    "rating": prop.rating,
                }
                properties_data.append(property_data)

            # Prepare response
            result_text = f"I found {len(properties)} properties in {location}. "

            if len(properties) > 0:
                result_text += "Here are the top options:\n\n"

                for i, prop in enumerate(properties_data):
                    result_text += f"{i+1}. {prop['name']} in {prop['location']}: "
                    result_text += f"${prop['price']} per night, "
                    result_text += f"{prop['bedrooms']} bedrooms, "
                    result_text += f"up to {prop['max_guests']} guests. "
                    if prop["rating"]:
                        result_text += f"Rated {prop['rating']}/5. "
                    result_text += "\n"

                # Ask if user wants more details
                result_text += "\nWould you like to know more details about any of these properties?"

            dispatcher.utter_message(text=result_text)

            return [SlotSet("search_results", properties_data)]

        except Exception as e:
            logger.error(f"Error searching properties: {e}")
            dispatcher.utter_message(
                text="I'm sorry, I encountered an error while searching for properties. Please try again."
            )
            return []


class ActionProvidePropertyDetails(Action):
    """Action to provide detailed information about a property."""

    def name(self) -> Text:
        return "action_provide_property_details"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:

        try:
            # Get search results from slot
            properties_data = tracker.get_slot("search_results")

            if not properties_data or len(properties_data) == 0:
                dispatcher.utter_message(
                    text="I don't have any property details to share. Let's search for properties first."
                )
                return [FollowupAction("utter_ask_location")]

            # Determine which property to provide details for
            # For now, just use the first one
            property_data = properties_data[0]

            # Prepare detailed information
            details = f"Here are the details for {property_data['name']} in {property_data['location']}:\n\n"

            details += f"Price: ${property_data['price']} per night\n"
            details += f"Bedrooms: {property_data['bedrooms']}\n"
            details += f"Bathrooms: {property_data['bathrooms']}\n"
            details += f"Maximum guests: {property_data['max_guests']}\n"

            if property_data.get("amenities"):
                details += f"Amenities: {', '.join(property_data['amenities'][:5])}"
                if len(property_data["amenities"]) > 5:
                    details += f" and {len(property_data['amenities']) - 5} more"
                details += "\n"

            if property_data.get("rating"):
                details += f"Rating: {property_data['rating']}/5\n"

            # Add a prompt to book
            details += "\nWould you like to book this property?"

            dispatcher.utter_message(text=details)

            return [SlotSet("selected_property_id", property_data["id"])]

        except Exception as e:
            logger.error(f"Error providing property details: {e}")
            dispatcher.utter_message(
                text="I'm sorry, I encountered an error while retrieving property details. Please try again."
            )
            return []


class ActionBookProperty(Action):
    """Action to book a property."""

    def name(self) -> Text:
        return "action_book_property"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:

        try:
            # Get necessary information from slots
            property_id = tracker.get_slot("selected_property_id")
            check_in_date_str = tracker.get_slot("check_in_date")
            check_out_date_str = tracker.get_slot("check_out_date")
            guests = tracker.get_slot("number_of_guests")
            user_name = tracker.get_slot("user_name")
            user_email = tracker.get_slot("user_email")
            user_phone = tracker.get_slot("user_phone")

            # Validate required information
            if not property_id:
                dispatcher.utter_message(
                    text="I need to know which property you'd like to book. Let's search for properties first."
                )
                return [FollowupAction("utter_ask_location")]

            if not check_in_date_str or not check_out_date_str:
                dispatcher.utter_message(
                    text="I need to know your check-in and check-out dates."
                )
                return [FollowupAction("utter_ask_check_in_date")]

            if not guests:
                dispatcher.utter_message(
                    text="I need to know how many guests will be staying."
                )
                return [FollowupAction("utter_ask_guests")]

            # Convert string dates to datetime objects
            check_in_date = parse_date(check_in_date_str)
            check_out_date = parse_date(check_out_date_str)

            if not check_in_date or not check_out_date:
                dispatcher.utter_message(
                    text="I couldn't understand your dates. Please provide them in a format like 'June 15 to June 20'."
                )
                return [FollowupAction("utter_ask_check_in_date")]

            # Create or update user
            user_data = {
                "phone_number": user_phone,
                "email": user_email,
                "name": user_name,
            }
            user = db_manager.create_or_update_user(user_data)

            if not user:
                dispatcher.utter_message(
                    text="I'm sorry, there was an error creating your user profile. Please try again."
                )
                return []

            # Create booking
            booking_data = {
                "property_id": property_id,
                "user_id": user.id,
                "check_in_date": check_in_date,
                "check_out_date": check_out_date,
                "num_guests": guests,
                "status": "confirmed",
                "confirmation_code": "".join(
                    random.choices(string.ascii_uppercase + string.digits, k=6)
                ),
            }
            booking = db_manager.create_booking(booking_data)

            if not booking:
                dispatcher.utter_message(
                    text="I'm sorry, there was an error creating your booking. Please try again."
                )
                return []

            # Get property information
            property_data = None
            search_results = tracker.get_slot("search_results")
            if search_results:
                for prop in search_results:
                    if prop["id"] == property_id:
                        property_data = prop
                        break

            # Prepare confirmation message
            property_name = property_data["name"] if property_data else "your property"
            location = (
                property_data["location"] if property_data else "your destination"
            )

            confirmation = f"Great! Your booking is confirmed. You'll be staying at {property_name} in {location} "
            confirmation += f"from {check_in_date_str} to {check_out_date_str} with {guests} guests. "
            confirmation += f"Your confirmation code is {booking.confirmation_code}. "
            confirmation += f"A confirmation email will be sent to {user_email}. "
            confirmation += "Thank you for booking with StayVista!"

            dispatcher.utter_message(text=confirmation)

            return [SlotSet("booking_id", booking.confirmation_code)]

        except Exception as e:
            logger.error(f"Error booking property: {e}")
            dispatcher.utter_message(
                text="I'm sorry, I encountered an error while creating your booking. Please try again."
            )
            return []


class ActionCancelBooking(Action):
    """Action to cancel a booking."""

    def name(self) -> Text:
        return "action_cancel_booking"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:

        try:
            # Get booking ID from slot
            booking_id = tracker.get_slot("booking_id")

            if not booking_id:
                dispatcher.utter_message(
                    text="I need your booking confirmation code to cancel your reservation. Do you have it?"
                )
                return []

            # Get booking from database
            booking = db_manager.get_booking_by_confirmation_code(booking_id)

            if not booking:
                dispatcher.utter_message(
                    text=f"I couldn't find a booking with confirmation code {booking_id}. Please check the code and try again."
                )
                return []

            # Update booking status to canceled
            booking.status = "cancelled"
            db_manager.session.commit()

            # Prepare cancellation message
            cancellation = (
                f"Your booking with confirmation code {booking_id} has been cancelled. "
            )
            cancellation += "If you paid any deposit, it will be refunded according to the property's cancellation policy. "
            cancellation += "Is there anything else I can help you with?"

            dispatcher.utter_message(text=cancellation)

            return [SlotSet("booking_id", None)]

        except Exception as e:
            logger.error(f"Error cancelling booking: {e}")
            dispatcher.utter_message(
                text="I'm sorry, I encountered an error while cancelling your booking. Please try again."
            )
            return []


class ActionCheckAvailability(Action):
    """Action to check property availability."""

    def name(self) -> Text:
        return "action_check_availability"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:

        try:
            # Get necessary information from slots
            property_id = tracker.get_slot("selected_property_id")
            check_in_date_str = tracker.get_slot("check_in_date")
            check_out_date_str = tracker.get_slot("check_out_date")

            # Validate required information
            if not property_id:
                dispatcher.utter_message(
                    text="I need to know which property you'd like to check availability for. Let's search for properties first."
                )
                return [FollowupAction("utter_ask_location")]

            if not check_in_date_str or not check_out_date_str:
                dispatcher.utter_message(
                    text="I need to know your check-in and check-out dates to check availability."
                )
                return [FollowupAction("utter_ask_check_in_date")]

            # Convert string dates to datetime objects
            check_in_date = parse_date(check_in_date_str)
            check_out_date = parse_date(check_out_date_str)

            if not check_in_date or not check_out_date:
                dispatcher.utter_message(
                    text="I couldn't understand your dates. Please provide them in a format like 'June 15 to June 20'."
                )
                return [FollowupAction("utter_ask_check_in_date")]

            # Check availability in the database
            # For the sake of this example, we'll just return that it's available
            # In a real implementation, you would check against existing bookings

            # Get property information
            property_data = None
            search_results = tracker.get_slot("search_results")
            if search_results:
                for prop in search_results:
                    if prop["id"] == property_id:
                        property_data = prop
                        break

            property_name = property_data["name"] if property_data else "this property"

            # Prepare availability message
            availability = f"Good news! {property_name} is available for your dates from {check_in_date_str} to {check_out_date_str}. "
            availability += "Would you like to proceed with booking?"

            dispatcher.utter_message(text=availability)

            return []

        except Exception as e:
            logger.error(f"Error checking availability: {e}")
            dispatcher.utter_message(
                text="I'm sorry, I encountered an error while checking availability. Please try again."
            )
            return []


class ActionResetBookingForm(Action):
    """Action to reset all booking-related slots."""

    def name(self) -> Text:
        return "action_reset_booking_form"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:

        try:
            # Reset all slots
            return [AllSlotsReset()]

        except Exception as e:
            logger.error(f"Error resetting booking form: {e}")
            return []
