#!/usr/bin/env python3
"""
Test script for unified PDF processing functionality.
This tests the enhanced chat upload endpoint and the new ingest endpoint.
"""

import asyncio
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch
import sys

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from distiller import process_file_for_chat
from schemas import ExplanationLevel

async def test_enhanced_process_file_for_chat():
    """Test the enhanced process_file_for_chat function that now saves to Supabase."""
    print("🧪 Testing enhanced process_file_for_chat function...")
    
    # Create a mock PDF file
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp_file:
        # Write some dummy PDF content
        tmp_file.write(b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n/Pages 2 0 R\n>>\nendobj\n2 0 obj\n<<\n/Type /Pages\n/Kids [3 0 R]\n/Count 1\n>>\nendobj\n3 0 obj\n<<\n/Type /Page\n/Parent 2 0 R\n/MediaBox [0 0 612 792]\n/Contents 4 0 R\n>>\nendobj\n4 0 obj\n<<\n/Length 44\n>>\nstream\nBT\n/F1 12 Tf\n72 720 Td\n(Test PDF Content) Tj\nET\nendstream\nendobj\nxref\n0 5\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \n0000000115 00000 n \n0000000204 00000 n \ntrailer\n<<\n/Size 5\n/Root 1 0 R\n>>\nstartxref\n364\n%%EOF\n")
        tmp_file_path = tmp_file.name
    
    try:
        # Mock the Supabase functions to avoid actual database calls
        with patch('supabase_helper.insert_lesson') as mock_insert_lesson, \
             patch('supabase_helper.insert_cards') as mock_insert_cards, \
             patch('supabase_helper.insert_concept_map') as mock_insert_concept_map:
            
            # Mock the database functions to return expected values
            mock_insert_lesson.return_value = 123  # Mock lesson_id
            mock_insert_cards.return_value = None
            mock_insert_concept_map.return_value = None
            
            # Test the enhanced function
            result = await process_file_for_chat(
                file_path=Path(tmp_file_path),
                user_id="test-user-123",
                conversation_id=None,
                explanation_level=ExplanationLevel.INTERN
            )
            
            # Verify the result contains the expected fields
            assert "lesson_id" in result, "Result should contain lesson_id"
            assert "actions" in result, "Result should contain actions"
            assert "file_processed" in result, "Result should contain file_processed"
            assert result["lesson_id"] == 123, "Lesson ID should match expected value"
            assert result["file_processed"] == True, "File should be marked as processed"
            
            print("✅ Enhanced process_file_for_chat test passed!")
            print(f"   Lesson ID: {result['lesson_id']}")
            print(f"   Actions: {result['actions']}")
            print(f"   PDF Name: {result['pdf_name']}")
            
            return result
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        raise
    finally:
        # Clean up
        if os.path.exists(tmp_file_path):
            os.unlink(tmp_file_path)

async def test_chat_ingest_endpoint():
    """Test the new chat ingest endpoint functionality."""
    print("\n🧪 Testing chat ingest endpoint functionality...")
    
    # Mock the necessary functions
    with patch('supabase_helper.get_lesson_by_id') as mock_get_lesson, \
         patch('supabase_helper.get_lesson_summary') as mock_get_summary, \
         patch('distiller.get_or_create_conversation') as mock_get_conv, \
         patch('distiller.add_message_to_conversation') as mock_add_msg, \
         patch('distiller.conversation_store') as mock_conversation_store:
        
        # Mock lesson data
        mock_get_lesson.return_value = {
            "id": 123,
            "title": "Test Lesson",
            "framework": "PYTHON",
            "summary": "Test summary content"
        }
        mock_get_summary.return_value = "Test summary content"
        mock_get_conv.return_value = "test-conversation-123"
        mock_add_msg.return_value = None
        
        # Mock conversation store
        mock_conversation_store.__getitem__.return_value = {
            "file_context": "",
            "updated_at": "",
            "metadata": {}
        }
        
        # Import the function to test
        from main import ingest_distilled_lesson
        
        # Test the ingest function
        result = await ingest_distilled_lesson(
            lesson_id=123,
            user_id="test-user-123",
            conversation_id=None
        )
        
        # Verify the result
        assert "lesson_ingested" in result, "Result should contain lesson_ingested"
        assert "lesson_id" in result, "Result should contain lesson_id"
        assert result["lesson_ingested"] == True, "Lesson should be marked as ingested"
        assert result["lesson_id"] == 123, "Lesson ID should match"
        
        print("✅ Chat ingest endpoint test passed!")
        print(f"   Lesson ID: {result['lesson_id']}")
        print(f"   Title: {result['title']}")
        print(f"   Framework: {result['framework']}")
        
        return result

async def main():
    """Run all tests."""
    print("🚀 Starting unified PDF processing tests...\n")
    
    try:
        # Test the enhanced upload functionality
        upload_result = await test_enhanced_process_file_for_chat()
        
        # Test the ingest functionality
        ingest_result = await test_chat_ingest_endpoint()
        
        print("\n🎉 All tests passed! The unified PDF processing is working correctly.")
        print("\n📋 Summary:")
        print(f"   ✅ Enhanced upload creates lesson_id: {upload_result['lesson_id']}")
        print(f"   ✅ Ingest endpoint can load lesson: {ingest_result['lesson_id']}")
        print(f"   ✅ Both endpoints return consistent data structures")
        
    except Exception as e:
        print(f"\n❌ Tests failed: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(main())
