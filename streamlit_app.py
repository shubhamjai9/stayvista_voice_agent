#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
import streamlit as st
from datetime import datetime, timedelta
import pandas as pd
from PIL import Image
import requests
from io import BytesIO
import uuid
import time
import threading
import queue
import tempfile
import base64

# Import the JsonDatabaseManager
from database.json_db_manager import JsonDatabaseManager

# Import speech recognition and TTS components
try:
    import sounddevice as sd
    import soundfile as sf
    import numpy as np
    from vosk import Model, KaldiRecognizer
    import pyttsx3
    import wave
    import pyaudio

    SPEECH_ENABLED = True
except ImportError:
    SPEECH_ENABLED = False
    st.warning(
        "Speech components not available. Install required packages to enable voice features."
    )

# Set page configuration
st.set_page_config(
    page_title="StayVista Voice Agent Dashboard",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded",
)


# Initialize the database manager
@st.cache_resource
def get_db_manager():
    return JsonDatabaseManager("data")


db_manager = get_db_manager()


# Initialize text-to-speech engine
@st.cache_resource
def get_tts_engine():
    if SPEECH_ENABLED:
        engine = pyttsx3.init()
        # Configure voice properties
        engine.setProperty("rate", 150)  # Speed of speech
        engine.setProperty("volume", 0.9)  # Volume (0.0 to 1.0)
        return engine
    return None


tts_engine = get_tts_engine()


# Initialize speech recognition
@st.cache_resource
def get_speech_recognizer():
    if SPEECH_ENABLED:
        try:
            model_path = "speech_processing/models/vosk-model-small-en-us-0.15"
            if os.path.exists(model_path):
                model = Model(model_path)
                recognizer = KaldiRecognizer(model, 16000)
                return recognizer
            else:
                st.warning(
                    f"Vosk model not found at {model_path}. Voice recognition disabled."
                )
                return None
        except Exception as e:
            st.error(f"Error loading speech recognition model: {e}")
            return None
    return None


speech_recognizer = get_speech_recognizer()


# Helper functions
def text_to_speech(text, autoplay=True):
    """Convert text to speech and return audio HTML"""
    if not SPEECH_ENABLED or tts_engine is None:
        return None

    try:
        # Create a temporary file for the audio
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_audio:
            temp_path = temp_audio.name

        # Save speech to the temporary file
        tts_engine.save_to_file(text, temp_path)
        tts_engine.runAndWait()

        # Read the file and encode to base64
        audio_bytes = open(temp_path, "rb").read()
        audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")

        # Create HTML with audio controls
        audio_html = f'<audio {"autoplay" if autoplay else ""} controls><source src="data:audio/wav;base64,{audio_base64}" type="audio/wav"></audio>'

        # Clean up the temporary file
        os.unlink(temp_path)

        return audio_html
    except Exception as e:
        st.error(f"Error in text-to-speech: {e}")
        return None


def record_audio(duration=5, sample_rate=16000):
    """Record audio for the specified duration and return as bytes"""
    if not SPEECH_ENABLED:
        return None

    try:
        # Record audio
        recording = sd.rec(
            int(duration * sample_rate),
            samplerate=sample_rate,
            channels=1,
            dtype="int16",
        )
        sd.wait()

        # Create a temporary file for the audio
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp_audio:
            temp_path = temp_audio.name

        # Save the recording to WAV file
        sf.write(temp_path, recording, sample_rate)

        # Read the file
        audio_bytes = open(temp_path, "rb").read()

        # Clean up the temporary file
        os.unlink(temp_path)

        return audio_bytes
    except Exception as e:
        st.error(f"Error recording audio: {e}")
        return None


def speech_to_text(audio_bytes):
    """Convert audio to text using Vosk speech recognition"""
    if not SPEECH_ENABLED or speech_recognizer is None or audio_bytes is None:
        return None

    try:
        # Reset the recognizer
        speech_recognizer.Reset()

        # Process the audio data
        speech_recognizer.AcceptWaveform(audio_bytes)
        result = json.loads(speech_recognizer.Result())

        # Extract the recognized text
        if "text" in result and result["text"].strip():
            return result["text"]

        return None
    except Exception as e:
        st.error(f"Error in speech recognition: {e}")
        return None


