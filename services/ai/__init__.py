"""
Campus-Link AI Service Layer Package.
Integrates Google Gemini AI with deterministic placement calculations.
"""
from services.ai.gemini_client import GeminiClient, get_gemini_client
from services.ai.career_twin_service import CareerTwinService
from services.ai.skill_gap_service import SkillGapService
from services.ai.career_roadmap_service import CareerRoadmapService
from services.ai.job_match_service import JobMatchService
from services.ai.interview_ai_service import InterviewAIService
from services.ai.resume_ai_service import ResumeAIService
from services.ai.project_ai_service import ProjectAIService
from services.ai.placement_ai_service import PlacementAIService
from services.ai.recruiter_ai_service import RecruiterAIService
from services.ai.career_chat_service import CareerChatService

__all__ = [
    "GeminiClient",
    "get_gemini_client",
    "CareerTwinService",
    "SkillGapService",
    "CareerRoadmapService",
    "JobMatchService",
    "InterviewAIService",
    "ResumeAIService",
    "ProjectAIService",
    "PlacementAIService",
    "RecruiterAIService",
    "CareerChatService",
]
