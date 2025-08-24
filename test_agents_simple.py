#!/usr/bin/env python3
"""
Simple Test Script for TrainPI Agentic AI System
Tests the core functionality without external dependencies
"""

import sys
import asyncio
from typing import Dict, Any


def test_agent_imports():
    """Test that all agent modules can be imported"""
    print("🔍 Testing agent imports...")
    
    try:
        from agents import (
            BaseAgent, SummarizerAgent, DiagnosticAgent, AgentRouter,
            ingest_pdf, gen_summary, gen_flashcards, gen_quiz,
            qa_flashcards, qa_quiz, repair_flashcards, repair_quiz,
            get_mastery, update_mastery
        )
        print("✅ All agent imports successful")
        return True
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False


def test_agent_classes():
    """Test that agent classes can be instantiated"""
    print("🔍 Testing agent class instantiation...")
    
    try:
        from agents import BaseAgent, SummarizerAgent, DiagnosticAgent, AgentRouter
        
        # Test base agent
        base_agent = BaseAgent("test_pdf_123", "test_user_456", "test_topic")
        assert base_agent.pdf_id == "test_pdf_123"
        assert base_agent.user_id == "test_user_456"
        assert base_agent.topic == "test_topic"
        
        # Test summarizer agent
        summarizer = SummarizerAgent("test_pdf_123", "test_user_456", "test_topic")
        assert isinstance(summarizer, SummarizerAgent)
        
        # Test diagnostic agent
        diagnostic = DiagnosticAgent("test_pdf_123", "test_user_456", "test_topic")
        assert isinstance(diagnostic, DiagnosticAgent)
        
        # Test agent router
        router = AgentRouter()
        assert isinstance(router, AgentRouter)
        
        print("✅ All agent classes instantiated successfully")
        return True
        
    except Exception as e:
        print(f"❌ Agent class test failed: {e}")
        return False


def test_agent_router():
    """Test the agent router functionality"""
    print("🔍 Testing agent router...")
    
    try:
        from agents import AgentRouter
        
        router = AgentRouter()
        
        # Test intent detection
        intent_result = router.detect_intent("I want a summary of this document")
        print(f"Intent detection result: {intent_result}")
        assert "intent" in intent_result
        assert intent_result["intent"] == "summary"
        
        # Test routing
        route_result = router.route_request("summary", {"pdf_id": "test123"})
        print(f"Route result: {route_result}")
        assert "agent" in route_result
        assert route_result["agent"] == "SummarizerAgent"
        
        print("✅ Agent router working correctly")
        return True
        
    except Exception as e:
        print(f"❌ Agent router test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_validation_system():
    """Test the validation system"""
    print("🔍 Testing validation system...")
    
    try:
        from agents import qa_flashcards, qa_quiz
        
        # Test flashcard validation
        valid_flashcards = [
            {"front": "What is Python?", "back": "A programming language"},
            {"front": "What is ML?", "back": "Machine Learning"}
        ]
        print(f"Testing flashcard validation with: {valid_flashcards}")
        result = qa_flashcards(valid_flashcards)
        print(f"Flashcard validation result: {result}")
        assert result == True
        
        # Test quiz validation
        valid_quiz = [
            {
                "question": "What is Python?",
                "options": ["Programming Language", "Development Tool", "Web Framework", "Database System"],
                "answer_idx": 0
            }
        ]
        print(f"Testing quiz validation with: {valid_quiz}")
        print(f"Quiz data types: question={type(valid_quiz[0]['question'])}, options={type(valid_quiz[0]['options'])}, answer_idx={type(valid_quiz[0]['answer_idx'])}")
        result = qa_quiz(valid_quiz)
        print(f"Quiz validation result: {result}")
        
        # If validation fails, let's see what the errors are
        if not result:
            from agents import get_quiz_errors
            errors = get_quiz_errors(valid_quiz)
            print(f"Quiz validation errors: {errors}")
        
        assert result == True
        
        print("✅ Validation system working correctly")
        return True
        
    except Exception as e:
        print(f"❌ Validation test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_repair_system():
    """Test the repair system"""
    print("🔍 Testing repair system...")
    
    try:
        from agents import can_repair_flashcards, can_repair_quiz
        
        # Test repairability checks
        repairable_flashcards = [
            {"front": "What is Python?", "back": ""},  # Missing back
            {"front": "", "back": "A language"}        # Missing front
        ]
        assert can_repair_flashcards(repairable_flashcards) == True
        
        print("✅ Repair system working correctly")
        return True
        
    except Exception as e:
        print(f"❌ Repair test failed: {e}")
        return False


def test_mastery_system():
    """Test the mastery tracking system"""
    print("🔍 Testing mastery system...")
    
    try:
        from agents import get_mastery, update_mastery
        
        # Test mastery functions
        mastery_data = get_mastery("test_user")
        assert isinstance(mastery_data, dict)
        
        # Test mastery update
        update_mastery("test_user", {"python": 0.8})
        
        print("✅ Mastery system working correctly")
        return True
        
    except Exception as e:
        print(f"❌ Mastery test failed: {e}")
        return False


async def test_async_functions():
    """Test async functions"""
    print("🔍 Testing async functions...")
    
    try:
        from agents import create_summarizer_agent, create_diagnostic_agent, SummarizerAgent, DiagnosticAgent
        
        # Test agent creation
        summarizer = await create_summarizer_agent("test_pdf", "test_user", "test_topic")
        assert isinstance(summarizer, SummarizerAgent)
        
        diagnostic = await create_diagnostic_agent("test_pdf", "test_user", "test_topic")
        assert isinstance(diagnostic, DiagnosticAgent)
        
        print("✅ Async functions working correctly")
        return True
        
    except Exception as e:
        print(f"❌ Async test failed: {e}")
        return False


async def main():
    """Run all tests"""
    print("🚀 Testing TrainPI Optimized Agentic AI System")
    print("=" * 60)

    tests = [
        test_agent_imports,
        test_agent_classes,
        test_agent_router,
        test_validation_system,
        test_repair_system,
        test_mastery_system,
        test_async_functions
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        try:
            if asyncio.iscoroutinefunction(test):
                result = await test()
            else:
                result = test()
                
            if result:
                passed += 1
        except Exception as e:
            print(f"❌ Test {test.__name__} crashed: {e}")

    print("\n" + "=" * 60)
    print(f"📊 Test Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed! The optimized agentic system is working correctly.")
        print("\n✨ Key Features Available:")
        print("   • PDF Ingestion & Processing")
        print("   • Intelligent Content Generation (Summaries, Flashcards, Quizzes)")
        print("   • Quality Validation & Auto-Repair")
        print("   • Adaptive Diagnostic Testing")
        print("   • Mastery Tracking & Progress Analytics")
        print("   • Smart Intent Detection & Routing")
        return 0
    else:
        print("⚠️  Some tests failed. Please check the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
