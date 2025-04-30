#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
import json
import uuid
import logging
import random
import string
from pathlib import Path
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

def generate_confirmation_code(length=6):
    """
    Generate a random confirmation code for bookings.
    
    Args:
        length (int, optional): Length of the code. Defaults to 6.
    
    Returns:
        str: Random confirmation code
    """
    # Use uppercase letters and digits for readability
    chars = string.ascii_uppercase + string.digits
    # Exclude confusing characters like O, 0, I, 1
    chars = chars.replace('O', '').replace('0', '').replace('I', '').replace('1', '')
    
    return ''.join(random.choices(chars, k=length))

def parse_date_str(date_str):
    """
    Parse a date string into a datetime object.
    
    Args:
        date_str (str): Date string to parse
    
    Returns:
        datetime: Parsed datetime object, or None if parsing fails
    """
    # List of date formats to try
    formats = [
        "%Y-%m-%d",  # 2023-06-15
        "%B %d",     # June 15
        "%b %d",     # Jun 15
        "%d %B",     # 15 June
        "%d %b",     # 15 Jun
        "%B %d, %Y", # June 15, 2023
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

def mask_phone_number(phone_number):
    """
    Mask a phone number for privacy.
    
    Args:
        phone_number (str): Phone number to mask
    
    Returns:
        str: Masked phone number
    """
    if not phone_number:
        return ""
    
    # Remove non-digit characters
    digits = re.sub(r'\D', '', phone_number)
    
    # If less than 4 digits, don't mask
    if len(digits) < 4:
        return phone_number
    
    # Keep last 4 digits, mask the rest
    masked = '*' * (len(digits) - 4) + digits[-4:]
    
    # If original had a specific format, try to preserve it
    if '+' in phone_number:
        return '+' + masked
    if '-' in phone_number:
        # Simple approach: just add a dash before the last 4 digits
        return masked[:-4] + '-' + masked[-4:]
    
    return masked

def mask_email(email):
    """
    Mask an email address for privacy.
    
    Args:
        email (str): Email address to mask
    
    Returns:
        str: Masked email
    """
    if not email or '@' not in email:
        return email
    
    username, domain = email.split('@', 1)
    
    # Mask username except first and last character
    if len(username) > 2:
        masked_username = username[0] + '*' * (len(username) - 2) + username[-1]
    else:
        masked_username = username
    
    return f"{masked_username}@{domain}"

def extract_entities_from_text(text, entity_patterns):
    """
    Extract entities from text using regex patterns.
    
    Args:
        text (str): Text to extract entities from
        entity_patterns (dict): Dictionary of entity names and their regex patterns
    
    Returns:
        dict: Dictionary of extracted entities
    """
    entities = {}
    
    for entity_name, pattern in entity_patterns.items():
        matches = re.findall(pattern, text, re.IGNORECASE)
        if matches:
            entities[entity_name] = matches
    
    return entities

def log_conversation(call_sid, user_message, agent_response, intent=None, entities=None, user_id=None):
    """
    Log a conversation interaction to file.
    
    Args:
        call_sid (str): Call SID from Twilio
        user_message (str): User's message
        agent_response (str): Agent's response
        intent (str, optional): Recognized intent. Defaults to None.
        entities (dict, optional): Extracted entities. Defaults to None.
        user_id (str, optional): User ID if known. Defaults to None.
    """
    timestamp = datetime.now().isoformat()
    
    log_entry = {
        "timestamp": timestamp,
        "call_sid": call_sid,
        "user_id": user_id,
        "user_message": user_message,
        "agent_response": agent_response,
        "intent": intent,
        "entities": entities or {}
    }
    
    log_dir = Path(__file__).parent.parent / "logs"
    log_dir.mkdir(exist_ok=True)
    
    log_file = log_dir / "conversation_logs.jsonl"
    
    with open(log_file, "a") as f:
        f.write(json.dumps(log_entry) + "\n")

def get_date_range(start_date, end_date):
    """
    Get a list of dates between start_date and end_date.
    
    Args:
        start_date (datetime): Start date
        end_date (datetime): End date
    
    Returns:
        list: List of dates as datetime objects
    """
    if not start_date or not end_date:
        return []
    
    dates = []
    current_date = start_date
    
    while current_date <= end_date:
        dates.append(current_date)
        current_date += timedelta(days=1)
    
    return dates 