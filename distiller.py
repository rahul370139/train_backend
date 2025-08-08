from typing import List, Dict, Optional
from pathlib import Path
import io, os, json, asyncio
import fitz  # PyMuPDF
from loguru import logger
import httpx
from schemas import ExplanationLevel, Framework
import uuid
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

CHUNK_WORDS = 400
OVERLAP = 50

# In-memory conversation storage (replace with database in production)
conversation_store = {}

# Enhanced conversation metadata for better UX
conversation_metadata = {
    "recent_pdfs": {},  # Store recent PDFs per user
    "user_preferences": {},  # Store user preferences
    "framework_detection": {},  # Store detected frameworks
    "explanation_levels": {}  # Store user's explanation level preference
}

async def cohere_embed(batch: List[str]) -> List[List[float]]:
    """Generate embeddings using Cohere API"""
    url = "https://api.cohere.ai/v1/embed"
    headers = {
        "Authorization": f"Bearer {os.getenv('COHERE_API_KEY')}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "embed-english-light-v3.0",
        "texts": batch,
        "input_type": "search_document"
    }

    async with httpx.AsyncClient() as client:
        res = await client.post(url, headers=headers, json=payload)
        res.raise_for_status()
        return res.json()["embeddings"]

async def call_groq(messages: List[Dict]) -> str:
    """Call Groq API with optimized model"""
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {os.getenv('GROQ_API_KEY')}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "llama3-8b-8192",  # Lightweight model for best performance
        "messages": messages,
        "temperature": 0.7,
        "stream": False
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            res = await client.post(url, headers=headers, json=payload)
            res.raise_for_status()
            response_data = res.json()
            
            if "choices" in response_data and len(response_data["choices"]) > 0:
                return response_data["choices"][0]["message"]["content"]
            else:
                logger.error(f"Unexpected Groq response format: {response_data}")
                return ""
                
    except httpx.TimeoutException:
        logger.error("Groq API request timed out")
        return ""
    except httpx.HTTPStatusError as e:
        logger.error(f"Groq API HTTP error: {e.response.status_code} - {e.response.text}")
        return ""
    except Exception as e:
        logger.error(f"Groq API call failed: {e}")
        return ""

def pdf_to_text(path: Path) -> str:
    try:
        doc = fitz.open(str(path))
        text = "\n\n".join(page.get_text() for page in doc)
        
        # Check if we got meaningful text
        if not text or len(text.strip()) < 10:
            raise ValueError("No selectable text found in PDF - file might be scanned")
        
        return text
    except (fitz.FileDataError, fitz.PdfReadError, ValueError) as e:
        logger.error(f"PDF extraction failed: {e}")
        raise RuntimeError("Failed to extract text from PDF - the file might be scanned or corrupted")
    except Exception as e:
        logger.error(f"PDF extraction failed: {e}")
        raise RuntimeError("Failed to extract text from PDF.")

def chunk_text(text: str) -> List[str]:
    words = text.split()
    chunks, cur = [], []
    for i, w in enumerate(words):
        cur.append(w)
        if len(cur) >= CHUNK_WORDS:
            chunks.append(" ".join(cur))
            cur = cur[-OVERLAP:]  # overlap
    if cur:
        chunks.append(" ".join(cur))
    return chunks

async def embed_chunks(chunks: List[str]) -> List[List[float]]:
    """
    Generate embeddings for text chunks using Cohere API.
    Creates semantic vector representations for similarity search and content understanding.
    """
    try:
        # Use Cohere API for embeddings
        embeddings = await cohere_embed(chunks)
        logger.info(f"Successfully generated {len(embeddings)} embeddings using Cohere")
        return embeddings
        
    except Exception as e:
        logger.error(f"Cohere embedding generation failed: {e}")
        # Return fallback embeddings
        return [_generate_fallback_embedding(chunk) for chunk in chunks]

def _generate_fallback_embedding(text: str) -> List[float]:
    """
    Generate a fallback embedding based on text characteristics.
    Uses simple heuristics to create meaningful vector representations.
    """
    embedding = [0.0] * 384
    
    # Basic text analysis
    words = text.lower().split()
    char_count = len(text)
    word_count = len(words)
    
    # Technical indicators
    technical_terms = ['api', 'database', 'algorithm', 'function', 'class', 'method', 'variable', 'loop', 'condition', 'error']
    framework_terms = ['react', 'python', 'javascript', 'docker', 'kubernetes', 'aws', 'azure', 'node', 'express', 'fastapi']
    learning_terms = ['learn', 'understand', 'practice', 'example', 'tutorial', 'guide', 'step', 'process', 'method']
    
    # Calculate technical density
    technical_score = sum(1 for word in words if word in technical_terms) / max(word_count, 1)
    framework_score = sum(1 for word in words if word in framework_terms) / max(word_count, 1)
    learning_score = sum(1 for word in words if word in learning_terms) / max(word_count, 1)
    
    # Set embedding values based on characteristics
    embedding[0] = min(technical_score, 1.0)  # Technical complexity
    embedding[1] = min(framework_score, 1.0)  # Framework usage
    embedding[2] = min(learning_score, 1.0)   # Learning focus
    embedding[3] = min(char_count / 1000, 1.0)  # Content length
    embedding[4] = min(word_count / 100, 1.0)   # Word density
    
    # Add some randomness for uniqueness
    import random
    random.seed(hash(text) % 10000)
    for i in range(5, 384):
        embedding[i] = random.uniform(-0.1, 0.1)
    
    return embedding

def _normalize_embedding(embedding: List[float]) -> List[float]:
    """
    Normalize embedding values to [-1, 1] range.
    """
    if not embedding:
        return [0.0] * 384
    
    # Clip values to [-1, 1]
    normalized = [max(-1.0, min(1.0, float(val))) for val in embedding]
    
    # Ensure we have exactly 384 values
    while len(normalized) < 384:
        normalized.append(0.0)
    
    return normalized[:384]

