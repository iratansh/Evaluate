package com.evaluate.aiinterviewer.controller;

import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

@RestController
@RequestMapping("/health")
public class HealthController {

    @GetMapping({"", "/"})
    public Map<String, String> healthCheck() {
        return Map.of(
                "status", "healthy",
                "service", "AI Interviewer API",
                "version", "1.0.0"
        );
    }

    @GetMapping("/ready")
    public Map<String, Object> readinessCheck() {
        return Map.of(
                "status", "ready",
                "dependencies", Map.of(
                        "ollama", "pending",
                        "azure_speech", "pending"
                )
        );
    }
}
