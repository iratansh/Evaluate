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
        
        # Initialize result with strict scoring in mind
        result = {
            "score": 0.0,  # Start with 0, require explicit scoring
            "feedback": "",
            "suggestions": []
        }
        
        # Debug: Print the actual response to understand the format
        print(f"DEBUG - Raw LLM Response: {response[:500]}...")  
        
        lines = response.split('\n')
        current_section = None
        feedback_parts = []
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Handle the specific format from enhance_evaluation_prompt
            if line.startswith("Score:"):
                current_section = "score"
                try:
                    score_text = line.replace("Score:", "").strip()
                    # Extract numeric score (handle "7/10", "7", "[0-10]", etc.)
                    import re
                    score_match = re.search(r'(\d+(?:\.\d+)?)', score_text)
                    if score_match:
                        result["score"] = float(score_match.group(1))
                        print(f"DEBUG - Extracted score: {result['score']}")
                    else:
                        result["score"] = 0.0  # Default to 0 if parsing fails
                        print(f"DEBUG - Failed to parse score from: {score_text}")
                except Exception as e:
                    result["score"] = 0.0
                    print(f"DEBUG - Score parsing error: {e}")
            
            elif line.startswith("Relevance_Check:"):
                current_section = "relevance"
                content = line.replace("Relevance_Check:", "").strip()
                feedback_parts.append(f"Relevance: {content}")
                
            elif line.startswith("Content_Quality:"):
                current_section = "content"
                content = line.replace("Content_Quality:", "").strip()
                feedback_parts.append(f"Content Quality: {content}")
                
            elif line.startswith("Missing_Elements:"):
                current_section = "missing"
                content = line.replace("Missing_Elements:", "").strip()
                feedback_parts.append(f"Missing Elements: {content}")
                
            elif line.startswith("Improvement_Suggestions:"):
                current_section = "suggestions"
                content = line.replace("Improvement_Suggestions:", "").strip()
                if content:
                    result["suggestions"].append(content)
            
            # Continue adding content to current section
            elif current_section and line and not any(line.startswith(p + ":") for p in ["Score", "Relevance_Check", "Content_Quality", "Missing_Elements", "Improvement_Suggestions"]):
                if current_section in ["relevance", "content", "missing"]:
                    # Add continuation text to the last feedback part
                    if feedback_parts:
                        feedback_parts[-1] += f" {line}"
                elif current_section == "suggestions" and line:
                    # Handle bullet points or numbered lists for suggestions
                    if line.startswith(("- ", "* ", "• ")) or (len(line) > 2 and line[0].isdigit() and line[1] in ".)"):
                        suggestion = line.lstrip("- *•0123456789.)")
                        result["suggestions"].append(suggestion.strip())
                    else:
                        result["suggestions"].append(line)
        
        # Combine feedback parts
        result["feedback"] = "\n\n".join(feedback_parts) if feedback_parts else ""
        
        # If parsing completely failed, check if this is gibberish/random input
        if not result["feedback"] and result["score"] == 0.0:
            # Check if the answer is actually gibberish (random characters, no real words)
            import re
            word_pattern = re.compile(r'\b[a-zA-Z]{3,}\b')  # Words with 3+ letters
            words = word_pattern.findall(answer)
            word_ratio = len(words) / max(1, len(answer.split()))
            
            if word_ratio < 0.3 or len(answer.strip()) < 5:
                # This looks like gibberish - apply strict scoring as intended
                result["score"] = 1.0
                result["feedback"] = "Your response appears to be gibberish or random characters. Please provide a coherent answer that addresses the technical question asked."
                result["suggestions"] = [
                    "Read the question carefully and ensure you understand what is being asked",
                    "Provide a structured response with clear explanations",
                    "Use proper technical terminology relevant to the domain",
                    "Include specific examples or use cases where appropriate"
                ]
                print(f"DEBUG - Detected gibberish input, applying strict scoring")
                return result
        
        # Only fall back to length-based scoring if we truly couldn't parse anything AND it's not gibberish
        if not result["feedback"] and result["score"] == 0.0:
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
        
        # More generous scoring logic
        if answer_length < 5:
            score = 2.0
            feedback = "Your answer is too brief. Technical interviews require detailed explanations with specific examples."
        elif answer_length < 15:
            score = 4.0
            feedback = "Your answer covers some basics but needs more detail. Try to explain the reasoning behind your approach."
        elif answer_length < 40:
            score = 6.5
            feedback = "Good answer with reasonable detail. Consider adding specific examples or discussing alternative approaches."
        elif answer_length < 80:
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