def calculate_embedding_similarity(embedding1: List[float], embedding2: List[float]) -> float:
    """
    Calculate cosine similarity between two embeddings.
    Returns a value between -1 and 1, where 1 means identical.
    """
    if not embedding1 or not embedding2:
        return 0.0
    
    # Ensure both embeddings have the same length
    min_length = min(len(embedding1), len(embedding2))
    if min_length == 0:
        return 0.0
    
    # Calculate dot product and magnitudes
    dot_product = sum(embedding1[i] * embedding2[i] for i in range(min_length))
    magnitude1 = sum(val ** 2 for val in embedding1[:min_length]) ** 0.5
    magnitude2 = sum(val ** 2 for val in embedding2[:min_length]) ** 0.5
    
    # Avoid division by zero
    if magnitude1 == 0 or magnitude2 == 0:
        return 0.0
    
    # Calculate cosine similarity
    similarity = dot_product / (magnitude1 * magnitude2)
    
    # Ensure result is in [-1, 1] range
    return max(-1.0, min(1.0, similarity))

def find_similar_content(query_embedding: List[float], content_embeddings: List[List[float]], top_k: int = 5) -> List[tuple]:
    """
    Find the most similar content based on embedding similarity.
    Returns list of (index, similarity_score) tuples sorted by similarity.
    """
    similarities = []
    
    for i, content_embedding in enumerate(content_embeddings):
        similarity = calculate_embedding_similarity(query_embedding, content_embedding)
        similarities.append((i, similarity))
    
    # Sort by similarity (descending) and return top_k results
    similarities.sort(key=lambda x: x[1], reverse=True)
    return similarities[:top_k]

async def generate_content_embedding(text: str) -> List[float]:
    """
    Generate a single embedding for a piece of content using Cohere API.
    Useful for querying and similarity search.
    """
    try:
        # Use Cohere API for single text embedding
        embeddings = await cohere_embed([text])
        if embeddings and len(embeddings) > 0:
            return embeddings[0]
        else:
            return _generate_fallback_embedding(text)
            
    except Exception as e:
        logger.error(f"Failed to generate content embedding: {e}")
        return _generate_fallback_embedding(text)

def get_explanation_prompt(level: ExplanationLevel) -> str:
    """Get the appropriate prompt based on explanation level."""
    prompts = {
        ExplanationLevel.FIVE_YEAR_OLD: "Explain this like you're talking to a 5-year-old. Use simple words, analogies, and avoid technical jargon.",
        ExplanationLevel.INTERN: "Explain this for someone who is learning and has basic knowledge. Use clear examples and step-by-step explanations.",
        ExplanationLevel.SENIOR: "Explain this for an experienced professional. You can use technical terms and assume advanced knowledge."
    }
    return prompts.get(level, prompts[ExplanationLevel.INTERN])

async def detect_framework(text: str) -> Framework:
    """Enhanced framework detection with confidence scoring"""
    try:
        prompt = f"""
        Analyze this text and identify the primary framework, tool, or technology being discussed.
        
        Text: {text[:2000]}
        
        Return a JSON object with this structure:
        {{
            "primary_framework": "FASTAPI|REACT|PYTHON|NODEJS|DOCKER|LANGCHAIN|ML_AI|GENERIC",
            "confidence": 0.85,
            "detected_frameworks": [
                {{
                    "name": "FASTAPI",
                    "confidence": 0.9,
                    "mentions": 5
                }},
                {{
                    "name": "PYTHON", 
                    "confidence": 0.7,
                    "mentions": 3
                }}
            ],
            "reasoning": "Brief explanation of why this framework was chosen"
        }}
        
        If multiple frameworks are mentioned, choose the most prominent one as primary.
        If no specific framework is clear, return GENERIC.
        """
        messages = [{"role": "user", "content": prompt}]
        result = await call_groq(messages)
        
        try:
            framework_data = json.loads(result)
            primary = framework_data.get("primary_framework", "GENERIC")
            return Framework(primary) if primary in [f.value for f in Framework] else Framework.GENERIC
        except json.JSONDecodeError:
            # Fallback to simple detection
            result = result.strip().lower()
            return Framework(result) if result in [f.value for f in Framework] else Framework.GENERIC
            
    except Exception as e:
        logger.error(f"Framework detection failed: {e}")
        return Framework.GENERIC

async def detect_multiple_frameworks(text: str) -> Dict:
    """Detect multiple frameworks with confidence scores"""
    try:
        prompt = f"""
        Analyze this text and identify ALL frameworks, tools, or technologies mentioned.
        
        Text: {text[:2000]}
        
        Return a JSON object with this structure:
        {{
            "frameworks": [
                {{
                    "name": "FASTAPI",
                    "confidence": 0.9,
                    "mentions": 5,
                    "context": "API development framework"
                }},
                {{
                    "name": "PYTHON",
                    "confidence": 0.7,
                    "mentions": 3,
                    "context": "Programming language"
                }}
            ],
            "primary_framework": "FASTAPI",
            "total_frameworks": 2
        }}
        """
        messages = [{"role": "user", "content": prompt}]
        result = await call_groq(messages)
        
        try:
            return json.loads(result)
        except json.JSONDecodeError:
            return {"frameworks": [], "primary_framework": "GENERIC", "total_frameworks": 0}
            
    except Exception as e:
        logger.error(f"Multiple framework detection failed: {e}")
        return {"frameworks": [], "primary_framework": "GENERIC", "total_frameworks": 0}

