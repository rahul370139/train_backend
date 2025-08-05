#!/usr/bin/env python3
"""
Test script for TrainPI backend integration
Tests all major endpoints to ensure they're working correctly
"""

import requests
import json
import sys
from typing import Dict, Any

BASE_URL = "https://trainbackend-production.up.railway.app"

def test_endpoint(endpoint: str, method: str = "GET", data: Dict[str, Any] = None, files: Dict[str, Any] = None) -> bool:
    """Test a single endpoint"""
    try:
        url = f"{BASE_URL}{endpoint}"
        
        print(f"\n🔍 Testing {method} {endpoint}")
        print(f"   URL: {url}")
        
        if method == "GET":
            response = requests.get(url, timeout=30)
        elif method == "POST":
            if files:
                response = requests.post(url, files=files, timeout=60)
            else:
                response = requests.post(url, json=data, timeout=30)
        elif method == "PUT":
            response = requests.put(url, json=data, timeout=30)
        
        print(f"   Status: {response.status_code}")
        
        if response.status_code in [200, 201]:
            try:
                result = response.json()
                print(f"   ✅ Success: {json.dumps(result, indent=2)[:200]}...")
                return True
            except:
                print(f"   ✅ Success: {response.text[:200]}...")
                return True
        else:
            print(f"   ❌ Error: {response.text}")
            return False
            
    except Exception as e:
        print(f"   ❌ Exception: {e}")
        return False

def test_health_endpoints():
    """Test health and basic endpoints"""
    print("\n🏥 Testing Health Endpoints")
    print("=" * 50)
    
    success = True
    success &= test_endpoint("/")
    success &= test_endpoint("/health")
    success &= test_endpoint("/docs")
    
    return success

def test_career_endpoints():
    """Test career-related endpoints"""
    print("\n💼 Testing Career Endpoints")
    print("=" * 50)
    
    success = True
    
    # Test career quiz
    success &= test_endpoint("/api/career/quiz")
    
    # Test career match with sample data
    sample_answers = [3, 4, 2, 5, 3, 4, 2, 3, 4, 5]  # 10 answers 1-5
    sample_data = {
        "answers": sample_answers,
        "owner_id": "test-user-123",
        "user_profile": {
            "experience_level": "beginner",
            "interests": ["technology", "problem-solving"]
        }
    }
    success &= test_endpoint("/api/career/match", "POST", sample_data)
    
    # Test skills endpoint
    success &= test_endpoint("/api/skills")
    
    # Test explanation levels
    success &= test_endpoint("/api/explanation-levels")
    
    return success

def test_learning_endpoints():
    """Test learning and chat endpoints"""
    print("\n📚 Testing Learning Endpoints")
    print("=" * 50)
    
    success = True
    
    # Test chat endpoint
    chat_data = {
        "message": "Hello, can you help me learn Python?",
        "user_id": "test-user-123",
        "explanation_level": "intern"  # Use lowercase enum value
    }
    success &= test_endpoint("/api/chat", "POST", chat_data)
    
    return success

def test_unified_career_endpoints():
    """Test unified career system endpoints"""
    print("\n🎯 Testing Unified Career System")
    print("=" * 50)
    
    success = True
    
    # Test unified roadmap
    roadmap_data = {
        "user_profile": {
            "experience_level": "beginner",
            "current_role": "student",
            "interests": ["technology", "programming"]
        },
        "user_skills": ["python", "basic-programming"],
        "user_interests": ["web-development", "ai"]
    }
    success &= test_endpoint("/api/career/roadmap/unified", "POST", roadmap_data)
    
    # Test career guidance
    guidance_data = {
        "target_role": "Software Developer",
        "user_profile": {
            "experience_level": "beginner",
            "current_role": "student"
        },
        "user_id": "test-user-123",
        "query": "How can I become a software developer?"
    }
    success &= test_endpoint("/api/career/guidance", "POST", guidance_data)
    
    # Test interview prep
    prep_data = {
        "target_role": "Software Developer",
        "user_profile": {
            "experience_level": "beginner"
        }
    }
    success &= test_endpoint("/api/career/roadmap/interview-prep", "POST", prep_data)
    
    return success

def test_smart_career_endpoints():
    """Test smart career pathfinder endpoints"""
    print("\n🧠 Testing Smart Career Pathfinder")
    print("=" * 50)
    
    success = True
    
    # Test smart career request
    smart_data = {
        "user_profile": {
            "current_role": "student",
            "experience_level": "beginner",
            "interests": ["programming", "technology"],
            "skills": ["python", "basic-programming"],
            "goals": ["become a software developer"]
        },
        "target_role": "Software Developer"
    }
    success &= test_endpoint("/api/career/smart/comprehensive-plan", "POST", smart_data)
    
    return success

def test_user_management_endpoints():
    """Test user management endpoints"""
    print("\n👤 Testing User Management")
    print("=" * 50)
    
    success = True
    
    # Test user role upsert
    user_data = {
        "user_id": "test-user-123",
        "role": "Software Developer",
        "experience_level": "beginner",
        "interests": ["programming", "web-development"]
    }
    success &= test_endpoint("/api/users/test-user-123/role", "PUT", user_data)
    
    # Test get user role
    success &= test_endpoint("/api/users/test-user-123/role")
    
    return success

def main():
    """Run all tests"""
    print("🚀 TrainPI Backend Integration Test")
    print("=" * 60)
    print(f"Testing backend at: {BASE_URL}")
    
    all_success = True
    
    # Test all endpoint categories
    all_success &= test_health_endpoints()
    all_success &= test_career_endpoints()
    all_success &= test_learning_endpoints()
    all_success &= test_unified_career_endpoints()
    all_success &= test_smart_career_endpoints()
    all_success &= test_user_management_endpoints()
    
    print("\n" + "=" * 60)
    if all_success:
        print("🎉 ALL TESTS PASSED! Backend is fully operational.")
        print("✅ Your backend is ready for frontend integration.")
    else:
        print("❌ SOME TESTS FAILED! Check the errors above.")
        print("🔧 Fix the failing endpoints before proceeding with frontend integration.")
    
    return 0 if all_success else 1

if __name__ == "__main__":
    sys.exit(main()) 