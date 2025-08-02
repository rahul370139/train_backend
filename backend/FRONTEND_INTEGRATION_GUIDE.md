# 🎨 Frontend Integration Guide for TrainPI

## 📋 Overview
This guide provides all the information needed to integrate the TrainPI backend with your existing frontend. The backend provides 4 main pages with comprehensive API endpoints.

## 🏗️ System Architecture

### 4 Main Pages:
1. **Microlearning Platform** - PDF processing and AI-generated content
2. **Smart Career Pathfinder** - Adaptive skill suggestions and career discovery
3. **Unified Career Roadmap Generator** - Comprehensive career planning
4. **Dashboard & Analytics** - User progress and recommendations

## 🔗 API Base URL
After deployment, your backend will be available at:
```
https://your-app.vercel.app/api
```

## 📄 Page 1: Microlearning Platform

### Features:
- PDF upload and processing
- AI-generated summaries, flashcards, and quizzes
- Framework detection and explanation levels
- Concept map generation

### Key Endpoints:

#### 1. Upload and Process PDF
```javascript
// POST /api/distill
const uploadPDF = async (file, ownerId, explanationLevel = 'intern', framework = 'generic') => {
  const formData = new FormData();
  formData.append('file', file);
  
  const response = await fetch(`https://your-app.vercel.app/api/distill?owner_id=${ownerId}&explanation_level=${explanationLevel}&framework=${framework}`, {
    method: 'POST',
    body: formData
  });
  
  return response.json();
};

// Response:
{
  "lesson_id": "123",
  "bullets": ["• Key point 1", "• Key point 2"],
  "flashcards": [{"front": "Question?", "back": "Answer"}],
  "quiz": [{"question": "Q?", "options": ["a","b","c","d"], "answer": "a"}],
  "concept_map": {"nodes": [...], "edges": [...]},
  "framework": "python",
  "explanation_level": "intern"
}
```

#### 2. Get Available Frameworks
```javascript
// GET /api/frameworks
const getFrameworks = async () => {
  const response = await fetch('https://your-app.vercel.app/api/frameworks');
  return response.json();
};
```

#### 3. Get Explanation Levels
```javascript
// GET /api/explanation-levels
const getExplanationLevels = async () => {
  const response = await fetch('https://your-app.vercel.app/api/explanation-levels');
  return response.json();
};
```

### UI Components Needed:
- File upload component with drag & drop
- Progress indicator during processing
- Summary display with bullet points
- Flashcards component with flip animation
- Quiz component with multiple choice
- Concept map visualization
- Framework and explanation level selectors

## 🎯 Page 2: Smart Career Pathfinder

### Features:
- Adaptive skill suggestions based on user selections
- Initial suggestions based on user profile
- Career discovery with matching scores
- Smart UI that guides users through selection

### Key Endpoints:

#### 1. Get Initial Suggestions
```javascript
// GET /api/career/smart/initial-suggestions
const getInitialSuggestions = async (userProfile = null) => {
  const params = userProfile ? `?user_profile=${JSON.stringify(userProfile)}` : '';
  const response = await fetch(`https://your-app.vercel.app/api/career/smart/initial-suggestions${params}`);
  return response.json();
};

// Response:
{
  "interests": ["Technology", "Design", "Data Science"],
  "skills": ["python", "javascript", "react", "design"],
  "message": "Select your interests to get started"
}
```

#### 2. Suggest Next Skills
```javascript
// POST /api/career/smart/suggest-skills
const suggestSkills = async (selectedInterests, selectedSkills, userProfile = null) => {
  const response = await fetch('https://your-app.vercel.app/api/career/smart/suggest-skills', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      selected_interests: selectedInterests,
      selected_skills: selectedSkills,
      user_profile: userProfile
    })
  });
  return response.json();
};

