"""
Recruiter Portal, Workflows & Production AI Tools Integration Tests.
Verifies Recruiter Dashboard, Opportunity Posting, Pipeline Stage Transitions,
Google Calendar Interview Scheduling, Candidate Semantic Matching, and Batch Resume Parser.
"""
import io
import pytest
from datetime import date, timedelta
from app import create_app
from extensions import db
from models.user import User
from models.recruiter import Recruiter
from models.company import Company
from models.job import Job
from models.student import Student
from models.application import Application
from models.interview import Interview
from models.role import ROLE_RECRUITER, ROLE_STUDENT
from data.seed_data import seed_database


@pytest.fixture
def app():
    """Create test application context with seeded database."""
    test_app = create_app("testing")
    with test_app.app_context():
        db.create_all()
        seed_database()

        if not User.query.filter_by(email="recruiter@demo.com").first():
            ru = User(email="recruiter@demo.com", role=ROLE_RECRUITER)
            ru.set_password("Recruiter@123")
            db.session.add(ru)
            db.session.flush()
            comp = Company.query.first()
            r = Recruiter(user_id=ru.id, company_id=comp.id if comp else 1, name="Demo Recruiter", designation="Talent Lead")
            db.session.add(r)
            db.session.commit()

        yield test_app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def authenticated_recruiter(client):
    """Logs in demo recruiter before tests."""
    client.post("/login", data={
        "email": "recruiter@demo.com",
        "password": "Recruiter@123"
    }, follow_redirects=True)
    return client


def test_recruiter_dashboard(authenticated_recruiter):
    """Test recruiter dashboard KPI metrics and job summary."""
    resp = authenticated_recruiter.get("/recruiter/dashboard")
    assert resp.status_code == 200
    assert b"Recruitment Overview" in resp.data or b"Active Jobs" in resp.data or b"Dashboard" in resp.data


def test_post_job_flow(authenticated_recruiter, app):
    """Test posting a new campus recruitment requisition."""
    job_payload = {
        "title": "Cloud Infrastructure Architect",
        "role_category": "Cloud & Infrastructure",
        "description": "Design and automate AWS/Kubernetes microservices architecture for high availability.",
        "min_cgpa": "7.5",
        "salary_min": "10.0",
        "salary_max": "16.0",
        "location": "Bangalore / Hybrid",
        "experience_level": "Fresher (0-1 yrs)",
        "deadline": (date.today() + timedelta(days=45)).strftime("%Y-%m-%d"),
        "custom_skills": "AWS, Docker, Kubernetes, Terraform, Linux"
    }

    resp = authenticated_recruiter.post("/recruiter/post-job", data=job_payload, follow_redirects=True)
    assert resp.status_code == 200

    with app.app_context():
        posted = Job.query.filter_by(title="Cloud Infrastructure Architect").first()
        assert posted is not None
        assert posted.min_cgpa == 7.5
        assert posted.salary_max == 16.0


def test_candidate_pipeline_and_status_update(authenticated_recruiter, app):
    """Test candidate pipeline view and advancing candidate through stages."""
    with app.app_context():
        app_record = Application.query.first()
        assert app_record is not None
        app_id = app_record.id

    # Pipeline view
    resp = authenticated_recruiter.get("/recruiter/candidates")
    assert resp.status_code == 200

    # Advance stage to 'interview'
    stage_resp = authenticated_recruiter.post(f"/recruiter/candidates/{app_id}/status", data={
        "status": "interview"
    }, follow_redirects=True)
    assert stage_resp.status_code == 200

    with app.app_context():
        updated_app = db.session.get(Application, app_id)
        assert updated_app.status == "interview"


def test_interview_scheduling_and_google_calendar_url(authenticated_recruiter, app):
    """Test interview round scheduling and Google Calendar link generation."""
    with app.app_context():
        app_record = Application.query.first()
        app_id = app_record.id

    sched_data = {
        "application_id": app_id,
        "scheduled_date": (date.today() + timedelta(days=3)).strftime("%Y-%m-%d"),
        "scheduled_time": "02:30 PM",
        "interview_type": "technical",
        "round_number": 1,
        "meeting_link_or_venue": "https://meet.google.com/placementiq-demo",
        "interviewer_name": "Demo Recruiter (Lead Tech Panel)"
    }

    resp = authenticated_recruiter.post("/recruiter/schedule", data=sched_data, follow_redirects=True)
    assert resp.status_code == 200

    with app.app_context():
        interview = Interview.query.filter_by(application_id=app_id).order_by(Interview.id.desc()).first()
        assert interview is not None
        assert interview.scheduled_time == "02:30 PM"
        
        # Verify Google Calendar link format
        cal_url = interview.google_calendar_url
        assert "calendar.google.com/calendar/render" in cal_url
        assert "action=TEMPLATE" in cal_url
        assert "Interview" in cal_url


def test_recruiter_semantic_candidate_matcher(authenticated_recruiter):
    """Test natural language vector candidate search."""
    resp = authenticated_recruiter.post("/recruiter/ai/api/semantic-match", json={
        "query": "Find Python backend candidates skilled in FastAPI, SQL, and Docker microservices"
    })
    assert resp.status_code == 200
    data = resp.get_json()
    assert data.get("success") is True
    assert "candidates" in data
    assert len(data["candidates"]) > 0
    top_candidate = data["candidates"][0]
    assert "semantic_match_score" in top_candidate


def test_batch_resume_parser_view_and_api(authenticated_recruiter):
    """Test Batch Resume Parser page and multi-file parsing API."""
    # View render redirects to candidate matching
    view_resp = authenticated_recruiter.get("/recruiter/batch-resume-parser")
    assert view_resp.status_code == 302

    # Multi-file upload test
    resume1_bytes = io.BytesIO(b"""
    Alex Rivera
    alex.rivera@example.com | +1 (555) 234-5678 | San Francisco, CA
    Full Stack Software Engineer
    SKILLS: Python, React, TypeScript, FastAPI, PostgreSQL, Docker, AWS, Git
    EXPERIENCE:
    Software Engineer - Cloud Systems (2022 - Present)
    Built high-throughput REST APIs and containerized microservices.
    """)
    resume1_bytes.name = "alex_rivera_resume.txt"

    resume2_bytes = io.BytesIO(b"""
    Taylor Chen
    taylor.chen@example.com | (555) 987-6543
    Machine Learning & Data Engineer
    SKILLS: Python, PyTorch, TensorFlow, Scikit-Learn, SQL, Pandas, NumPy
    EDUCATION:
    B.S. in Computer Science & Data Science
    """)
    resume2_bytes.name = "taylor_chen_resume.txt"

    upload_data = {
        "resumes": [(resume1_bytes, "alex_rivera_resume.txt"), (resume2_bytes, "taylor_chen_resume.txt")]
    }

    parse_resp = authenticated_recruiter.post("/recruiter/api/batch-parse-resumes", data=upload_data, content_type="multipart/form-data")
    assert parse_resp.status_code == 200
    parse_data = parse_resp.get_json()

    assert parse_data.get("success") is True
    assert parse_data.get("total_files") == 2
    candidates = parse_data.get("candidates", [])
    assert len(candidates) == 2
    assert "Python" in candidates[0].get("skills", [])
