#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import logging
import requests
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

class RasaConnector:
    """
    Connector to the Rasa NLU server for intent recognition and dialog management.
    """
    
    def __init__(self, rasa_url):
        """
        Initialize the Rasa connector.
        
        Args:
            rasa_url (str): URL of the Rasa server
        """
        self.rasa_url = rasa_url.rstrip('/')
        logger.info(f"Initialized Rasa connector to {rasa_url}")
    
    def get_response(self, message, sender_id=None):
        """
        Get a response from Rasa for a user message.
        
        Args:
            message (str): User message
            sender_id (str, optional): Unique sender ID for conversation tracking.
                                     Defaults to None (generates a new session).
            
        Returns:
            str: Response text from Rasa
        """
        try:
            # Prepare the request payload
            payload = {
                "message": message
            }
            
            if sender_id:
                payload["sender"] = sender_id
            
            # Make the request to Rasa
            response = requests.post(
                f"{self.rasa_url}/webhooks/rest/webhook",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            response.raise_for_status()
            
            # Process the response
            response_data = response.json()
            
            # Extract the text responses
            if response_data:
                # Combine all text responses
                messages = [msg.get("text", "") for msg in response_data if "text" in msg]
                return " ".join(messages)
            else:
                logger.warning("Received empty response from Rasa")
                return "I'm sorry, I'm having trouble understanding. Could you please rephrase that?"
            
        except requests.RequestException as e:
            logger.error(f"Error communicating with Rasa: {e}")
            return "I'm sorry, I'm currently experiencing technical difficulties. Please try again later."
    
    def parse_message(self, message):
        """
        Parse a message to extract intents and entities using Rasa NLU.
        
        Args:
            message (str): Message to parse
            
        Returns:
            dict: Parsed result with intents and entities
        """
        try:
            # Make request to Rasa's parse endpoint
            response = requests.post(
                f"{self.rasa_url}/model/parse",
                json={"text": message},
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            response.raise_for_status()
            
            # Return the parsed result
            return response.json()
            
        except requests.RequestException as e:
            logger.error(f"Error parsing message with Rasa: {e}")
            return {
                "intent": {"name": "none", "confidence": 0.0},
                "entities": [],
                "text": message
            }
    
    def get_intent(self, message):
        """
        Extract the top intent from a message.
        
        Args:
            message (str): Message to analyze
            
        Returns:
            tuple: (intent_name, confidence)
        """
        parse_result = self.parse_message(message)
        intent = parse_result.get("intent", {})
        return intent.get("name", "none"), intent.get("confidence", 0.0)
    
    def get_entities(self, message):
        """
        Extract entities from a message.
        
        Args:
            message (str): Message to analyze
            
        Returns:
            list: List of entity dictionaries
        """
        parse_result = self.parse_message(message)
        return parse_result.get("entities", [])
    
    def trigger_intent(self, intent, sender_id=None, entities=None):
        """
        Manually trigger a specific intent in Rasa.
        
        Args:
            intent (str): Intent name to trigger
            sender_id (str, optional): Unique sender ID. Defaults to None.
            entities (list, optional): List of entities. Defaults to None.
            
        Returns:
            str: Response text from Rasa
        """
        try:
            # Prepare the request payload
            payload = {
                "name": intent
            }
            
            if sender_id:
                payload["sender"] = sender_id
            
            if entities:
                payload["entities"] = entities
            
            # Make the request to Rasa
            response = requests.post(
                f"{self.rasa_url}/conversations/{sender_id or 'default'}/trigger_intent",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            response.raise_for_status()
            
            # Process the response
            response_data = response.json()
            
            # Extract messages from the response
            messages = []
            for msg in response_data.get("messages", []):
                if msg.get("type") == "text":
                    messages.append(msg.get("text", ""))
            
            return " ".join(messages)
            
        except requests.RequestException as e:
            logger.error(f"Error triggering intent in Rasa: {e}")
            return "I'm sorry, I'm currently experiencing technical difficulties. Please try again later."
    
    def get_tracker(self, sender_id):
        """
        Get the current conversation tracker for a sender.
        
        Args:
            sender_id (str): Unique sender ID
            
        Returns:
            dict: Tracker data
        """
        try:
            response = requests.get(
                f"{self.rasa_url}/conversations/{sender_id}/tracker",
                timeout=10
            )
            response.raise_for_status()
            
            return response.json()
            
        except requests.RequestException as e:
            logger.error(f"Error retrieving tracker from Rasa: {e}")
            return {"events": [], "slots": {}}
    
    def get_slot(self, sender_id, slot_name):
        """
        Get the value of a specific slot for a conversation.
        
        Args:
            sender_id (str): Unique sender ID
            slot_name (str): Name of the slot to retrieve
            
        Returns:
            any: Slot value, or None if not set
        """
        tracker = self.get_tracker(sender_id)
        return tracker.get("slots", {}).get(slot_name)
    
    def set_slot(self, sender_id, slot_name, slot_value):
        """
        Set a slot value for a conversation.
        
        Args:
            sender_id (str): Unique sender ID
            slot_name (str): Name of the slot to set
            slot_value (any): Value to set the slot to
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            response = requests.post(
                f"{self.rasa_url}/conversations/{sender_id}/tracker/slots",
                json={slot_name: slot_value},
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            response.raise_for_status()
            
            return True
            
        except requests.RequestException as e:
            logger.error(f"Error setting slot in Rasa: {e}")
            return False
    
    def restart_conversation(self, sender_id):
        """
        Restart a conversation.
        
        Args:
            sender_id (str): Unique sender ID
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            response = requests.post(
                f"{self.rasa_url}/conversations/{sender_id}/tracker/events",
                json={"event": "restart"},
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            response.raise_for_status()
            
            return True
            
        except requests.RequestException as e:
            logger.error(f"Error restarting conversation in Rasa: {e}")
            return False 