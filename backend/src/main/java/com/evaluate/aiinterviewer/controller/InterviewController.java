package com.evaluate.aiinterviewer.controller;

import com.evaluate.aiinterviewer.dto.*;
import com.evaluate.aiinterviewer.model.InterviewQuestion;
import com.evaluate.aiinterviewer.model.InterviewSession;
import com.evaluate.aiinterviewer.repository.InterviewQuestionRepository;
import com.evaluate.aiinterviewer.repository.InterviewSessionRepository;
import com.evaluate.aiinterviewer.service.LlmService;
import com.evaluate.aiinterviewer.service.RagService;
import com.evaluate.aiinterviewer.service.SpeechService;
import com.evaluate.aiinterviewer.service.StorageService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;
import org.springframework.web.server.ResponseStatusException;

import java.time.LocalDateTime;
import java.time.Duration;
import java.util.*;
import java.util.stream.Collectors;

@RestController
@RequestMapping("/api/interview")
@RequiredArgsConstructor
@Slf4j
public class InterviewController {

    private final InterviewSessionRepository sessionRepository;
    private final InterviewQuestionRepository questionRepository;
    private final LlmService llmService;
    private final RagService ragService;
    private final SpeechService speechService;
    private final StorageService storageService;

    // ─── Domains ────────────────────────────────────────────────────────

    @GetMapping("/domains")
    public InterviewDomainsDto getDomains() {
        return new InterviewDomainsDto();
    }

    // ─── Sessions ───────────────────────────────────────────────────────

    @PostMapping("/sessions")
    public InterviewSessionResponseDto createSession(@RequestBody InterviewSessionCreateDto dto) {
        try {
            InterviewSession session = new InterviewSession();
            session.setDomain(dto.getDomain());
            session.setDifficulty(dto.getDifficulty() != null ? dto.getDifficulty() : "medium");
            session.setDurationMinutes(dto.getDurationMinutes() != null ? dto.getDurationMinutes() : 45);
            session.setStatus("active");

            session = sessionRepository.save(session);
            return toResponseDto(session);
        } catch (Exception e) {
            throw new ResponseStatusException(HttpStatus.INTERNAL_SERVER_ERROR,
                    "Error creating session: " + e.getMessage());
        }
    }

