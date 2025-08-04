from distiller import chunk_text, pdf_to_text, detect_framework, generate_concept_map, get_role_based_recommendations, process_chat_message, process_file_for_chat, get_conversation_history, get_user_conversations
import pytest
from pathlib import Path
from fastapi.testclient import TestClient
import io
import asyncio
from schemas import ExplanationLevel, Framework

# Existing chunking test
def test_chunking():
    txt = "word " * 5000
    chunks = chunk_text(txt)
    assert chunks, "No chunks produced"
    assert len(" ".join(chunks).split()) >= 5000

# PDF extraction test
def test_pdf_to_text(tmp_path):
    # Create a simple PDF file using fitz
    import fitz
    pdf_path = tmp_path / "test.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Hello PDF extraction!")
    doc.save(str(pdf_path))
    doc.close()
    text = pdf_to_text(pdf_path)
    assert "Hello PDF extraction!" in text

# Framework detection test
@pytest.mark.asyncio
async def test_detect_framework():
    # Test with Python-related content
    python_text = "Python is a programming language. We use FastAPI for web development."
    framework = await detect_framework(python_text)
    assert framework in [Framework.PYTHON, Framework.FASTAPI, Framework.GENERIC]
    
    # Test with generic content
    generic_text = "This is a general document about various topics."
    framework = await detect_framework(generic_text)
    assert framework == Framework.GENERIC

# Concept map generation test
@pytest.mark.asyncio
async def test_generate_concept_map():
    summary = "Python is a programming language. FastAPI is a web framework built on Python. We use it to create APIs."
    concept_map = await generate_concept_map(summary)
    assert isinstance(concept_map, dict)
    assert "nodes" in concept_map
    assert "edges" in concept_map
    assert isinstance(concept_map["nodes"], list)
    assert isinstance(concept_map["edges"], list)

# Role-based recommendations test
@pytest.mark.asyncio
async def test_get_role_based_recommendations():
    recommendations = await get_role_based_recommendations(
        user_id="test_user",
        role="Software Engineer",
        experience_level="Mid",
        interests=["Python", "Web Development"]
    )
    assert isinstance(recommendations, list)
    # Should return 5 recommendations
    assert len(recommendations) <= 5

# Chatbot tests
@pytest.mark.asyncio
async def test_process_chat_message():
    # Test basic chat functionality
    result = await process_chat_message(
        user_id="test_user",
        message="What is Python?",
        conversation_id=None,
        explanation_level=ExplanationLevel.INTERN
    )
    assert isinstance(result, dict)
    assert "response" in result
    assert "conversation_id" in result
    assert "message_id" in result
    assert "timestamp" in result
    assert len(result["response"]) > 0

@pytest.mark.asyncio
async def test_process_file_for_chat(tmp_path):
    # Create a test PDF
    import fitz
    pdf_path = tmp_path / "chat_test.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Python is a programming language used for web development.")
    doc.save(str(pdf_path))
    doc.close()
    
    # Test file processing for chat
    result = await process_file_for_chat(
        file_path=pdf_path,
        user_id="test_user",
        conversation_id=None,
        explanation_level=ExplanationLevel.INTERN
    )
    assert isinstance(result, dict)
    assert "response" in result
    assert "conversation_id" in result
    assert "file_processed" in result
    assert result["file_processed"] == True
    assert "summary" in result

def test_get_conversation_history():
    # First create a conversation by sending a message
    import asyncio
    result = asyncio.run(process_chat_message(
        user_id="test_user",
        message="Hello",
        conversation_id=None,
        explanation_level=ExplanationLevel.INTERN
    ))
    
    conversation_id = result["conversation_id"]
    history = get_conversation_history(conversation_id)
    
    assert history is not None
    assert history["conversation_id"] == conversation_id
    assert history["user_id"] == "test_user"
    assert "messages" in history
    assert len(history["messages"]) >= 2  # User message + AI response

def test_get_user_conversations():
    # Create a conversation first
    import asyncio
    asyncio.run(process_chat_message(
        user_id="test_user",
        message="Test message",
        conversation_id=None,
        explanation_level=ExplanationLevel.INTERN
    ))
    
    conversations = get_user_conversations("test_user")
    assert isinstance(conversations, list)
    assert len(conversations) > 0
    
    # Check conversation structure
    conv = conversations[0]
    assert "conversation_id" in conv
    assert "created_at" in conv
    assert "updated_at" in conv
    assert "message_count" in conv
    assert "has_file_context" in conv

