package com.evaluate.aiinterviewer.service;

import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import jakarta.annotation.PostConstruct;
import java.io.*;
import java.util.Optional;
import java.util.UUID;

@Service
@Slf4j
public class SpeechService {

    @Value("${azure.speech.key:}")
    private String speechKey;

    @Value("${azure.speech.region:}")
    private String speechRegion;

    private boolean azureSpeechAvailable = false;
    private Object speechConfig; // Will be SpeechConfig if Azure SDK is available

    @PostConstruct
    public void initialize() {
        try {
            if (speechKey != null && !speechKey.isEmpty() && speechRegion != null && !speechRegion.isEmpty()) {
                Class<?> speechConfigClass = Class.forName("com.microsoft.cognitiveservices.speech.SpeechConfig");
                var fromSubscription = speechConfigClass.getMethod("fromSubscription", String.class, String.class);
                speechConfig = fromSubscription.invoke(null, speechKey, speechRegion);

                // Set voice
                var setVoice = speechConfigClass.getMethod("setSpeechSynthesisVoiceName", String.class);
                setVoice.invoke(speechConfig, "en-US-TonyNeural");

                // Set recognition language
                var setLang = speechConfigClass.getMethod("setSpeechRecognitionLanguage", String.class);
                setLang.invoke(speechConfig, "en-US");

                azureSpeechAvailable = true;
                log.info("SpeechService initialized with Azure Speech Services");
            } else {
                log.info("SpeechService initialized (Azure Speech credentials not configured)");
            }
        } catch (ClassNotFoundException e) {
            log.info("SpeechService initialized (Azure Speech SDK not available)");
        } catch (Exception e) {
            log.warn("Failed to initialize Azure Speech: {}", e.getMessage());
        }
    }

    /**
     * Convert text to speech audio bytes.
     * Returns empty Optional if Azure Speech is not available.
     */
    public Optional<byte[]> textToSpeech(String text) {
        if (!azureSpeechAvailable || speechConfig == null) {
            log.info("TTS requested but Azure Speech not available: {}...", text.substring(0, Math.min(50, text.length())));
            return Optional.empty();
        }

        try {
            Class<?> synthesizerClass = Class.forName("com.microsoft.cognitiveservices.speech.SpeechSynthesizer");
            Class<?> speechConfigClass = Class.forName("com.microsoft.cognitiveservices.speech.SpeechConfig");
            var constructor = synthesizerClass.getConstructor(speechConfigClass);
            Object synthesizer = constructor.newInstance(speechConfig);

            var speakText = synthesizerClass.getMethod("SpeakText", String.class);
            Object result = speakText.invoke(synthesizer, text);

            // Check result reason
            var getReason = result.getClass().getMethod("getReason");
            Object reason = getReason.invoke(result);

            if ("SynthesizingAudioCompleted".equals(reason.toString())) {
                var getAudioData = result.getClass().getMethod("getAudioData");
                byte[] audioData = (byte[]) getAudioData.invoke(result);
                log.info("TTS completed successfully for: {}...", text.substring(0, Math.min(50, text.length())));
                return Optional.of(audioData);
            } else {
                log.warn("TTS failed: {}", reason);
                return Optional.empty();
            }
        } catch (Exception e) {
            log.error("Error in text_to_speech: {}", e.getMessage());
            return Optional.empty();
        }
    }

