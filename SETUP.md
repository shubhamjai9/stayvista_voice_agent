# StayVista Voice Booking Agent Setup Guide

This guide will help you set up and run the StayVista voice booking agent on your local machine.

## Prerequisites

- Python 3.8 or higher
- PostgreSQL (for database)
- Twilio account (for telephony integration)
- Ngrok (for making your local server accessible via the internet)

## Installation Steps

1. **Clone the repository**

   ```bash
   git clone <repository-url>
   cd stayvista_voice_agent
   ```

2. **Create a virtual environment**

   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

4. **Set up the database**

   - Create a PostgreSQL database:
     ```bash
     createdb stayvista_db
     ```

   - Alternatively, you can use SQLite for development:
     ```
     DATABASE_URL=sqlite:///stayvista.db
     ```

5. **Download the Vosk speech recognition model**

   ```bash
   mkdir -p speech_processing/models
   cd speech_processing/models
   
   # Download a model from https://alphacephei.com/vosk/models
   # For English, you can use:
   wget https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip
   unzip vosk-model-small-en-us-0.15.zip
   
   cd ../..
   ```

6. **Configure environment variables**

   Create a `.env` file in the root directory:

   ```
   # Database
   DATABASE_URL=postgresql://username:password@localhost:5432/stayvista_db
   
   # Twilio
   TWILIO_ACCOUNT_SID=your_account_sid
   TWILIO_AUTH_TOKEN=your_auth_token
   TWILIO_PHONE_NUMBER=+1234567890
   
   # Webhook
   WEBHOOK_URL=https://your-ngrok-url.ngrok.io/webhook
   
   # Rasa
   RASA_SERVER_URL=http://localhost:5005
   
   # Debug
   DEBUG=True
   ```

   Replace the placeholder values with your actual credentials.

7. **Initialize the database**

   ```bash
   python -m database.init_db
   ```

8. **Train the Rasa model**

   ```bash
   cd nlu
   rasa train
   ```

## Running the Application

You'll need to run several components in separate terminal windows.

1. **Start the Rasa server**

   ```bash
   cd nlu
   rasa run -m models --enable-api
   ```

2. **Start the Rasa action server**

   ```bash
   cd nlu
   rasa run actions
   ```

3. **Start Ngrok to expose your webhook**

   ```bash
   ngrok http 5000
   ```

   This will give you a public URL. Update your `.env` file with the new `WEBHOOK_URL`.

4. **Start the main application**

   ```bash
   python app.py
   ```

5. **Configure Twilio**

   - Go to your Twilio console
   - Set up a phone number
   - Configure the voice webhook URL to point to your Ngrok URL + `/webhook`
   - Set the webhook method to HTTP POST

## Testing

1. **Test the voice agent by calling your Twilio number**

   When someone calls the Twilio number, the call will be forwarded to your application.

2. **Test the components individually**

   - **Database**:
     ```bash
     python -c "from database.db_manager import DatabaseManager; db = DatabaseManager('sqlite:///stayvista.db'); print(db.create_tables())"
     ```

   - **Speech Recognition**:
     ```bash
     python -c "from speech_processing.asr import SpeechRecognizer; asr = SpeechRecognizer(); print(asr.recognize_from_microphone(duration=5))"
     ```

   - **Rasa NLU**:
     ```bash
     python -c "from nlu.rasa_connector import RasaConnector; rasa = RasaConnector('http://localhost:5005'); print(rasa.get_response('Hello'))"
     ```

## Data Collection

1. **Run the StayVista scraper to collect property data**

   ```bash
   python -m scraper.stayvista_scraper --location "Bali" --limit 20
   ```

## Troubleshooting

- **Database connection issues**: Check your PostgreSQL credentials and make sure the database exists.
- **Rasa server not responding**: Ensure that both Rasa server and action server are running.
- **Speech recognition errors**: Verify that the Vosk model is properly downloaded and installed.
- **Twilio webhook errors**: Make sure Ngrok is running and the webhook URL is correctly configured in Twilio.

## Next Steps

1. Implement more complex dialogue scenarios
2. Add more sophisticated entity extraction
3. Integrate with StayVista's actual API when available
4. Add multi-language support
5. Implement more advanced speech processing 