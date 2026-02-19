package com.evaluate.aiinterviewer.dto;

import lombok.Data;
import lombok.NoArgsConstructor;
import lombok.AllArgsConstructor;

import java.util.List;

@Data
@NoArgsConstructor
@AllArgsConstructor
public class InterviewDomainsDto {
    private List<String> domains = List.of(
            "Software Engineering",
            "Data Science",
            "AI/ML",
            "Hardware/ECE",
            "Robotics"
    );
}
