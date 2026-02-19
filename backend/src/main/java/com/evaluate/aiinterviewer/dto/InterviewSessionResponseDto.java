package com.evaluate.aiinterviewer.dto;

import lombok.Data;
import lombok.NoArgsConstructor;
import lombok.AllArgsConstructor;
import lombok.Builder;

import java.time.LocalDateTime;

@Data
@NoArgsConstructor
@AllArgsConstructor
@Builder
public class InterviewSessionResponseDto {
    private Long id;
    private String domain;
    private String difficulty;
    private Integer durationMinutes;
    private String status;
    private Double score;
    private LocalDateTime createdAt;
    private LocalDateTime completedAt;
}
