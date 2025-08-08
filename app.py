from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
import asyncio, tempfile, os, json
from pathlib import Path
from typing import Optional, Dict, List
from distiller import (
    pdf_to_text, chunk_text, embed_chunks, detect_framework, detect_multiple_frameworks,
    map_reduce_summary, gen_flashcards_quiz, generate_concept_map,
    process_chat_message, process_file_for_chat,
    get_conversation_history, get_user_conversations,
    get_side_menu_data, update_explanation_level, update_framework_preference
)
from supabase_helper import (
    insert_lesson, insert_cards, insert_concept_map, mark_lesson_completed,
    get_user_completed_lessons, upsert_user_role, get_user_role,
    get_lessons_by_framework, get_user_progress_stats,
    get_lesson_summary, get_lesson_cards, get_lesson_concept_map, get_lesson_by_id
)
from schemas import ExplanationLevel, Framework
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="TrainPI API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://v0-frontend-opal-nine.vercel.app",
        "https://v0-frontend-opal-nine.vercel.app/",
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
        "null",  # For local HTML files opened directly in browser
        "*"  # Allow all origins for development/testing
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "TrainPI API is running", "status": "healthy", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "TrainPI API", "timestamp": "2024-08-01"}

@app.get("/api/test")
async def test_endpoint():
    return {"message": "API is working correctly", "endpoint": "test"}

@app.get("/api/frameworks")
async def get_frameworks():
    return {
        "frameworks": [
            "React", "Vue", "Angular", "Node.js", "Python", "Java", "C#", "Go"
        ]
    }

