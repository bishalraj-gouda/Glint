"""
Test suite verifying all PlacementIQ AI navigation routes, HTTP GET/POST handling,
sidebar link resolution, and seamless rendering without database OperationalErrors.
"""
import pytest
from app import create_app
from extensions import db
from models.user import User
from models.student import Student
from models.recruiter import Recruiter
from data.seed_data import seed_database


@pytest.fixture
def app():
    """Create test application using SQLite in-memory database."""
    app = create_app("testing")
    with app.app_context():
        db.create_all()
        seed_database()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


def login_student(client):
    """Authenticate Rahul Sharma (Student)."""
    return client.post("/login", data={
        "email": "rahul.sharma@campus.edu",
        "password": "Student@123"
    }, follow_redirects=True)


def login_recruiter(client):
    """Authenticate Priya Recruiter (Nexus Technologies)."""
    return client.post("/login", data={
        "email": "priya.recruiter@nexustech.com",
        "password": "Recruiter@123"
    }, follow_redirects=True)


# ==============================================================================
# 1. Unauthenticated Security Checks (Must redirect to /login)
# ==============================================================================

@pytest.mark.parametrize("route", [
    "/student/ai/career-twin",
    "/student/career-twin",
    "/student/ai/skill-gap",
    "/student/skill-gap",
    "/student/ai/interview-simulator",
    "/student/interview-simulator",
    "/student/ai/resume-intelligence",
    "/student/resume-intelligence",
    "/recruiter/ai/candidate-matcher",
    "/recruiter/candidate-matcher",
])
def test_unauthenticated_routes_redirect(client, route):
    """Verify unauthenticated access to all 5 AI modules is protected."""
    res = client.get(route)
    assert res.status_code == 302
    assert "/login" in res.headers["Location"]


# ==============================================================================
# 2. Student Portal Routes Verification (GET and POST)
# ==============================================================================

def test_student_career_twin_routes(client):
    """Verify /student/ai/career-twin and /student/career-twin redirect cleanly to dashboard."""
    login_student(client)

    # Test /student/ai/career-twin (GET) redirects
    res1 = client.get("/student/ai/career-twin")
    assert res1.status_code == 302

    # Test /student/career-twin (GET) redirects
    res2 = client.get("/student/career-twin")
    assert res2.status_code == 302


def test_student_skill_gap_routes(client):
    """Verify /student/ai/skill-gap and /student/skill-gap render properly."""
    login_student(client)

    # Test /student/ai/skill-gap (GET)
    res1 = client.get("/student/ai/skill-gap")
    assert res1.status_code == 200
    assert b"Skill Gap" in res1.data or b"Adaptive Roadmap" in res1.data

    # Test /student/skill-gap (GET)
    res2 = client.get("/student/skill-gap")
    assert res2.status_code == 200
    assert b"Skill Gap" in res2.data or b"Adaptive Roadmap" in res2.data

    # Test POST method with target role selection
    res_post = client.post("/student/ai/skill-gap", data={"role": "Data Science & AI Engineer"})
    assert res_post.status_code == 200
    assert b"Data Science" in res_post.data or b"Skill Gap" in res_post.data


def test_student_interview_simulator_routes(client):
    """Verify /student/ai/interview-simulator and /student/interview-simulator redirect cleanly to dashboard."""
    login_student(client)

    # Test /student/ai/interview-simulator (GET) redirects
    res1 = client.get("/student/ai/interview-simulator")
    assert res1.status_code == 302

    # Test /student/interview-simulator (GET) redirects
    res2 = client.get("/student/interview-simulator")
    assert res2.status_code == 302


def test_student_resume_intelligence_routes(client):
    """Verify /student/ai/resume-intelligence and /student/resume-intelligence render properly."""
    login_student(client)

    # Test /student/ai/resume-intelligence (GET)
    res1 = client.get("/student/ai/resume-intelligence")
    assert res1.status_code == 200
    assert b"Resume Intelligence" in res1.data

    # Test /student/resume-intelligence (GET)
    res2 = client.get("/student/resume-intelligence")
    assert res2.status_code == 200
    assert b"Resume Intelligence" in res2.data

    # Test POST with resume text audit
    sample_text = "John Doe | Python, Flask, SQL, Git, REST APIs, Docker | B.Tech Computer Science CGPA 8.5"
    res_post = client.post("/student/ai/resume-intelligence", data={"resume_text": sample_text}, follow_redirects=True)
    assert res_post.status_code == 200
    assert b"Resume Intelligence" in res_post.data