async def map_reduce_summary(chunks: List[str], explanation_level: ExplanationLevel = ExplanationLevel.INTERN) -> str:
    explanation_prompt = get_explanation_prompt(explanation_level)
    
    async def summarize_chunk(chunk):
        try:
            messages = [
                {"role": "system", "content": f"Summarize the text into 3 concise bullets. {explanation_prompt}"},
                {"role": "user", "content": chunk},
            ]
            return await call_groq(messages)
        except Exception as e:
            logger.error(f"LLM summarize_chunk failed: {e}")
            raise RuntimeError("LLM summarization failed.")
    
    try:
        mapped = await asyncio.gather(*[summarize_chunk(ch) for ch in chunks])
        reduce_prompt = (
            f"You are creating a training cheat-sheet. {explanation_prompt} "
            "Merge these bullet groups into **max 10 key bullets**:\n"
            + "\n".join(mapped)
        )
        messages = [{"role": "user", "content": reduce_prompt}]
        return await call_groq(messages)
    except Exception as e:
        logger.error(f"LLM map_reduce_summary failed: {e}")
        # Return a simple summary instead of failing
        return "• " + " • ".join([chunk[:100] + "..." for chunk in chunks[:5]])

async def gen_flashcards_quiz(summary: str, explanation_level: ExplanationLevel = ExplanationLevel.INTERN) -> Dict[str, list]:
    explanation_prompt = get_explanation_prompt(explanation_level)
    prompt = (
        f"Given the following summary, create {explanation_prompt}:\n"
        "1. 5 flashcards as JSON list of { \"front\": str, \"back\": str }\n"
        "2. 5 multiple-choice questions as JSON list of {\n"
        "   \"question\": str, \"options\": [a,b,c,d], \"answer\": \"a\"\n"
        "}\n"
        "Return valid JSON with keys 'flashcards' and 'quiz'.\n"
        "Summary:\n"
        f"{summary}"
    )
    try:
        messages = [{"role": "user", "content": prompt}]
        response = await call_groq(messages)
        
        # Try to extract JSON from response
        try:
            # Look for JSON in the response
            start_idx = response.find('{')
            end_idx = response.rfind('}') + 1
            if start_idx != -1 and end_idx != 0:
                json_str = response[start_idx:end_idx]
                data = json.loads(json_str)
                return data
            else:
                # If no JSON found, return fallback
                return _get_fallback_flashcards_quiz(summary)
        except json.JSONDecodeError:
            # Fallback to structured response
            return _get_fallback_flashcards_quiz(summary)
            
    except Exception as e:
        logger.error(f"LLM flashcards/quiz failed: {e}")
        return _get_fallback_flashcards_quiz(summary)

def _get_fallback_flashcards_quiz(summary: str) -> Dict[str, list]:
    """Generate fallback flashcards and quiz when LLM fails"""
    # Extract key concepts from summary
    words = summary.split()
    key_concepts = [word for word in words if len(word) > 5][:5]
    
    flashcards = []
    for i, concept in enumerate(key_concepts):
        flashcards.append({
            "front": f"What is {concept}?",
            "back": f"{concept} is a key concept from the document."
        })
    
    quiz = []
    for i, concept in enumerate(key_concepts):
        quiz.append({
            "question": f"Which of the following relates to {concept}?",
            "options": [f"Option {j+1}" for j in range(4)],
            "answer": "a"
        })
    
    return {
        "flashcards": flashcards,
        "quiz": quiz
    }

async def generate_concept_map(summary: str) -> Dict:
    """Generate a concept map showing relationships between key concepts."""
    try:
        prompt = f"""
Create a concept map from this summary. Return as JSON with this structure:
{{
  "nodes": [
    {{"id": "concept1", "label": "Concept Name", "level": 1}},
    {{"id": "concept2", "label": "Related Concept", "level": 2}}
  ],
  "edges": [
    {{"from": "concept1", "to": "concept2", "label": "relationship"}}
  ]
}}

Summary: {summary}
"""
        messages = [{"role": "user", "content": prompt}]
        response = await call_groq(messages)
        
        # Try to extract JSON from response
        try:
            # Look for JSON in the response
            start_idx = response.find('{')
            end_idx = response.rfind('}') + 1
            if start_idx != -1 and end_idx != 0:
                json_str = response[start_idx:end_idx]
                data = json.loads(json_str)
                return data
            else:
                # If no JSON found, return fallback
                return _get_fallback_concept_map(summary)
        except json.JSONDecodeError:
            # Fallback to structured response
            return _get_fallback_concept_map(summary)
            
    except Exception as e:
        logger.error(f"Concept map generation failed: {e}")
        return _get_fallback_concept_map(summary)

def _get_fallback_concept_map(summary: str) -> Dict:
    """Generate fallback concept map when LLM fails"""
    # Extract key concepts from summary
    words = summary.split()
    key_concepts = [word for word in words if len(word) > 5][:3]
    
    nodes = []
    edges = []
    
    for i, concept in enumerate(key_concepts):
        nodes.append({
            "id": f"concept{i+1}",
            "label": concept,
            "level": 1
        })
        
        if i > 0:
            edges.append({
                "from": f"concept{i}",
                "to": f"concept{i+1}",
                "label": "related to"
            })
    
    return {
        "nodes": nodes,
        "edges": edges
    }



# Chatbot functions
def get_or_create_conversation(conversation_id: Optional[str], user_id: str) -> str:
    """Get existing conversation or create new one with enhanced metadata."""
    if conversation_id and conversation_id in conversation_store:
        return conversation_id
    
    new_conversation_id = str(uuid.uuid4())
    conversation_store[new_conversation_id] = {
        "user_id": user_id,
        "messages": [],
        "file_context": None,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
        "metadata": {
            "recent_pdfs": [],
            "framework_preferences": [],
            "explanation_level": "INTERN",
            "user_skills": [],
            "interaction_history": []
        }
    }
    return new_conversation_id

def update_user_preferences(user_id: str, preferences: Dict):
    """Update user preferences for personalized experience."""
    if user_id not in conversation_metadata["user_preferences"]:
        conversation_metadata["user_preferences"][user_id] = {}
    
    conversation_metadata["user_preferences"][user_id].update(preferences)

def get_user_preferences(user_id: str) -> Dict:
    """Get user preferences for personalized experience."""
    return conversation_metadata["user_preferences"].get(user_id, {})

