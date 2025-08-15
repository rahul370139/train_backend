# SkillSpring Backend

A comprehensive backend system for AI-powered career guidance and personalized learning experiences. Built with FastAPI, featuring intelligent PDF processing, LLM-powered content generation, and sophisticated recommendation systems.

## 🏗️ Architecture Overview

### Core Components
- **FastAPI Application** (`main.py`) - Main API server with comprehensive endpoints
- **Content Distiller** (`distiller.py`) - PDF processing, LLM integration, and content generation
- **Career System** (`unified_career_system.py`) - Career matching, roadmap generation, and skill analysis
- **Database Helper** (`supabase_helper.py`) - Supabase integration for data persistence
- **Data Schemas** (`schemas.py`) - Pydantic models for API contracts

### Technology Stack
- **Framework**: FastAPI (Python 3.9+)
- **LLM Provider**: Groq (llama3-8b-8192 model)
- **Embeddings**: Cohere (text-embedding-ada-002)
- **Database**: Supabase (PostgreSQL)
- **Vector Search**: pgvector extension
- **Deployment**: Railway/Render

## 🚀 Core Features

### 1. Learn Page - AI-Powered PDF Processing

#### PDF Upload & Processing (`/api/chat/upload`)
- **Chunking Strategy**: Intelligent text segmentation (500-800 chars) with overlap
- **Embedding Generation**: Cohere embeddings for semantic search
- **Content Analysis**: Automatic framework detection (Python, JavaScript, etc.)
- **Summary Generation**: LLM-powered bullet-point summaries
- **In-Memory Caching**: Stores processed content for session persistence

#### Content Generation Endpoints
- **Summary** (`/api/chat` + "create summary"): Key takeaways and insights
- **Quiz** (`/api/chat` + "generate quiz"): Interactive questions with multiple choice
- **Flashcards** (`/api/chat` + "create flashcards"): Front-back learning cards
- **Micro-lessons** (`/api/chat` + "create lesson"): Structured learning content
- **Workflows** (`/api/chat` + "create workflow"): Visual process diagrams (Mermaid)
- **Concept Maps** (`/api/chat` + "create concept map"): Knowledge graph visualization

#### Smart Content Generation
- **Retrieval-Augmented Generation (RAG)**: Uses relevant PDF chunks as context
- **Variable Item Counts**: Generate 5-20 quiz questions or flashcards on demand
- **Explanation Levels**: Intern, Junior, Senior, Expert content adaptation
- **Context-Aware**: Maintains conversation continuity across requests

### 2. Career Page - Intelligent Career Guidance

#### Career Matching System (`/api/career/match`)
- **Multi-Dimensional Analysis**: Skills, interests, experience level, goals
- **Skill Gap Analysis**: Identifies missing competencies for target roles
- **Personality Alignment**: Work style and cultural fit assessment
- **Market Demand**: Current industry trends and opportunities

#### Career Roadmap Generation (`/api/career/roadmap`)
- **Personalized Paths**: Custom learning journeys based on current state
- **Skill Progression**: Logical skill development sequences
- **Resource Recommendations**: Courses, projects, and certifications
- **Timeline Estimation**: Realistic milestones and deadlines

#### Skill Analysis & Recommendations
- **Technical Skills**: Programming languages, frameworks, tools
- **Soft Skills**: Communication, leadership, problem-solving
- **Domain Knowledge**: Industry-specific expertise areas
- **Learning Resources**: Curated content and practice materials

### 3. Dashboard - Unified Learning Management

#### Learning Progress Tracking
- **Session Management**: Conversation and lesson persistence
- **Content History**: Generated summaries, quizzes, and lessons
- **Skill Development**: Progress tracking across learning paths
- **Performance Analytics**: Quiz scores and learning metrics

#### Content Management
- **Lesson Organization**: Structured content hierarchy
- **Search & Discovery**: Semantic search across uploaded materials
- **Content Reuse**: Leverage previous generations for new requests
- **Export Capabilities**: Download generated content and roadmaps

## 🔧 Technical Implementation

### LLM Integration
- **Model**: Groq's llama3-8b-8192 (optimized for speed)
- **Temperature**: 0.3 (strict JSON adherence)
- **Timeout**: 25 seconds with 2 retries
- **Prompt Engineering**: Structured prompts for consistent outputs
- **JSON Parsing**: Robust error handling for malformed responses

### Vector Search & Retrieval
- **Chunking**: Optimal text segmentation for context retrieval
- **Embedding Dimensions**: 1536-dimensional vectors (Cohere)
- **Similarity Search**: Cosine similarity for relevant content retrieval
- **Context Window**: Intelligent chunk selection for LLM context

### Caching Strategy
- **In-Memory Store**: Session-based content caching
- **Conversation Context**: Maintains file context across requests
- **Generated Content**: Caches LLM outputs to reduce API calls
- **User Sessions**: Persistent conversation tracking

