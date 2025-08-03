import uuid
import os
import asyncio
from typing import Optional
from app.config import settings
import wave

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
            # Using Tony (Neural) - a professional male voice
            self.speech_config.speech_synthesis_voice_name = "en-US-TonyNeural"
            print("SpeechService initialized with Azure Speech Services (Male voice: Tony)")
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
        """Convert speech audio to text with better silence detection"""
        if not AZURE_SPEECH_AVAILABLE or not self.speech_config:
            print(f"STT requested but Azure Speech not available for {len(audio_data)} bytes")
            return "Speech recognition not available. Please type your answer."
            
        try:
            # Quick check for silence by analyzing audio data amplitude
            import struct
            import numpy as np
            
            # Try to detect if audio is mostly silence
            try:
                # Assuming 16-bit PCM audio
                if len(audio_data) > 44:  # Skip WAV header if present
                    # Check if it starts with RIFF header
                    if audio_data[:4] == b'RIFF':
                        # Find data chunk
                        data_start = audio_data.find(b'data')
                        if data_start != -1:
                            data_start += 8  # Skip 'data' and size
                            audio_samples = audio_data[data_start:]
                        else:
                            audio_samples = audio_data[44:]  # Standard WAV header size
                    else:
                        audio_samples = audio_data
                    
                    # Convert bytes to 16-bit integers
                    if len(audio_samples) > 1000:
                        samples = []
                        for i in range(0, min(len(audio_samples) - 1, 10000), 2):
                            sample = struct.unpack('<h', audio_samples[i:i+2])[0]
                            samples.append(abs(sample))
                        
                        # Calculate average amplitude
                        avg_amplitude = np.mean(samples)
                        max_amplitude = np.max(samples)
                        
                        print(f"Audio analysis - Avg amplitude: {avg_amplitude}, Max amplitude: {max_amplitude}")
                        
                        # If average amplitude is very low, it's likely silence
                        if avg_amplitude < 100 and max_amplitude < 500:
                            print("Detected silence or very quiet audio")
                            return ""
            except Exception as e:
                print(f"Error analyzing audio amplitude: {e}")
                # Continue with normal speech recognition
            
            # Create a temporary WAV file with proper headers
            temp_file = f"temp_audio_{uuid.uuid4()}.wav"
            
            # If the audio_data doesn't have WAV headers, we need to add them
            try:
                # Try to use the audio data as-is first (might already be a proper WAV)
                with open(temp_file, "wb") as f:
                    f.write(audio_data)
                
                # Test if it's a valid WAV by trying to read it
                with wave.open(temp_file, 'rb') as wav_test:
                    wav_test.readframes(1)
                    
            except (wave.Error, Exception):
                # If it's not a valid WAV, assume it's raw audio and create a proper WAV file
                print("Creating proper WAV file from raw audio data")
                with wave.open(temp_file, 'wb') as wav_file:
                    wav_file.setnchannels(1)  # Mono
                    wav_file.setsampwidth(2)  # 16-bit
                    wav_file.setframerate(16000)  # 16kHz sample rate
                    wav_file.writeframes(audio_data)
            
            # Create audio input from file
            audio_input = speechsdk.AudioConfig(filename=temp_file)
            
            # Configure speech recognizer with better settings
            speech_recognizer = speechsdk.SpeechRecognizer(
                speech_config=self.speech_config,
                audio_config=audio_input
            )
            
            # Set properties for better recognition
            speech_recognizer.properties.set_property(
                speechsdk.PropertyId.SpeechServiceConnection_InitialSilenceTimeoutMs, "5000"
            )
            speech_recognizer.properties.set_property(
                speechsdk.PropertyId.SpeechServiceConnection_EndSilenceTimeoutMs, "1000"
            )
            
            # Run recognition in thread pool
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
            
            if result.reason == speechsdk.ResultReason.RecognizedSpeech:
                print(f"STT recognized: {result.text}")
                return result.text
            elif result.reason == speechsdk.ResultReason.NoMatch:
                print("STT: No speech recognized")
                # Return empty string for no speech instead of error message
                return ""
            elif result.reason == speechsdk.ResultReason.Canceled:
                cancellation_details = speechsdk.CancellationDetails(result)
                print(f"STT cancelled: {cancellation_details.reason}, {cancellation_details.error_details}")
                if cancellation_details.reason == speechsdk.CancellationReason.Error:
                    return "Speech recognition error. Please type your answer."
                else:
                    # Likely no speech detected
                    return ""
            else:
                print(f"STT failed: {result.reason}")
                return "Speech recognition failed. Please type your answer."
                
        except Exception as e:
            print(f"Error in speech_to_text: {e}")
            return "Speech recognition error. Please type your answer."

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