    /**
     * Convert speech audio bytes to text.
     * Returns fallback message if Azure Speech is not available.
     */
    public String speechToText(byte[] audioData) {
        if (!azureSpeechAvailable || speechConfig == null) {
            log.info("STT requested but Azure Speech not available for {} bytes", audioData.length);
            return "Speech recognition not available. Please type your answer.";
        }

        String tempFile = "temp_audio_" + UUID.randomUUID() + ".wav";
        try {
            // Convert to WAV if needed
            byte[] wavData = convertToWavIfNeeded(audioData);

            // Write to temp file
            try (FileOutputStream fos = new FileOutputStream(tempFile)) {
                fos.write(wavData);
            }

            // Use Azure Speech SDK via reflection
            Class<?> audioConfigClass = Class.forName("com.microsoft.cognitiveservices.speech.audio.AudioConfig");
            var fromWavFile = audioConfigClass.getMethod("fromWavFileInput", String.class);
            Object audioConfig = fromWavFile.invoke(null, tempFile);

            Class<?> recognizerClass = Class.forName("com.microsoft.cognitiveservices.speech.SpeechRecognizer");
            Class<?> speechConfigClass = Class.forName("com.microsoft.cognitiveservices.speech.SpeechConfig");
            var constructor = recognizerClass.getConstructor(speechConfigClass, audioConfigClass);
            Object recognizer = constructor.newInstance(speechConfig, audioConfig);

            var recognizeOnce = recognizerClass.getMethod("recognizeOnceAsync");
            Object future = recognizeOnce.invoke(recognizer);
            Object result = future.getClass().getMethod("get").invoke(future);

            var getReason = result.getClass().getMethod("getReason");
            Object reason = getReason.invoke(result);

            String reasonStr = reason.toString();
            if ("RecognizedSpeech".equals(reasonStr)) {
                var getText = result.getClass().getMethod("getText");
                String text = (String) getText.invoke(result);
                log.info("STT recognized: '{}'", text);
                return text != null && !text.trim().isEmpty() ? text.trim()
                        : "No speech detected. Please speak clearly and try again.";
            } else if ("NoMatch".equals(reasonStr)) {
                return "No speech detected. Please ensure your microphone is working and try again.";
            } else {
                return "Speech recognition failed. Please try again or type your answer.";
            }
        } catch (Exception e) {
            log.error("Error in speech_to_text: {}", e.getMessage());
            return "Speech recognition error. Please type your answer instead.";
        } finally {
            new File(tempFile).delete();
        }
    }

    private byte[] convertToWavIfNeeded(byte[] audioData) {
        // Check if already WAV
        if (audioData.length >= 4 && audioData[0] == 'R' && audioData[1] == 'I'
                && audioData[2] == 'F' && audioData[3] == 'F') {
            return audioData;
        }

        // Create a basic WAV wrapper for raw PCM data
        int sampleRate = 16000;
        int bitsPerSample = 16;
        int numChannels = 1;
        int dataSize = audioData.length;

        ByteArrayOutputStream baos = new ByteArrayOutputStream();
        try (DataOutputStream dos = new DataOutputStream(baos)) {
            // WAV header
            dos.writeBytes("RIFF");
            writeIntLE(dos, 36 + dataSize);
            dos.writeBytes("WAVE");
            dos.writeBytes("fmt ");
            writeIntLE(dos, 16); // chunk size
            writeShortLE(dos, (short) 1); // PCM format
            writeShortLE(dos, (short) numChannels);
            writeIntLE(dos, sampleRate);
            writeIntLE(dos, sampleRate * numChannels * bitsPerSample / 8);
            writeShortLE(dos, (short) (numChannels * bitsPerSample / 8));
            writeShortLE(dos, (short) bitsPerSample);
            dos.writeBytes("data");
            writeIntLE(dos, dataSize);
            dos.write(audioData);
        } catch (IOException e) {
            log.error("Error converting to WAV: {}", e.getMessage());
            return audioData;
        }

        return baos.toByteArray();
    }

    private void writeIntLE(DataOutputStream dos, int value) throws IOException {
        dos.write(value & 0xFF);
        dos.write((value >> 8) & 0xFF);
        dos.write((value >> 16) & 0xFF);
        dos.write((value >> 24) & 0xFF);
    }

    private void writeShortLE(DataOutputStream dos, short value) throws IOException {
        dos.write(value & 0xFF);
        dos.write((value >> 8) & 0xFF);
    }
}