def process_voice_input(user_query, conversation_history):
    """Process voice input and generate a response"""
    # For demo purposes, we'll implement a simple rule-based response system
    # In a real system, this would connect to Rasa or another NLU system

    # Convert query to lowercase for easier comparison
    query = user_query.lower()

    # Define some sample responses
    if any(word in query for word in ["hello", "hi", "hey"]):
        return "Hello! How can I help you with your accommodation needs today?"

    elif any(word in query for word in ["book", "reservation", "stay"]):
        return "I'd be happy to help you book a stay. Could you tell me your destination and dates?"

    elif any(
        word in query
        for word in ["property", "properties", "house", "apartment", "villa"]
    ):
        return "We have many beautiful properties available. Would you like me to search for a specific location or type of property?"

    elif any(
        word in query for word in ["malibu", "miami", "beach", "mountain", "aspen"]
    ):
        location = next(
            (word for word in ["malibu", "miami", "beach", "aspen"] if word in query),
            "location",
        )
        return f"I've found several properties in {location.capitalize()}. Would you like to hear more about them?"

    elif any(
        word in query for word in ["date", "when", "month", "week", "weekend", "day"]
    ):
        return "What dates were you thinking of for your stay? Or if you're flexible, I can suggest some options with good availability."

    elif any(
        word in query for word in ["price", "cost", "expensive", "cheap", "affordable"]
    ):
        return "Our properties range from affordable to luxury. What's your budget per night?"

    elif any(
        word in query for word in ["amenities", "pool", "wifi", "kitchen", "view"]
    ):
        return "Many of our properties include amenities like pools, WiFi, fully equipped kitchens, and scenic views. Any specific amenities you're looking for?"

    elif any(word in query for word in ["thank", "thanks"]):
        return "You're welcome! Is there anything else I can help you with?"

    elif any(word in query for word in ["bye", "goodbye"]):
        return "Thank you for using StayVista! Have a wonderful day."

    else:
        return "I'm not sure I understood that. Could you tell me more about what you're looking for in a property?"


def update_conversation_log(conversation_history, speaker, text):
    """Update the conversation log with a new message"""
    conversation_history.append(
        {"timestamp": datetime.now().isoformat(), "speaker": speaker, "text": text}
    )
    return conversation_history


def parse_date(date_str):
    """Parse date string into datetime object."""
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except:
        return None


def format_date(date_obj):
    """Format datetime object into string."""
    if isinstance(date_obj, datetime):
        return date_obj.strftime("%Y-%m-%d")
    return date_obj


def load_image_from_url(url):
    """Load image from URL."""
    try:
        response = requests.get(url)
        return Image.open(BytesIO(response.content))
    except:
        return None


