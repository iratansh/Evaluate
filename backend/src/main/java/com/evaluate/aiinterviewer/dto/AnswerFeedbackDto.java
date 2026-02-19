package com.evaluate.aiinterviewer.dto;

import lombok.Data;
import lombok.NoArgsConstructor;
import lombok.AllArgsConstructor;
import lombok.Builder;

import java.util.List;

@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class AnswerFeedbackDto {
    private Long questionId;
    private Double score;
    private String feedback;
    private List<String> suggestions;
    private Boolean error;
}
