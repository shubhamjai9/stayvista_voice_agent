# StayVista Voice Booking Agent

A voice-based booking agent for StayVista (stayvista.com) that allows users to book accommodations through phone calls.

## Features

- Web scraping to gather StayVista property data
- Voice call handling with Twilio
- Speech-to-Text using Vosk (offline) or Whisper
- Natural Language Understanding with Rasa
- Property search and filtering
- Booking management
- Text-to-Speech responses

## Project Structure

```
stayvista_voice_agent/
├── scraper/             # Web scraping module for StayVista data
├── database/            # Database models and connection
├── nlu/                 # Rasa NLU configuration and training data
├── speech_processing/   # ASR and TTS modules
├── telephony/           # Twilio integration
└── utils/               # Helper functions
```

## Setup

1. Clone the repository
2. Create a virtual environment:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
4. Download Vosk model:
   ```
   mkdir -p speech_processing/models
   # Download model from https://alphacephei.com/vosk/models
   # Extract to speech_processing/models/
   ```
5. Set up environment variables:
   ```
   cp .env.example .env
   # Edit .env with your credentials
   ```
6. Initialize the database:
   ```
   python database/init_db.py
   ```
7. Run the scraper:
   ```
   python scraper/stayvista_scraper.py
   ```
8. Start the Rasa server:
   ```
   cd nlu
   rasa train
   rasa run -m models --enable-api
   ```
9. In a separate terminal, start the action server:
   ```
   cd nlu
   rasa run actions
   ```
10. Start the voice agent service:
    ```
    python app.py
    ```

## Environment Variables

- `TWILIO_ACCOUNT_SID`: Your Twilio account SID
- `TWILIO_AUTH_TOKEN`: Your Twilio auth token
- `TWILIO_PHONE_NUMBER`: Your Twilio phone number
- `DATABASE_URL`: PostgreSQL connection string
- `WEBHOOK_URL`: Ngrok or public URL for Twilio webhook 