@app.post("/api/distill")
async def distill(owner_id: str, file: UploadFile = File(...)):
    """Enhanced distill endpoint that returns lesson_id and available actions"""
    if not file.filename.endswith(".pdf"):
        raise HTTPException(400, "Only PDF files are supported")
    
    if not file.size or file.size > 50 * 1024 * 1024:  # 50MB limit
        raise HTTPException(413, "File too large. Maximum size is 50MB")
    
    tmp = None
    try:
        # Create temporary file
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        content = await file.read()
        tmp.write(content)
        tmp.close()
        
        # Extract text and process with proper error handling
        try:
            text = pdf_to_text(Path(tmp.name))
            if not text or len(text.strip()) < 10:
                raise HTTPException(422, "Failed to extract text from PDF - the file might be scanned or corrupted")
        except Exception as pdf_error:
            logger.error(f"PDF text extraction failed: {pdf_error}")
            raise HTTPException(422, "Failed to process PDF – maybe it's scanned or has no selectable text?")
        
        chunks = chunk_text(text)
        logger.info(f"{len(chunks)} chunks created")
        
        if not chunks:
            raise HTTPException(422, "No content could be extracted from the PDF")
        
        # Auto-detect framework
        framework_detection = await detect_multiple_frameworks(text)
        primary_framework = framework_detection.get("primary_framework", Framework.GENERIC)
        
        # Generate summary and other content
        summary = await map_reduce_summary(chunks, ExplanationLevel.INTERN)
        embeds = await embed_chunks(chunks)
        qa = await gen_flashcards_quiz(summary, ExplanationLevel.INTERN)
        concept_map = await generate_concept_map(summary)
        
        # Save to Supabase
        lesson_id = insert_lesson(owner_id, file.filename, summary, primary_framework, ExplanationLevel.INTERN)
        
        # Insert concept map
        insert_concept_map(lesson_id, concept_map)
        
        # Insert cards (bullets, flashcards, quiz)
        card_rows = []
        for i, b in enumerate(summary.split("•")):
            if b.strip():
                card_rows.append({
                    "lesson_id": lesson_id,
                    "card_type": "bullet",
                    "payload": {"order": i, "text": b.strip()},
                    "embed_vector": embeds[min(i, len(embeds)-1)] if embeds else [],
                })
        
        for fc in qa["flashcards"]:
            card_rows.append({
                "lesson_id": lesson_id,
                "card_type": "flashcard",
                "payload": fc,
            })
        
        for q in qa["quiz"]:
            card_rows.append({
                "lesson_id": lesson_id,
                "card_type": "quiz",
                "payload": q,
            })
        
        insert_cards(lesson_id, card_rows)
        
        # Get preview bullets (first 3)
        bullets = [b.strip() for b in summary.split("•") if b.strip()]
        preview = bullets[:3] if len(bullets) >= 3 else bullets
        
        return {
            "lesson_id": lesson_id,
            "actions": ["summary", "lesson", "quiz", "flashcards", "workflow"],
            "preview": preview
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Distill processing failed: {e}")
        raise HTTPException(500, f"Failed to process PDF: {str(e)}")
    finally:
        if tmp and os.path.exists(tmp.name):
            try:
                os.unlink(tmp.name)
            except:
                pass

@app.get("/api/lesson/{lesson_id}/{action}")
async def lesson_action(lesson_id: int, action: str):
    """Handle different lesson actions like summary, quiz, etc."""
    try:
        if action == "summary":
            summary = get_lesson_summary(lesson_id)
            if summary:
                # Format summary as bullet points
                bullets = [b.strip() for b in summary.split("•") if b.strip()]
                return {"content": bullets}
            else:
                raise HTTPException(404, f"Summary not found for lesson {lesson_id}")
        
        elif action == "quiz":
            quiz_cards = get_lesson_cards(lesson_id, "quiz")
            if quiz_cards:
                questions = [card["payload"] for card in quiz_cards]
                return {"content": {"questions": questions}}
            else:
                # Generate quiz on-demand if not found in Supabase
                logger.info(f"Quiz not found in Supabase for lesson {lesson_id}, generating on-demand")
                quiz_content = await _generate_quiz_on_demand(lesson_id)
                return {"content": {"questions": quiz_content}}
        
        elif action == "flashcards":
            flashcard_cards = get_lesson_cards(lesson_id, "flashcard")
            if flashcard_cards:
                cards = [card["payload"] for card in flashcard_cards]
                return {"content": {"cards": cards}}
            else:
                # Generate flashcards on-demand if not found in Supabase
                logger.info(f"Flashcards not found in Supabase for lesson {lesson_id}, generating on-demand")
                flashcard_content = await _generate_flashcards_on_demand(lesson_id)
                return {"content": {"cards": flashcard_content}}
        
        elif action == "lesson":
            lesson_data = get_lesson_by_id(lesson_id)
            if lesson_data:
                # Get all bullet points
                bullet_cards = get_lesson_cards(lesson_id, "bullet")
                bullets = [card["payload"]["text"] for card in bullet_cards if "payload" in card and "text" in card["payload"]]
                
                # Get concept map
                concept_map = get_lesson_concept_map(lesson_id)
                
                return {
                    "content": {
                        "title": lesson_data.get("title", "Untitled Lesson"),
                        "summary": lesson_data.get("summary", ""),
                        "framework": lesson_data.get("framework", "generic"),
                        "bullets": bullets,
                        "concept_map": concept_map
                    }
                }
            else:
                raise HTTPException(404, f"Lesson not found: {lesson_id}")
        
        elif action == "workflow":
            # For workflow, we'll generate a simple workflow from the concept map
            concept_map = get_lesson_concept_map(lesson_id)
            if concept_map and concept_map.get("nodes"):
                workflow_steps = [node.get("title", "Step") for node in concept_map["nodes"]]
                return {"content": {"workflow": workflow_steps}}
            else:
                # Fallback to lesson summary as workflow
                summary = get_lesson_summary(lesson_id)
                if summary:
                    bullets = [b.strip() for b in summary.split("•") if b.strip()]
                    return {"content": {"workflow": bullets}}
                else:
                    raise HTTPException(404, f"Workflow not found for lesson {lesson_id}")
        
        else:
            raise HTTPException(400, f"Unknown action: {action}")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Lesson action failed: {e}")
        raise HTTPException(500, f"Failed to get {action} for lesson {lesson_id}")

@app.post("/api/lesson/{lesson_id}/{action}")
async def lesson_action_post(lesson_id: int, action: str):
    """POST endpoint for lesson actions - alternative to GET"""
    return await lesson_action(lesson_id, action)

@app.post("/api/chat/lesson/summary")
async def get_lesson_summary_chat(lesson_id: int, user_id: str):
    """Get lesson summary for chat integration"""
    try:
        summary = get_lesson_summary(lesson_id)
        if summary:
            bullets = [b.strip() for b in summary.split("•") if b.strip()]
            return {"content": bullets}
        else:
            raise HTTPException(404, f"Summary not found for lesson {lesson_id}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Lesson summary chat failed: {e}")
        raise HTTPException(500, f"Failed to get summary for lesson {lesson_id}")

@app.post("/api/chat")
async def chat_with_ai(user_id: str, message: str, conversation_id: Optional[str] = None):
    """Chat endpoint for AI interactions"""
    try:
        response = await process_chat_message(
            user_id=user_id,
            message=message,
            conversation_id=conversation_id,
            explanation_level=ExplanationLevel.INTERN
        )
        return response
    except Exception as e:
        logger.error(f"Chat processing failed: {e}")
        raise HTTPException(500, f"Chat processing failed: {str(e)}")

@app.post("/api/chat/upload")
async def upload_file_for_chat(
    user_id: str,
    conversation_id: Optional[str] = None,
    explanation_level: ExplanationLevel = ExplanationLevel.INTERN,
    file: UploadFile = File(...)
):
    """Upload file for chat processing"""
    if not file.filename.endswith(".pdf"):
        raise HTTPException(400, "PDF only")
    
    try:
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
        tmp.write(await file.read())
        tmp.close()
        
        response = await process_file_for_chat(
            file_path=Path(tmp.name),
            user_id=user_id,
            conversation_id=conversation_id,
            explanation_level=explanation_level
        )
        
        return response
        
    except Exception as e:
        logger.error(f"File upload for chat failed: {e}")
        raise HTTPException(500, f"File processing failed: {str(e)}")
    finally:
        if 'tmp' in locals():
            os.unlink(tmp.name)

async def _generate_quiz_on_demand(lesson_id: int) -> List[Dict]:
    """Generate quiz questions on-demand when Supabase data is not available"""
    try:
        # Get lesson summary to generate relevant quiz questions
        summary = get_lesson_summary(lesson_id)
        if not summary:
            # Generate a basic quiz based on common programming concepts
            return _generate_fallback_quiz()
        
        # Use the distiller's quiz generation with the summary
        from distiller import gen_flashcards_quiz, ExplanationLevel
        quiz_data = await gen_flashcards_quiz(summary, ExplanationLevel.INTERN)
        return quiz_data.get("quiz", _generate_fallback_quiz())
        
    except Exception as e:
        logger.error(f"Failed to generate quiz on-demand: {e}")
        return _generate_fallback_quiz()

async def _generate_flashcards_on_demand(lesson_id: int) -> List[Dict]:
    """Generate flashcards on-demand when Supabase data is not available"""
    try:
        # Get lesson summary to generate relevant flashcards
        summary = get_lesson_summary(lesson_id)
        if not summary:
            # Generate basic flashcards based on common programming concepts
            return _generate_fallback_flashcards()
        
        # Use the distiller's flashcard generation with the summary
        from distiller import gen_flashcards_quiz, ExplanationLevel
        flashcard_data = await gen_flashcards_quiz(summary, ExplanationLevel.INTERN)
        return flashcard_data.get("flashcards", _generate_fallback_flashcards())
        
    except Exception as e:
        logger.error(f"Failed to generate flashcards on-demand: {e}")
        return _generate_fallback_flashcards()

def _generate_fallback_quiz() -> List[Dict]:
    """Generate sophisticated fallback quiz questions"""
    return [
        {
            "question": "What is the primary purpose of API design?",
            "options": [
                "To make code run faster",
                "To provide a clear interface for data exchange",
                "To reduce file sizes",
                "To add more colors to the UI"
            ],
            "answer": "b"
        },
        {
            "question": "Which of the following is a best practice for error handling?",
            "options": [
                "Ignore all errors",
                "Use try-catch blocks appropriately",
                "Always use global error handlers",
                "Never handle errors"
            ],
            "answer": "b"
        },
        {
            "question": "What does REST stand for in RESTful APIs?",
            "options": [
                "Remote Execution System Transfer",
                "Representational State Transfer",
                "Real-time Event Streaming Technology",
                "Rapid Endpoint Service Transfer"
            ],
            "answer": "b"
        },
        {
            "question": "Which HTTP method is typically used for creating new resources?",
            "options": [
                "GET",
                "POST",
                "PUT",
                "DELETE"
            ],
            "answer": "b"
        },
        {
            "question": "What is the purpose of middleware in web applications?",
            "options": [
                "To make the app slower",
                "To process requests before they reach the main handler",
                "To only handle database operations",
                "To replace the main application logic"
            ],
            "answer": "b"
        }
    ]

def _generate_fallback_flashcards() -> List[Dict]:
    """Generate sophisticated fallback flashcards"""
    return [
        {
            "front": "What is an API?",
            "back": "An Application Programming Interface (API) is a set of rules and protocols that allows different software applications to communicate with each other."
        },
        {
            "front": "What is the difference between GET and POST?",
            "back": "GET requests retrieve data and are idempotent, while POST requests submit data and may change server state."
        },
        {
            "front": "What is error handling?",
            "back": "Error handling is the process of anticipating, detecting, and resolving programming, application, or communication errors."
        },
        {
            "front": "What is middleware?",
            "back": "Middleware is software that acts as a bridge between different applications, allowing them to communicate and share data."
        },
        {
            "front": "What is a RESTful API?",
            "back": "A RESTful API follows REST principles, using HTTP methods to perform CRUD operations on resources in a stateless manner."
        }
    ] 