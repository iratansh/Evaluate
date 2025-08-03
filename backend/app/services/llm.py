import os
import httpx
from typing import List, Dict, Optional
from app.config import settings
from app.services.rag import rag_service

class LLMService:
    def __init__(self):
        self.ollama_base_url = settings.OLLAMA_BASE_URL
        self.model = settings.OLLAMA_MODEL
        self.client = httpx.AsyncClient(timeout=60.0)
    
    async def generate_question(self, domain: str, difficulty: str, context: str = None) -> Dict:
        """Generate interview question based on domain and difficulty using RAG"""
        # Get enhanced prompt with topic-specific context
        prompt = await rag_service.enhance_question_prompt(domain, difficulty, context)
        
        try:
            response = await self._call_ollama(prompt)
            parsed_response = self._parse_question_response(response)
            
            # If parsing failed or returned None, use fallback
            if not parsed_response or not parsed_response.get("question_text"):
                return self._get_fallback_question(domain, difficulty)
            
            return parsed_response
        except Exception as e:
            print(f"Error generating question: {e}")
            return self._get_fallback_question(domain, difficulty)
    
    async def evaluate_answer(self, question: str, answer: str, domain: str) -> Dict:
        """Evaluate user's answer and provide feedback using RAG"""
        # Get enhanced prompt with domain-specific context
        prompt = await rag_service.enhance_evaluation_prompt(question, answer, domain)
        
        try:
            response = await self._call_ollama(prompt)
            return self._parse_evaluation_response(response, question, answer, domain)
        except Exception as e:
            print(f"Error evaluating answer: {e}")
            # Return a more detailed fallback evaluation
            return self._get_fallback_evaluation(question, answer, domain)
    
    async def _call_ollama(self, prompt: str) -> str:
        """Make API call to Ollama"""
        try:
            response = await self.client.post(
                f"{self.ollama_base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False
                }
            )
            response.raise_for_status()
            return response.json().get("response", "")
        except httpx.ConnectError:
            print("Warning: Ollama is not running. Using fallback responses.")
            return "Ollama not available"
        except Exception as e:
            print(f"Error calling Ollama: {e}")
            return "Error generating response"
    
    def _parse_question_response(self, response: str) -> Dict:
        """Parse LLM response for question generation"""
        # If Ollama is not available, return None to trigger fallback
        if response == "Ollama not available" or response == "Error generating response":
            return None
        
        lines = response.split('\n')
        result = {
            "question_text": None,
            "question_type": "technical",
            "expected_concepts": ["Domain knowledge", "Problem solving"]
        }
        
        # Try to extract question from LLM response
        for line in lines:
            if line.startswith("Question:"):
                result["question_text"] = line.replace("Question:", "").strip()
            elif line.startswith("Type:"):
                result["question_type"] = line.replace("Type:", "").strip()
            elif line.startswith("Expected_concepts:"):
                concepts = line.replace("Expected_concepts:", "").strip()
                result["expected_concepts"] = [c.strip() for c in concepts.split(",")]
        
        # If we couldn't extract a proper question, try to use the whole response
        if not result["question_text"] and response.strip():
            # Clean up the response and use it as the question
            clean_response = response.strip()
            # Remove common LLM prefixes
            prefixes_to_remove = ["Question:", "Q:", "Interview Question:", "Technical Question:"]
            for prefix in prefixes_to_remove:
                if clean_response.startswith(prefix):
                    clean_response = clean_response[len(prefix):].strip()
            
            if len(clean_response) > 10:  # Make sure it's a reasonable question
                result["question_text"] = clean_response
        
        return result
    
    def _parse_evaluation_response(self, response: str, question: str, answer: str, domain: str) -> Dict:
        """Parse LLM response for answer evaluation with better parsing"""
        if response == "Ollama not available" or response == "Error generating response":
            return self._get_fallback_evaluation(question, answer, domain)
        
        lines = response.split('\n')
        result = {
            "score": 5.0,
            "feedback": "",
            "suggestions": []
        }
        
        # Track which section we're in
        current_section = None
        
        for line in lines:
            line = line.strip()
            
            # Identify sections
            if line.startswith("Score:"):
                current_section = "score"
                try:
                    score_text = line.replace("Score:", "").strip()
                    # Extract numeric score (handle "7/10" or just "7")
                    if "/" in score_text:
                        score_num = score_text.split("/")[0].strip()
                    else:
                        score_num = score_text.split()[0]
                    result["score"] = float(score_num)
                except:
                    result["score"] = 5.0
            
            elif any(line.startswith(prefix) for prefix in ["Strengths:", "Feedback:", "Evaluation:"]):
                current_section = "strengths"
                # Extract the content after the prefix
                for prefix in ["Strengths:", "Feedback:", "Evaluation:"]:
                    if line.startswith(prefix):
                        content = line.replace(prefix, "").strip()
                        if content:
                            result["feedback"] = content
                        break
            
            elif any(line.startswith(prefix) for prefix in ["Improvements:", "Areas for Improvement:", "Weaknesses:"]):
                current_section = "improvements"
                # Add improvements to feedback
                for prefix in ["Improvements:", "Areas for Improvement:", "Weaknesses:"]:
                    if line.startswith(prefix):
                        content = line.replace(prefix, "").strip()
                        if content and result["feedback"]:
                            result["feedback"] += f"\n\nAreas for improvement: {content}"
                        elif content:
                            result["feedback"] = f"Areas for improvement: {content}"
                        break
            
            elif any(line.startswith(prefix) for prefix in ["Suggestions:", "Recommendations:", "Next Steps:"]):
                current_section = "suggestions"
                # Extract suggestions
                for prefix in ["Suggestions:", "Recommendations:", "Next Steps:"]:
                    if line.startswith(prefix):
                        content = line.replace(prefix, "").strip()
                        if content:
                            # Split by common delimiters
                            if "," in content:
                                result["suggestions"] = [s.strip() for s in content.split(",")]
                            elif ";" in content:
                                result["suggestions"] = [s.strip() for s in content.split(";")]
                            else:
                                result["suggestions"] = [content]
                        break
            
            # Continue adding content to current section
            elif current_section and line and not any(line.startswith(p + ":") for p in ["Score", "Strengths", "Feedback", "Improvements", "Suggestions"]):
                if current_section == "strengths" and line:
                    if result["feedback"]:
                        result["feedback"] += f" {line}"
                    else:
                        result["feedback"] = line
                elif current_section == "improvements" and line:
                    result["feedback"] += f" {line}"
                elif current_section == "suggestions" and line:
                    # Handle bullet points or numbered lists
                    if line.startswith(("- ", "* ", "• ")) or (len(line) > 2 and line[0].isdigit() and line[1] in ".)"):
                        suggestion = line.lstrip("- *•0123456789.)")
                        result["suggestions"].append(suggestion.strip())
        
        # If we didn't parse anything meaningful, provide a basic evaluation
        if not result["feedback"] or result["feedback"] == "Answer evaluated.":
            length_score = min(9, max(4, len(answer.split()) / 8))  # More generous length-based scoring
            result["score"] = length_score
            
            if len(answer.split()) < 15:
                result["feedback"] = "Your answer demonstrates understanding but could benefit from more detailed explanations and specific examples."
                result["suggestions"] = [
                    "Provide more detailed explanations of key concepts",
                    "Include specific examples or use cases",
                    "Discuss relevant technical approaches or methodologies"
                ]
            elif len(answer.split()) > 100:
                result["feedback"] = "You provided a very comprehensive answer with excellent detail. Your thorough approach shows strong understanding."
                result["suggestions"] = [
                    "Consider organizing complex responses with clear structure",
                    "Focus on the most critical aspects first",
                    "Practice concise summaries of key points"
                ]
            else:
                result["feedback"] = "Solid answer that demonstrates good understanding. You covered the important concepts well."
                result["suggestions"] = [
                    "Include more technical terminology specific to " + domain,
                    "Provide concrete examples to reinforce your points",
                    "Consider discussing trade-offs or alternative approaches"
                ]
        
        # Ensure we always have suggestions
        if not result["suggestions"]:
            result["suggestions"] = self._get_domain_specific_suggestions(domain)
        
        return result
    
    def _get_fallback_evaluation(self, question: str, answer: str, domain: str) -> Dict:
        """Provide a meaningful fallback evaluation when LLM is unavailable"""
        # Basic scoring based on answer length and keywords
        answer_length = len(answer.split())
        answer_lower = answer.lower().strip()
        
        # Check for non-answers or very poor responses
        non_answers = ['i don\'t know', 'no idea', 'not sure', 'don\'t know', 'idk', 'dunno', 'no clue', 'unsure']
        if any(non_answer in answer_lower for non_answer in non_answers):
            score = 0.5
            feedback = "Not knowing the answer is understandable, but in interviews you should try to demonstrate your thought process or mention related concepts."
        elif answer_length < 3:
            score = 1.0
            feedback = "Your answer is extremely brief. Technical interviews require detailed explanations with specific examples and reasoning."
        elif answer_length < 8:
            score = 2.5
            feedback = "Your answer is too brief. Try to explain your reasoning, provide examples, and demonstrate your understanding."
        elif answer_length < 20:
            score = 4.0
            feedback = "Your answer covers some basics but needs more detail. Explain the reasoning behind your approach and provide specific examples."
        elif answer_length < 50:
            score = 6.0
            feedback = "Good answer with reasonable detail. Consider adding specific examples, discussing trade-offs, or alternative approaches."
        elif answer_length < 100:
            score = 7.5
            feedback = "Well-structured answer with good detail. You demonstrated solid understanding of the concepts."
        else:
            score = 8.0
            feedback = "Comprehensive answer with excellent detail. You showed deep understanding and considered multiple aspects."
        
        # Boost score for domain-specific keywords
        domain_keywords = self._get_domain_keywords(domain)
        keyword_matches = sum(1 for keyword in domain_keywords if keyword.lower() in answer.lower())
        
        if keyword_matches > 0:
            # Boost score by up to 1.5 points for relevant keywords
            keyword_boost = min(1.5, keyword_matches * 0.3)
            score = min(9.5, score + keyword_boost)
            feedback += f" Great use of {keyword_matches} relevant technical term{'s' if keyword_matches > 1 else ''}."
        
        # Domain-specific suggestions
        suggestions = self._get_domain_specific_suggestions(domain)
        
        return {
            "score": score,
            "feedback": feedback,
            "suggestions": suggestions
        }
    
    def _get_domain_keywords(self, domain: str) -> List[str]:
        """Get relevant technical keywords for each domain"""
        keywords_map = {
            # Handle both underscore format and full names
            "software_engineering": [
                "algorithm", "complexity", "scalability", "design pattern", "OOP", "SOLID", 
                "database", "API", "REST", "microservices", "testing", "debugging", "optimization",
                "data structure", "array", "linked list", "tree", "graph", "hash", "performance"
            ],
            "Software Engineering": [
                "algorithm", "complexity", "scalability", "design pattern", "OOP", "SOLID", 
                "database", "API", "REST", "microservices", "testing", "debugging", "optimization",
                "data structure", "array", "linked list", "tree", "graph", "hash", "performance"
            ],
            "data_science": [
                "statistics", "probability", "regression", "classification", "clustering", "model",
                "feature", "dataset", "correlation", "variance", "bias", "validation", "cross-validation",
                "pandas", "numpy", "matplotlib", "sklearn", "analysis", "hypothesis", "p-value"
            ],
            "Data Science": [
                "statistics", "probability", "regression", "classification", "clustering", "model",
                "feature", "dataset", "correlation", "variance", "bias", "validation", "cross-validation",
                "pandas", "numpy", "matplotlib", "sklearn", "analysis", "hypothesis", "p-value"
            ],
            "ai_ml": [
                "neural network", "deep learning", "gradient", "backpropagation", "overfitting",
                "regularization", "CNN", "RNN", "transformer", "attention", "training", "inference",
                "supervised", "unsupervised", "reinforcement", "algorithm", "optimization", "loss function"
            ],
            "AI/ML": [
                "neural network", "deep learning", "gradient", "backpropagation", "overfitting",
                "regularization", "CNN", "RNN", "transformer", "attention", "training", "inference",
                "supervised", "unsupervised", "reinforcement", "algorithm", "optimization", "loss function"
            ],
            "hardware_ece": [
                "circuit", "voltage", "current", "resistance", "capacitor", "inductor", "transistor",
                "amplifier", "digital", "analog", "microcontroller", "FPGA", "PCB", "signal", "power",
                "frequency", "impedance", "oscilloscope", "multimeter", "semiconductor"
            ],
            "Hardware/ECE": [
                "circuit", "voltage", "current", "resistance", "capacitor", "inductor", "transistor",
                "amplifier", "digital", "analog", "microcontroller", "FPGA", "PCB", "signal", "power",
                "frequency", "impedance", "oscilloscope", "multimeter", "semiconductor"
            ],
            "robotics": [
                "sensor", "actuator", "control", "PID", "kinematics", "dynamics", "path planning",
                "localization", "mapping", "SLAM", "computer vision", "feedback", "servo", "motor",
                "encoder", "IMU", "lidar", "camera", "autonomous", "navigation"
            ],
            "Robotics": [
                "sensor", "actuator", "control", "PID", "kinematics", "dynamics", "path planning",
                "localization", "mapping", "SLAM", "computer vision", "feedback", "servo", "motor",
                "encoder", "IMU", "lidar", "camera", "autonomous", "navigation"
            ]
        }
        
        return keywords_map.get(domain, [])
    
    def _get_domain_specific_suggestions(self, domain: str) -> List[str]:
        """Get domain-specific improvement suggestions"""
        suggestions_map = {
            # Handle both underscore format and full names
            "software_engineering": [
                "Discuss time and space complexity when relevant",
                "Consider scalability and maintainability",
                "Include specific design patterns or principles"
            ],
            "Software Engineering": [
                "Discuss time and space complexity when relevant",
                "Consider scalability and maintainability",
                "Include specific design patterns or principles"
            ],
            "data_science": [
                "Mention relevant statistical concepts",
                "Discuss data preprocessing and validation",
                "Consider model evaluation metrics"
            ],
            "Data Science": [
                "Mention relevant statistical concepts",
                "Discuss data preprocessing and validation",
                "Consider model evaluation metrics"
            ],
            "ai_ml": [
                "Explain the mathematical intuition behind algorithms",
                "Discuss model architecture choices",
                "Consider training and inference optimization"
            ],
            "AI/ML": [
                "Explain the mathematical intuition behind algorithms",
                "Discuss model architecture choices",
                "Consider training and inference optimization"
            ],
            "hardware_ece": [
                "Include circuit analysis or component specifications",
                "Discuss power consumption and efficiency",
                "Consider real-world constraints and tolerances"
            ],
            "Hardware/ECE": [
                "Include circuit analysis or component specifications",
                "Discuss power consumption and efficiency",
                "Consider real-world constraints and tolerances"
            ],
            "robotics": [
                "Discuss sensor fusion and perception",
                "Consider real-time constraints",
                "Include control theory concepts when relevant"
            ],
            "Robotics": [
                "Discuss sensor fusion and perception",
                "Consider real-time constraints",
                "Include control theory concepts when relevant"
            ]
        }

        return suggestions_map.get(domain, [
            "Provide more specific technical details",
            "Include examples from real-world applications",
            "Structure your answer clearly"
        ])
    
    def _get_fallback_question(self, domain: str, difficulty: str) -> Dict:
        """Fallback questions when LLM is unavailable"""
        fallback_questions = {
            # Handle both underscore format and full names
            "software_engineering": {
                "easy": "What is the difference between a class and an object in object-oriented programming?",
                "medium": "Explain the SOLID principles and provide an example of each.",
                "hard": "Design a scalable microservices architecture for an e-commerce platform."
            },
            "Software Engineering": {
                "easy": "What is the difference between a class and an object in object-oriented programming?",
                "medium": "Explain the SOLID principles and provide an example of each.",
                "hard": "Design a scalable microservices architecture for an e-commerce platform."
            },
            "data_science": {
                "easy": "What is the difference between supervised and unsupervised learning?",
                "medium": "Explain bias-variance tradeoff and how to handle it.",
                "hard": "Design an A/B testing framework for a recommendation system."
            },
            "Data Science": {
                "easy": "What is the difference between supervised and unsupervised learning?",
                "medium": "Explain bias-variance tradeoff and how to handle it.",
                "hard": "Design an A/B testing framework for a recommendation system."
            },
            "ai_ml": {
                "easy": "What is the difference between artificial intelligence and machine learning?",
                "medium": "Explain the concept of backpropagation in neural networks.",
                "hard": "How would you implement a transformer model from scratch?"
            },
            "AI/ML": {
                "easy": "What is the difference between artificial intelligence and machine learning?",
                "medium": "Explain the concept of backpropagation in neural networks.",
                "hard": "How would you implement a transformer model from scratch?"
            },
            "hardware_ece": {
                "easy": "Explain Ohm's law and its applications.",
                "medium": "What is the difference between analog and digital signals?",
                "hard": "Design a low-power microcontroller system for IoT applications."
            },
            "Hardware/ECE": {
                "easy": "Explain Ohm's law and its applications.",
                "medium": "What is the difference between analog and digital signals?",
                "hard": "Design a low-power microcontroller system for IoT applications."
            },
            "robotics": {
                "easy": "What are the main components of a robotic system?",
                "medium": "Explain PID control and its use in robotics.",
                "hard": "How would you implement SLAM for an autonomous robot?"
            },
            "Robotics": {
                "easy": "What are the main components of a robotic system?",
                "medium": "Explain PID control and its use in robotics.",
                "hard": "How would you implement SLAM for an autonomous robot?"
            }
        }
        
        # Try to get question for the exact domain first
        questions_for_domain = fallback_questions.get(domain, {})
        question = questions_for_domain.get(difficulty)
        
        # If not found, try a fallback
        if not question:
            question = "Tell me about your experience and approach to solving problems in this field."
        
        return {
            "question_text": question,
            "question_type": "technical",
            "expected_concepts": ["Domain knowledge", "Problem solving"]
        }

# Global instance
llm_service = LLMService()