    @GetMapping("/sessions/{sessionId}")
    public InterviewSessionResponseDto getSession(@PathVariable Long sessionId) {
        InterviewSession session = sessionRepository.findById(sessionId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Session not found"));
        return toResponseDto(session);
    }

    @PutMapping("/sessions/{sessionId}/complete")
    public Map<String, Object> completeSession(@PathVariable Long sessionId) {
        InterviewSession session = sessionRepository.findById(sessionId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Session not found"));

        List<InterviewQuestion> scoredQuestions = questionRepository.findBySessionIdAndScoreIsNotNull(sessionId);

        if (!scoredQuestions.isEmpty()) {
            double avgScore = scoredQuestions.stream()
                    .mapToDouble(InterviewQuestion::getScore)
                    .average()
                    .orElse(0.0);
            session.setScore(Math.round(avgScore * 100.0) / 100.0);
        }

        session.setStatus("completed");
        session.setCompletedAt(LocalDateTime.now());
        sessionRepository.save(session);

        Map<String, Object> result = new HashMap<>();
        result.put("message", "Session completed");
        result.put("final_score", session.getScore());
        return result;
    }

    @GetMapping("/sessions/{sessionId}/questions")
    public List<InterviewQuestion> getSessionQuestions(@PathVariable Long sessionId) {
        return questionRepository.findBySessionIdOrderByIdAsc(sessionId);
    }

    // ─── Questions ──────────────────────────────────────────────────────

    @PostMapping("/questions")
    public QuestionResponseDto getNextQuestion(@RequestBody QuestionRequestDto request) {
        log.info("Question request received for session {}, context: {}",
                request.getSessionId(), request.getContext());

        InterviewSession session = sessionRepository.findById(request.getSessionId())
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Session not found"));

        // Check if interview time is up
        LocalDateTime now = LocalDateTime.now();
        LocalDateTime sessionEndTime = session.getCreatedAt().plusMinutes(session.getDurationMinutes());
        if (sessionEndTime.isBefore(now)) {
            if (!"completed".equals(session.getStatus())) {
                completeSession(session.getId());
            }
            throw new ResponseStatusException(HttpStatus.GONE,
                    "Interview time has expired. Redirecting to results.");
        }

        List<InterviewQuestion> existingQuestions =
                questionRepository.findBySessionIdOrderByIdAsc(request.getSessionId());
        log.info("Found {} existing questions for session {}", existingQuestions.size(), request.getSessionId());

        // Logic for handling different scenarios
        String context = request.getContext();
        if (context == null || context.trim().isEmpty()) {
            log.info("Request for first question (no context)");
            if (!existingQuestions.isEmpty()) {
                InterviewQuestion first = existingQuestions.get(0);
                log.info("Returning existing first question: {}", first.getId());
                return toQuestionDto(first, "technical");
            }
            log.info("No existing questions, creating first question");
        } else {
            log.info("Request with context: {}...", context.substring(0, Math.min(100, context.length())));

            if (!context.contains("Moving to next question")) {
                log.info("Potential duplicate call, checking for unanswered questions");
                Optional<InterviewQuestion> unanswered = existingQuestions.stream()
                        .filter(q -> q.getUserAnswer() == null)
                        .findFirst();

                if (unanswered.isPresent()) {
                    log.info("Returning existing unanswered question: {}", unanswered.get().getId());
                    return toQuestionDto(unanswered.get(), "technical");
                }
            } else {
                log.info("Explicit request for next question");
            }
        }

        // Generate a new question
        log.info("Generating new question...");
        Map<String, Object> questionData = llmService.generateQuestion(
                session.getDomain(), session.getDifficulty(), context);

        InterviewQuestion dbQuestion = new InterviewQuestion();
        dbQuestion.setSessionId(request.getSessionId());
        dbQuestion.setQuestionText((String) questionData.get("question_text"));
        dbQuestion.setExpectedAnswer(String.valueOf(questionData.getOrDefault("expected_concepts", List.of())));

        dbQuestion = questionRepository.save(dbQuestion);
        log.info("Created new question with ID: {}", dbQuestion.getId());

        return QuestionResponseDto.builder()
                .id(dbQuestion.getId())
                .sessionId(dbQuestion.getSessionId())
                .questionText(dbQuestion.getQuestionText())
                .questionType((String) questionData.getOrDefault("question_type", "technical"))
                .build();
    }

    // ─── Answers ────────────────────────────────────────────────────────

    @PostMapping("/questions/{questionId}/answer")
    public AnswerFeedbackDto submitAnswer(
            @PathVariable Long questionId,
            @RequestBody AnswerSubmissionDto answer) {

        InterviewQuestion question = questionRepository.findById(questionId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Question not found"));

        InterviewSession session = sessionRepository.findById(question.getSessionId())
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Session not found"));

        // Check if session is still active
        LocalDateTime now = LocalDateTime.now();
        LocalDateTime sessionEndTime = session.getCreatedAt().plusMinutes(session.getDurationMinutes());
        if (sessionEndTime.isBefore(now)) {
            if (!"completed".equals(session.getStatus())) {
                completeSession(session.getId());
            }
            throw new ResponseStatusException(HttpStatus.GONE, "Interview time has expired.");
        }

        // Evaluate answer using LLM
        @SuppressWarnings("unchecked")
        Map<String, Object> evaluation = llmService.evaluateAnswer(
                question.getQuestionText(), answer.getAnswerText(), session.getDomain());

        // Update question with answer and feedback
        question.setUserAnswer(answer.getAnswerText());
        question.setScore(((Number) evaluation.get("score")).doubleValue());
        question.setFeedback((String) evaluation.get("feedback"));
        question.setAnsweredAt(LocalDateTime.now());
        questionRepository.save(question);

        @SuppressWarnings("unchecked")
        List<String> suggestions = (List<String>) evaluation.getOrDefault("suggestions", List.of());

        return AnswerFeedbackDto.builder()
                .questionId(questionId)
                .score(((Number) evaluation.get("score")).doubleValue())
                .feedback((String) evaluation.get("feedback"))
                .suggestions(suggestions)
                .build();
    }

    @PostMapping("/questions/{questionId}/audio")
    public ResponseEntity<?> submitAudioAnswer(
            @PathVariable Long questionId,
            @RequestParam("audio_file") MultipartFile audioFile) {
        try {
            InterviewQuestion question = questionRepository.findById(questionId)
                    .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Question not found"));

            InterviewSession session = sessionRepository.findById(question.getSessionId())
                    .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Session not found"));

            // Check if session is still active
            LocalDateTime now = LocalDateTime.now();
            LocalDateTime sessionEndTime = session.getCreatedAt().plusMinutes(session.getDurationMinutes());
            if (sessionEndTime.isBefore(now)) {
                if (!"completed".equals(session.getStatus())) {
                    completeSession(session.getId());
                }
                throw new ResponseStatusException(HttpStatus.GONE, "Interview time has expired.");
            }

            byte[] audioData = audioFile.getBytes();

            // Convert speech to text
            String transcribedText = speechService.speechToText(audioData);

            // Check for empty or failed transcription
            if (transcribedText == null || transcribedText.trim().isEmpty()) {
                return ResponseEntity.ok(AnswerFeedbackDto.builder()
                        .questionId(questionId)
                        .score(0.0)
                        .feedback("No speech detected in the audio. Please ensure you're speaking clearly into the microphone and try again.")
                        .suggestions(List.of(
                                "Check that your microphone is working and not muted",
                                "Speak clearly and loudly enough for the microphone to pick up",
                                "Try recording again or use the text input option instead",
                                "Speak clearly and at a normal pace",
                                "Try recording again or type your answer instead"
                        ))
                        .error(true)
                        .build());
            }

            // Check if too short
            if (transcribedText.trim().length() < 10) {
                return ResponseEntity.ok(AnswerFeedbackDto.builder()
                        .questionId(questionId)
                        .score(0.0)
                        .feedback("Answer too short: '" + transcribedText + "'. Please provide a more detailed response.")
                        .suggestions(List.of(
                                "Elaborate on your answer with examples",
                                "Explain your reasoning",
                                "Consider the key concepts related to the question"
                        ))
                        .error(true)
                        .build());
            }

            // Upload audio file
            storageService.uploadAudio(audioData);

            // Submit as text answer
            AnswerSubmissionDto submission = new AnswerSubmissionDto();
            submission.setQuestionId(questionId);
            submission.setAnswerText(transcribedText);

            AnswerFeedbackDto feedbackDto = submitAnswer(questionId, submission);
            return ResponseEntity.ok(feedbackDto);

        } catch (ResponseStatusException e) {
            throw e;
        } catch (Exception e) {
            throw new ResponseStatusException(HttpStatus.INTERNAL_SERVER_ERROR,
                    "Error processing audio: " + e.getMessage());
        }
    }

    // ─── Speech / TTS ───────────────────────────────────────────────────

    @GetMapping("/questions/{questionId}/speech")
    public ResponseEntity<?> getQuestionAudio(@PathVariable Long questionId) {
        InterviewQuestion question = questionRepository.findById(questionId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Question not found"));

        Optional<byte[]> audioData = speechService.textToSpeech(question.getQuestionText());

        if (audioData.isEmpty()) {
            return ResponseEntity.ok(Map.of(
                    "error", "Text-to-speech not available",
                    "question_text", question.getQuestionText()
            ));
        }

        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.parseMediaType("audio/wav"));
        headers.set("Content-Disposition", "attachment; filename=question_" + questionId + ".wav");

        return new ResponseEntity<>(audioData.get(), headers, HttpStatus.OK);
    }

    @PostMapping("/feedback/speech")
    public ResponseEntity<?> generateFeedbackSpeech(@RequestBody FeedbackSpeechRequestDto request) {
        Optional<byte[]> audioData = speechService.textToSpeech(request.getText());

        if (audioData.isEmpty()) {
            return ResponseEntity.ok(Map.of("error", "Text-to-speech service not available"));
        }

        HttpHeaders headers = new HttpHeaders();
        headers.setContentType(MediaType.parseMediaType("audio/wav"));
        headers.set("Content-Disposition", "attachment; filename=feedback_audio.wav");

        return new ResponseEntity<>(audioData.get(), headers, HttpStatus.OK);
    }

    // ─── Domain Topics ──────────────────────────────────────────────────

    @GetMapping("/domains/{domain}/topics")
    public Map<String, Object> getDomainTopics(@PathVariable String domain) {
        try {
            Map<String, RagService.DomainKnowledge> kb = ragService.getKnowledgeBase();
            if (kb.containsKey(domain)) {
                List<String> topics = kb.get(domain).sections.stream()
                        .map(s -> s.sectionName)
                        .filter(s -> s != null && !s.isEmpty())
                        .collect(Collectors.toList());

                Map<String, Object> result = new HashMap<>();
                result.put("domain", domain);
                result.put("topics", topics);
                result.put("total_topics", topics.size());
                return result;
            }

            // Final fallback
            Map<String, Object> result = new HashMap<>();
            result.put("domain", domain);
            result.put("topics", List.of("General " + domain + " interview topics"));
            result.put("total_topics", 1);
            return result;

        } catch (Exception e) {
            log.error("Error in getDomainTopics: {}", e.getMessage());
            Map<String, Object> result = new HashMap<>();
            result.put("domain", domain);
            result.put("topics", List.of("General " + domain + " interview topics"));
            result.put("total_topics", 1);
            result.put("error", e.getMessage());
            return result;
        }
    }

    // ─── Helpers ────────────────────────────────────────────────────────

    private InterviewSessionResponseDto toResponseDto(InterviewSession session) {
        return InterviewSessionResponseDto.builder()
                .id(session.getId())
                .domain(session.getDomain())
                .difficulty(session.getDifficulty())
                .durationMinutes(session.getDurationMinutes())
                .status(session.getStatus())
                .score(session.getScore())
                .createdAt(session.getCreatedAt())
                .completedAt(session.getCompletedAt())
                .build();
    }

    private QuestionResponseDto toQuestionDto(InterviewQuestion q, String questionType) {
        return QuestionResponseDto.builder()
                .id(q.getId())
                .sessionId(q.getSessionId())
                .questionText(q.getQuestionText())
                .questionType(questionType)
                .build();
    }
}
