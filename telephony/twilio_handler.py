#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import logging
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse, Gather
from twilio.base.exceptions import TwilioRestException

logger = logging.getLogger(__name__)

class TwilioHandler:
    """
    Handler for Twilio telephony integration.
    """
    
    def __init__(self, account_sid, auth_token, phone_number):
        """
        Initialize the Twilio client.
        
        Args:
            account_sid (str): Twilio account SID
            auth_token (str): Twilio auth token
            phone_number (str): Twilio phone number
        """
        self.account_sid = account_sid
        self.auth_token = auth_token
        self.phone_number = phone_number
        self.client = Client(account_sid, auth_token)
        logger.info("TwilioHandler initialized")
    
    def make_call(self, to_number, webhook_url):
        """
        Initiate an outbound call.
        
        Args:
            to_number (str): The recipient's phone number
            webhook_url (str): URL to handle the call
            
        Returns:
            call: Twilio call object
        """
        try:
            call = self.client.calls.create(
                to=to_number,
                from_=self.phone_number,
                url=webhook_url,
                status_callback=f"{webhook_url}/status_callback",
                status_callback_event=["initiated", "ringing", "answered", "completed"],
                status_callback_method="POST"
            )
            logger.info(f"Call initiated to {to_number}, SID: {call.sid}")
            return call
        except TwilioRestException as e:
            logger.error(f"Error making call: {e}")
            return None
    
    def create_twiml_response(self):
        """
        Create a new TwiML response.
        
        Returns:
            VoiceResponse: A new TwiML response object
        """
        return VoiceResponse()
    
    def add_speech_recognition(self, response, action_url, timeout=3, speech_timeout="auto", language="en-US"):
        """
        Add speech recognition to a TwiML response.
        
        Args:
            response (VoiceResponse): The TwiML response to add to
            action_url (str): URL to send the speech results to
            timeout (int): How long to wait for speech
            speech_timeout (str): How long to wait for silence to consider the speech complete
            language (str): Language for speech recognition
            
        Returns:
            Gather: The Gather TwiML verb
        """
        gather = Gather(
            input='speech', 
            action=action_url,
            timeout=timeout,
            speech_timeout=speech_timeout,
            language=language
        )
        response.append(gather)
        return gather
    
    def get_call_logs(self, limit=20):
        """
        Retrieve recent call logs.
        
        Args:
            limit (int): Maximum number of logs to retrieve
            
        Returns:
            list: List of call records
        """
        try:
            calls = self.client.calls.list(limit=limit)
            return calls
        except TwilioRestException as e:
            logger.error(f"Error retrieving call logs: {e}")
            return []
    
    def end_call(self, call_sid):
        """
        End an active call.
        
        Args:
            call_sid (str): The SID of the call to end
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            call = self.client.calls(call_sid).update(status="completed")
            logger.info(f"Call {call_sid} ended")
            return True
        except TwilioRestException as e:
            logger.error(f"Error ending call {call_sid}: {e}")
            return False 