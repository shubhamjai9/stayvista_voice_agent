#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import logging
from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, 
    DateTime, ForeignKey, Text, JSON, create_engine
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

logger = logging.getLogger(__name__)

Base = declarative_base()

class Property(Base):
    """StayVista property model."""
    
    __tablename__ = 'properties'
    
    id = Column(Integer, primary_key=True)
    
    # Basic property information
    stayvista_id = Column(String(100), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    property_type = Column(String(50))  # e.g., villa, apartment, house
    
    # Location
    location_id = Column(Integer, ForeignKey('locations.id'))
    location = relationship("Location", back_populates="properties")
    latitude = Column(Float)
    longitude = Column(Float)
    address = Column(String(255))
    
    # Capacity and rooms
    max_guests = Column(Integer)
    bedrooms = Column(Integer)
    bathrooms = Column(Integer)
    beds = Column(Integer)
    
    # Pricing and availability
    base_price = Column(Float)  # per night in USD
    cleaning_fee = Column(Float)
    service_fee = Column(Float)
    minimum_stay = Column(Integer)  # in nights
    
    # Features
    amenities = Column(JSON)  # List of amenities as JSON
    
    # Media
    thumbnail_url = Column(String(255))
    photo_urls = Column(JSON)  # List of photo URLs as JSON
    
    # Metadata
    rating = Column(Float)
    num_reviews = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    bookings = relationship("Booking", back_populates="property")
    
    def __repr__(self):
        return f"<Property(id={self.id}, name='{self.name}', location='{self.location.name if self.location else 'None'}')>"
    
    @property
    def amenities_list(self):
        """Return amenities as a list of strings."""
        if isinstance(self.amenities, str):
            return json.loads(self.amenities)
        return self.amenities if self.amenities else []


class Location(Base):
    """Location model for StayVista properties."""
    
    __tablename__ = 'locations'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    region = Column(String(100))
    country = Column(String(100), nullable=False)
    
    # Relationships
    properties = relationship("Property", back_populates="location")
    
    def __repr__(self):
        return f"<Location(id={self.id}, name='{self.name}', country='{self.country}')>"


class User(Base):
    """User model for customers booking StayVista properties."""
    
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    phone_number = Column(String(20), unique=True)
    email = Column(String(100), unique=True)
    name = Column(String(100))
    
    # Preferences (as JSON)
    preferences = Column(JSON)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    bookings = relationship("Booking", back_populates="user")
    
    def __repr__(self):
        return f"<User(id={self.id}, name='{self.name}', phone='{self.phone_number}')>"


class Booking(Base):
    """Booking model for StayVista property reservations."""
    
    __tablename__ = 'bookings'
    
    id = Column(Integer, primary_key=True)
    
    # Booking details
    user_id = Column(Integer, ForeignKey('users.id'))
    property_id = Column(Integer, ForeignKey('properties.id'))
    check_in_date = Column(DateTime, nullable=False)
    check_out_date = Column(DateTime, nullable=False)
    num_guests = Column(Integer, default=1)
    
    # Status
    status = Column(String(20), default="pending")  # pending, confirmed, cancelled, completed
    confirmation_code = Column(String(20), unique=True)
    
    # Financial
    total_price = Column(Float)
    payment_status = Column(String(20), default="unpaid")  # unpaid, paid, refunded
    
    # Notes
    special_requests = Column(Text)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="bookings")
    property = relationship("Property", back_populates="bookings")
    
    def __repr__(self):
        return f"<Booking(id={self.id}, property_id={self.property_id}, check_in='{self.check_in_date.date()}')>"


class ConversationLog(Base):
    """Model for logging conversation history."""
    
    __tablename__ = 'conversation_logs'
    
    id = Column(Integer, primary_key=True)
    
    # Call and user information
    call_sid = Column(String(50))
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    caller_number = Column(String(20))
    
    # Message content
    user_message = Column(Text)
    agent_response = Column(Text)
    intent = Column(String(100))
    entities = Column(JSON)
    
    # Context and state
    session_state = Column(JSON)  # Current session state as JSON
    
    # Timestamps
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    user = relationship("User")
    
    def __repr__(self):
        return f"<ConversationLog(id={self.id}, intent='{self.intent}', timestamp='{self.timestamp}')>" 