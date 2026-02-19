package com.evaluate.aiinterviewer.repository;

import com.evaluate.aiinterviewer.model.InterviewQuestion;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface InterviewQuestionRepository extends JpaRepository<InterviewQuestion, Long> {

    List<InterviewQuestion> findBySessionIdOrderByIdAsc(Long sessionId);

    List<InterviewQuestion> findBySessionIdAndScoreIsNotNull(Long sessionId);
}
