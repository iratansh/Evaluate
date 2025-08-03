import os
import httpx
from typing import List, Dict, Optional
from app.config import settings

class LLMService:
    def __init__(self):
        self.ollama_base_url = settings.OLLAMA_BASE_URL
        self.model = settings.OLLAMA_MODEL
        self.client = httpx.AsyncClient(timeout=60.0)
    
    async def generate_question(self, domain: str, difficulty: str, context: str = None) -> Dict:
        """Generate interview question based on domain and difficulty"""
        prompt = f"""
        You are an expert interviewer for {domain} positions.
        Generate a {difficulty} level interview question.
        
        Domain: {domain}
        Difficulty: {difficulty}
        
        Context from previous questions: {context or "This is the first question"}
        
        Provide a well-structured question that tests both theoretical knowledge and practical application.
        Make it engaging and relevant to current industry practices.
        
        Format your response as:
        Question: [Your question here]
        Type: [technical/behavioral/coding]
        Expected_concepts: [key concepts the answer should cover]
        """
        
        try:
            response = await self._call_ollama(prompt)
            return self._parse_question_response(response)
        except Exception as e:
            print(f"Error generating question: {e}")
            return self._get_fallback_question(domain, difficulty)
    
    async def evaluate_answer(self, question: str, answer: str, domain: str) -> Dict:
        """Evaluate user's answer and provide feedback"""
        prompt = f"""
        As an expert interviewer for {domain}, evaluate this answer:
        
        Question: {question}
        Answer: {answer}
        
        Provide:
        1. Score (0-10)
        2. Strengths in the answer
        3. Areas for improvement
        4. Suggestions for better answers
        
        Format:
        Score: [0-10]
        Strengths: [list strengths]
        Improvements: [areas to improve]
        Suggestions: [specific suggestions]
        """
        
        try:
            response = await self._call_ollama(prompt)
            return self._parse_evaluation_response(response)
        except Exception as e:
            print(f"Error evaluating answer: {e}")
            return {
                "score": 5.0,
                "feedback": "Unable to evaluate answer at this time.",
                "suggestions": ["Please try again later."]
            }
    
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
        lines = response.split('\n')
        result = {
            "question_text": "What are the key principles of good software design?",
            "question_type": "technical",
            "expected_concepts": ["SOLID principles", "Design patterns", "Clean code"]
        }
        
        for line in lines:
            if line.startswith("Question:"):
                result["question_text"] = line.replace("Question:", "").strip()
            elif line.startswith("Type:"):
                result["question_type"] = line.replace("Type:", "").strip()
            elif line.startswith("Expected_concepts:"):
                concepts = line.replace("Expected_concepts:", "").strip()
                result["expected_concepts"] = [c.strip() for c in concepts.split(",")]
        
        return result
    
    def _parse_evaluation_response(self, response: str) -> Dict:
        """Parse LLM response for answer evaluation"""
        lines = response.split('\n')
        result = {
            "score": 5.0,
            "feedback": "Answer evaluated.",
            "suggestions": ["Keep practicing!"]
        }
        
        for line in lines:
            if line.startswith("Score:"):
                try:
                    score_text = line.replace("Score:", "").strip()
                    result["score"] = float(score_text.split()[0])
                except:
                    result["score"] = 5.0
            elif line.startswith("Strengths:"):
                result["feedback"] = line.replace("Strengths:", "").strip()
            elif line.startswith("Suggestions:"):
                suggestions = line.replace("Suggestions:", "").strip()
                result["suggestions"] = [s.strip() for s in suggestions.split(",")]
        
        return result
    
    def _get_fallback_question(self, domain: str, difficulty: str) -> Dict:
        """Fallback questions when LLM is unavailable"""
        fallback_questions = {
            "Software Engineering": {
                "easy": "What is the difference between a class and an object in object-oriented programming?",
                "medium": "Explain the SOLID principles and provide an example of each.",
                "hard": "Design a scalable microservices architecture for an e-commerce platform."
            },
            "Data Science": {
                "easy": "What is the difference between supervised and unsupervised learning?",
                "medium": "Explain bias-variance tradeoff and how to handle it.",
                "hard": "Design an A/B testing framework for a recommendation system."
            },
            "AI/ML": {
                "easy": "What is the difference between artificial intelligence and machine learning?",
                "medium": "Explain the concept of backpropagation in neural networks.",
                "hard": "How would you implement a transformer model from scratch?"
            },
            "Hardware/ECE": {
                "easy": "Explain Ohm's law and its applications.",
                "medium": "What is the difference between analog and digital signals?",
                "hard": "Design a low-power microcontroller system for IoT applications."
            },
            "Robotics": {
                "easy": "What are the main components of a robotic system?",
                "medium": "Explain PID control and its use in robotics.",
                "hard": "How would you implement SLAM for an autonomous robot?"
            }
        }
        
        question = fallback_questions.get(domain, {}).get(difficulty, 
            "Tell me about your experience in this field.")
        
        return {
            "question_text": question,
            "question_type": "technical",
            "expected_concepts": ["Domain knowledge", "Problem solving"]
        }

# Global instance
llm_service = LLMService()