def store_recent_pdf(user_id: str, pdf_name: str, framework: str, summary: str):
    """Store recent PDF information for quick access."""
    if user_id not in conversation_metadata["recent_pdfs"]:
        conversation_metadata["recent_pdfs"][user_id] = []
    
    pdf_info = {
        "name": pdf_name,
        "framework": framework,
        "summary": summary,
        "uploaded_at": datetime.utcnow().isoformat()
    }
    
    # Keep only last 5 PDFs
    recent_pdfs = conversation_metadata["recent_pdfs"][user_id]
    recent_pdfs.append(pdf_info)
    if len(recent_pdfs) > 5:
        recent_pdfs.pop(0)
    
    conversation_metadata["recent_pdfs"][user_id] = recent_pdfs

def get_recent_pdfs(user_id: str) -> List[Dict]:
    """Get recent PDFs for user."""
    return conversation_metadata["recent_pdfs"].get(user_id, [])

def add_message_to_conversation(conversation_id: str, role: str, content: str):
    """Add a message to the conversation history."""
    if conversation_id not in conversation_store:
        return
    
    message = {
        "role": role,
        "content": content,
        "timestamp": datetime.utcnow().isoformat()
    }
    conversation_store[conversation_id]["messages"].append(message)
    conversation_store[conversation_id]["updated_at"] = datetime.utcnow().isoformat()

async def process_chat_message(user_id: str, message: str, conversation_id: Optional[str], explanation_level: ExplanationLevel) -> Dict:
    """Process a chat message and generate a response with enhanced learning content options."""
    try:
        conv_id = get_or_create_conversation(conversation_id, user_id)
        add_message_to_conversation(conv_id, "user", message)
        
        # Get conversation context
        conversation = conversation_store[conv_id]
        messages = conversation["messages"]
        file_context = conversation.get("file_context")
        
        # Check for special commands
        message_lower = message.lower().strip()
        
        # Enhanced command detection
        if any(cmd in message_lower for cmd in ["create lesson", "generate lesson", "make lesson", "lesson about", "create microlearning"]):
            return await _handle_lesson_generation(message, conv_id, file_context, explanation_level)
        
        elif any(cmd in message_lower for cmd in ["create quiz", "generate quiz", "make quiz", "quiz about"]):
            return await _handle_quiz_generation(message, conv_id, file_context, explanation_level)
        
        elif any(cmd in message_lower for cmd in ["create flashcards", "generate flashcards", "make flashcards", "flashcards about"]):
            return await _handle_flashcard_generation(message, conv_id, file_context, explanation_level)
        
        elif any(cmd in message_lower for cmd in ["create workflow", "generate workflow", "make diagram", "create chart", "workflow about"]):
            return await _handle_workflow_generation(message, conv_id, file_context, explanation_level)
        
        elif any(cmd in message_lower for cmd in ["create summary", "generate summary", "make summary", "summarize", "bullet points"]):
            return await _handle_summary_generation(message, conv_id, file_context, explanation_level)
        
        elif any(cmd in message_lower for cmd in ["explain like 5", "explain like 15", "explain like senior", "explain for beginner", "explain for expert"]):
            return await _handle_explanation_level_change(message, conv_id, file_context, explanation_level)
        
        elif any(cmd in message_lower for cmd in ["help", "commands", "what can you do", "options"]):
            return await _handle_help_command(conv_id, file_context)
        
        # Regular chat message
        else:
            return await _handle_regular_chat(message, conv_id, file_context, explanation_level)
        
    except Exception as e:
        logger.error(f"Chat message processing failed: {e}")
        raise RuntimeError("Failed to process chat message.")

async def _handle_lesson_generation(message: str, conv_id: str, file_context: Optional[str], explanation_level: ExplanationLevel) -> Dict:
    """Enhanced lesson generation with microlearning focus."""
    try:
        # Extract topic from message
        topic = _extract_topic_from_message(message, ["lesson about", "create lesson", "generate lesson", "make lesson", "create microlearning"])
        
        # Get conversation metadata for context
        conversation = conversation_store.get(conv_id, {})
        metadata = conversation.get("metadata", {})
        current_pdf = metadata.get("current_pdf", {})
        framework = current_pdf.get("framework", "GENERIC")
        
        prompt = f"""
        Create a comprehensive microlearning lesson about: {topic}
        
        {f"Use this context if relevant: {file_context}" if file_context else ""}
        
        Framework Context: {framework}
        Explanation Level: {explanation_level.value}
        
        {get_explanation_prompt(explanation_level)}
        
        Create an engaging, interactive microlearning lesson that follows these principles:
        - Keep sections short and focused (5-10 minutes each)
        - Include practical examples and real-world applications
        - Add interactive elements and exercises
        - Use clear, step-by-step instructions
        - Include visual elements descriptions where helpful
        
        Return the lesson as JSON with this structure:
        {{
            "title": "Lesson Title",
            "overview": "Brief overview",
            "learning_objectives": ["Objective 1", "Objective 2", "Objective 3"],
            "estimated_duration": "30-45 minutes",
            "difficulty_level": "beginner|intermediate|advanced",
            "sections": [
                {{
                    "title": "Section Title",
                    "content": "Detailed content with examples",
                    "duration": "5-10 minutes",
                    "examples": ["Example 1", "Example 2"],
                    "key_points": ["Point 1", "Point 2"],
                    "interactive_elements": ["Exercise 1", "Quiz question"]
                }}
            ],
            "exercises": [
                {{
                    "type": "practice|quiz|project",
                    "title": "Exercise Title",
                    "description": "Exercise description",
                    "instructions": "Step-by-step instructions",
                    "expected_outcome": "What the user should achieve"
                }}
            ],
            "summary": "Key takeaways and next steps",
            "additional_resources": ["Resource 1", "Resource 2"],
            "framework_specific": {framework != "GENERIC"}
        }}
        """
        
        messages = [{"role": "user", "content": prompt}]
        response = await call_groq(messages)
        lesson_data = json.loads(response)
        
        # Create engaging response
        response_text = f"""🎓 **Lesson Created Successfully!**

**{lesson_data['title']}**
{lesson_data['overview']}

📚 **What you'll learn:**
{chr(10).join(f"• {obj}" for obj in lesson_data.get('learning_objectives', []))}

⏱️ **Duration:** {lesson_data.get('estimated_duration', '30-45 minutes')}
🎯 **Level:** {lesson_data.get('difficulty_level', 'intermediate')}

Ready to start learning! The lesson is structured for easy understanding and includes interactive exercises."""
        
        add_message_to_conversation(conv_id, "assistant", response_text)
        
        return {
            "response": response_text,
            "conversation_id": conv_id,
            "message_id": str(uuid.uuid4()),
            "timestamp": datetime.utcnow().isoformat(),
            "lesson_data": lesson_data,
            "type": "lesson",
            "framework": framework
        }
        
    except Exception as e:
        logger.error(f"Lesson generation failed: {e}")
        return await _handle_regular_chat(message, conv_id, file_context, explanation_level)

