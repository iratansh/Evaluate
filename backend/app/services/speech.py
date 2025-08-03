import uuid
import os
import asyncio
from typing import Optional
from app.config import settings

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
            # Set voice for text-to-speech
            self.speech_config.speech_synthesis_voice_name = "en-US-JennyNeural"
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
            # Create synthesizer with in-memory audio output
            audio_config = speechsdk.audio.AudioOutputConfig(use_default_speaker=False)
            synthesizer = speechsdk.SpeechSynthesizer(
                speech_config=self.speech_config,
                audio_config=None  # This will return audio data
            )
            
            # Run synthesis in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, 
                lambda: synthesizer.speak_text(text)
            )
            
            if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                return result.audio_data
            else:
                print(f"TTS failed: {result.reason}")
                return None
                
        except Exception as e:
            print(f"Error in text_to_speech: {e}")
            return None
    
    async def speech_to_text(self, audio_data: bytes) -> Optional[str]:
        """Convert speech audio to text"""
        if not AZURE_SPEECH_AVAILABLE or not self.speech_config:
            print(f"STT requested but Azure Speech not available for {len(audio_data)} bytes")
            return "Speech recognition not available. Please type your answer."
            
        try:
            # Save audio data to temporary file
            temp_file = f"temp_audio_{uuid.uuid4()}.wav"
            with open(temp_file, "wb") as f:
                f.write(audio_data)
            
            # Create audio input from file
            audio_input = speechsdk.AudioConfig(filename=temp_file)
            speech_recognizer = speechsdk.SpeechRecognizer(
                speech_config=self.speech_config,
                audio_config=audio_input
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
                return result.text
            elif result.reason == speechsdk.ResultReason.NoMatch:
                return "Could not understand the audio. Please try again."
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
