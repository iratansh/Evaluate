package com.evaluate.aiinterviewer;

import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.test.web.servlet.MockMvc;

import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

@SpringBootTest
@AutoConfigureMockMvc
class AiInterviewerApplicationTests {

    @Autowired
    private MockMvc mockMvc;

    @Test
    void contextLoads() {
    }

    @Test
    void testHealthCheck() throws Exception {
        mockMvc.perform(get("/health/"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.status").value("healthy"));
    }

    @Test
    void testRootEndpoint() throws Exception {
        mockMvc.perform(get("/"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.message").exists());
    }

    @Test
    void testGetDomains() throws Exception {
        mockMvc.perform(get("/api/interview/domains"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.domains").isArray())
                .andExpect(jsonPath("$.domains[0]").value("Software Engineering"));
    }

    @Test
    void testCreateInterviewSession() throws Exception {
        String sessionData = """
                {
                    "domain": "Software Engineering",
                    "difficulty": "medium",
                    "duration_minutes": 45
                }
                """;

        mockMvc.perform(post("/api/interview/sessions")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(sessionData))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.domain").value("Software Engineering"))
                .andExpect(jsonPath("$.difficulty").value("medium"))
                .andExpect(jsonPath("$.status").value("active"));
    }
}
