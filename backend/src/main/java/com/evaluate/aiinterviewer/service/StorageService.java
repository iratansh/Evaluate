package com.evaluate.aiinterviewer.service;

import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;

import jakarta.annotation.PostConstruct;
import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.Optional;
import java.util.UUID;

@Service
@Slf4j
public class StorageService {

    @Value("${azure.storage.connection-string:}")
    private String connectionString;

    private boolean azureStorageAvailable = false;
    private Object blobServiceClient;
    private final String containerName = "interview-audio";
    private String localAudioDir = "./data/audio";

    @PostConstruct
    public void initialize() {
        if (connectionString != null && !connectionString.isEmpty()) {
            try {
                Class<?> blobServiceClientClass = Class.forName("com.azure.storage.blob.BlobServiceClient");
                Class<?> builderClass = Class.forName("com.azure.storage.blob.BlobServiceClientBuilder");
                Object builder = builderClass.getDeclaredConstructor().newInstance();
                var connStrMethod = builderClass.getMethod("connectionString", String.class);
                builder = connStrMethod.invoke(builder, connectionString);
                var buildMethod = builderClass.getMethod("buildClient");
                blobServiceClient = buildMethod.invoke(builder);
                azureStorageAvailable = true;
                log.info("StorageService initialized with Azure Blob Storage");
            } catch (Exception e) {
                log.warn("Failed to initialize Azure Blob Storage: {}", e.getMessage());
                fallbackToLocal();
            }
        } else {
            log.info("StorageService: Azure Storage connection string not configured");
            fallbackToLocal();
        }
    }

    private void fallbackToLocal() {
        azureStorageAvailable = false;
        blobServiceClient = null;
        try {
            Files.createDirectories(Paths.get(localAudioDir));
        } catch (IOException e) {
            log.error("Failed to create local audio directory: {}", e.getMessage());
        }
        log.info("StorageService initialized with local storage (fallback)");
    }

    public Optional<String> uploadAudio(byte[] audioData, String fileExtension) {
        String filename = UUID.randomUUID() + "." + fileExtension;

        // Try Azure first
        if (azureStorageAvailable && blobServiceClient != null) {
            try {
                // Use reflection for Azure SDK
                var getBlobContainer = blobServiceClient.getClass().getMethod("getBlobContainerClient", String.class);
                Object containerClient = getBlobContainer.invoke(blobServiceClient, containerName);

                var getBlobClient = containerClient.getClass().getMethod("getBlobClient", String.class);
                Object blobClient = getBlobClient.invoke(containerClient, filename);

                // Upload using BinaryData
                Class<?> binaryDataClass = Class.forName("com.azure.core.util.BinaryData");
                var fromBytes = binaryDataClass.getMethod("fromBytes", byte[].class);
                Object binaryData = fromBytes.invoke(null, audioData);

                var upload = blobClient.getClass().getMethod("upload", binaryDataClass, boolean.class);
                upload.invoke(blobClient, binaryData, true);

                String blobUrl = "azure://" + containerName + "/" + filename;
                log.info("Audio uploaded to Azure Blob: {}", filename);
                return Optional.of(blobUrl);
            } catch (Exception e) {
                log.error("Error uploading to Azure Blob Storage: {}", e.getMessage());
            }
        }

        // Fallback to local storage
        try {
            Path localPath = Paths.get(localAudioDir, filename);
            Files.createDirectories(localPath.getParent());
            try (FileOutputStream fos = new FileOutputStream(localPath.toFile())) {
                fos.write(audioData);
            }
            return Optional.of("/audio/" + filename);
        } catch (IOException e) {
            log.error("Error saving audio locally: {}", e.getMessage());
            return Optional.empty();
        }
    }

    public Optional<String> uploadAudio(byte[] audioData) {
        return uploadAudio(audioData, "wav");
    }
}
