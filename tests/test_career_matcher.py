import pytest
import pandas as pd
import numpy as np
from pathlib import Path
import tempfile
import os

# Import the career matcher
from career_matcher import CareerMatcher, RIASEC

class TestCareerMatcher:
    """Test career matching functionality"""
    
    @pytest.fixture
    def sample_data(self):
        """Create sample career data for testing"""
        return [
            {
                "soc_code": "15-1132.00", "title": "Software Developer", 
                "salary_low": 70000, "salary_high": 120000, "growth_pct": 25.0,
                "realistic": 30, "investigative": 80, "artistic": 40, 
                "social": 20, "enterprising": 50, "conventional": 60,
                "top_skills": "programming, problem solving, teamwork",
                "day_in_life": "Design and develop software applications."
            },
            {
                "soc_code": "15-1131.00", "title": "Computer Programmer",
                "salary_low": 65000, "salary_high": 110000, "growth_pct": 15.0,
                "realistic": 40, "investigative": 70, "artistic": 30,
                "social": 15, "enterprising": 35, "conventional": 75,
                "top_skills": "coding, debugging, documentation",
                "day_in_life": "Write and test code, maintain programs."
            },
            {
                "soc_code": "15-1151.00", "title": "Computer User Support Specialist",
                "salary_low": 45000, "salary_high": 75000, "growth_pct": 16.0,
                "realistic": 40, "investigative": 50, "artistic": 20,
                "social": 80, "enterprising": 45, "conventional": 60,
                "top_skills": "technical support, troubleshooting, communication",
                "day_in_life": "Help users with technical issues."
            }
        ]
    
    @pytest.fixture
    def temp_career_data(self, sample_data):
        """Create temporary career data file"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            df = pd.DataFrame(sample_data)
            df.to_csv(f.name, index=False)
            yield f.name
        os.unlink(f.name)
    
    def test_career_matcher_initialization(self, temp_career_data):
        """Test career matcher initialization"""
        # Temporarily replace the data path
        original_path = CareerMatcher.__init__.__defaults__
        
        # Create matcher with temp data
        matcher = CareerMatcher()
        matcher.data_path = Path(temp_career_data)
        matcher.df = pd.read_csv(temp_career_data)
        
        assert len(matcher.df) == 3
        assert "title" in matcher.df.columns
        assert "realistic" in matcher.df.columns
        assert "investigative" in matcher.df.columns
    
    def test_answers_to_vec(self):
        """Test conversion of quiz answers to RIASEC vector"""
        # Test case: someone who likes technical work (high realistic, investigative)
        answers = [5, 5, 1, 2, 3, 4, 5, 5, 2, 3]  # High on realistic/investigative
        
        vec = CareerMatcher.answers_to_vec(answers)
        
        assert len(vec) == 6  # 6 RIASEC dimensions
        assert isinstance(vec, np.ndarray)
        assert vec.dtype == float
        
        # Check that realistic and investigative are higher than others
        realistic_idx = RIASEC.index("realistic")
        investigative_idx = RIASEC.index("investigative")
        social_idx = RIASEC.index("social")
        
        assert vec[realistic_idx] > vec[social_idx]
        assert vec[investigative_idx] > vec[social_idx]
    
    def test_answers_to_vec_validation(self):
        """Test validation of quiz answers"""
        # Test wrong number of answers
        with pytest.raises(AssertionError):
            CareerMatcher.answers_to_vec([1, 2, 3, 4, 5])  # Only 5 answers
        
        # Test valid answers
        answers = [1, 2, 3, 4, 5, 1, 2, 3, 4, 5]  # 10 answers, all 1-5
        vec = CareerMatcher.answers_to_vec(answers)
        assert len(vec) == 6
    
    def test_top_matches(self, temp_career_data):
        """Test career matching functionality"""
        matcher = CareerMatcher()
        matcher.data_path = Path(temp_career_data)
        matcher.df = pd.read_csv(temp_career_data)
        
        # Normalize the data
        matcher.df[RIASEC] = matcher.df[RIASEC].apply(
            lambda col: (col - col.mean()) / (col.std() + 1e-9)
        )
        matcher.df["vec_norm"] = np.linalg.norm(matcher.df[RIASEC].values, axis=1)
        
        # Test answers favoring technical work (high realistic/investigative)
        answers = [5, 5, 1, 2, 3, 4, 5, 5, 2, 3]
        matches = matcher.top_matches(answers, k=2)
        
        assert len(matches) == 2
        assert "title" in matches[0]
        assert "final_score" in matches[0]
        assert matches[0]["title"] in ["Software Developer", "Computer Programmer"]
    
    def test_get_quiz_questions(self, temp_career_data):
        """Test quiz questions retrieval"""
        matcher = CareerMatcher()
        matcher.data_path = Path(temp_career_data)
        
        questions = matcher.get_quiz_questions()
        
        assert len(questions) == 10
        assert questions[0]["id"] == 0
        assert questions[0]["category"] == "Realistic"
        assert "Repairing" in questions[0]["question"]
        
        # Check all questions have required fields
        for q in questions:
            assert "id" in q
            assert "question" in q
            assert "category" in q
            assert "description" in q
    
    def test_career_matcher_error_handling(self):
        """Test error handling in career matcher"""
        matcher = CareerMatcher()
        
        # Test with invalid answers
        with pytest.raises(AssertionError):
            CareerMatcher.answers_to_vec([1, 2, 3])  # Too few answers
        
        # Test top_matches with empty data (should handle gracefully)
        # This would happen if the CSV file is empty or corrupted
        empty_df = pd.DataFrame(columns=RIASEC + ["title", "salary_low", "salary_high"])
        matcher.df = empty_df
        matches = matcher.top_matches([1, 2, 3, 4, 5, 1, 2, 3, 4, 5])
        assert len(matches) == 0

class TestCareerAPI:
    """Test career API endpoints"""
    
    @pytest.mark.asyncio
    async def test_get_career_quiz(self):
        """Test GET /api/career/quiz endpoint"""
        from fastapi.testclient import TestClient
        from main import app
        
        with TestClient(app) as client:
            response = client.get("/api/career/quiz")
            assert response.status_code == 200
            
            data = response.json()
            assert "questions" in data
            assert len(data["questions"]) == 10
            
            # Check first question structure
            first_q = data["questions"][0]
            assert "id" in first_q
            assert "question" in first_q
            assert "category" in first_q
            assert "description" in first_q
    
    @pytest.mark.asyncio
    async def test_career_match_valid(self):
        """Test POST /api/career/match with valid data"""
        from fastapi.testclient import TestClient
        from main import app
        
        with TestClient(app) as client:
            request_data = {
                "owner_id": "test_user_123",
                "answers": [3, 4, 2, 3, 4, 3, 2, 4, 3, 4]  # 10 answers, 1-5
            }
            
            response = client.post("/api/career/match", json=request_data)
            assert response.status_code == 200
            
            data = response.json()
            assert "results" in data
            assert len(data["results"]) > 0
            
            # Check first result structure
            first_result = data["results"][0]
            assert "title" in first_result
            assert "salary_low" in first_result
            assert "salary_high" in first_result
            assert "growth_pct" in first_result
            assert "common_skills" in first_result
            assert "day_in_life" in first_result
            assert "similarity" in first_result
    
    @pytest.mark.asyncio
    async def test_career_match_invalid_answers(self):
        """Test POST /api/career/match with invalid data"""
        from fastapi.testclient import TestClient
        from main import app
        
        with TestClient(app) as client:
            # Too few answers (should return 422 for validation error)
            request_data = {
                "owner_id": "test_user_123",
                "answers": [1, 2, 3, 4, 5]  # Only 5 answers
            }
            
            response = client.post("/api/career/match", json=request_data)
            assert response.status_code == 422  # Validation error
            
            # Invalid answer values (should return 400 from endpoint validation)
            request_data = {
                "owner_id": "test_user_123",
                "answers": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]  # Values > 5
            }
            
            response = client.post("/api/career/match", json=request_data)
            assert response.status_code == 400  # Business logic validation
    
    @pytest.mark.asyncio
    async def test_career_match_missing_owner_id(self):
        """Test POST /api/career/match with missing owner_id"""
        from fastapi.testclient import TestClient
        from main import app
        
        with TestClient(app) as client:
            request_data = {
                "answers": [3, 4, 2, 3, 4, 3, 2, 4, 3, 4]
            }
            
            response = client.post("/api/career/match", json=request_data)
            assert response.status_code == 422  # Validation error 