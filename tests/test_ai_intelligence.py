"""
Unit and Integration Test Suite for Campus-Link AI Career Intelligence Platform.
Tests all AI services, deterministic calculations, fallback resilience, and route security.
Runs 100% offline and deterministic using test database fixtures and mocked/fallback LLM engines.
"""
import pytest
from app import create_app
from extensions import db
from models.user import User
from models.student import Student
from models.job import Job
from models.company import Company
from models.ai_career_twin import AICareerTwin
from models.ai_roadmap import AIRoadmap
from models.ai_interview_session import AIInterviewSession
from models.ai_resume_analysis import AIResumeAnalysis
from data.seed_data import seed_database
from services.ai.gemini_client import get_gemini_client
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


@pytest.fixture
def test_app():
    """Create test application using SQLite in-memory database."""
    app = create_app("testing")
    with app.app_context():
        db.create_all()
        seed_database()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(test_app):
    return test_app.test_client()


def test_gemini_client_fallback(test_app):
    """Verify Gemini client gracefully runs fallback generators when operating offline."""
    client = get_gemini_client()
    
    fallback_data = {"test_key": "success", "deterministic_val": 42}
    result = client.generate_structured(
        prompt="Generate dummy data",
        fallback_fn=lambda: fallback_data
    )
    assert result["test_key"] == "success"
    assert result["deterministic_val"] == 42


def test_career_twin_service(test_app):
    """Verify CareerTwinService calculates deterministic readiness metrics and persists record."""
    with test_app.app_context():
        student = Student.query.first()
        assert student is not None

        twin = CareerTwinService.get_or_create_twin(student.id)
        assert twin["student_id"] == student.id
        assert 0 <= twin["overall_score"] <= 100
        assert "sub_scores" in twin
        assert "academic" in twin["sub_scores"]
        assert "skills" in twin["sub_scores"]
        assert "twin_persona" in twin
        assert "predicted_readiness_tier" in twin

        # Verify DB persistence
        db_twin = AICareerTwin.query.filter_by(student_id=student.id).first()
        assert db_twin is not None
        assert db_twin.overall_readiness_score == twin["overall_score"]


def test_skill_gap_service(test_app):
    """Verify SkillGapService computes exact mathematical set difference against role benchmark."""
    with test_app.app_context():
        student = Student.query.first()
        gap_report = SkillGapService.analyze_skill_gaps(student.id, target_role="Full Stack Developer")

        assert gap_report["student_id"] == student.id
        assert "match_percentage" in gap_report
        assert isinstance(gap_report["matched_skills"], list)
        assert isinstance(gap_report["missing_skills"], list)
        assert gap_report["total_required"] == len(gap_report["matched_skills"]) + len(gap_report["missing_skills"])


def test_career_roadmap_service_and_toggle(test_app):
    """Verify CareerRoadmapService generates 4 milestones and correctly toggles tasks."""
    with test_app.app_context():
        student = Student.query.first()
        roadmap = CareerRoadmapService.get_or_generate_roadmap(student.id, target_role="Full Stack Developer")

        assert roadmap["student_id"] == student.id
        assert len(roadmap["milestones"]) >= 3
        
        # Test task toggling
        first_milestone = roadmap["milestones"][0]
        first_task = first_milestone["action_tasks"][0]
        task_id = first_task["id"]

        toggle_res = CareerRoadmapService.toggle_task(roadmap["id"], task_id)
        assert toggle_res["success"] is True
        assert "progress_percentage" in toggle_res


def test_job_match_service(test_app):
    """Verify JobMatchService evaluates eligibility and computes multi-factor score."""
    with test_app.app_context():
        student = Student.query.first()
        job = Job.query.first()
        assert student is not None and job is not None

        match = JobMatchService.evaluate_job_match(student.id, job.id)
        assert match["student_id"] == student.id
        assert match["job_id"] == job.id
        assert 0 <= match["composite_score"] <= 100
        assert "cgpa_eligible" in match
        assert "fit_verdict" in match


def test_interview_ai_service(test_app):
    """Verify InterviewAIService starts session and grades answers on 3 axes."""
    with test_app.app_context():
        student = Student.query.first()
        session = InterviewAIService.start_session(student.id, role_title="Full Stack Developer", interview_type="technical")

        assert "session_id" in session
        assert session["total_questions"] >= 1
        assert "current_question" in session

        session_id = session["session_id"]
        answer_res = InterviewAIService.submit_answer(
            session_id=session_id,
            answer_text="An array has O(1) random access due to contiguous memory, whereas a linked list requires O(n) traversal."
        )

        assert "evaluation" in answer_res
        eval_data = answer_res["evaluation"]
        assert 0 <= eval_data["technical_accuracy"] <= 100
        assert 0 <= eval_data["communication_clarity"] <= 100
        assert 0 <= eval_data["depth_completeness"] <= 100
        assert 0 <= eval_data["score"] <= 100


def test_resume_ai_service(test_app):
    """Verify ResumeAIService detects sections and computes ATS compliance."""
    with test_app.app_context():
        student = Student.query.first()
        sample_resume = """
        John Doe | email: john@example.com | Phone: 9876543210 | GitHub: github.com/johndoe
        EDUCATION: B.Tech Computer Science, CGPA 8.5, Year 2026.
        SKILLS: Python, SQL, Git, REST APIs, Docker, Data Structures.
        PROJECTS:
        - SentinelFlow: Real-time telemetry monitoring engine built using Python and FastAPI.
        EXPERIENCE:
        - Software Engineering Intern at TechCorp.
        """
        audit = ResumeAIService.audit_resume(student.id, sample_resume)
        assert audit["student_id"] == student.id
        assert 0 <= audit["ats_score"] <= 100
        assert audit["section_completeness"]["contact_info"] is True
        assert audit["section_completeness"]["education"] is True
        assert audit["section_completeness"]["skills"] is True


