#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import logging
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple, Union
from sqlalchemy import create_engine, and_, or_, func
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.exc import SQLAlchemyError

from .models import Base, Property, Location, User, Booking, ConversationLog

logger = logging.getLogger(__name__)

class DatabaseManager:
    """
    Database manager for StayVista voice agent.
    Handles all database operations.
    """
    
    def __init__(self, database_url):
        """
        Initialize the database manager.
        
        Args:
            database_url (str): Database connection URL
        """
        self.database_url = database_url
        
        try:
            # Create engine and session
            self.engine = create_engine(database_url)
            session_factory = sessionmaker(bind=self.engine)
            self.Session = scoped_session(session_factory)
            
            logger.info("Database connection initialized")
        except Exception as e:
            logger.error(f"Failed to initialize database connection: {e}")
            raise
    
    def create_tables(self):
        """
        Create all database tables if they don't exist.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            Base.metadata.create_all(self.engine)
            logger.info("Database tables created")
            return True
        except SQLAlchemyError as e:
            logger.error(f"Failed to create database tables: {e}")
            return False
    
    # Location operations
    
    def get_location_by_name(self, name: str, country: str = None) -> Optional[Location]:
        """
        Get a location by name.
        
        Args:
            name (str): Location name
            country (str, optional): Country name. Defaults to None.
            
        Returns:
            Location: Location object if found, None otherwise
        """
        session = self.Session()
        try:
            query = session.query(Location).filter(func.lower(Location.name) == func.lower(name))
            
            if country:
                query = query.filter(func.lower(Location.country) == func.lower(country))
            
            return query.first()
        except SQLAlchemyError as e:
            logger.error(f"Error getting location by name: {e}")
            return None
        finally:
            session.close()
    
    def create_location(self, name: str, country: str, region: str = None) -> Optional[Location]:
        """
        Create a new location.
        
        Args:
            name (str): Location name
            country (str): Country name
            region (str, optional): Region name. Defaults to None.
            
        Returns:
            Location: Created location object if successful, None otherwise
        """
        session = self.Session()
        try:
            # Check if location already exists
            existing = self.get_location_by_name(name, country)
            if existing:
                return existing
            
            # Create new location
            location = Location(name=name, country=country, region=region)
            session.add(location)
            session.commit()
            logger.info(f"Created location: {name}, {country}")
            return location
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Error creating location: {e}")
            return None
        finally:
            session.close()
    
    # Property operations
    
    def get_property_by_stayvista_id(self, stayvista_id: str) -> Optional[Property]:
        """
        Get a property by StayVista ID.
        
        Args:
            stayvista_id (str): StayVista property ID
            
        Returns:
            Property: Property object if found, None otherwise
        """
        session = self.Session()
        try:
            return session.query(Property).filter(Property.stayvista_id == stayvista_id).first()
        except SQLAlchemyError as e:
            logger.error(f"Error getting property by StayVista ID: {e}")
            return None
        finally:
            session.close()
    
    def create_or_update_property(self, property_data: Dict[str, Any]) -> Optional[Property]:
        """
        Create or update a property.
        
        Args:
            property_data (dict): Property data
            
        Returns:
            Property: Created/updated property object if successful, None otherwise
        """
        session = self.Session()
        try:
            # Check if property already exists
            stayvista_id = property_data.get("stayvista_id")
            if not stayvista_id:
                logger.error("Property data missing required field: stayvista_id")
                return None
            
            # Get or create the property
            property_obj = self.get_property_by_stayvista_id(stayvista_id)
            if property_obj:
                # Update existing property
                for key, value in property_data.items():
                    if key != "location" and hasattr(property_obj, key):
                        setattr(property_obj, key, value)
            else:
                # Create new property
                # Handle location separately
                location_data = property_data.pop("location", None)
                if location_data:
                    location = self.get_location_by_name(location_data["name"], location_data.get("country"))
                    if not location:
                        location = self.create_location(
                            location_data["name"],
                            location_data.get("country", "Unknown"),
                            location_data.get("region")
                        )
                    property_data["location_id"] = location.id if location else None
                
                property_obj = Property(**property_data)
                session.add(property_obj)
            
            session.commit()
            logger.info(f"Created/updated property: {property_obj.name}")
            return property_obj
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Error creating/updating property: {e}")
            return None
        finally:
            session.close()
    
    def search_properties(self, 
                        location: str = None, 
                        check_in: datetime = None, 
                        check_out: datetime = None,
                        guests: int = None,
                        bedrooms: int = None,
                        amenities: List[str] = None,
                        max_price: float = None,
                        limit: int = 10) -> List[Property]:
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
            List[Property]: List of matching properties
        """
        session = self.Session()
        try:
            # Start with a base query
            query = session.query(Property)
            
            # Apply location filter if provided
            if location:
                location_obj = self.get_location_by_name(location)
                if location_obj:
                    query = query.filter(Property.location_id == location_obj.id)
                else:
                    # If location not found, return empty list
                    return []
            
            # Apply date filter if provided
            if check_in and check_out:
                # Find bookings that overlap with requested dates
                unavailable_property_ids = session.query(Booking.property_id).filter(
                    and_(
                        Booking.status != 'cancelled',
                        or_(
                            and_(
                                Booking.check_in_date <= check_in,
                                Booking.check_out_date > check_in
                            ),
                            and_(
                                Booking.check_in_date < check_out,
                                Booking.check_out_date >= check_out
                            ),
                            and_(
                                Booking.check_in_date >= check_in,
                                Booking.check_out_date <= check_out
                            )
                        )
                    )
                ).all()
                
                unavailable_ids = [id for (id,) in unavailable_property_ids]
                if unavailable_ids:
                    query = query.filter(Property.id.notin_(unavailable_ids))
            
            # Apply guest filter if provided
            if guests:
                query = query.filter(Property.max_guests >= guests)
            
            # Apply bedroom filter if provided
            if bedrooms:
                query = query.filter(Property.bedrooms >= bedrooms)
            
            # Apply price filter if provided
            if max_price:
                query = query.filter(Property.base_price <= max_price)
            
            # Apply amenities filter if provided
            # Note: This is a simple implementation and may not be efficient for all databases
            properties = query.limit(limit).all()
            
            if amenities:
                # Filter properties that have all required amenities
                filtered_properties = []
                for prop in properties:
                    prop_amenities = prop.amenities_list
                    if all(amenity.lower() in [a.lower() for a in prop_amenities] for amenity in amenities):
                        filtered_properties.append(prop)
                return filtered_properties
            
            return properties
        except SQLAlchemyError as e:
            logger.error(f"Error searching properties: {e}")
            return []
        finally:
            session.close()
    
    # User operations
    
    def get_user_by_phone(self, phone_number: str) -> Optional[User]:
        """
        Get a user by phone number.
        
        Args:
            phone_number (str): User's phone number
            
        Returns:
            User: User object if found, None otherwise
        """
        session = self.Session()
        try:
            return session.query(User).filter(User.phone_number == phone_number).first()
        except SQLAlchemyError as e:
            logger.error(f"Error getting user by phone: {e}")
            return None
        finally:
            session.close()
    
    def create_or_update_user(self, user_data: Dict[str, Any]) -> Optional[User]:
        """
        Create or update a user.
        
        Args:
            user_data (dict): User data
            
        Returns:
            User: Created/updated user object if successful, None otherwise
        """
        session = self.Session()
        try:
            # Check if user already exists
            phone_number = user_data.get("phone_number")
            if not phone_number:
                logger.error("User data missing required field: phone_number")
                return None
            
            # Get or create the user
            user = self.get_user_by_phone(phone_number)
            if user:
                # Update existing user
                for key, value in user_data.items():
                    if hasattr(user, key):
                        setattr(user, key, value)
            else:
                # Create new user
                user = User(**user_data)
                session.add(user)
            
            session.commit()
            logger.info(f"Created/updated user: {user.name if user.name else phone_number}")
            return user
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Error creating/updating user: {e}")
            return None
        finally:
            session.close()
    
    # Booking operations
    
    def create_booking(self, booking_data: Dict[str, Any]) -> Optional[Booking]:
        """
        Create a new booking.
        
        Args:
            booking_data (dict): Booking data
            
        Returns:
            Booking: Created booking object if successful, None otherwise
        """
        session = self.Session()
        try:
            # Validate required fields
            required_fields = ["property_id", "check_in_date", "check_out_date"]
            for field in required_fields:
                if field not in booking_data:
                    logger.error(f"Booking data missing required field: {field}")
                    return None
            
            # Check if property exists
            property_obj = session.query(Property).get(booking_data["property_id"])
            if not property_obj:
                logger.error(f"Property with ID {booking_data['property_id']} not found")
                return None
            
            # Create the booking
            booking = Booking(**booking_data)
            session.add(booking)
            session.commit()
            
            logger.info(f"Created booking: {booking.id} for property {property_obj.name}")
            return booking
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Error creating booking: {e}")
            return None
        finally:
            session.close()
    
    def get_booking_by_confirmation_code(self, confirmation_code: str) -> Optional[Booking]:
        """
        Get a booking by confirmation code.
        
        Args:
            confirmation_code (str): Booking confirmation code
            
        Returns:
            Booking: Booking object if found, None otherwise
        """
        session = self.Session()
        try:
            return session.query(Booking).filter(Booking.confirmation_code == confirmation_code).first()
        except SQLAlchemyError as e:
            logger.error(f"Error getting booking by confirmation code: {e}")
            return None
        finally:
            session.close()
    
    # Conversation log operations
    
    def log_conversation(self, log_data: Dict[str, Any]) -> Optional[ConversationLog]:
        """
        Log a conversation interaction.
        
        Args:
            log_data (dict): Log data
            
        Returns:
            ConversationLog: Created log object if successful, None otherwise
        """
        session = self.Session()
        try:
            # Create the log entry
            log = ConversationLog(**log_data)
            session.add(log)
            session.commit()
            
            logger.info(f"Logged conversation: {log.id}, intent: {log.intent}")
            return log
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Error logging conversation: {e}")
            return None
        finally:
            session.close()
    
    def get_conversation_history(self, call_sid: str = None, user_id: int = None) -> List[ConversationLog]:
        """
        Get conversation history for a call or user.
        
        Args:
            call_sid (str, optional): Twilio call SID. Defaults to None.
            user_id (int, optional): User ID. Defaults to None.
            
        Returns:
            List[ConversationLog]: List of conversation logs
        """
        session = self.Session()
        try:
            query = session.query(ConversationLog).order_by(ConversationLog.timestamp.asc())
            
            if call_sid:
                query = query.filter(ConversationLog.call_sid == call_sid)
            
            if user_id:
                query = query.filter(ConversationLog.user_id == user_id)
            
            return query.all()
        except SQLAlchemyError as e:
            logger.error(f"Error getting conversation history: {e}")
            return []
        finally:
            session.close()
    
    def close(self):
        """Close database connections."""
        self.Session.remove()
        if self.engine:
            self.engine.dispose()
            logger.info("Database connections closed") 