# Voice chat component
def voice_chat_interface():
    st.title("Voice Chat with StayVista")

    # Initialize session state for conversation history
    if "conversation_history" not in st.session_state:
        st.session_state.conversation_history = []
        # Add initial greeting
        system_greeting = "Hello! I'm your StayVista voice assistant. How can I help you find the perfect accommodation today?"
        st.session_state.conversation_history = update_conversation_log(
            st.session_state.conversation_history, "system", system_greeting
        )

        # Generate and play TTS audio for greeting
        if SPEECH_ENABLED and tts_engine is not None:
            greeting_audio = text_to_speech(system_greeting)
            if greeting_audio:
                st.markdown(greeting_audio, unsafe_allow_html=True)

    # Display conversation history
    chat_container = st.container()
    with chat_container:
        for message in st.session_state.conversation_history:
            if message["speaker"] == "user":
                st.markdown(
                    f"<div style='text-align: right; margin: 10px; padding: 10px; background-color: #e6f7ff; border-radius: 10px;'><b>You:</b> {message['text']}</div>",
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f"<div style='text-align: left; margin: 10px; padding: 10px; background-color: #f0f0f0; border-radius: 10px;'><b>StayVista:</b> {message['text']}</div>",
                    unsafe_allow_html=True,
                )

    # Voice input section
    col1, col2, col3 = st.columns([1, 1, 1])

    with col1:
        # Text input as a fallback
        user_text_input = st.text_input("Type your message:", key="text_message")

        if st.button("Send", key="send_text"):
            if user_text_input.strip():
                # Update conversation with user message
                st.session_state.conversation_history = update_conversation_log(
                    st.session_state.conversation_history, "user", user_text_input
                )

                # Process user input and get response
                response = process_voice_input(
                    user_text_input, st.session_state.conversation_history
                )

                # Update conversation with system response
                st.session_state.conversation_history = update_conversation_log(
                    st.session_state.conversation_history, "system", response
                )

                # Generate and play TTS audio for response
                if SPEECH_ENABLED and tts_engine is not None:
                    response_audio = text_to_speech(response)
                    if response_audio:
                        st.session_state.last_audio = response_audio

                # Clear text input
                st.session_state.text_message = ""

                # Force page refresh to update conversation
                st.rerun()

    with col2:
        # Voice recording button
        if SPEECH_ENABLED:
            if st.button("🎙️ Press to Speak", key="record_button"):
                # Show a spinner while recording
                with st.spinner("Listening..."):
                    # Record audio
                    st.info("Recording... Speak now!")
                    audio_bytes = record_audio(duration=5)

                    if audio_bytes:
                        # Convert speech to text
                        transcribed_text = speech_to_text(audio_bytes)

                        if transcribed_text:
                            # Update conversation with user message
                            st.session_state.conversation_history = (
                                update_conversation_log(
                                    st.session_state.conversation_history,
                                    "user",
                                    transcribed_text,
                                )
                            )

                            # Process user input and get response
                            response = process_voice_input(
                                transcribed_text, st.session_state.conversation_history
                            )

                            # Update conversation with system response
                            st.session_state.conversation_history = (
                                update_conversation_log(
                                    st.session_state.conversation_history,
                                    "system",
                                    response,
                                )
                            )

                            # Generate and play TTS audio for response
                            if tts_engine is not None:
                                response_audio = text_to_speech(response)
                                if response_audio:
                                    st.session_state.last_audio = response_audio

                            # Force page refresh to update conversation
                            st.rerun()
                        else:
                            st.error(
                                "Sorry, I couldn't understand what you said. Please try again."
                            )
                    else:
                        st.error("No audio recorded. Please try again.")
        else:
            st.warning(
                "Voice recording is not available. Please install the required packages."
            )

    with col3:
        # Play last system response
        if "last_audio" in st.session_state and st.session_state.last_audio:
            st.markdown("### Last Response")
            st.markdown(st.session_state.last_audio, unsafe_allow_html=True)