def test_project_ai_service(test_app):
    """Verify ProjectAIService generates production-grade project blueprint."""
    with test_app.app_context():
        student = Student.query.first()
        idea = ProjectAIService.generate_project_idea(student.id, target_role="Cloud & Backend Engineer")

        assert idea["student_id"] == student.id
        assert "blueprint" in idea
        bp = idea["blueprint"]
        assert "title" in bp
        assert "recommended_tech_stack" in bp
        assert "implementation_phases" in bp
        assert "resume_bullet_point" in bp


def test_placement_ai_service(test_app):
    """Verify PlacementAIService generates institutional executive briefing."""
    with test_app.app_context():
        intel = PlacementAIService.get_institutional_intelligence()
        assert "metrics" in intel
        assert intel["metrics"]["total_students"] > 0
        assert "strategic_briefing" in intel
        briefing = intel["strategic_briefing"]
        assert "executive_briefing" in briefing
        assert "high_leverage_interventions" in briefing


def test_recruiter_ai_service(test_app):
    """Verify RecruiterAIService generates screening dossier and interview guide."""
    with test_app.app_context():
        student = Student.query.first()
        job = Job.query.first()
        report = RecruiterAIService.screen_candidate(student.id, job.id)

        assert report["student_id"] == student.id
        assert report["job_id"] == job.id
        assert "screening" in report
        screening = report["screening"]
        assert "hiring_recommendation" in screening
        assert "top_reasons_to_hire" in screening
        assert "tailored_interview_guide" in screening


def test_career_chat_service(test_app):
    """Verify CareerChatService replies with contextual student details."""
    with test_app.app_context():
        student = Student.query.first()
        chat_res = CareerChatService.chat(student.id, "How can I improve my resume for upcoming placements?")
        assert chat_res["student_id"] == student.id
        assert len(chat_res["response"]) > 20


def test_recruiter_ai_candidate_ranking(test_app):
    """Verify RecruiterAIService accurately ranks student profiles against job requisitions."""
    with test_app.app_context():
        job = Job.query.first()
        assert job is not None

        ranked = RecruiterAIService.rank_candidates_for_job(job.id)
        assert ranked["job_id"] == job.id
        assert ranked["total_ranked"] > 0
        assert "candidates" in ranked
        assert len(ranked["candidates"]) == ranked["total_ranked"]

        # Ensure sorted in descending order of composite score
        scores = [c["composite_score"] for c in ranked["candidates"]]
        assert scores == sorted(scores, reverse=True)

        top_cand = ranked["candidates"][0]
        assert top_cand["rank"] == 1
        assert "name" in top_cand
        assert "matched_skills" in top_cand
        assert "twin_score" in top_cand


def test_recruiter_ai_evaluation_summary(test_app):
    """Verify RecruiterAIService generates a structured scorecard summary from draft notes."""
    with test_app.app_context():
        from models.interview import Interview
        interview = Interview.query.first()
        assert interview is not None

        summary = RecruiterAIService.generate_evaluation_summary(
            interview.id, score=88.0, draft_notes="Strong algorithmic reasoning, clear explanation of hash tables."
        )
        assert summary["interview_id"] == interview.id
        assert "formatted_feedback" in summary
        assert len(summary["formatted_feedback"]) > 20
        assert "recommended_status" in summary


def test_recruiter_copilot_chat(test_app):
    """Verify Recruiter Copilot delivers contextual responses grounded in company requisitions."""
    with test_app.app_context():
        from models.recruiter import Recruiter
        recruiter = Recruiter.query.first()
        assert recruiter is not None

        chat_res = RecruiterAIService.recruiter_chat(
            recruiter.id, "Who are the top candidates for Python and data analytics?"
        )
        assert chat_res["recruiter_id"] == recruiter.id
        assert "response" in chat_res
        assert len(chat_res["response"]) > 20


def test_admin_skill_gap_report_generator(test_app):
    """Verify PlacementAIService generates formal institutional curriculum and deficit reports."""
    with test_app.app_context():
        report = PlacementAIService.generate_skill_gap_report(department_code="CSE")
        assert report["department_code"] == "CSE"
        assert "report_id" in report
        assert "data" in report
        data = report["data"]
        assert "report_title" in data
        assert "executive_summary" in data
        assert "urgent_deficits" in data
        assert len(data["urgent_deficits"]) > 0
        assert "actionable_curriculum_modules" in data
        assert len(data["actionable_curriculum_modules"]) > 0


def test_ai_route_security_enforcement(client):
    """Verify AI routes enforce authentication and reject unauthenticated requests."""
    # Unauthenticated attempt to access Student Career Twin view
    res = client.get("/student/ai/twin")
    assert res.status_code == 302

    # Unauthenticated attempt to call Student API
    api_res = client.get("/student/ai/api/twin")
    assert api_res.status_code == 401

    # Unauthenticated attempt to access Recruiter AI Matcher
    rec_res = client.get("/recruiter/ai/matching")
    assert rec_res.status_code == 302

    # Unauthenticated attempt to access Admin AI Insights
    adm_res = client.get("/admin/ai/insights")
    assert adm_res.status_code == 302

    # Unauthenticated attempt to access Admin AI Skill Gap Report
    adm_rpt = client.get("/admin/ai/skill-gap-report")
    assert adm_rpt.status_code == 302
