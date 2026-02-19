package com.evaluate.aiinterviewer.service;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.web.reactive.function.client.WebClient;
import reactor.core.publisher.Mono;

import java.time.Duration;
import java.util.*;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

@Service
@Slf4j
@RequiredArgsConstructor
public class LlmService {

    private final WebClient ollamaWebClient;
    private final RagService ragService;

    @Value("${ollama.model:llama3.2}")
    private String model;

    public Map<String, Object> generateQuestion(String domain, String difficulty, String context) {
        String prompt = ragService.enhanceQuestionPrompt(domain, difficulty, context);

        try {
            String response = callOllama(prompt);
            Map<String, Object> parsed = parseQuestionResponse(response);

            if (parsed == null || parsed.get("question_text") == null) {
                return getFallbackQuestion(domain, difficulty);
            }
            return parsed;
        } catch (Exception e) {
            log.error("Error generating question: {}", e.getMessage());
            return getFallbackQuestion(domain, difficulty);
        }
    }

    public Map<String, Object> evaluateAnswer(String question, String answer, String domain) {
        String prompt = ragService.enhanceEvaluationPrompt(question, answer, domain);

        try {
            String response = callOllama(prompt);
            return parseEvaluationResponse(response, question, answer, domain);
        } catch (Exception e) {
            log.error("Error evaluating answer: {}", e.getMessage());
            return getFallbackEvaluation(question, answer, domain);
        }
    }

    private String callOllama(String prompt) {
        try {
            Map<String, Object> body = Map.of(
                    "model", model,
                    "prompt", prompt,
                    "stream", false
            );

            @SuppressWarnings("unchecked")
            Map<String, Object> result = ollamaWebClient.post()
                    .uri("/api/generate")
                    .bodyValue(body)
                    .retrieve()
                    .bodyToMono(Map.class)
                    .timeout(Duration.ofSeconds(60))
                    .onErrorResume(e -> {
                        log.warn("Ollama not available: {}", e.getMessage());
                        return Mono.just(Map.of("response", "Ollama not available"));
                    })
                    .block();

            return result != null ? (String) result.getOrDefault("response", "") : "";
        } catch (Exception e) {
            log.warn("Error calling Ollama: {}", e.getMessage());
            return "Ollama not available";
        }
    }

    private Map<String, Object> parseQuestionResponse(String response) {
        if ("Ollama not available".equals(response) || "Error generating response".equals(response)) {
            return null;
        }

        Map<String, Object> result = new HashMap<>();
        result.put("question_type", "technical");
        result.put("expected_concepts", List.of("Domain knowledge", "Problem solving"));

        String[] lines = response.split("\n");
        for (String line : lines) {
            if (line.startsWith("Question:")) {
                result.put("question_text", line.replace("Question:", "").trim());
            } else if (line.startsWith("Type:")) {
                result.put("question_type", line.replace("Type:", "").trim());
            } else if (line.startsWith("Expected_concepts:")) {
                String concepts = line.replace("Expected_concepts:", "").trim();
                result.put("expected_concepts", Arrays.asList(concepts.split(",")));
            }
        }

        if (result.get("question_text") == null && response.trim().length() > 10) {
            String clean = response.trim();
            String[] prefixes = {"Question:", "Q:", "Interview Question:", "Technical Question:"};
            for (String prefix : prefixes) {
                if (clean.startsWith(prefix)) {
                    clean = clean.substring(prefix.length()).trim();
                }
            }
            if (clean.length() > 10) {
                result.put("question_text", clean);
            }
        }

        return result;
    }

