"""
TrainPI Agents Package
Agentic AI system for intelligent tutoring and learning management
"""

from .study_agent import (
    BaseAgent, SummarizerAgent, DiagnosticAgent, AgentRouter,
    create_summarizer_agent, create_diagnostic_agent, create_agent_router
)
from .learn_tools import (
    ingest_pdf, gen_summary, gen_flashcards, gen_quiz,
    PDFIngestionManager, ContentGenerator
)
from .validators import (
    qa_flashcards, qa_quiz, qa_summary,
    get_flashcard_errors, get_quiz_errors, get_summary_errors,
    FlashcardValidator, QuizValidator, SummaryValidator
)
from .repairs import (
    repair_flashcards, repair_quiz,
    can_repair_flashcards, can_repair_quiz,
    FlashcardRepairer, QuizRepairer
)
from .mastery import (
    get_mastery, update_mastery,
    get_topic_mastery, get_learning_progress, get_recommended_topics,
    MasteryTracker
)

__all__ = [
    # Core Agent Classes
    "BaseAgent",
    "SummarizerAgent", 
    "DiagnosticAgent",
    "AgentRouter",
    
    # Agent Factory Functions
    "create_summarizer_agent",
    "create_diagnostic_agent", 
    "create_agent_router",
    
    # Learning Tools
    "ingest_pdf",
    "gen_summary",
    "gen_flashcards",
    "gen_quiz",
    "PDFIngestionManager",
    "ContentGenerator",
    
    # Validation System
    "qa_flashcards",
    "qa_quiz", 
    "qa_summary",
    "get_flashcard_errors",
    "get_quiz_errors",
    "get_summary_errors",
    "FlashcardValidator",
    "QuizValidator",
    "SummaryValidator",
    
    # Repair System
    "repair_flashcards",
    "repair_quiz",
    "can_repair_flashcards",
    "can_repair_quiz",
    "FlashcardRepairer",
    "QuizRepairer",
    
    # Mastery System
    "get_mastery",
    "update_mastery",
    "get_topic_mastery",
    "get_learning_progress",
    "get_recommended_topics",
    "MasteryTracker"
]