// Response:
{
  "suggested_skills": ["typescript", "vue", "nodejs"],
  "categorized_suggestions": {
    "Programming": ["typescript", "nodejs"],
    "Web Development": ["vue", "react"]
  },
  "career_paths": ["Frontend Developer", "Full Stack Developer"],
  "message": "Great choices! Here are related skills..."
}
```

#### 3. Discover Careers
```javascript
// POST /api/career/smart/discover
const discoverCareers = async (selectedInterests, selectedSkills, userProfile = null) => {
  const response = await fetch('https://your-app.vercel.app/api/career/smart/discover', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      selected_interests: selectedInterests,
      selected_skills: selectedSkills,
      user_profile: userProfile
    })
  });
  return response.json();
};

// Response:
{
  "recommended_careers": [
    {
      "title": "Web Developer",
      "score": 0.85,
      "skill_match": 75.5,
      "salary_range": {"min": 60000, "max": 120000},
      "growth_pct": 15.2,
      "required_skills": ["javascript", "html", "css"],
      "day_in_life": "Designing and building websites..."
    }
  ],
  "insights": {...},
  "skill_analysis": {...}
}
```

### UI Components Needed:
- Interest selection cards with checkboxes
- Skill suggestion chips with add/remove
- Progress stepper showing current step
- Career cards with scores and details
- Skill match visualization
- "Continue to Roadmap" button

## 🗺️ Page 3: Unified Career Roadmap Generator

### Features:
- Target role recommendation (if not provided)
- Detailed 3-level career roadmap
- Interview preparation and coaching
- Market insights and learning recommendations

### Key Endpoints:

#### 1. Generate Unified Roadmap
```javascript
// POST /api/career/roadmap/unified
const generateRoadmap = async (userProfile, targetRole = null, userSkills = [], userInterests = []) => {
  const response = await fetch('https://your-app.vercel.app/api/career/roadmap/unified', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      user_profile: userProfile,
      target_role: targetRole,
      user_skills: userSkills,
      user_interests: userInterests
    })
  });
  return response.json();
};

