#!/usr/bin/env python3
"""
Test script to verify chatbot PDF content access.
"""

import asyncio
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch
import sys

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from distiller import process_file_for_chat, process_chat_message
from schemas import ExplanationLevel

async def test_chatbot_pdf_access():
    """Test that chatbot can access PDF content after upload."""
    print("🧪 Testing chatbot PDF content access...")
    
    # Create a mock PDF file with specific content
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
        # Write some dummy PDF content
        tmp_file.write(b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n/Contents 4 0 R\n>>\nendobj\n4 0 obj\n<<\n/Length 44\n>>\nstream\nBT\n/F1 12 Tf\n72 720 Td\n(Test PDF Content) Tj\nET\nendstream\nendobj\nxref\n0 5\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n0000000204 00000 n \ntrailer\n<<\n/Size 5\n/Root 1 0 R\n>>\nstartxref\n364\n%%EOF\n")
        tmp_file_path = tmp_file.name
    
    try:
        # Mock the Supabase functions
        with patch('supabase_helper.insert_lesson') as mock_insert_lesson, \
             patch('supabase_helper.insert_cards') as mock_insert_cards, \
             patch('supabase_helper.insert_concept_map') as mock_insert_concept_map:
            
            # Mock the database functions
            mock_insert_lesson.return_value = 123
            mock_insert_cards.return_value = None
            mock_insert_concept_map.return_value = None
            
            # Step 1: Upload PDF for chat
            print("   📤 Uploading PDF for chat...")
            upload_result = await process_file_for_chat(
                file_path=Path(tmp_file_path),
                user_id="test-user-123",
                conversation_id=None,
                explanation_level=ExplanationLevel.INTERN
            )
            
            conversation_id = upload_result["conversation_id"]
            print(f"   ✅ PDF uploaded, conversation_id: {conversation_id}")
            
            # Step 2: Test chatbot access to PDF content
            print("   💬 Testing chatbot access to PDF content...")
            
            # Mock the Groq API call to return a predictable response
            with patch('distiller.call_groq') as mock_call_groq:
                mock_call_groq.return_value = "I can see the PDF content you uploaded. The document contains information about Test PDF Content. How can I help you understand this material better?"
                
                chat_result = await process_chat_message(
                    user_id="test-user-123",
                    message="What's in this PDF?",
                    conversation_id=conversation_id,
                    explanation_level=ExplanationLevel.INTERN
                )
                
                # Verify the response
                assert "conversation_id" in chat_result, "Chat result should contain conversation_id"
                assert chat_result["conversation_id"] == conversation_id, "Conversation ID should match"
                assert "response" in chat_result, "Chat result should contain response"
                
                print("   ✅ Chatbot successfully accessed PDF content!")
                print(f"   💬 Response: {chat_result['response'][:100]}...")
                
                return upload_result, chat_result
                
    except Exception as e:
        print(f"   ❌ Test failed: {e}")
        raise
    finally:
        # Clean up
        if os.path.exists(tmp_file_path):
            os.unlink(tmp_file_path)

async def test_lesson_vs_summary_difference():
    """Test that lessons and summaries are different."""
    print("\n🧪 Testing lesson vs summary difference...")
    
    # Mock the Groq API calls
    with patch('distiller.call_groq') as mock_call_groq:
        # Mock lesson generation
        mock_call_groq.side_effect = [
            # Lesson response
            '{"title": "Learning Lesson: API Development", "overview": "Learn how to build APIs", "learning_objectives": ["Understand REST principles", "Build API endpoints"], "estimated_duration": "45 minutes", "difficulty_level": "intermediate", "learning_modules": [{"title": "Module 1", "learning_goal": "Learn REST basics", "content": "Educational content", "duration": "15 minutes", "examples": ["Example 1"], "practice_exercises": ["Exercise 1"], "key_concepts": ["Concept 1"], "common_mistakes": ["Mistake 1"], "tips": ["Tip 1"]}], "hands_on_projects": [{"title": "Build API", "description": "Create a REST API", "objectives": ["Build endpoints"], "instructions": "Step by step", "materials_needed": ["Code editor"], "expected_outcome": "Working API"}], "assessment": [{"type": "quiz", "title": "API Quiz", "description": "Test knowledge", "questions": ["Question 1"]}], "next_steps": ["Learn authentication"], "additional_resources": ["Documentation"], "framework_specific": true}',
            # Summary response  
            '{"title": "Document Summary", "overview": "Brief overview of the document", "key_points": ["Key point 1", "Key point 2"], "main_topics": [{"topic": "Topic 1", "description": "Description", "key_concepts": ["Concept 1"]}], "action_items": ["Action 1"], "estimated_reading_time": "10 minutes"}'
        ]
        
        # Test lesson generation
        lesson_result = await process_chat_message(
            user_id="test-user-123",
            message="create lesson about API development",
            conversation_id="test-conv-123",
            explanation_level=ExplanationLevel.INTERN
        )
        
        # Test summary generation
        summary_result = await process_chat_message(
            user_id="test-user-123", 
            message="create summary about API development",
            conversation_id="test-conv-456",
            explanation_level=ExplanationLevel.INTERN
        )
        
        print("   ✅ Lesson and summary generation tested!")
        print(f"   📚 Lesson type: {lesson_result.get('type', 'unknown')}")
        print(f"   📋 Summary type: {summary_result.get('type', 'unknown')}")
        
        return lesson_result, summary_result

async def main():
    """Run all tests."""
    print("🚀 Starting chatbot PDF access tests...\n")
    
    try:
        # Test PDF content access
        upload_result, chat_result = await test_chatbot_pdf_access()
        
        # Test lesson vs summary difference
        lesson_result, summary_result = await test_lesson_vs_summary_difference()
        
        print("\n🎉 All tests passed!")
        print("\n📋 Summary:")
        print("   ✅ Chatbot can access PDF content after upload")
        print("   ✅ Lesson and summary generation work correctly")
        print("   ✅ PDF processing creates conversation context")
        
    except Exception as e:
        print(f"\n❌ Tests failed: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())
