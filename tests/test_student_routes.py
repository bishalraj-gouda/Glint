"""
Student Features, AI Intelligence & External Profile Integration Tests.
Verifies Student Profile updates, GitHub enrichment, Skill Gap synchronization,
Roadmap task toggle & proof-of-work, and AI mock interview APIs.
"""
import pytest
from app import create_app
from extensions import db
from models.user import User
from models.student import Student
from models.role import ROLE_STUDENT
from data.seed_data import seed_database


@pytest.fixture
def app():
    """Create test application with seeded SQLite database."""
    test_app = create_app("testing")
    with test_app.app_context():
        db.create_all()
        seed_database()

        if not User.query.filter_by(email="student@demo.com").first():
            u = User(email="student@demo.com", role=ROLE_STUDENT)
            u.set_password("Student@123")
            db.session.add(u)
            db.session.flush()
            s = Student(
                user_id=u.id,
                name="Demo Student",
                roll_number="DEMO-2026",
                department_id=1,
                year=4,
                cgpa=8.75,
                target_role="Full Stack Developer",
                github_url="https://github.com/octocat",
                linkedin_url="https://linkedin.com/in/demostudent",
                portfolio_url="https://demostudent.dev"
            )
            db.session.add(s)
            db.session.commit()

        yield test_app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def authenticated_student(client):
    """Logs in the demo student before tests."""
    client.post("/login", data={
        "email": "student@demo.com",
        "password": "Student@123"
    }, follow_redirects=True)
    return client


def test_student_dashboard_page(authenticated_student):
    """Test accessing student dashboard."""
    resp = authenticated_student.get("/student/dashboard")
    assert resp.status_code == 200
    assert b"Demo Student" in resp.data or b"Placement Readiness" in resp.data


def test_student_profile_update_external_handles(authenticated_student, app):
    """Test updating GitHub, LinkedIn, portfolio handles and headline on student profile."""
    update_data = {
        "headline": "Senior Full-Stack & Distributed Systems Architect",
        "bio": "Building scalable platforms with Python, FastAPI, and Next.js.",
        "github_url": "https://github.com/torvalds",
        "linkedin_url": "https://linkedin.com/in/linustorvalds",
        "portfolio_url": "https://torvalds.kernel.org",
        "target_role": "Full Stack Developer"
    }

    resp = authenticated_student.post("/student/profile", data=update_data, follow_redirects=True)
    assert resp.status_code == 200

    with app.app_context():
        user = User.query.filter_by(email="student@demo.com").first()
        student = user.student_profile
        assert student.headline == "Senior Full-Stack & Distributed Systems Architect"
        assert student.github_url == "https://github.com/torvalds"
        assert student.linkedin_url == "https://linkedin.com/in/linustorvalds"
        assert student.portfolio_url == "https://torvalds.kernel.org"


def test_student_github_sync_api(authenticated_student):
    """Test GitHub telemetry enrichment API."""
    resp = authenticated_student.post("/student/api/github/sync", json={
        "github_url": "https://github.com/octocat"
    })
    assert resp.status_code == 200
    data = resp.get_json()
    assert data.get("success") is True
    assert "github_data" in data or "username" in data


def test_skill_gap_page_render(authenticated_student):
    """Test rendering skill gaps & adaptive roadmap page."""
    resp = authenticated_student.get("/student/ai/skill-gap")
    assert resp.status_code == 200
    assert b"Target Benchmark" in resp.data
    assert b"Verified Matched Skills" in resp.data
    assert b"Critical Missing Competencies" in resp.data


def test_skill_gap_dynamic_analyze_api(authenticated_student):
    """Test synchronous AI skill gap analysis API returns 6 dynamic UI blocks."""
    resp = authenticated_student.post("/student/ai/api/skill-gap/analyze", json={
        "target_role": "Full Stack Developer"
    })
    assert resp.status_code == 200
    data = resp.get_json()

    assert data.get("success") is True
    # 1. Target Benchmark & Percentage
    assert "benchmark_match_ratio" in data or "match_percentage" in data
    # 2. Verified Matched Skills
    assert "verified_matched_skills" in data or "matched_skills" in data
    # 3. Critical Missing Competencies
    assert "critical_missing_competencies" in data or "missing_skills" in data
    # 4. Recruiter Urgency Diagnostic
    assert "market_urgency_summary" in data
    # 5. Interview Probing Questions
    assert "probing_questions" in data or "practice_interview_questions" in data
    # 6. Curriculum / Roadmap Timeline
    assert "curriculum" in data or "roadmap" in data


def test_roadmap_task_toggle_and_proof_submission(authenticated_student):
    """Test toggling roadmap task and submitting proof-of-work link."""
    # First get or generate active roadmap
    resp = authenticated_student.get("/student/ai/api/roadmap")
    assert resp.status_code == 200
    roadmap_data = resp.get_json()
    roadmap_id = roadmap_data.get("id")
    assert roadmap_id is not None

    milestones = roadmap_data.get("milestones", [])
    assert len(milestones) > 0
    first_task = milestones[0]["action_tasks"][0]
    task_id = first_task["id"]

    # Toggle task
    toggle_resp = authenticated_student.post("/student/ai/api/roadmap/task/toggle", json={
        "roadmap_id": roadmap_id,
        "task_id": task_id
    })
    assert toggle_resp.status_code == 200
    tdata = toggle_resp.get_json()
    assert tdata.get("success") is True
    assert "progress_percentage" in tdata

    # Submit Proof of Work
    proof_resp = authenticated_student.post("/student/ai/api/roadmap/task/proof", json={
        "roadmap_id": roadmap_id,
        "task_id": task_id,
        "proof_url": "https://github.com/octocat/Hello-World/commit/7fd1a60b01f91b314f59955a4e4d4e80d8edf11d",
        "proof_notes": "Implemented CRUD operations with verified automated unit tests."
    })
    assert proof_resp.status_code == 200
    pdata = proof_resp.get_json()
    assert pdata.get("success") is True


def test_interview_simulator_page_and_api(authenticated_student):
    """Test AI Mock Interview Studio and session lifecycle."""
    resp = authenticated_student.get("/student/ai/interview-simulator")
    assert resp.status_code == 302

    # Start session
    start_resp = authenticated_student.post("/student/ai/api/interview/start", json={
        "role_title": "Full Stack Developer",
        "interview_type": "technical"
    })
    assert start_resp.status_code == 200
    session_data = start_resp.get_json()
    session_id = session_data.get("session_id")
    assert session_id is not None

    # Submit Answer
    ans_resp = authenticated_student.post("/student/ai/api/interview/submit", json={
        "session_id": session_id,
        "answer": "RESTful services use HTTP methods such as GET, POST, PUT, DELETE for idempotent resource representation. In contrast, GraphQL provides a single query endpoint with client-defined schema schemas."
    })
    assert ans_resp.status_code == 200
    ans_data = ans_resp.get_json()
    assert "evaluation" in ans_data
    # 4-axis scoring verification
    eval_metrics = ans_data["evaluation"]
    assert "technical_accuracy" in eval_metrics
    assert "communication_clarity" in eval_metrics


def test_resume_intelligence_page(authenticated_student):
    """Test Resume Intelligence ATS scoring page."""
    resp = authenticated_student.get("/student/ai/resume-intelligence")
    assert resp.status_code == 200
    assert b"Resume" in resp.data or b"ATS" in resp.data
