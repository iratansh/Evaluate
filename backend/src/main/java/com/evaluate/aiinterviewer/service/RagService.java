package com.evaluate.aiinterviewer.service;

import jakarta.annotation.PostConstruct;
import lombok.extern.slf4j.Slf4j;
import org.springframework.core.io.ClassPathResource;
import org.springframework.core.io.Resource;
import org.springframework.stereotype.Service;

import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.*;
import java.util.stream.Collectors;

@Service
@Slf4j
public class RagService {

    private final Map<String, DomainKnowledge> knowledgeBase = new HashMap<>();

    public static class DomainKnowledge {
        public String content;
        public List<Section> sections = new ArrayList<>();
    }

    public static class Section {
        public String sectionName;
        public String content;

        public Section(String sectionName, String content) {
            this.sectionName = sectionName;
            this.content = content;
        }
    }

    @PostConstruct
    public void initialize() {
        String[] domains = {"software_engineering", "data_science", "ai_ml", "hardware_ece", "robotics"};
        for (String domain : domains) {
            try {
                Resource resource = new ClassPathResource("data/" + domain + "/topics.md");
                if (resource.exists()) {
                    String content;
                    try (BufferedReader reader = new BufferedReader(
                            new InputStreamReader(resource.getInputStream(), StandardCharsets.UTF_8))) {
                        content = reader.lines().collect(Collectors.joining("\n"));
                    }

                    DomainKnowledge dk = new DomainKnowledge();
                    dk.content = content;
                    dk.sections = splitMarkdownContent(content, domain);
                    knowledgeBase.put(domain, dk);
                    log.info("Loaded domain: {}", domain);
                }
            } catch (IOException e) {
                log.warn("Could not load topics for domain: {}", domain, e);
            }
        }
        log.info("Loaded {} domains into knowledge base", knowledgeBase.size());
    }

    private List<Section> splitMarkdownContent(String content, String domain) {
        List<Section> sections = new ArrayList<>();
        String[] lines = content.split("\n");
        StringBuilder currentSection = new StringBuilder();
        String currentHeading = "";

        for (String line : lines) {
            if (line.startsWith("## ")) {
                if (!currentSection.isEmpty()) {
                    sections.add(new Section(currentHeading,
                            "Domain: " + domain + "\nSection: " + currentHeading + "\n" + currentSection.toString().trim()));
                }
                currentHeading = line.substring(3).trim();
                currentSection = new StringBuilder();
                currentSection.append(line).append("\n");
            } else {
                currentSection.append(line).append("\n");
            }
        }

        if (!currentSection.isEmpty()) {
            sections.add(new Section(currentHeading,
                    "Domain: " + domain + "\nSection: " + currentHeading + "\n" + currentSection.toString().trim()));
        }

        return sections;
    }

    public Map<String, DomainKnowledge> getKnowledgeBase() {
        return knowledgeBase;
    }

    public List<String> getRelevantContext(String query, String domain, int nResults) {
        if (knowledgeBase.containsKey(domain)) {
            List<Section> sections = knowledgeBase.get(domain).sections;

            if (query.toLowerCase().contains("topics")) {
                return sections.stream()
                        .map(s -> s.sectionName)
                        .collect(Collectors.toList());
            }

            String[] queryWords = query.toLowerCase().split("\\s+");
            List<Map.Entry<Integer, String>> scored = new ArrayList<>();

            for (Section section : sections) {
                String contentLower = section.content.toLowerCase();
                int score = 0;
                for (String word : queryWords) {
                    if (contentLower.contains(word)) score++;
                }
                if (score > 0) {
                    scored.add(Map.entry(score, section.content));
                }
            }

            scored.sort((a, b) -> b.getKey().compareTo(a.getKey()));
            return scored.stream()
                    .limit(nResults)
                    .map(Map.Entry::getValue)
                    .collect(Collectors.toList());
        }

        return getFallbackContext(domain);
    }

    public List<String> getRelevantContext(String query, String domain) {
        return getRelevantContext(query, domain, 3);
    }

    private List<String> getFallbackContext(String domain) {
        return List.of("General " + domain + " interview topics");
    }

    public String enhanceQuestionPrompt(String domain, String difficulty, String context) {
        String query = domain + " " + difficulty + " interview question topics";
        List<String> relevantContext = getRelevantContext(query, domain);
        String contextText = String.join("\n", relevantContext);

        return """
                You are an expert interviewer for %s positions.
                Generate a %s level interview question based on the following context.
                Ensure that the question is specific, practical, and relevant to current industry practices and also doesn't require code execution.
                
                RELEVANT TOPICS AND CONTEXT:
                %s
                
                Domain: %s
                Difficulty: %s
                Previous context: %s
                
                Based on the relevant topics above, create a specific, practical question that:
                1. Tests both theoretical knowledge and practical application
                2. Is appropriate for the %s difficulty level
                3. Draws from the specific topics mentioned in the context
                4. Is engaging and relevant to current industry practices
                
                Format your response as:
                Question: [Your specific question here]
                Type: [technical/behavioral/coding]
                Expected_concepts: [key concepts from the context that the answer should cover]
                Difficulty_justification: [why this is %s level]
                """.formatted(domain, difficulty, contextText, domain, difficulty,
                context != null ? context : "This is the first question",
                difficulty, difficulty);
    }

    public String enhanceEvaluationPrompt(String question, String answer, String domain) {
        List<String> relevantContext = getRelevantContext(question, domain, 2);
        String contextText = String.join("\n", relevantContext);

        return """
                You are an EXTREMELY STRICT technical interviewer for %s. Your reputation depends on maintaining the highest standards. You must be ruthless in your evaluation and never give undeserved scores.

                DOMAIN CONTEXT:
                %s

                Question: %s
                Answer: %s

                **CRITICAL EVALUATION RULES:**

                **FIRST: RELEVANCE CHECK**
                - Does the answer actually address the question asked? If not, score 0-1 immediately.
                - Is the answer in the correct domain (%s)? If not, score 0-1 immediately.
                - Is the answer coherent and understandable? If it's gibberish, nonsense, or unrelated rambling, score 0-1 immediately.

                **STRICT SCORING RUBRIC (BE RUTHLESS):**

                **0-1: IMMEDIATE FAIL** - Gibberish, random characters, or nonsensical text
                **2-3: FUNDAMENTALLY WRONG** - Major factual errors
                **4-5: SEVERELY INADEQUATE** - On-topic but superficial
                **6-7: BELOW EXPECTATIONS** - Covers basics but lacks detail
                **8-9: MEETS EXPECTATIONS** - Accurate, well-structured
                **10: EXCEPTIONAL** - Comprehensive and insightful

                **FORMAT YOUR RESPONSE:**
                Score: [0-10]
                Relevance_Check: [Pass/Fail - explain why]
                Content_Quality: [Assessment of technical accuracy and depth]
                Missing_Elements: [Key concepts not addressed]
                Improvement_Suggestions: [Specific, actionable advice]

                **Remember: Your job is to maintain standards, not to be kind. Be merciless with poor answers.**
                """.formatted(domain, contextText, question, answer, domain);
    }
}