    @SuppressWarnings("unchecked")
    private Map<String, Object> parseEvaluationResponse(String response, String question, String answer, String domain) {
        if ("Ollama not available".equals(response) || "Error generating response".equals(response)) {
            return getFallbackEvaluation(question, answer, domain);
        }

        double score = 0.0;
        List<String> feedbackParts = new ArrayList<>();
        List<String> suggestions = new ArrayList<>();
        String currentSection = null;

        String[] lines = response.split("\n");
        for (String line : lines) {
            line = line.trim();
            if (line.isEmpty()) continue;

            if (line.startsWith("Score:")) {
                currentSection = "score";
                Pattern pattern = Pattern.compile("(\\d+(?:\\.\\d+)?)");
                Matcher matcher = pattern.matcher(line.replace("Score:", ""));
                if (matcher.find()) {
                    score = Double.parseDouble(matcher.group(1));
                }
            } else if (line.startsWith("Relevance_Check:")) {
                currentSection = "relevance";
                feedbackParts.add("Relevance: " + line.replace("Relevance_Check:", "").trim());
            } else if (line.startsWith("Content_Quality:")) {
                currentSection = "content";
                feedbackParts.add("Content Quality: " + line.replace("Content_Quality:", "").trim());
            } else if (line.startsWith("Missing_Elements:")) {
                currentSection = "missing";
                feedbackParts.add("Missing Elements: " + line.replace("Missing_Elements:", "").trim());
            } else if (line.startsWith("Improvement_Suggestions:")) {
                currentSection = "suggestions";
                String content = line.replace("Improvement_Suggestions:", "").trim();
                if (!content.isEmpty()) suggestions.add(content);
            } else if (currentSection != null) {
                if ("suggestions".equals(currentSection)) {
                    if (line.matches("^[-*•]\\s.*") || line.matches("^\\d+[.)].+")) {
                        suggestions.add(line.replaceAll("^[-*•\\d.)]+\\s*", "").trim());
                    } else {
                        suggestions.add(line);
                    }
                } else if (List.of("relevance", "content", "missing").contains(currentSection)) {
                    if (!feedbackParts.isEmpty()) {
                        feedbackParts.set(feedbackParts.size() - 1,
                                feedbackParts.get(feedbackParts.size() - 1) + " " + line);
                    }
                }
            }
        }

        String feedbackStr = String.join("\n\n", feedbackParts);

        // Check for gibberish
        if (feedbackStr.isEmpty() && score == 0.0) {
            Pattern wordPattern = Pattern.compile("\\b[a-zA-Z]{3,}\\b");
            Matcher wordMatcher = wordPattern.matcher(answer);
            int wordCount = 0;
            while (wordMatcher.find()) wordCount++;
            double wordRatio = (double) wordCount / Math.max(1, answer.split("\\s+").length);

            if (wordRatio < 0.3 || answer.trim().length() < 5) {
                return Map.of(
                        "score", 1.0,
                        "feedback", "Your response appears to be gibberish or random characters. Please provide a coherent answer.",
                        "suggestions", List.of(
                                "Read the question carefully",
                                "Provide a structured response with clear explanations",
                                "Use proper technical terminology",
                                "Include specific examples"
                        )
                );
            }
        }

        // Fallback scoring if parsing failed
        if (feedbackStr.isEmpty() && score == 0.0) {
            return getLengthBasedEvaluation(answer, domain);
        }

        if (suggestions.isEmpty()) {
            suggestions = getDomainSpecificSuggestions(domain);
        }

        Map<String, Object> result = new HashMap<>();
        result.put("score", score);
        result.put("feedback", feedbackStr);
        result.put("suggestions", suggestions);
        return result;
    }

    private Map<String, Object> getLengthBasedEvaluation(String answer, String domain) {
        int wordCount = answer.split("\\s+").length;
        double score = Math.min(9, Math.max(4, wordCount / 8.0));
        String feedback;
        List<String> suggestions;

        if (wordCount < 15) {
            feedback = "Your answer demonstrates understanding but could benefit from more detailed explanations and specific examples.";
            suggestions = List.of("Provide more detailed explanations", "Include specific examples", "Discuss relevant technical approaches");
        } else if (wordCount > 100) {
            feedback = "You provided a very comprehensive answer with excellent detail.";
            suggestions = List.of("Consider organizing with clear structure", "Focus on critical aspects first", "Practice concise summaries");
        } else {
            feedback = "Solid answer that demonstrates good understanding.";
            suggestions = List.of("Include more technical terminology specific to " + domain,
                    "Provide concrete examples", "Consider discussing trade-offs");
        }

        return Map.of("score", score, "feedback", feedback, "suggestions", suggestions);
    }