async def _handle_quiz_generation(message: str, conv_id: str, file_context: Optional[str], explanation_level: ExplanationLevel) -> Dict:
    """Handle quiz generation command."""
    try:
        topic = _extract_topic_from_message(message, ["quiz about", "create quiz", "generate quiz", "make quiz"])
        
        prompt = f"""
        Create a quiz about: {topic}
        
        {f"Use this context if relevant: {file_context}" if file_context else ""}
        
        {get_explanation_prompt(explanation_level)}
        
        Return the quiz as JSON with this structure:
        {{
            "title": "Quiz Title",
            "description": "Quiz description",
            "questions": [
                {{
                    "question": "Question text",
                    "options": ["A", "B", "C", "D"],
                    "correct_answer": "A",
                    "explanation": "Why this is correct"
                }}
            ],
            "total_questions": 5,
            "estimated_time": "10-15 minutes"
        }}
        """
        
        messages = [{"role": "user", "content": prompt}]
        response = await call_groq(messages)
        quiz_data = json.loads(response)
        response = f"I've created a quiz about {topic} for you! Here's what I've prepared:\n\n**{quiz_data['title']}**\n{quiz_data['description']}"
        
        add_message_to_conversation(conv_id, "assistant", response)
        
        return {
            "response": response,
            "conversation_id": conv_id,
            "message_id": str(uuid.uuid4()),
            "timestamp": datetime.utcnow().isoformat(),
            "quiz_data": quiz_data,
            "type": "quiz"
        }
        
    except Exception as e:
        logger.error(f"Quiz generation failed: {e}")
        return await _handle_regular_chat(message, conv_id, file_context, explanation_level)

async def _handle_flashcard_generation(message: str, conv_id: str, file_context: Optional[str], explanation_level: ExplanationLevel) -> Dict:
    """Handle flashcard generation command."""
    try:
        topic = _extract_topic_from_message(message, ["flashcards about", "create flashcards", "generate flashcards", "make flashcards"])
        
        prompt = f"""
        Create flashcards about: {topic}
        
        {f"Use this context if relevant: {file_context}" if file_context else ""}
        
        {get_explanation_prompt(explanation_level)}
        
        Return the flashcards as JSON with this structure:
        {{
            "title": "Flashcard Set Title",
            "description": "Description of the flashcard set",
            "cards": [
                {{
                    "front": "Question or term",
                    "back": "Answer or definition",
                    "category": "Category (optional)"
                }}
            ],
            "total_cards": 10,
            "estimated_study_time": "15-20 minutes"
        }}
        """
        
        messages = [{"role": "user", "content": prompt}]
        response = await call_groq(messages)
        flashcard_data = json.loads(response)
        response = f"I've created flashcards about {topic} for you! Here's what I've prepared:\n\n**{flashcard_data['title']}**\n{flashcard_data['description']}"
        
        add_message_to_conversation(conv_id, "assistant", response)
        
        return {
            "response": response,
            "conversation_id": conv_id,
            "message_id": str(uuid.uuid4()),
            "timestamp": datetime.utcnow().isoformat(),
            "flashcard_data": flashcard_data,
            "type": "flashcards"
        }
        
    except Exception as e:
        logger.error(f"Flashcard generation failed: {e}")
        return await _handle_regular_chat(message, conv_id, file_context, explanation_level)

async def _handle_help_command(conv_id: str, file_context: Optional[str] = None) -> Dict:
    """Handle help command with enhanced options."""
    
    # Check if file has been uploaded
    if file_context:
        help_text = """🎉 **Great! I've processed your uploaded document.** 

Here are the interactive options I can create for you:

**📋 Content Generation Options:**
🔹 **"Create summary"** - Generate bullet-point summary of your document
🔹 **"Create lesson"** - Generate comprehensive microlearning lesson
🔹 **"Generate quiz"** - Create interactive quiz from your content
🔹 **"Make flashcards"** - Create study flashcards
🔹 **"Create workflow"** - Generate workflow/diagram from your content

**🎯 Explanation Levels:**
🔹 **"Explain like 5"** - Simple, beginner-friendly explanations
🔹 **"Explain like 15"** - Intermediate level explanations  
🔹 **"Explain like senior"** - Advanced, expert-level explanations

**💬 General Learning:**
🔹 Ask me questions about your document
🔹 Get clarification on any concepts
🔹 Request specific examples or use cases

**📖 Example Commands:**
- "Create summary" - Get key points from your document
- "Generate quiz about [topic]" - Quiz on specific topic
- "Make flashcards about [concept]" - Flashcards for study
- "Create workflow for [process]" - Visual workflow diagram
- "Explain like 5: [concept]" - Simple explanation

Just tell me what you'd like to create!"""
    else:
        help_text = """🤖 **I'm TrainPI, your AI learning assistant!**

Here's what I can help you with:

**📚 Learning Content Generation:**
🔹 **"Create lesson about [topic]"** - Generate comprehensive microlearning lessons
🔹 **"Generate quiz about [topic]"** - Create interactive quizzes
🔹 **"Make flashcards about [topic]"** - Create study flashcards
🔹 **"Create workflow about [topic]"** - Generate workflow/diagram
🔹 **"Create summary about [topic]"** - Generate bullet-point summaries

**🎯 Explanation Levels:**
🔹 **"Explain like 5"** - Simple, beginner-friendly explanations
🔹 **"Explain like 15"** - Intermediate level explanations  
🔹 **"Explain like senior"** - Advanced, expert-level explanations

**📖 PDF Processing:**
🔹 Upload PDFs to get context-aware learning materials
🔹 I'll analyze your document and create personalized content

**💬 General Learning Support:**
🔹 Ask me questions about any topic
🔹 Get step-by-step explanations
🔹 Request examples and use cases

**📋 Example Commands:**
- "Create lesson about Python functions"
- "Generate quiz about React hooks"
- "Make flashcards about SQL basics"
- "Create workflow for user authentication"
- "Explain like 5: machine learning"

**📎 Upload a PDF first to get the most out of my features!**

Just ask me anything or use the commands above to get started!"""
    
    add_message_to_conversation(conv_id, "assistant", help_text)
    
    return {
        "response": help_text,
        "conversation_id": conv_id,
        "message_id": str(uuid.uuid4()),
        "timestamp": datetime.utcnow().isoformat(),
        "type": "help",
        "has_file_context": file_context is not None
    }

