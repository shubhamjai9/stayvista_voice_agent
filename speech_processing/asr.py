#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import json
import wave
import logging
import numpy as np
from pathlib import Path
import sounddevice as sd
from vosk import Model, KaldiRecognizer

logger = logging.getLogger(__name__)

class SpeechRecognizer:
    """
    Speech recognition using Vosk (offline) or other providers.
    """
    
    def __init__(self, model_path=None, sample_rate=16000):
        """
        Initialize the speech recognizer.
        
        Args:
            model_path (str, optional): Path to Vosk model. Defaults to None (uses default path).
            sample_rate (int, optional): Audio sample rate. Defaults to 16000.
        """
        self.sample_rate = sample_rate
        
        # Set default model path if not provided
        if model_path is None:
            model_path = os.path.join(Path(__file__).parent, "models", "vosk-model-small-en-us-0.15")
        
        # Try to load Vosk model
        try:
            self.model = Model(model_path)
            logger.info(f"Loaded Vosk model from {model_path}")
            self.recognizer = KaldiRecognizer(self.model, self.sample_rate)
            self.recognizer.SetWords(True)  # Enable word timestamps
            self.initialized = True
        except Exception as e:
            logger.error(f"Failed to load Vosk model: {e}")
            self.initialized = False
    
    def recognize_from_microphone(self, duration=5.0):
        """
        Recognize speech from microphone.
        
        Args:
            duration (float, optional): Recording duration in seconds. Defaults to 5.0.
            
        Returns:
            str: Recognized text
        """
        if not self.initialized:
            logger.error("Speech recognizer not initialized")
            return ""
        
        logger.info(f"Recording audio for {duration} seconds...")
        
        # Record audio from microphone
        audio_data = sd.rec(
            int(duration * self.sample_rate), 
            samplerate=self.sample_rate, 
            channels=1, 
            dtype='int16'
        )
        sd.wait()  # Wait for recording to complete
        
        # Convert to bytes and process with Vosk
        audio_bytes = audio_data.tobytes()
        
        if self.recognizer.AcceptWaveform(audio_bytes):
            result = json.loads(self.recognizer.Result())
            text = result.get("text", "")
            logger.info(f"Recognized text: {text}")
            return text
        else:
            logger.warning("No speech detected")
            return ""
    
    def recognize_from_file(self, audio_file):
        """
        Recognize speech from an audio file.
        
        Args:
            audio_file (str): Path to audio file
            
        Returns:
            str: Recognized text
        """
        if not self.initialized:
            logger.error("Speech recognizer not initialized")
            return ""
        
        if not os.path.exists(audio_file):
            logger.error(f"Audio file not found: {audio_file}")
            return ""
        
        logger.info(f"Processing audio file: {audio_file}")
        
        try:
            # Open the audio file
            wf = wave.open(audio_file, "rb")
            
            # Check if the audio format is compatible
            if wf.getnchannels() != 1 or wf.getsampwidth() != 2 or wf.getcomptype() != "NONE":
                logger.error("Audio file must be mono PCM WAV format")
                return ""
            
            # Create a new recognizer with the file's sample rate
            file_sample_rate = wf.getframerate()
            recognizer = KaldiRecognizer(self.model, file_sample_rate)
            recognizer.SetWords(True)
            
            # Process the audio file
            results = []
            while True:
                data = wf.readframes(4000)
                if len(data) == 0:
                    break
                if recognizer.AcceptWaveform(data):
                    part_result = json.loads(recognizer.Result())
                    results.append(part_result.get("text", ""))
            
            # Get final result
            final_result = json.loads(recognizer.FinalResult())
            results.append(final_result.get("text", ""))
            
            # Combine all results
            text = " ".join(results).strip()
            logger.info(f"Recognized text from file: {text}")
            return text
            
        except Exception as e:
            logger.error(f"Error processing audio file: {e}")
            return ""
    
    def recognize_from_bytes(self, audio_bytes, sample_rate=None):
        """
        Recognize speech from raw audio bytes.
        
        Args:
            audio_bytes (bytes): Raw audio data
            sample_rate (int, optional): Sample rate of the audio. Defaults to None (uses instance sample rate).
            
        Returns:
            str: Recognized text
        """
        if not self.initialized:
            logger.error("Speech recognizer not initialized")
            return ""
        
        if sample_rate is None:
            sample_rate = self.sample_rate
        
        # Create a new recognizer with the specified sample rate if different
        if sample_rate != self.sample_rate:
            recognizer = KaldiRecognizer(self.model, sample_rate)
            recognizer.SetWords(True)
        else:
            recognizer = self.recognizer
        
        # Process the audio
        if recognizer.AcceptWaveform(audio_bytes):
            result = json.loads(recognizer.Result())
            text = result.get("text", "")
        else:
            # Get partial result if no complete speech detected
            result = json.loads(recognizer.PartialResult())
            text = result.get("partial", "")
        
        logger.info(f"Recognized text from bytes: {text}")
        return text 