### Error Handling & Fallbacks
- **Graceful Degradation**: Continues operation if Supabase fails
- **Fallback Content**: Pre-generated responses for common failures
- **Retry Logic**: Exponential backoff for transient errors
- **Logging**: Comprehensive error tracking and debugging

## 📡 API Endpoints

### Learn Page Endpoints
```
POST /api/chat/upload              # PDF upload and processing
POST /api/chat                     # Chat with AI (content generation)
GET  /api/chat/lesson/{id}/content # Retrieve lesson content
POST /api/chat/ingest-distilled    # Process extracted content
```

### Career Page Endpoints
```
POST /api/career/match             # Career matching analysis
POST /api/career/roadmap           # Generate career roadmap
GET  /api/career/skills            # Available skills list
POST /api/career/analyze           # Skills and experience analysis
```

### Dashboard Endpoints
```
GET  /api/dashboard/user/{id}      # User dashboard data
GET  /api/dashboard/lessons        # User's learning content
GET  /api/dashboard/progress       # Learning progress metrics
POST /api/dashboard/export         # Export learning data
```

## 🔄 Data Flow

### PDF Processing Pipeline
1. **Upload** → File validation and storage
2. **Chunking** → Text segmentation with overlap
3. **Embedding** → Vector generation for semantic search
4. **Analysis** → Framework detection and summary generation
5. **Caching** → Store processed content in memory
6. **Persistence** → Optional Supabase storage

### Content Generation Flow
1. **User Request** → Natural language command
2. **Context Retrieval** → Relevant PDF chunks via embeddings
3. **LLM Generation** → Structured content creation
4. **Response Formatting** → JSON payload with multiple formats
5. **Frontend Rendering** → Interactive content display

### Career Guidance Process
1. **Profile Input** → Skills, experience, goals
2. **Analysis Engine** → Multi-dimensional assessment
3. **Recommendation Engine** → Career path suggestions
4. **Roadmap Generation** → Personalized learning journey
5. **Resource Curation** → Learning materials and milestones

## 🎯 Key Features

### Intelligent Content Generation
- **Context-Aware**: Uses uploaded PDF content for relevant generation
- **Adaptive Difficulty**: Adjusts content complexity based on user level
- **Interactive Elements**: Quiz questions, flashcards, visual workflows
- **Multi-Format Output**: JSON, text, and structured data formats

### Career Intelligence
- **Market-Aware**: Current industry trends and demand
- **Skill Mapping**: Comprehensive skill taxonomy and relationships
- **Personalization**: User-specific recommendations and paths
- **Progress Tracking**: Learning milestones and achievements

### Performance Optimization
- **Async Processing**: Non-blocking API operations
- **Smart Caching**: Reduce redundant LLM calls
- **Batch Operations**: Efficient content processing
- **Connection Pooling**: Optimized database interactions

## 🔒 Security & Reliability

### Data Protection
- **User Isolation**: Strict user ID validation
- **Content Privacy**: User-specific content storage
- **API Rate Limiting**: Prevent abuse and ensure fairness
- **Input Validation**: Comprehensive request sanitization

### System Reliability
- **Graceful Degradation**: Continues operation during partial failures
- **Retry Mechanisms**: Automatic retry for transient errors
- **Health Monitoring**: System status and performance metrics
- **Backup Strategies**: Fallback content and error recovery

## 🚀 Deployment

### Environment Variables
```bash
GROQ_API_KEY=your_groq_api_key
COHERE_API_KEY=your_cohere_api_key
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
```

### Railway Deployment
- **Automatic Scaling**: Based on traffic and load
- **Health Checks**: Continuous monitoring and restart
- **Log Aggregation**: Centralized logging and debugging
- **SSL Termination**: Automatic HTTPS configuration

## 📊 Monitoring & Debugging

### Logging Strategy
- **Structured Logging**: JSON-formatted log entries
- **Performance Metrics**: Response times and throughput
- **Error Tracking**: Detailed error context and stack traces
- **User Activity**: Request patterns and usage analytics

### Debug Endpoints
- **Health Check**: `/health` - System status
- **Metrics**: `/metrics` - Performance indicators
- **Debug Info**: `/debug` - Runtime information
- **Test Mode**: Fallback responses for development

## 🔮 Future Enhancements

### Planned Features
- **Multi-Language Support**: Internationalization and localization
- **Advanced Analytics**: Learning pattern analysis and insights
- **Collaborative Learning**: Group study and peer recommendations
- **Mobile Optimization**: Progressive web app capabilities
- **Integration APIs**: Third-party learning platform connections

### Technical Improvements
- **Vector Database**: Dedicated vector storage for better search
- **Model Fine-tuning**: Custom LLM training for domain expertise
- **Real-time Updates**: WebSocket support for live interactions
- **Microservices**: Modular architecture for scalability

---

*This backend powers the SkillSpring platform, providing intelligent career guidance and personalized learning experiences through advanced AI and machine learning technologies.*