async def _handle_regular_chat(message: str, conv_id: str, file_context: Optional[str], explanation_level: ExplanationLevel) -> Dict:
    """Handle regular chat messages."""
    # Build system prompt
    system_prompt = f"""You are TrainPI, an AI learning assistant. {get_explanation_prompt(explanation_level)}

Your role is to help users learn and understand concepts. Be helpful, encouraging, and educational.

If a file has been uploaded, you can reference its content to provide more specific answers.

You can also generate lessons, quizzes, and flashcards when asked."""
    
    # Build messages for LLM
    llm_messages = [{"role": "system", "content": system_prompt}]
    
    # Add file context if available
    if file_context:
        llm_messages.append({
            "role": "system", 
            "content": f"File context: {file_context}\n\nUse this information to provide more specific and relevant answers."
        })
    
    # Add conversation history (last 10 messages to avoid token limits)
    conversation = conversation_store[conv_id]
    messages = conversation["messages"]
    for msg in messages[-10:]:
        llm_messages.append({"role": msg["role"], "content": msg["content"]})
    
    # Generate response
    response = await call_groq(llm_messages)
    add_message_to_conversation(conv_id, "assistant", response)
    
    return {
        "response": response,
        "conversation_id": conv_id,
        "message_id": str(uuid.uuid4()),
        "timestamp": datetime.utcnow().isoformat(),
        "type": "chat"
    }

async def _handle_workflow_generation(message: str, conv_id: str, file_context: Optional[str], explanation_level: ExplanationLevel) -> Dict:
    """Handle workflow/diagram generation command."""
    try:
        topic = _extract_topic_from_message(message, ["workflow about", "create workflow", "generate workflow", "make diagram", "create chart"])
        
        prompt = f"""
        Create a comprehensive workflow/diagram for: {topic}
        
        {f"Use this context if relevant: {file_context}" if file_context else ""}
        
        Explanation Level: {explanation_level.value}
        
        {get_explanation_prompt(explanation_level)}
        
        Create an engaging, visual workflow that includes:
        - Clear process steps
        - Decision points where applicable
        - Visual elements and icons
        - Time estimates for each step
        - Best practices and tips
        
        Return the workflow as JSON with this structure:
        {{
            "title": "Workflow Title",
            "description": "Comprehensive workflow description",
            "type": "flowchart|process|decision_tree|timeline|sequence",
            "mermaid_code": "graph TD\\n    A[Start] --> B[Process]\\n    B --> C[End]",
            "nodes": [
                {{
                    "id": "node1",
                    "label": "Start",
                    "type": "start",
                    "description": "Initial step description",
                    "duration": "5 minutes",
                    "tips": ["Tip 1", "Tip 2"]
                }},
                {{
                    "id": "node2",
                    "label": "Process Step",
                    "type": "process",
                    "description": "Process step description",
                    "duration": "10 minutes",
                    "tips": ["Best practice 1", "Best practice 2"]
                }}
            ],
            "edges": [
                {{
                    "from": "node1",
                    "to": "node2",
                    "label": "Next",
                    "condition": "When ready to proceed"
                }}
            ],
            "steps": [
                {{
                    "step": 1,
                    "title": "Step Title",
                    "description": "Detailed step description",
                    "duration": "5 minutes",
                    "best_practices": ["Practice 1", "Practice 2"],
                    "common_mistakes": ["Mistake 1", "Mistake 2"]
                }}
            ],
            "estimated_duration": "30-45 minutes",
            "difficulty_level": "beginner|intermediate|advanced",
            "prerequisites": ["Prerequisite 1", "Prerequisite 2"],
            "tools_needed": ["Tool 1", "Tool 2"]
        }}
        """
        
        messages = [{"role": "user", "content": prompt}]
        response = await call_groq(messages)
        workflow_data = json.loads(response)
        response_text = f"I've created a workflow for {topic}! Here's what I've prepared:\n\n**{workflow_data['title']}**\n{workflow_data['description']}"
        
        add_message_to_conversation(conv_id, "assistant", response_text)
        
        return {
            "response": response_text,
            "conversation_id": conv_id,
            "message_id": str(uuid.uuid4()),
            "timestamp": datetime.utcnow().isoformat(),
            "workflow_data": workflow_data,
            "type": "workflow"
        }
        
    except Exception as e:
        logger.error(f"Workflow generation failed: {e}")
        return await _handle_regular_chat(message, conv_id, file_context, explanation_level)

