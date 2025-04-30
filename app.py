#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import logging
from pathlib import Path
from dotenv import load_dotenv
from flask import Flask, request, Response
from twilio.twiml.voice_response import VoiceResponse

# Load environment variables from .env file
env_path = Path(".") / ".env"
load_dotenv(dotenv_path=env_path)

# Import local modules
from telephony.twilio_handler import TwilioHandler
from speech_processing.asr import SpeechRecognizer
from speech_processing.tts import TextToSpeech
from nlu.rasa_connector import RasaConnector
from database.json_db_manager import JsonDatabaseManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("stayvista_agent.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Initialize components
db_manager = JsonDatabaseManager(os.getenv("DATA_DIR", "data"))
speech_recognizer = SpeechRecognizer()
text_to_speech = TextToSpeech()
rasa_connector = RasaConnector(os.getenv("RASA_SERVER_URL", "http://localhost:5005"))
twilio_handler = TwilioHandler(
    account_sid=os.getenv("TWILIO_ACCOUNT_SID"),
    auth_token=os.getenv("TWILIO_AUTH_TOKEN"),
    phone_number=os.getenv("TWILIO_PHONE_NUMBER"),
)


@app.route("/webhook", methods=["POST"])
def webhook():
    """Webhook endpoint for Twilio to send incoming call information."""
    logger.info("Received webhook call from Twilio")

    response = VoiceResponse()

    # Start the conversation with a greeting
    response.say("Welcome to StayVista booking service. How can I help you today?")

    # Gather user input
    # Use the <Gather> verb to capture user speech
    gather = response.gather(
        input="speech",
        action="/process_speech",
        timeout=3,
        speech_timeout="auto",
        language="en-US",
    )

    # If the user doesn't say anything, prompt them again
    response.say("I didn't hear anything. Please try again.")
    response.redirect("/webhook")

    return str(response)


@app.route("/process_speech", methods=["POST"])
def process_speech():
    """Process the speech input from the user."""
    logger.info("Processing speech input")

    # Get the speech input from the request
    speech_result = request.values.get("SpeechResult", "")
    logger.info(f"Received speech: {speech_result}")

    if speech_result:
        # Send the speech to Rasa for intent recognition and response generation
        rasa_response = rasa_connector.get_response(speech_result)

        # Create TwiML response
        response = VoiceResponse()

        # Convert Rasa response to speech
        response.say(rasa_response)

        # Continue the conversation
        gather = response.gather(
            input="speech",
            action="/process_speech",
            timeout=3,
            speech_timeout="auto",
            language="en-US",
        )

        # If the user doesn't say anything, end the call
        response.say(
            "I didn't hear anything. Thank you for calling StayVista. Goodbye!"
        )
        response.hangup()
    else:
        # If no speech was detected, prompt again
        response = VoiceResponse()
        response.say("I couldn't understand that. Could you please repeat?")
        gather = response.gather(
            input="speech",
            action="/process_speech",
            timeout=3,
            speech_timeout="auto",
            language="en-US",
        )

        # If the user doesn't say anything again, end the call
        response.say(
            "I didn't hear anything. Thank you for calling StayVista. Goodbye!"
        )
        response.hangup()

    return str(response)


@app.route("/status_callback", methods=["POST"])
def status_callback():
    """Handle call status updates from Twilio."""
    call_status = request.values.get("CallStatus")
    call_sid = request.values.get("CallSid")

    logger.info(f"Call {call_sid} status: {call_status}")

    return Response(status=200)


if __name__ == "__main__":
    # Run the Flask app
    port = int(os.environ.get("PORT", 5000))
    app.run(
        host="0.0.0.0", port=port, debug=(os.getenv("DEBUG", "False").lower() == "true")
    )
