import uuid
import os
import asyncio
from typing import Optional
from app.config import settings
import wave
import io

try:
    import azure.cognitiveservices.speech as speechsdk
    AZURE_SPEECH_AVAILABLE = True
except ImportError:
    AZURE_SPEECH_AVAILABLE = False
    print("Azure Speech SDK not installed. Run: pip install azure-cognitiveservices-speech")

try:
    from azure.storage.blob import BlobServiceClient
    AZURE_STORAGE_AVAILABLE = True
except ImportError:
    AZURE_STORAGE_AVAILABLE = False
    print("Azure Storage SDK not installed. Run: pip install azure-storage-blob")

class SpeechService:
    def __init__(self):
        # Azure Speech Services configuration from environment
        self.speech_key = settings.AZURE_SPEECH_KEY
        self.speech_region = settings.AZURE_SPEECH_REGION
        
        if AZURE_SPEECH_AVAILABLE and self.speech_key and self.speech_region:
            self.speech_config = speechsdk.SpeechConfig(
                subscription=self.speech_key,
                region=self.speech_region
            )
            # Set male voice for text-to-speech
            self.speech_config.speech_synthesis_voice_name = "en-US-TonyNeural"
            
            # Configure speech recognition for better accuracy
            self.speech_config.speech_recognition_language = "en-US"
            
            print("SpeechService initialized with Azure Speech Services")
        else:
            self.speech_config = None
            if not self.speech_key or not self.speech_region:
                print("SpeechService initialized (Azure Speech credentials not configured)")
            else:
                print("SpeechService initialized (Azure Speech SDK not available)")
    
    async def text_to_speech(self, text: str) -> Optional[bytes]:
        """Convert text to speech audio"""
        if not AZURE_SPEECH_AVAILABLE or not self.speech_config:
            print(f"TTS requested but Azure Speech not available: {text[:50]}...")
            return None
            
        try:
            # Create synthesizer with audio output configuration for byte stream
            synthesizer = speechsdk.SpeechSynthesizer(
                speech_config=self.speech_config,
                audio_config=None  # This returns audio data as bytes
            )
            
            # Run synthesis in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, 
                lambda: synthesizer.speak_text(text)
            )
            
            if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                print(f"TTS completed successfully for: {text[:50]}...")
                return result.audio_data
            elif result.reason == speechsdk.ResultReason.Canceled:
                cancellation_details = speechsdk.CancellationDetails(result)
                print(f"TTS cancelled: {cancellation_details.reason}, {cancellation_details.error_details}")
                return None
            else:
                print(f"TTS failed: {result.reason}")
                return None
                
        except Exception as e:
            print(f"Error in text_to_speech: {e}")
            return None
    
    async def speech_to_text(self, audio_data: bytes) -> Optional[str]:
        """Convert speech audio to text using temporary file approach"""
        if not AZURE_SPEECH_AVAILABLE or not self.speech_config:
            print(f"STT requested but Azure Speech not available for {len(audio_data)} bytes")
            return "Speech recognition not available. Please type your answer."
            
        try:
            print(f"Processing audio data: {len(audio_data)} bytes")
            
            # Create a temporary file for the audio data
            temp_file = f"temp_audio_{uuid.uuid4()}.wav"
            
            # Convert to WAV format if needed and save to file
            wav_data = await self._convert_to_wav_if_needed(audio_data)
            
            with open(temp_file, "wb") as f:
                f.write(wav_data)
            
            # Create audio config from file
            audio_config = speechsdk.audio.AudioConfig(filename=temp_file)
            
            # Create recognizer with optimized settings
            speech_recognizer = speechsdk.SpeechRecognizer(
                speech_config=self.speech_config,
                audio_config=audio_config
            )
            
            # Configure recognition properties for better accuracy
            speech_recognizer.properties.set_property(
                speechsdk.PropertyId.SpeechServiceConnection_InitialSilenceTimeoutMs, "8000"
            )
            speech_recognizer.properties.set_property(
                speechsdk.PropertyId.SpeechServiceConnection_EndSilenceTimeoutMs, "2000"
            )
            
            # Perform recognition
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                speech_recognizer.recognize_once
            )
            
            # Clean up temp file
            try:
                os.remove(temp_file)
            except:
                pass
            
            # Process result
            if result.reason == speechsdk.ResultReason.RecognizedSpeech:
                recognized_text = result.text.strip()
                print(f"STT recognized: '{recognized_text}'")
                if recognized_text:
                    return recognized_text
                else:
                    return "No speech detected. Please speak clearly and try again."
                    
            elif result.reason == speechsdk.ResultReason.NoMatch:
                print(f"STT: No speech recognized")
                # Provide more helpful feedback
                no_match_details = result.no_match_details
                if no_match_details == speechsdk.NoMatchReason.InitialSilenceTimeout:
                    return "No speech detected. Please start speaking after clicking record."
                elif no_match_details == speechsdk.NoMatchReason.InitialBabbleTimeout:
                    return "Could not understand the audio. Please speak more clearly."
                else:
                    return "No speech detected. Please ensure your microphone is working and try again."
                    
            elif result.reason == speechsdk.ResultReason.Canceled:
                cancellation_details = speechsdk.CancellationDetails(result)
                print(f"STT cancelled: {cancellation_details.reason}")
                print(f"Error details: {cancellation_details.error_details}")
                
                if cancellation_details.reason == speechsdk.CancellationReason.Error:
                    if "1006" in str(cancellation_details.error_details):
                        return "No speech detected in the recording. Please speak clearly into the microphone."
                    else:
                        return "Speech recognition error. Please try again or type your answer."
                else:
                    return "Speech recognition was cancelled. Please try again."
            else:
                print(f"STT failed with reason: {result.reason}")
                return "Speech recognition failed. Please try again or type your answer."
                
        except Exception as e:
            print(f"Error in speech_to_text: {e}")
            import traceback
            traceback.print_exc()
            return "Speech recognition error. Please type your answer instead."
    
    async def _convert_to_wav_if_needed(self, audio_data: bytes) -> bytes:
        """Convert audio to WAV format if it's not already"""
        # Check if already WAV
        if audio_data[:4] == b'RIFF':
            print("Audio is already in WAV format")
            return audio_data
        
        print(f"Converting audio to WAV format. Input format detected from first 10 bytes: {audio_data[:10]}")
        
        # Try to use pydub for better format conversion
        try:
            from pydub import AudioSegment
            print("Using pydub for audio conversion")
            
            # Try to detect and convert WebM/other formats
            audio_buffer = io.BytesIO(audio_data)
            
            # Try different formats
            for format_type in ['webm', 'ogg', 'mp4', 'wav']:
                try:
                    audio_buffer.seek(0)
                    audio = AudioSegment.from_file(audio_buffer, format=format_type)
                    
                    # Convert to WAV with speech-optimized settings
                    wav_buffer = io.BytesIO()
                    audio = audio.set_frame_rate(16000).set_channels(1).set_sample_width(2)
                    audio.export(wav_buffer, format="wav")
                    
                    wav_buffer.seek(0)
                    converted_data = wav_buffer.read()
                    print(f"Successfully converted {format_type} to WAV: {len(converted_data)} bytes")
                    return converted_data
                    
                except Exception as e:
                    print(f"Failed to convert as {format_type}: {e}")
                    continue
                    
        except ImportError:
            print("pydub not available, using fallback conversion")
        
        # Fallback: Create a basic WAV file
        # This might not work for all formats but will prevent crashes
        sample_rate = 16000
        bits_per_sample = 16
        num_channels = 1
        
        # If the audio data looks like raw PCM, wrap it in WAV
        if len(audio_data) > 44:  # Minimum size for meaningful audio
            wav_buffer = io.BytesIO()
            
            # Try to extract meaningful audio data (skip potential headers)
            audio_samples = audio_data
            if len(audio_data) > 1000:
                # Skip first 1000 bytes which might be headers
                audio_samples = audio_data[1000:]
            
            with wave.open(wav_buffer, 'wb') as wav_file:
                wav_file.setnchannels(num_channels)
                wav_file.setsampwidth(bits_per_sample // 8)
                wav_file.setframerate(sample_rate)
                wav_file.writeframes(audio_samples)
            
            wav_buffer.seek(0)
            fallback_data = wav_buffer.read()
            print(f"Created fallback WAV file: {len(fallback_data)} bytes")
            return fallback_data
        
        # If all else fails, return original data
        print("Returning original audio data")
        return audio_data
    
    def create_silence_wav(self, duration_seconds: float = 0.1) -> bytes:
        """Create a WAV file with silence for testing"""
        sample_rate = 16000
        num_samples = int(sample_rate * duration_seconds)
        
        wav_buffer = io.BytesIO()
        with wave.open(wav_buffer, 'wb') as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            # Write silence (zeros)
            wav_file.writeframes(b'\x00' * (num_samples * 2))
        
        wav_buffer.seek(0)
        return wav_buffer.read()

class StorageService:
    def __init__(self):
        # Azure Storage configuration from environment
        self.connection_string = settings.AZURE_STORAGE_CONNECTION_STRING
        self.container_name = "interview-audio"
        
        if AZURE_STORAGE_AVAILABLE and self.connection_string:
            try:
                self.blob_service_client = BlobServiceClient.from_connection_string(self.connection_string)
                # Create container if it doesn't exist
                self._create_container()
                print("StorageService initialized with Azure Blob Storage")
            except Exception as e:
                print(f"Failed to initialize Azure Blob Storage: {e}")
                self._fallback_to_local()
        else:
            if not self.connection_string:
                print("StorageService: Azure Storage connection string not configured")
            self._fallback_to_local()
    
    def _create_container(self):
        """Create the container if it doesn't exist"""
        try:
            container_client = self.blob_service_client.get_container_client(self.container_name)
            if not container_client.exists():
                # Create container with private access (no public access)
                container_client.create_container()
                print(f"Created private container: {self.container_name}")
        except Exception as e:
            print(f"Error creating container: {e}")
    
    def _fallback_to_local(self):
        """Fallback to local storage"""
        self.blob_service_client = None
        self.local_audio_dir = "./app/data/audio"
        os.makedirs(self.local_audio_dir, exist_ok=True)
        print("StorageService initialized with local storage (fallback)")
    
    async def upload_audio(self, audio_data: bytes, file_extension: str = "wav") -> Optional[str]:
        """Upload audio file and return URL"""
        filename = f"{uuid.uuid4()}.{file_extension}"
        
        # Try Azure Blob Storage first
        if self.blob_service_client:
            try:
                blob_client = self.blob_service_client.get_blob_client(
                    container=self.container_name,
                    blob=filename
                )
                
                # Upload the audio data
                blob_client.upload_blob(audio_data, overwrite=True)
                
                # For private storage, return the blob name instead of public URL
                # The frontend will need to request this through an API endpoint
                blob_url = f"azure://{self.container_name}/{filename}"
                print(f"Audio uploaded to Azure Blob: {filename}")
                return blob_url
                
            except Exception as e:
                print(f"Error uploading to Azure Blob Storage: {e}")
                # Fall through to local storage
        
        # Fallback to local storage
        try:
            if not hasattr(self, 'local_audio_dir'):
                self.local_audio_dir = "./app/data/audio"
                os.makedirs(self.local_audio_dir, exist_ok=True)
            
            local_path = os.path.join(self.local_audio_dir, filename)
            with open(local_path, "wb") as f:
                f.write(audio_data)
            
            # Return relative URL for local access
            return f"/audio/{filename}"
            
        except Exception as e:
            print(f"Error saving audio locally: {e}")
            return None

# Global instances
speech_service = SpeechService()
storage_service = StorageService()