async def _handle_summary_generation(message: str, conv_id: str, file_context: Optional[str], explanation_level: ExplanationLevel) -> Dict:
    """Handle summary/bullet points generation command."""
    try:
        topic = _extract_topic_from_message(message, ["summary about", "create summary", "generate summary", "make summary", "summarize", "bullet points"])
        
        if file_context:
            # Use existing file context for summary
            prompt = f"""
            Create a comprehensive summary with bullet points for the uploaded document.
            
            {get_explanation_prompt(explanation_level)}
            
            Document content: {file_context}
            
            Return the summary as JSON with this structure:
            {{
                "title": "Document Summary",
                "overview": "Brief overview",
                "key_points": [
                    "Key point 1",
                    "Key point 2",
                    "Key point 3"
                ],
                "main_topics": [
                    {{
                        "topic": "Topic Name",
                        "description": "Topic description",
                        "key_concepts": ["Concept 1", "Concept 2"]
                    }}
                ],
                "action_items": [
                    "Action item 1",
                    "Action item 2"
                ],
                "estimated_reading_time": "10-15 minutes"
            }}
            """
        else:
            # Generate summary for a specific topic
            prompt = f"""
            Create a comprehensive summary with bullet points for: {topic}
            
            {get_explanation_prompt(explanation_level)}
            
            Return the summary as JSON with this structure:
            {{
                "title": "Summary: {topic}",
                "overview": "Brief overview",
                "key_points": [
                    "Key point 1",
                    "Key point 2",
                    "Key point 3"
                ],
                "main_topics": [
                    {{
                        "topic": "Topic Name",
                        "description": "Topic description",
                        "key_concepts": ["Concept 1", "Concept 2"]
                    }}
                ],
                "action_items": [
                    "Action item 1",
                    "Action item 2"
                ],
                "estimated_reading_time": "10-15 minutes"
            }}
            """
        
        messages = [{"role": "user", "content": prompt}]
        response = await call_groq(messages)
        summary_data = json.loads(response)
        response_text = f"I've created a summary for {topic}! Here's what I've prepared:\n\n**{summary_data['title']}**\n{summary_data['overview']}"
        
        add_message_to_conversation(conv_id, "assistant", response_text)
        
        return {
            "response": response_text,
            "conversation_id": conv_id,
            "message_id": str(uuid.uuid4()),
            "timestamp": datetime.utcnow().isoformat(),
            "summary_data": summary_data,
            "type": "summary"
        }
        
    except Exception as e:
        logger.error(f"Summary generation failed: {e}")
        return await _handle_regular_chat(message, conv_id, file_context, explanation_level)

async def _handle_explanation_level_change(message: str, conv_id: str, file_context: Optional[str], explanation_level: ExplanationLevel) -> Dict:
    """Handle explanation level change command."""
    try:
        message_lower = message.lower()
        
        # Determine new explanation level
        if any(level in message_lower for level in ["explain like 5", "explain for beginner", "simple", "basic"]):
            new_level = ExplanationLevel.BEGINNER
            level_name = "Beginner (Age 5)"
        elif any(level in message_lower for level in ["explain like 15", "explain for intermediate", "moderate"]):
            new_level = ExplanationLevel.INTERN
            level_name = "Intermediate (Age 15)"
        elif any(level in message_lower for level in ["explain like senior", "explain for expert", "advanced", "detailed"]):
            new_level = ExplanationLevel.SENIOR
            level_name = "Senior/Expert"
        else:
            new_level = explanation_level
            level_name = "Current level"
        
        # Generate explanation with new level
        topic = _extract_topic_from_message(message, ["explain like 5", "explain like 15", "explain like senior", "explain for beginner", "explain for expert"])
        
        prompt = f"""
        Explain {topic} at a {level_name} level.
        
        {f"Use this context if relevant: {file_context}" if file_context else ""}
        
        {get_explanation_prompt(new_level)}
        
        Make sure the explanation is appropriate for the specified level.
        """
        
        messages = [{"role": "user", "content": prompt}]
        response = await call_groq(messages)
        
        response_text = f"I've explained {topic} at a {level_name} level:\n\n{response}"
        add_message_to_conversation(conv_id, "assistant", response_text)
        
        return {
            "response": response_text,
            "conversation_id": conv_id,
            "message_id": str(uuid.uuid4()),
            "timestamp": datetime.utcnow().isoformat(),
            "explanation_level": new_level.value,
            "type": "explanation"
        }
        
    except Exception as e:
        logger.error(f"Explanation level change failed: {e}")
        return await _handle_regular_chat(message, conv_id, file_context, explanation_level)

def _extract_topic_from_message(message: str, commands: List[str]) -> str:
    """Extract topic from message after removing command words."""
    message_lower = message.lower()
    
    for cmd in commands:
        if cmd in message_lower:
            # Remove the command and clean up
            topic = message_lower.replace(cmd, "").strip()
            # Capitalize first letter of each word
            topic = " ".join(word.capitalize() for word in topic.split())
            return topic
    
    # Fallback: return the message itself
    return message.strip()