    private Map<String, Object> getFallbackEvaluation(String question, String answer, String domain) {
        int wordCount = answer.split("\\s+").length;
        double score;
        String feedback;

        if (wordCount < 5) {
            score = 2.0;
            feedback = "Your answer is too brief. Technical interviews require detailed explanations.";
        } else if (wordCount < 15) {
            score = 4.0;
            feedback = "Your answer covers some basics but needs more detail.";
        } else if (wordCount < 40) {
            score = 6.5;
            feedback = "Good answer with reasonable detail. Consider adding specific examples.";
        } else if (wordCount < 80) {
            score = 7.5;
            feedback = "Well-structured answer with good detail.";
        } else {
            score = 8.0;
            feedback = "Comprehensive answer with excellent detail.";
        }

        // Keyword boost
        List<String> keywords = getDomainKeywords(domain);
        long matches = keywords.stream().filter(k -> answer.toLowerCase().contains(k.toLowerCase())).count();
        if (matches > 0) {
            double boost = Math.min(1.5, matches * 0.3);
            score = Math.min(9.5, score + boost);
            feedback += " Great use of " + matches + " relevant technical term" + (matches > 1 ? "s" : "") + ".";
        }

        return Map.of(
                "score", score,
                "feedback", feedback,
                "suggestions", getDomainSpecificSuggestions(domain)
        );
    }

    private List<String> getDomainKeywords(String domain) {
        return switch (domain) {
            case "software_engineering", "Software Engineering" -> List.of(
                    "algorithm", "complexity", "scalability", "design pattern", "OOP", "SOLID",
                    "database", "API", "REST", "microservices", "testing", "debugging", "optimization",
                    "data structure", "array", "linked list", "tree", "graph", "hash", "performance"
            );
            case "data_science", "Data Science" -> List.of(
                    "statistics", "probability", "regression", "classification", "clustering", "model",
                    "feature", "dataset", "correlation", "variance", "bias", "validation", "cross-validation",
                    "pandas", "numpy", "matplotlib", "sklearn", "analysis", "hypothesis", "p-value"
            );
            case "ai_ml", "AI/ML" -> List.of(
                    "neural network", "deep learning", "gradient", "backpropagation", "overfitting",
                    "regularization", "CNN", "RNN", "transformer", "attention", "training", "inference",
                    "supervised", "unsupervised", "reinforcement", "algorithm", "optimization", "loss function"
            );
            case "hardware_ece", "Hardware/ECE" -> List.of(
                    "circuit", "voltage", "current", "resistance", "capacitor", "inductor", "transistor",
                    "amplifier", "digital", "analog", "microcontroller", "FPGA", "PCB", "signal", "power"
            );
            case "robotics", "Robotics" -> List.of(
                    "sensor", "actuator", "control", "PID", "kinematics", "dynamics", "path planning",
                    "localization", "mapping", "SLAM", "computer vision", "feedback", "servo", "motor"
            );
            default -> List.of();
        };
    }