# ==============================================================================
# 3. Recruiter Portal Routes Verification (GET and POST)
# ==============================================================================

def test_recruiter_candidate_matcher_routes(client):
    """Verify /recruiter/ai/candidate-matcher and /recruiter/candidate-matcher render properly."""
    login_recruiter(client)

    # Test /recruiter/ai/candidate-matcher (GET)
    res1 = client.get("/recruiter/ai/candidate-matcher")
    assert res1.status_code == 200
    assert b"Candidate Matching" in res1.data or b"Matching" in res1.data

    # Test /recruiter/candidate-matcher (GET)
    res2 = client.get("/recruiter/candidate-matcher")
    assert res2.status_code == 200
    assert b"Candidate Matching" in res2.data or b"Matching" in res2.data

    # Test filter parameters and POST submission
    res_post = client.post("/recruiter/ai/candidate-matcher", data={
        "min_cgpa": "7.5",
        "department": "CSE"
    })
    assert res_post.status_code == 200
    assert b"Candidate Matching" in res_post.data


# ==============================================================================
# 4. Sidebar Link Integrity Verification in Templates
# ==============================================================================

def test_student_sidebar_navigation_links(client):
    """Verify student dashboard template renders exact active routes for all AI modules in sidebar."""
    login_student(client)
    res = client.get("/student/dashboard")
    assert res.status_code == 200

    html = res.data.decode("utf-8")
    assert "/student/jobs" in html
    assert "/student/ai/skill" in html
    assert "/student/ai/resume-intelligence" in html


def test_recruiter_sidebar_navigation_links(client):
    """Verify recruiter dashboard template renders exact active routes for AI matcher in sidebar."""
    login_recruiter(client)
    res = client.get("/recruiter/dashboard")
    assert res.status_code == 200

    html = res.data.decode("utf-8")
    assert "/recruiter/ai/matching" in html or "/recruiter/ai/candidate-matcher" in html


# ==============================================================================
# 5. Admin Database Explorer & Manager Verification
# ==============================================================================

def login_admin(client):
    """Helper to authenticate administrator session."""
    from models.user import User, db
    user = User.query.filter_by(role="admin").first()
    if not user:
        user = User(email="admin@glint.edu", role="admin")
        user.set_password("Admin@123")
        db.session.add(user)
        db.session.commit()

    with client.session_transaction() as sess:
        sess["user_id"] = user.id
        sess["user_role"] = "admin"
        sess["user_email"] = user.email
        sess["session_display_name"] = "Admin TPO"
    return user


def test_admin_database_manager_views(client):
    """Verify admin can view, switch tables, and inspect records across database."""
    login_admin(client)

    # 1. Test main database explorer (defaults to students table)
    res = client.get("/admin/database")
    assert res.status_code == 200
    assert b"Database & Entity Manager" in res.data
    assert b"Students" in res.data

    # 2. Test switching to other entity tables
    for tbl in ["recruiters", "companies", "jobs", "applications", "placements", "departments", "skills", "users"]:
        res_tbl = client.get(f"/admin/database?table={tbl}")
        assert res_tbl.status_code == 200
        assert b"Directory" in res_tbl.data

    # 2b. Test recruiter table explicitly has Password column
    res_rec = client.get("/admin/database?table=recruiters")
    assert res_rec.status_code == 200
    assert b"Password" in res_rec.data
    assert b"Recruiter@123" in res_rec.data

    # 3. Test CSV Export endpoint
    res_csv = client.get("/admin/database/export/students")
    assert res_csv.status_code == 200
    assert res_csv.mimetype == "text/csv"
    assert b"Roll Number" in res_csv.data

    # 3b. Test CSV Export for recruiters includes Password column
    res_rec_csv = client.get("/admin/database/export/recruiters")
    assert res_rec_csv.status_code == 200
    assert b"Password" in res_rec_csv.data

    # 4. Verify sidebar has database manager link
    assert b"/admin/database" in res.data

    # 5. Test toggle status API (e.g. for jobs)
    from models.job import Job
    job = Job.query.first()
    if job:
        orig_status = job.status
        res_toggle = client.post(f"/admin/api/database/jobs/{job.id}/toggle-status")
        assert res_toggle.status_code == 200
        assert res_toggle.json["success"] is True

    # 6. Test delete protection (cannot delete own admin user)
    user = User.query.filter_by(role="admin").first()
    res_del_self = client.post(f"/admin/api/database/users/{user.id}/delete")
    assert res_del_self.status_code == 400
    assert b"Cannot delete your own" in res_del_self.data