// Response:
{
  "target_role": "Data Scientist",
  "roadmap": {
    "foundational": {
      "skills": ["python", "statistics"],
      "duration": "24 months",
      "courses": [...]
    },
    "intermediate": {...},
    "advanced": {...}
  },
  "interview_preparation": {
    "common_questions": [...],
    "technical_skills": [...],
    "portfolio_suggestions": [...]
  },
  "market_insights": {...},
  "learning_plan": {...},
  "coaching_advice": {...},
  "confidence_score": 0.85,
  "timeline": {...},
  "estimated_time_to_target": {...}
}
```

#### 2. Generate Interview Preparation
```javascript
// POST /api/career/roadmap/interview-prep
const getInterviewPrep = async (targetRole, userProfile = null) => {
  const response = await fetch('https://your-app.vercel.app/api/career/roadmap/interview-prep', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      target_role: targetRole,
      user_profile: userProfile
    })
  });
  return response.json();
};
```

### UI Components Needed:
- Role input field with autocomplete
- Skills and interests input
- Timeline visualization
- Roadmap levels with progress indicators
- Interview prep section with expandable cards
- Market insights dashboard
- Learning plan with course recommendations

## 📊 Page 4: Dashboard & Analytics

### Features:
- User progress tracking
- Lesson completion
- Role-based recommendations
- Learning analytics

### Key Endpoints:

#### 1. Update User Role
```javascript
// PUT /api/users/{user_id}/role
const updateUserRole = async (userId, role) => {
  const response = await fetch(`https://your-app.vercel.app/api/users/${userId}/role`, {
    method: 'PUT',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({role})
  });
  return response.json();
};
```

#### 2. Complete Lesson
```javascript
// POST /api/lessons/{lesson_id}/complete
const completeLesson = async (lessonId, userId, progressPercentage = 100.0) => {
  const response = await fetch(`https://your-app.vercel.app/api/lessons/${lessonId}/complete`, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      user_id: userId,
      progress_percentage: progressPercentage
    })
  });
  return response.json();
};
```

#### 3. Get User Progress
```javascript
// GET /api/users/{user_id}/progress
const getUserProgress = async (userId) => {
  const response = await fetch(`https://your-app.vercel.app/api/users/${userId}/progress`);
  return response.json();
};
```

#### 4. Get Recommendations
```javascript
// POST /api/recommendations
const getRecommendations = async (userId, userRole, completedLessons = []) => {
  const response = await fetch('https://your-app.vercel.app/api/recommendations', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      user_id: userId,
      user_role: userRole,
      completed_lessons: completedLessons
    })
  });
  return response.json();
};
```

### UI Components Needed:
- Progress charts and graphs
- Lesson completion cards
- Recommendation carousel
- User profile section
- Analytics dashboard
- Achievement badges

## 🤖 AI Chatbot Integration

### Features:
- Text-based conversations
- File upload support
- Conversation history
- Context-aware responses

### Key Endpoints:

#### 1. Send Chat Message
```javascript
// POST /api/chat
const sendChatMessage = async (userId, message, conversationId = null, explanationLevel = 'intern') => {
  const response = await fetch('https://your-app.vercel.app/api/chat', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
      user_id: userId,
      message,
      conversation_id: conversationId,
      explanation_level: explanationLevel
    })
  });
  return response.json();
};
```

#### 2. Upload File for Chat
```javascript
// POST /api/chat/upload
const uploadFileForChat = async (userId, file, conversationId = null, explanationLevel = 'intern') => {
  const formData = new FormData();
  formData.append('file', file);
  
  const response = await fetch(`https://your-app.vercel.app/api/chat/upload?user_id=${userId}&conversation_id=${conversationId}&explanation_level=${explanationLevel}`, {
    method: 'POST',
    body: formData
  });
  return response.json();
};
```

#### 3. Get Conversation History
```javascript
// GET /api/chat/conversations/{user_id}
const getUserConversations = async (userId) => {
  const response = await fetch(`https://your-app.vercel.app/api/chat/conversations/${userId}`);
  return response.json();
};
```

### UI Components Needed:
- Chat interface with message bubbles
- File upload area
- Conversation list sidebar
- Message input with send button
- Typing indicators

## 🎨 UI/UX Guidelines

### Design System:
- Use consistent color scheme across all pages
- Implement responsive design for mobile/desktop
- Add loading states for all API calls
- Include error handling with user-friendly messages
- Use smooth transitions and animations

### User Flow:
1. **Landing Page** → Choose between Microlearning or Career Planning
2. **Microlearning** → Upload PDF → View Results → Save to Dashboard
3. **Career Pathfinder** → Select Interests → Select Skills → Discover Careers → Generate Roadmap
4. **Dashboard** → View Progress → Get Recommendations → Continue Learning

### Error Handling:
```javascript
const handleApiError = (error) => {
  if (error.status === 500) {
    showMessage('Server error. Please try again later.');
  } else if (error.status === 400) {
    showMessage('Invalid input. Please check your data.');
  } else {
    showMessage('Network error. Please check your connection.');
  }
};
```

## 🔧 Integration Checklist

### Before Integration:
- [ ] Set up environment variables
- [ ] Test all endpoints with Postman/curl
- [ ] Verify CORS settings
- [ ] Check API response formats

### During Integration:
- [ ] Implement error handling for all API calls
- [ ] Add loading states for better UX
- [ ] Test on different devices and browsers
- [ ] Validate all form inputs

### After Integration:
- [ ] Test complete user flows
- [ ] Verify data persistence
- [ ] Check performance and loading times
- [ ] Test error scenarios

## 📞 Support

If you encounter any issues during integration:
1. Check the API response format matches the documentation
2. Verify all required parameters are being sent
3. Test endpoints individually using curl or Postman
4. Check browser console for CORS or network errors

## 🚀 Quick Start

1. Replace `https://your-app.vercel.app` with your actual backend URL
2. Start with the Microlearning page (simplest integration)
3. Add Career Pathfinder features incrementally
4. Implement Dashboard analytics last
5. Add chatbot features as final enhancement

Good luck with the integration! 🎯 