    private List<String> getDomainSpecificSuggestions(String domain) {
        return switch (domain) {
            case "software_engineering", "Software Engineering" -> List.of(
                    "Discuss time and space complexity when relevant",
                    "Consider scalability and maintainability",
                    "Include specific design patterns or principles"
            );
            case "data_science", "Data Science" -> List.of(
                    "Mention relevant statistical concepts",
                    "Discuss data preprocessing and validation",
                    "Consider model evaluation metrics"
            );
            case "ai_ml", "AI/ML" -> List.of(
                    "Explain the mathematical intuition behind algorithms",
                    "Discuss model architecture choices",
                    "Consider training and inference optimization"
            );
            case "hardware_ece", "Hardware/ECE" -> List.of(
                    "Include circuit analysis or component specifications",
                    "Discuss power consumption and efficiency",
                    "Consider real-world constraints and tolerances"
            );
            case "robotics", "Robotics" -> List.of(
                    "Discuss sensor fusion and perception",
                    "Consider real-time constraints",
                    "Include control theory concepts when relevant"
            );
            default -> List.of(
                    "Provide more specific technical details",
                    "Include examples from real-world applications",
                    "Structure your answer clearly"
            );
        };
    }

    private Map<String, Object> getFallbackQuestion(String domain, String difficulty) {
        Map<String, Map<String, String>> fallbacks = Map.of(
                "software_engineering", Map.of(
                        "easy", "What is the difference between a class and an object in object-oriented programming?",
                        "medium", "Explain the SOLID principles and provide an example of each.",
                        "hard", "Design a scalable microservices architecture for an e-commerce platform."
                ),
                "Software Engineering", Map.of(
                        "easy", "What is the difference between a class and an object in object-oriented programming?",
                        "medium", "Explain the SOLID principles and provide an example of each.",
                        "hard", "Design a scalable microservices architecture for an e-commerce platform."
                ),
                "data_science", Map.of(
                        "easy", "What is the difference between supervised and unsupervised learning?",
                        "medium", "Explain bias-variance tradeoff and how to handle it.",
                        "hard", "Design an A/B testing framework for a recommendation system."
                ),
                "Data Science", Map.of(
                        "easy", "What is the difference between supervised and unsupervised learning?",
                        "medium", "Explain bias-variance tradeoff and how to handle it.",
                        "hard", "Design an A/B testing framework for a recommendation system."
                ),
                "ai_ml", Map.of(
                        "easy", "What is the difference between artificial intelligence and machine learning?",
                        "medium", "Explain the concept of backpropagation in neural networks.",
                        "hard", "How would you implement a transformer model from scratch?"
                ),
                "AI/ML", Map.of(
                        "easy", "What is the difference between artificial intelligence and machine learning?",
                        "medium", "Explain the concept of backpropagation in neural networks.",
                        "hard", "How would you implement a transformer model from scratch?"
                ),
                "hardware_ece", Map.of(
                        "easy", "Explain Ohm's law and its applications.",
                        "medium", "What is the difference between analog and digital signals?",
                        "hard", "Design a low-power microcontroller system for IoT applications."
                ),
                "Hardware/ECE", Map.of(
                        "easy", "Explain Ohm's law and its applications.",
                        "medium", "What is the difference between analog and digital signals?",
                        "hard", "Design a low-power microcontroller system for IoT applications."
                )
        );

        // Robotics added separately due to Map.of() limit of 10 entries
        Map<String, String> roboticsFallbacks = Map.of(
                "easy", "What are the main components of a robotic system?",
                "medium", "Explain PID control and its use in robotics.",
                "hard", "How would you implement SLAM for an autonomous robot?"
        );

        Map<String, String> domainQuestions = fallbacks.getOrDefault(domain, null);
        if (domainQuestions == null && (domain.equals("robotics") || domain.equals("Robotics"))) {
            domainQuestions = roboticsFallbacks;
        }

        String questionText = domainQuestions != null ?
                domainQuestions.getOrDefault(difficulty,
                        "Tell me about your experience and approach to solving problems in this field.") :
                "Tell me about your experience and approach to solving problems in this field.";

        Map<String, Object> result = new HashMap<>();
        result.put("question_text", questionText);
        result.put("question_type", "technical");
        result.put("expected_concepts", List.of("Domain knowledge", "Problem solving"));
        return result;
    }
}
