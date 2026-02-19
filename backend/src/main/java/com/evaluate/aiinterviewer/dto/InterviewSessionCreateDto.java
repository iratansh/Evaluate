package com.evaluate.aiinterviewer.dto;

import lombok.Data;
import lombok.NoArgsConstructor;
import lombok.AllArgsConstructor;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class InterviewSessionCreateDto {
    private String domain;
    private String difficulty = "medium";
    private Integer durationMinutes = 45;
}
