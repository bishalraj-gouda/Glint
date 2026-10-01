from extensions import db
from models.role import Role, ROLE_STUDENT, ROLE_RECRUITER, ROLE_ADMIN
from models.user import User
from models.department import Department
from models.company import Company
from models.recruiter import Recruiter, RecruiterProfile
from models.student import Student, StudentProfile
from models.skill import Skill, StudentSkill
from models.project import Project
from models.certification import Certification
from models.job import Job, JobSkill
from models.application import Application
from models.interview import Interview
from models.placement import Placement
from models.ai_career_twin import AICareerTwin
from models.ai_interview_session import AIInterviewSession, InterviewQuestion, InterviewAnswer, AIEvaluation
from models.ai_roadmap import AIRoadmap
from models.ai_resume_analysis import AIResumeAnalysis
from models.resume import Resume
from models.career_goal import CareerGoal, SkillGapRecord, LearningRecommendation, JobMatch, AIActivityLog

__all__ = [
    "db",
    "Role",
    "ROLE_STUDENT",
    "ROLE_RECRUITER",
    "ROLE_ADMIN",
    "User",
    "Department",
    "Company",
    "Recruiter",
    "RecruiterProfile",
    "Student",
    "StudentProfile",
    "Skill",
    "StudentSkill",
    "Project",
    "Certification",
    "Job",
    "JobSkill",
    "Application",
    "Interview",
    "Placement",
    "AICareerTwin",
    "AIInterviewSession",
    "InterviewQuestion",
    "InterviewAnswer",
    "AIEvaluation",
    "AIRoadmap",
    "AIResumeAnalysis",
    "Resume",
    "CareerGoal",
    "SkillGapRecord",
    "LearningRecommendation",
    "JobMatch",
    "AIActivityLog",
]