# Main app
def main():
    # Sidebar
    st.sidebar.title("StayVista Voice Agent")
    page = st.sidebar.selectbox(
        "Select Page",
        [
            "Home",
            "Voice Chat",
            "Search Properties",
            "Property Details",
            "Booking",
            "Admin Dashboard",
        ],
    )

    # Home page
    if page == "Home":
        st.title("StayVista Voice Agent Dashboard")
        st.write(
            "Welcome to the StayVista Voice Agent Dashboard. This web interface allows you to interact with the StayVista voice agent system."
        )

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Features")
            st.markdown(
                """
            - **Voice Chat**: Talk directly with our voice assistant
            - **Search Properties**: Find properties by location, dates, guests, and amenities
            - **Property Details**: View comprehensive information about properties
            - **Booking**: Make reservations easily
            - **Admin Dashboard**: Monitor system activity
            """
            )

        with col2:
            st.subheader("Recent Properties")
            properties = db_manager.read_json_file(db_manager.properties_file)
            if properties:
                for prop in properties[:3]:
                    with st.expander(
                        f"{prop.get('name', 'Property')} - ${prop.get('base_price', 0)}/night"
                    ):
                        st.write(
                            f"Location: {prop.get('location', {}).get('name', 'Unknown')}"
                        )
                        st.write(f"Bedrooms: {prop.get('bedrooms', 0)}")
                        st.write(f"Rating: {prop.get('rating', 'N/A')}")

    # Voice Chat page
    elif page == "Voice Chat":
        voice_chat_interface()

    # Search Properties page
    elif page == "Search Properties":
        st.title("Search Properties")

        # Search form
        with st.form("search_form"):
            col1, col2, col3 = st.columns(3)

            with col1:
                location = st.text_input("Location", value="Malibu")
                guests = st.number_input("Number of Guests", min_value=1, value=2)

            with col2:
                check_in = st.date_input("Check-in Date", value=datetime.now())
                bedrooms = st.number_input("Number of Bedrooms", min_value=1, value=1)

            with col3:
                check_out = st.date_input(
                    "Check-out Date", value=datetime.now() + timedelta(days=7)
                )
                max_price = st.number_input(
                    "Maximum Price per Night", min_value=0, value=500
                )

            amenities = st.multiselect(
                "Amenities",
                [
                    "Wifi",
                    "Pool",
                    "Hot tub",
                    "Kitchen",
                    "Air conditioning",
                    "Beach access",
                ],
            )

            submitted = st.form_submit_button("Search Properties")

        if submitted:
            # Convert dates to datetime objects
            check_in_date = datetime.combine(check_in, datetime.min.time())
            check_out_date = datetime.combine(check_out, datetime.min.time())

            # Fetch all properties for filtering (in a real app, this would be done in the DB)
            all_properties = db_manager.read_json_file(db_manager.properties_file)

            # Filter properties by criteria
            filtered_properties = []
            for prop in all_properties:
                # Location filter
                location_match = (
                    location.lower() in str(prop.get("location", {})).lower()
                )

                # Guest and bedroom filter
                guest_match = prop.get("max_guests", 0) >= guests
                bedroom_match = prop.get("bedrooms", 0) >= bedrooms

                # Price filter
                price_match = prop.get("base_price", 0) <= max_price

                # Amenities filter
                prop_amenities = prop.get("amenities", [])
                if isinstance(prop_amenities, str):
                    try:
                        prop_amenities = json.loads(prop_amenities)
                    except:
                        prop_amenities = []

                amenities_match = True
                if amenities:
                    amenities_match = all(
                        a.lower() in [am.lower() for am in prop_amenities]
                        for a in amenities
                    )

                # Combined filter
                if (
                    location_match
                    and guest_match
                    and bedroom_match
                    and price_match
                    and amenities_match
                ):
                    filtered_properties.append(prop)

            if filtered_properties:
                st.success(f"Found {len(filtered_properties)} properties!")

                # Store search results in session state
                st.session_state.search_results = filtered_properties

                # Display properties in a grid
                cols = st.columns(3)
                for i, prop in enumerate(filtered_properties):
                    with cols[i % 3]:
                        st.subheader(prop.get("name", "Property"))

                        # Try to display thumbnail
                        thumbnail_url = prop.get("thumbnail_url")
                        if thumbnail_url:
                            img = load_image_from_url(thumbnail_url)
                            if img:
                                st.image(img, use_column_width=True)
                            else:
                                st.image(
                                    "https://placehold.co/600x400?text=No+Image",
                                    use_column_width=True,
                                )
                        else:
                            st.image(
                                "https://placehold.co/600x400?text=No+Image",
                                use_column_width=True,
                            )

                        st.write(f"**Price:** ${prop.get('base_price', 0)}/night")
                        st.write(f"**Bedrooms:** {prop.get('bedrooms', 0)}")
                        st.write(f"**Bathrooms:** {prop.get('bathrooms', 0)}")
                        st.write(f"**Max Guests:** {prop.get('max_guests', 0)}")

                        if "location" in prop:
                            location_name = prop["location"].get("name", "Unknown")
                            st.write(f"**Location:** {location_name}")

                        # View details button
                        if st.button(f"View Details", key=f"view_{i}"):
                            st.session_state.selected_property = prop
                            st.session_state.current_page = "Property Details"
                            st.rerun()
            else:
                st.warning(f"No properties found in {location} matching your criteria.")

    # Admin Dashboard page
    elif page == "Admin Dashboard":
        st.title("Admin Dashboard")

        tabs = st.tabs(["Properties", "Bookings", "Users", "Conversation Logs"])

        # Properties tab
        with tabs[0]:
            st.header("Properties")

            properties = db_manager.read_json_file(db_manager.properties_file)
            if properties:
                # Convert to DataFrame for display
                props_for_display = []
                for p in properties:
                    # Extract key fields
                    props_for_display.append(
                        {
                            "id": p.get("id", ""),
                            "name": p.get("name", ""),
                            "location": p.get("location", {}).get("name", ""),
                            "property_type": p.get("property_type", ""),
                            "bedrooms": p.get("bedrooms", 0),
                            "bathrooms": p.get("bathrooms", 0),
                            "max_guests": p.get("max_guests", 0),
                            "base_price": p.get("base_price", 0),
                            "rating": p.get("rating", 0),
                            "num_reviews": p.get("num_reviews", 0),
                        }
                    )

                df_props = pd.DataFrame(props_for_display)
                st.dataframe(df_props)
            else:
                st.info("No properties found in the database.")

        # Bookings tab
        with tabs[1]:
            st.header("Bookings")

            bookings = db_manager.read_json_file(db_manager.bookings_file)
            if bookings:
                # Convert to DataFrame for display
                bookings_for_display = []
                for b in bookings:
                    # Extract key fields
                    bookings_for_display.append(
                        {
                            "id": b.get("id", ""),
                            "property_id": b.get("property_id", ""),
                            "user_id": b.get("user_id", ""),
                            "check_in_date": b.get("check_in_date", ""),
                            "check_out_date": b.get("check_out_date", ""),
                            "num_guests": b.get("num_guests", 0),
                            "total_price": b.get("total_price", 0),
                            "status": b.get("status", ""),
                            "confirmation_code": b.get("confirmation_code", ""),
                            "created_at": b.get("created_at", ""),
                        }
                    )

                df_bookings = pd.DataFrame(bookings_for_display)
                st.dataframe(df_bookings)
            else:
                st.info("No bookings found in the database.")

        # Users tab
        with tabs[2]:
            st.header("Users")

            users = db_manager.read_json_file(db_manager.users_file)
            if users:
                # Convert to DataFrame for display
                users_for_display = []
                for u in users:
                    # Extract key fields
                    users_for_display.append(
                        {
                            "id": u.get("id", ""),
                            "name": u.get("name", ""),
                            "email": u.get("email", ""),
                            "phone_number": u.get("phone_number", ""),
                            "created_at": u.get("created_at", ""),
                        }
                    )

                df_users = pd.DataFrame(users_for_display)
                st.dataframe(df_users)
            else:
                st.info("No users found in the database.")

        # Logs tab
        with tabs[3]:
            st.header("Conversation Logs")

            logs = db_manager.read_json_file(db_manager.conversation_logs_file)
            if logs:
                for i, log in enumerate(logs):
                    with st.expander(
                        f"Conversation {i+1} - User: {log.get('user_id', 'Unknown')}"
                    ):
                        conversation = log.get("conversation", [])
                        for msg in conversation:
                            speaker = msg.get("speaker", "unknown")
                            text = msg.get("text", "")
                            timestamp = msg.get("timestamp", "")

                            if speaker == "user":
                                st.markdown(
                                    f"<div style='text-align: right;'><b>User:</b> {text} <small>({timestamp})</small></div>",
                                    unsafe_allow_html=True,
                                )
                            else:
                                st.markdown(
                                    f"<div style='text-align: left;'><b>System:</b> {text} <small>({timestamp})</small></div>",
                                    unsafe_allow_html=True,
                                )
            else:
                st.info("No conversation logs found in the database.")


# Run the app
if __name__ == "__main__":
    main()
