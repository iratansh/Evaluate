import { useState, useRef, useCallback } from 'react';

interface UseAudioRecorderReturn {
  isRecording: boolean;
  startRecording: () => Promise<void>;
  stopRecording: () => Promise<Blob | null>;
  error: string | null;
  isSupported: boolean;
}

export function useAudioRecorder(): UseAudioRecorderReturn {
  const [isRecording, setIsRecording] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const streamRef = useRef<MediaStream | null>(null);

  // Check if MediaRecorder is supported
  const isSupported = typeof window !== 'undefined' && 
    'MediaRecorder' in window && 
    'mediaDevices' in navigator;

  const startRecording = useCallback(async () => {
    try {
      setError(null);
      
      if (!isSupported) {
        throw new Error('Audio recording is not supported in this browser');
      }

      // Request microphone permission
      const stream = await navigator.mediaDevices.getUserMedia({ 
        audio: {
          channelCount: 1, // Mono audio
          sampleRate: 16000, // 16kHz sample rate for speech
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true
        } 
      });
      
      streamRef.current = stream;

      // Determine the best supported MIME type
      const mimeTypes = [
        'audio/webm;codecs=opus',
        'audio/webm',
        'audio/ogg;codecs=opus',
        'audio/mp4',
        'audio/mpeg',
        'audio/wav'
      ];

      let selectedMimeType = 'audio/webm';
      for (const mimeType of mimeTypes) {
        if (MediaRecorder.isTypeSupported(mimeType)) {
          selectedMimeType = mimeType;
          console.log(`Using MIME type: ${mimeType}`);
          break;
        }
      }

      // Create MediaRecorder with the selected MIME type
      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: selectedMimeType,
        audioBitsPerSecond: 64000 // 64kbps for good quality speech
      });

      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      // Handle data available event
      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      // Handle errors
      mediaRecorder.onerror = (event) => {
        console.error('MediaRecorder error:', event);
        setError('Recording error occurred');
        stopRecording();
      };

      // Start recording with timeslice to get data periodically
      mediaRecorder.start(100); // Get data every 100ms
      setIsRecording(true);
      
      console.log('Recording started');
    } catch (err) {
      console.error('Error starting recording:', err);
      setError(err instanceof Error ? err.message : 'Failed to start recording');
      setIsRecording(false);
      
      // Clean up stream if it was created
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop());
        streamRef.current = null;
      }
    }
  }, [isSupported]);

  const stopRecording = useCallback(async (): Promise<Blob | null> => {
    return new Promise((resolve) => {
      try {
        if (!mediaRecorderRef.current || mediaRecorderRef.current.state === 'inactive') {
          setIsRecording(false);
          resolve(null);
          return;
        }

        const mediaRecorder = mediaRecorderRef.current;

        // Set up the onstop handler before stopping
        mediaRecorder.onstop = async () => {
          console.log('Recording stopped, processing audio...');
          
          // Stop all tracks
          if (streamRef.current) {
            streamRef.current.getTracks().forEach(track => track.stop());
            streamRef.current = null;
          }

          // Create blob from chunks
          if (audioChunksRef.current.length > 0) {
            const audioBlob = new Blob(audioChunksRef.current, { 
              type: mediaRecorder.mimeType || 'audio/webm' 
            });
            
            console.log(`Created audio blob: ${audioBlob.size} bytes, type: ${audioBlob.type}`);
            
            // Convert to WAV if needed (for better Azure compatibility)
            const wavBlob = await convertToWav(audioBlob);
            
            setIsRecording(false);
            resolve(wavBlob);
          } else {
            console.warn('No audio chunks recorded');
            setIsRecording(false);
            resolve(null);
          }
        };

        // Stop the recording
        mediaRecorder.stop();
        
      } catch (err) {
        console.error('Error stopping recording:', err);
        setError('Failed to stop recording');
        setIsRecording(false);
        resolve(null);
      }
    });
  }, []);

  return {
    isRecording,
    startRecording,
    stopRecording,
    error,
    isSupported
  };
}

// Helper function to convert audio blob to WAV format
async function convertToWav(audioBlob: Blob): Promise<Blob> {
  // If already WAV, return as is
  if (audioBlob.type === 'audio/wav') {
    return audioBlob;
  }

  // For browsers that support AudioContext, we can do client-side conversion
  if ('AudioContext' in window || 'webkitAudioContext' in window) {
    try {
      const AudioContextClass = (window as any).AudioContext || (window as any).webkitAudioContext;
      const audioContext = new AudioContextClass({ sampleRate: 16000 });
      
      // Convert blob to ArrayBuffer
      const arrayBuffer = await audioBlob.arrayBuffer();
      
      // Decode audio data
      const audioBuffer = await audioContext.decodeAudioData(arrayBuffer);
      
      // Convert to WAV
      const wavBlob = await audioBufferToWav(audioBuffer);
      
      console.log(`Converted ${audioBlob.type} to WAV: ${wavBlob.size} bytes`);
      return wavBlob;
    } catch (error) {
      console.error('Error converting to WAV:', error);
      // Return original blob if conversion fails
      return audioBlob;
    }
  }

  // If AudioContext not supported, return original blob
  console.log('AudioContext not supported, using original audio format');
  return audioBlob;
}

// Convert AudioBuffer to WAV format
async function audioBufferToWav(audioBuffer: AudioBuffer): Promise<Blob> {
  const numberOfChannels = 1; // Mono
  const sampleRate = 16000; // 16kHz for speech
  const format = 1; // PCM
  const bitDepth = 16;

  // Resample if needed
  let buffer = audioBuffer;
  if (audioBuffer.sampleRate !== sampleRate) {
    buffer = await resampleAudioBuffer(audioBuffer, sampleRate);
  }

  // Get audio data
  const length = buffer.length * numberOfChannels * 2; // 2 bytes per sample
  const arrayBuffer = new ArrayBuffer(44 + length);
  const view = new DataView(arrayBuffer);

  // Write WAV header
  const writeString = (offset: number, string: string) => {
    for (let i = 0; i < string.length; i++) {
      view.setUint8(offset + i, string.charCodeAt(i));
    }
  };

  writeString(0, 'RIFF');
  view.setUint32(4, 36 + length, true);
  writeString(8, 'WAVE');
  writeString(12, 'fmt ');
  view.setUint32(16, 16, true); // fmt chunk size
  view.setUint16(20, format, true);
  view.setUint16(22, numberOfChannels, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, sampleRate * numberOfChannels * bitDepth / 8, true);
  view.setUint16(32, numberOfChannels * bitDepth / 8, true);
  view.setUint16(34, bitDepth, true);
  writeString(36, 'data');
  view.setUint32(40, length, true);

  // Write audio data
  const channelData = buffer.getChannelData(0);
  let offset = 44;
  for (let i = 0; i < channelData.length; i++) {
    const sample = Math.max(-1, Math.min(1, channelData[i]));
    view.setInt16(offset, sample * 0x7FFF, true);
    offset += 2;
  }

  return new Blob([arrayBuffer], { type: 'audio/wav' });
}

// Simple resampling function
async function resampleAudioBuffer(audioBuffer: AudioBuffer, targetSampleRate: number): Promise<AudioBuffer> {
  const offlineContext = new OfflineAudioContext(
    1, // numberOfChannels
    Math.floor(audioBuffer.duration * targetSampleRate),
    targetSampleRate
  );

  const source = offlineContext.createBufferSource();
  source.buffer = audioBuffer;
  source.connect(offlineContext.destination);
  source.start();

  return await offlineContext.startRendering();
}