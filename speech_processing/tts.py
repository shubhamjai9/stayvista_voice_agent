#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import logging
import tempfile
import pyttsx3
from pathlib import Path

logger = logging.getLogger(__name__)

class TextToSpeech:
    """
    Text-to-Speech (TTS) module using pyttsx3 (local) or other providers.
    """
    
    def __init__(self, voice=None, rate=170, volume=1.0):
        """
        Initialize the TTS engine.
        
        Args:
            voice (str, optional): Voice ID to use. Defaults to None (system default).
            rate (int, optional): Speech rate (words per minute). Defaults to 170.
            volume (float, optional): Volume (0.0 to 1.0). Defaults to 1.0.
        """
        try:
            # Initialize the TTS engine
            self.engine = pyttsx3.init()
            
            # Set properties
            self.engine.setProperty('rate', rate)
            self.engine.setProperty('volume', volume)
            
            # Set voice if specified
            if voice:
                self.set_voice(voice)
            else:
                # Try to find a good English voice
                voices = self.engine.getProperty('voices')
                for v in voices:
                    if 'en' in v.languages:
                        self.engine.setProperty('voice', v.id)
                        logger.info(f"Selected voice: {v.name}")
                        break
            
            self.initialized = True
            logger.info("TTS engine initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize TTS engine: {e}")
            self.initialized = False
    
    def set_voice(self, voice_id):
        """
        Set the voice to use.
        
        Args:
            voice_id (str): ID of the voice to use
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.initialized:
            logger.error("TTS engine not initialized")
            return False
        
        try:
            self.engine.setProperty('voice', voice_id)
            logger.info(f"Voice set to: {voice_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to set voice: {e}")
            return False
    
    def list_available_voices(self):
        """
        List all available voices.
        
        Returns:
            list: List of available voice objects
        """
        if not self.initialized:
            logger.error("TTS engine not initialized")
            return []
        
        try:
            voices = self.engine.getProperty('voices')
            for idx, voice in enumerate(voices):
                logger.info(f"Voice {idx}: {voice.name} ({voice.id}), languages: {voice.languages}")
            return voices
        except Exception as e:
            logger.error(f"Failed to list voices: {e}")
            return []
    
    def speak(self, text):
        """
        Speak the given text.
        
        Args:
            text (str): Text to speak
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.initialized:
            logger.error("TTS engine not initialized")
            return False
        
        if not text:
            logger.warning("Empty text provided for TTS")
            return False
        
        try:
            logger.info(f"Speaking: {text}")
            self.engine.say(text)
            self.engine.runAndWait()
            return True
        except Exception as e:
            logger.error(f"Failed to speak text: {e}")
            return False
    
    def save_to_file(self, text, output_file=None):
        """
        Save speech to an audio file.
        
        Args:
            text (str): Text to convert to speech
            output_file (str, optional): Path to save the audio file. 
                                         Defaults to None (creates temp file).
            
        Returns:
            str: Path to the saved audio file, or None if failed
        """
        if not self.initialized:
            logger.error("TTS engine not initialized")
            return None
        
        if not text:
            logger.warning("Empty text provided for TTS")
            return None
        
        # Create a temporary file if no output file specified
        if output_file is None:
            temp_dir = tempfile.gettempdir()
            output_file = os.path.join(temp_dir, f"tts_output_{hash(text)}.wav")
        
        try:
            logger.info(f"Saving speech to file: {output_file}")
            self.engine.save_to_file(text, output_file)
            self.engine.runAndWait()
            
            if os.path.exists(output_file):
                return output_file
            else:
                logger.error("Failed to save speech to file")
                return None
        except Exception as e:
            logger.error(f"Failed to save speech to file: {e}")
            return None 