# Endpoint test with new features
def test_distill_endpoint_with_new_features(monkeypatch, tmp_path):
    # Mock the functions before importing the app
    async def mock_map_reduce_summary(chunks, explanation_level=ExplanationLevel.INTERN):
        return "• Bullet 1\n• Bullet 2"
    
    async def mock_gen_flashcards_quiz(summary, explanation_level=ExplanationLevel.INTERN):
        # Return the expected dictionary structure directly
        return {
            "flashcards": [{"front": "What is Python?", "back": "A programming language"}],
            "quiz": [{"question": "What is Python?", "options": ["a", "b", "c", "d"], "answer": "a"}]
        }
    
    async def mock_embed_chunks(chunks):
        return [[0.0]*384 for _ in chunks]
    
    async def mock_detect_framework(text):
        return Framework.PYTHON
    
    async def mock_generate_concept_map(summary):
        return {"nodes": [{"id": "python", "label": "Python", "level": 1}], "edges": []}
    
    # Apply mocks to the module before importing main
    monkeypatch.setattr("distiller.map_reduce_summary", mock_map_reduce_summary)
    monkeypatch.setattr("distiller.gen_flashcards_quiz", mock_gen_flashcards_quiz)
    monkeypatch.setattr("distiller.embed_chunks", mock_embed_chunks)
    monkeypatch.setattr("distiller.detect_framework", mock_detect_framework)
    monkeypatch.setattr("distiller.generate_concept_map", mock_generate_concept_map)
    
    # Also mock the functions in main module since they're imported directly
    monkeypatch.setattr("main.map_reduce_summary", mock_map_reduce_summary)
    monkeypatch.setattr("main.gen_flashcards_quiz", mock_gen_flashcards_quiz)
    monkeypatch.setattr("main.embed_chunks", mock_embed_chunks)
    monkeypatch.setattr("main.detect_framework", mock_detect_framework)
    monkeypatch.setattr("main.generate_concept_map", mock_generate_concept_map)
    
    # Create a simple PDF
    import fitz
    pdf_path = tmp_path / "test2.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Python programming concepts!")
    doc.save(str(pdf_path))
    doc.close()
    
    with open(pdf_path, "rb") as f:
        # Import app after mocking
        from main import app
        client = TestClient(app)
        response = client.post(
            "/api/distill?owner_id=testuser&explanation_level=intern&framework=python", 
            files={"file": ("test2.pdf", f, "application/pdf")}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["lesson_id"] == 123  # Dummy ID from supabase_helper
        assert len(data["bullets"]) == 2
        assert len(data["flashcards"]) == 1
        assert len(data["quiz"]) == 1
        assert "concept_map" in data
        assert data["framework"] == "python"
        assert data["explanation_level"] == "intern"

# Test chatbot endpoints
def test_chat_endpoint(monkeypatch):
    from distiller import process_chat_message
    
    async def mock_process_chat_message(user_id, message, conversation_id, explanation_level):
        return {
            "response": "Hello! I'm TrainPI, your AI learning assistant.",
            "conversation_id": "test-conv-id",
            "message_id": "test-msg-id",
            "timestamp": "2024-01-01T00:00:00Z"
        }
    
    monkeypatch.setattr("distiller.process_chat_message", mock_process_chat_message)
    
    from main import app
    client = TestClient(app)
    response = client.post("/api/chat", json={
        "user_id": "test_user",
        "message": "Hello",
        "conversation_id": None,
        "explanation_level": "intern"
    })
    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    assert "conversation_id" in data

def test_chat_file_upload_endpoint(monkeypatch, tmp_path):
    from distiller import process_file_for_chat
    
    async def mock_process_file_for_chat(file_path, user_id, conversation_id, explanation_level):
        return {
            "response": "I've processed your file and found interesting content about Python programming.",
            "conversation_id": "test-conv-id",
            "message_id": "test-msg-id",
            "timestamp": "2024-01-01T00:00:00Z",
            "file_processed": True,
            "summary": "Python programming concepts"
        }
    
    monkeypatch.setattr("distiller.process_file_for_chat", mock_process_file_for_chat)
    
    # Create a test PDF
    import fitz
    pdf_path = tmp_path / "chat_upload_test.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Python programming content for chat.")
    doc.save(str(pdf_path))
    doc.close()
    
    from main import app
    client = TestClient(app)
    with open(pdf_path, "rb") as f:
        response = client.post(
            "/api/chat/upload?user_id=test_user&explanation_level=intern",
            files={"file": ("test.pdf", f, "application/pdf")}
        )
    assert response.status_code == 200
    data = response.json()
    assert "response" in data
    assert "conversation_id" in data

# Test new endpoints
def test_frameworks_endpoint():
    from main import app
    client = TestClient(app)
    response = client.get("/api/frameworks")
    assert response.status_code == 200
    data = response.json()
    assert "frameworks" in data
    assert len(data["frameworks"]) > 0

def test_explanation_levels_endpoint():
    from main import app
    client = TestClient(app)
    response = client.get("/api/explanation-levels")
    assert response.status_code == 200
    data = response.json()
    assert "explanation_levels" in data
    assert len(data["explanation_levels"]) == 3