async def process_file_for_chat(file_path: Path, user_id: str, conversation_id: Optional[str], explanation_level: ExplanationLevel) -> Dict:
    """Enhanced PDF processing with dynamic action buttons and framework detection."""
    try:
        # Extract text from file
        text = pdf_to_text(file_path)
        chunks = chunk_text(text)
        
        # Generate summary for context
        summary = await map_reduce_summary(chunks, explanation_level)
        
        # Detect frameworks with enhanced detection
        framework_detection = await detect_multiple_frameworks(text)
        primary_framework = framework_detection.get("primary_framework", "GENERIC")
        
        # Get or create conversation
        conv_id = get_or_create_conversation(conversation_id, user_id)
        
        # Store PDF information
        pdf_name = file_path.name
        store_recent_pdf(user_id, pdf_name, primary_framework, summary)
        
        # Add file context to conversation
        conversation_store[conv_id]["file_context"] = summary
        conversation_store[conv_id]["updated_at"] = datetime.utcnow().isoformat()
        
        # Update conversation metadata
        if "metadata" not in conversation_store[conv_id]:
            conversation_store[conv_id]["metadata"] = {}
        
        conversation_store[conv_id]["metadata"].update({
            "current_pdf": {
                "name": pdf_name,
                "framework": primary_framework,
                "detected_frameworks": framework_detection.get("frameworks", []),
                "uploaded_at": datetime.utcnow().isoformat()
            },
            "explanation_level": explanation_level.value
        })
        
        # Generate personalized response based on framework and content
        system_prompt = f"""You are TrainPI, an AI learning assistant. {get_explanation_prompt(explanation_level)}

A file has been uploaded and processed. Here's what I found:

**Document:** {pdf_name}
**Primary Framework:** {primary_framework}
**Summary:** {summary}

Provide a helpful, encouraging response about what you found in the file and suggest specific learning actions. Be enthusiastic and make the user excited about learning!"""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "I've uploaded a file. What can you tell me about it and what interactive learning options can you create for me?"}
        ]
        response = await call_groq(messages)
        
        # Create dynamic action buttons based on content
        action_buttons = [
            {"id": "summary", "label": "📋 Generate Summary", "description": "Get key bullet points"},
            {"id": "lesson", "label": "📚 Create Lesson", "description": "Generate comprehensive microlearning lesson"},
            {"id": "quiz", "label": "🧠 Generate Quiz", "description": "Create interactive quiz"},
            {"id": "flashcards", "label": "🗂️ Make Flashcards", "description": "Create study flashcards"},
            {"id": "workflow", "label": "🔄 Create Workflow", "description": "Generate visual workflow/diagram"}
        ]
        
        # Add framework-specific actions if detected
        if primary_framework != "GENERIC":
            action_buttons.append({
                "id": "framework_specific", 
                "label": f"🎯 {primary_framework} Focus", 
                "description": f"Create {primary_framework}-specific content"
            })
        
        # Create interactive response
        interactive_response = f"""{response}

🎯 **Interactive Learning Options Available:**

I can create these learning materials from your document:
• 📋 **"Create summary"** - Get key bullet points
• 📚 **"Create lesson"** - Generate comprehensive microlearning lesson
• 🧠 **"Generate quiz"** - Create interactive quiz
• 🗂️ **"Make flashcards"** - Create study flashcards
• 🔄 **"Create workflow"** - Generate visual workflow/diagram

🎓 **Explanation Levels:**
• **"Explain like 5"** - Simple explanations
• **"Explain like 15"** - Intermediate level
• **"Explain like senior"** - Advanced explanations

Just tell me what you'd like to create!"""
        
        add_message_to_conversation(conv_id, "assistant", interactive_response)
        
        return {
            "response": interactive_response,
            "conversation_id": conv_id,
            "message_id": str(uuid.uuid4()),
            "timestamp": datetime.utcnow().isoformat(),
            "file_processed": True,
            "summary": summary,
            "framework_detection": framework_detection,
            "action_buttons": action_buttons,
            "interactive_options": True,
            "pdf_name": pdf_name
        }
        
    except Exception as e:
        logger.error(f"File processing for chat failed: {e}")
        raise RuntimeError("Failed to process file for chat.")

def get_conversation_history(conversation_id: str) -> Optional[Dict]:
    """Get conversation history."""
    if conversation_id not in conversation_store:
        return None
    
    conversation = conversation_store[conversation_id]
    return {
        "conversation_id": conversation_id,
        "user_id": conversation["user_id"],
        "messages": conversation["messages"],
        "created_at": conversation["created_at"],
        "updated_at": conversation["updated_at"],
        "has_file_context": conversation.get("file_context") is not None
    }

def get_user_conversations(user_id: str) -> List[Dict]:
    """Get all conversations for a user."""
    user_conversations = []
    for conv_id, conversation in conversation_store.items():
        if conversation["user_id"] == user_id:
            user_conversations.append({
                "conversation_id": conv_id,
                "created_at": conversation["created_at"],
                "updated_at": conversation["updated_at"],
                "message_count": len(conversation["messages"]),
                "has_file_context": conversation.get("file_context") is not None
            })
    return user_conversations

def get_side_menu_data(user_id: str) -> Dict:
    """Get data for the side menu including recent PDFs and user preferences."""
    try:
        # Get recent PDFs
        recent_pdfs = get_recent_pdfs(user_id)
        
        # Get user preferences
        user_prefs = get_user_preferences(user_id)
        
        # Get current conversation metadata
        current_conversation = None
        for conv_id, conv_data in conversation_store.items():
            if conv_data["user_id"] == user_id:
                current_conversation = conv_data.get("metadata", {})
                break
        
        return {
            "recent_pdfs": recent_pdfs,
            "user_preferences": user_prefs,
            "current_conversation": current_conversation,
            "available_frameworks": [
                {"name": "FASTAPI", "icon": "🚀"},
                {"name": "REACT", "icon": "⚛️"},
                {"name": "PYTHON", "icon": "🐍"},
                {"name": "NODEJS", "icon": "🟢"},
                {"name": "DOCKER", "icon": "🐳"},
                {"name": "LANGCHAIN", "icon": "🔗"},
                {"name": "ML_AI", "icon": "🤖"},
                {"name": "GENERIC", "icon": "📚"}
            ],
            "explanation_levels": [
                {"value": "BEGINNER", "label": "5-year-old", "description": "Simple explanations"},
                {"value": "INTERN", "label": "Intern", "description": "Intermediate level"},
                {"value": "SENIOR", "label": "Senior Expert", "description": "Advanced explanations"}
            ]
        }
    except Exception as e:
        logger.error(f"Failed to get side menu data: {e}")
        return {
            "recent_pdfs": [],
            "user_preferences": {},
            "current_conversation": {},
            "available_frameworks": [],
            "explanation_levels": []
        }

def update_explanation_level(user_id: str, level: str):
    """Update user's explanation level preference."""
    update_user_preferences(user_id, {"explanation_level": level})

def update_framework_preference(user_id: str, framework: str):
    """Update user's framework preference."""
    update_user_preferences(user_id, {"preferred_framework": framework})
