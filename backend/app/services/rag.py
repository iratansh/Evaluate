import os
import json
from typing import List, Dict, Optional
from pathlib import Path
import httpx
from app.config import settings

try:
    CHROMADB_AVAILABLE = False
except ImportError:
    CHROMADB_AVAILABLE = False
    print("ChromaDB not available. Install with: pip install chromadb")

class RAGService:
    def __init__(self):
        self.ollama_base_url = settings.OLLAMA_BASE_URL
        self.client = httpx.AsyncClient(timeout=60.0)
        self.data_dir = Path("app/data")
        
        self.knowledge_base = {}
        print("RAGService initialized with file-based knowledge base")
        
        # Load topics into memory
        self._initialize_knowledge_base()
    
    def _initialize_knowledge_base(self):
        """Load all topic files into memory-based knowledge base"""
        try:
            # Process each domain directory
            for domain_dir in self.data_dir.iterdir():
                if domain_dir.is_dir():
                    topics_file = domain_dir / "topics.md"
                    if topics_file.exists():
                        content = topics_file.read_text()
                        
                        # Store content by domain
                        self.knowledge_base[domain_dir.name] = {
                            "content": content,
                            "sections": self._split_markdown_content(content, domain_dir.name)
                        }
            
            print(f"Loaded {len(self.knowledge_base)} domains into knowledge base")
            
        except Exception as e:
            print(f"Error initializing knowledge base: {e}")
    
    def _split_markdown_content(self, content: str, domain: str) -> List[Dict]:
        """Split markdown content into meaningful sections"""
        sections = []
        lines = content.split('\n')
        current_section = ""
        current_heading = ""
        
        for line in lines:
            if line.startswith('## '):
                # Save previous section
                if current_section.strip():
                    sections.append({
                        "section": current_heading,
                        "content": f"Domain: {domain}\nSection: {current_heading}\n{current_section.strip()}"
                    })
                
                # Start new section
                current_heading = line[3:].strip()
                current_section = line + '\n'
            else:
                current_section += line + '\n'
        
        # Add final section
        if current_section.strip():
            sections.append({
                "section": current_heading,
                "content": f"Domain: {domain}\nSection: {current_heading}\n{current_section.strip()}"
            })
        
        return sections
    
    async def get_relevant_context(self, query: str, domain: str, n_results: int = 3) -> List[str]:
        """Retrieve relevant context for a query from the knowledge base"""
        try:
            if domain in self.knowledge_base:
                sections = self.knowledge_base[domain]["sections"]
                
                # If query is generic, return all section headings
                if "topics" in query.lower():
                    return [section["section"] for section in sections]
                
                # Simple keyword matching for now (could be enhanced with embeddings later)
                query_words = query.lower().split()
                scored_sections = []
                
                for section in sections:
                    content_lower = section["content"].lower()
                    score = sum(1 for word in query_words if word in content_lower)
                    if score > 0:
                        scored_sections.append((score, section["content"]))
                
                # Sort by relevance and return top n_results
                scored_sections.sort(key=lambda x: x[0], reverse=True)
                return [content for _, content in scored_sections[:n_results]]
            
            return await self._fallback_context(domain)
            
        except Exception as e:
            print(f"Error querying knowledge base: {e}")
            return await self._fallback_context(domain)
    
    async def _fallback_context(self, domain: str) -> List[str]:
        """Fallback method to get context when ChromaDB is not available"""
        try:
            topics_file = self.data_dir / domain / "topics.md"
            if topics_file.exists():
                content = topics_file.read_text()
                # Return first few sections as context
                sections = content.split('## ')[:3]
                return [f"## {section}" for section in sections[1:]]  # Skip first empty section
            
            return [f"General {domain} interview topics"]
            
        except Exception as e:
            print(f"Error in fallback context: {e}")
            return [f"General {domain} interview topics"]
    
    async def generate_embedding(self, text: str) -> Optional[List[float]]:
        """Generate embeddings using Ollama (if available)"""
        try:
            response = await self.client.post(
                f"{self.ollama_base_url}/api/embeddings",
                json={
                    "model": "llama3.2", 
                    "prompt": text
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get("embedding")
            
        except Exception as e:
            print(f"Error generating embedding: {e}")
        
        return None
    
    async def enhance_question_prompt(self, domain: str, difficulty: str, context: str = None) -> str:
        """Enhance question generation prompt with relevant context"""
        # Get relevant context from knowledge base
        query = f"{domain} {difficulty} interview question topics"
        relevant_context = await self.get_relevant_context(query, domain)
        
        context_text = "\n".join(relevant_context) if relevant_context else ""
        
        enhanced_prompt = f"""
        You are an expert interviewer for {domain} positions.
        Generate a {difficulty} level interview question based on the following context.
        Ensure that the question is specific, practical, and relevant to current industry practices and also doesn't require code execution.
        
        RELEVANT TOPICS AND CONTEXT:
        {context_text}
        
        Domain: {domain}
        Difficulty: {difficulty}
        Previous context: {context or "This is the first question"}
        
        Based on the relevant topics above, create a specific, practical question that:
        1. Tests both theoretical knowledge and practical application
        2. Is appropriate for the {difficulty} difficulty level
        3. Draws from the specific topics mentioned in the context
        4. Is engaging and relevant to current industry practices
        
        Format your response as:
        Question: [Your specific question here]
        Type: [technical/behavioral/coding]
        Expected_concepts: [key concepts from the context that the answer should cover]
        Difficulty_justification: [why this is {difficulty} level]
        """
        
        return enhanced_prompt
    
    async def enhance_evaluation_prompt(self, question: str, answer: str, domain: str) -> str:
        """Enhance answer evaluation with domain-specific context"""
        # Get context related to the question
        relevant_context = await self.get_relevant_context(question, domain, n_results=2)
        context_text = "\n".join(relevant_context) if relevant_context else ""
        
        enhanced_prompt = f"""
            You are an EXTREMELY STRICT technical interviewer for {domain}. Your reputation depends on maintaining the highest standards. You must be ruthless in your evaluation and never give undeserved scores.

            DOMAIN CONTEXT:
            {context_text}

            Question: {question}
            Answer: {answer}

            **CRITICAL EVALUATION RULES:**

            **FIRST: RELEVANCE CHECK**
            - Does the answer actually address the question asked? If not, score 0-1 immediately.
            - Is the answer in the correct domain ({domain})? If not, score 0-1 immediately.
            - Is the answer coherent and understandable? If it's gibberish, nonsense, or unrelated rambling, score 0-1 immediately.

            **STRICT SCORING RUBRIC (BE RUTHLESS):**

            **0-1: IMMEDIATE FAIL**
            - Gibberish, random characters, or nonsensical text
            - Completely unrelated to the question (e.g., talking about cooking when asked about algorithms)
            - "I don't know" or equivalent non-answers
            - Copy-pasted irrelevant content
            - Answers that show zero understanding of the domain

            **2-3: FUNDAMENTALLY WRONG**
            - Answer attempts to address the topic but demonstrates fundamental misunderstanding
            - Contains major factual errors that would be dangerous in practice
            - Completely misses the core concept being asked about
            - Shows confusion about basic domain terminology

            **4-5: SEVERELY INADEQUATE**
            - Answer is on-topic but superficial and incomplete
            - Missing critical information that any practitioner should know
            - Contains minor errors but shows some basic understanding
            - Lacks the depth expected for the question level

            **6-7: BELOW EXPECTATIONS**
            - Answer covers basics but lacks detail and nuance
            - Shows understanding but misses important considerations
            - Good foundation but needs significant improvement
            - Would not satisfy a hiring manager

            **8-9: MEETS EXPECTATIONS**
            - Accurate, well-structured, and appropriately detailed
            - Demonstrates solid understanding of key concepts
            - Minor improvements possible but generally satisfactory

            **10: EXCEPTIONAL**
            - Comprehensive, insightful, and demonstrates deep expertise
            - Goes beyond the minimum requirements with valuable insights
            - Would impress any technical interviewer

            **EVALUATION CHECKLIST:**
            1. Is the answer relevant to the question? (If NO → 0-1)
            2. Does it demonstrate domain knowledge? (If NO → 0-2)
            3. Are there factual errors? (Deduct heavily)
            4. Is it complete enough for the question level?
            5. Does it show practical understanding?

            **INSTRUCTIONS:**
            - Start by checking relevance and coherence
            - Be absolutely ruthless with low-quality answers
            - Never be generous with scores - err on the side of being too strict
            - If in doubt between two scores, choose the lower one
            - Remember: A 5/10 means "severely inadequate" - use it appropriately

            **FORMAT YOUR RESPONSE:**
            Score: [0-10]
            Relevance_Check: [Pass/Fail - explain why]
            Content_Quality: [Assessment of technical accuracy and depth]
            Missing_Elements: [Key concepts from domain context that were not addressed]
            Improvement_Suggestions: [Specific, actionable advice based on domain context]

            **Remember: Your job is to maintain standards, not to be kind. Be merciless with poor answers.**
        """
        
        return enhanced_prompt

# Global instance
rag_service = RAGService()