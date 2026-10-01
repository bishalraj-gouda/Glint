import pytest
from app import create_app
from extensions import db
from models.user import User
from models.student import Student
from models.recruiter import Recruiter
from models.company import Company
from models.job import Job
from models.application import Application
from models.interview import Interview
from models.placement import Placement
from data.seed_data import seed_database


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


def test_seed_data_counts(test_app):
    """Verify minimum seed counts: 20 students, 5 recruiters, 5 companies, 10 jobs, 35+ skills."""
    with test_app.app_context():
        student_count = Student.query.count()
        recruiter_count = Recruiter.query.count()
        company_count = Company.query.count()
        job_count = Job.query.count()
        app_count = Application.query.count()
        interview_count = Interview.query.count()
        placement_count = Placement.query.count()

        assert student_count >= 20, f"Expected >= 20 students, found {student_count}"
        assert recruiter_count >= 5, f"Expected >= 5 recruiters, found {recruiter_count}"
        assert company_count >= 5, f"Expected >= 5 companies, found {company_count}"
        assert job_count >= 10, f"Expected >= 10 jobs, found {job_count}"
        assert app_count > 0, "Expected seed applications to exist"
        assert interview_count > 0, "Expected seed interviews to exist"
        assert placement_count > 0, "Expected seed placements to exist"


def test_password_hashing(test_app):
    """Verify that passwords are cryptographically hashed and never stored in plain text."""
    with test_app.app_context():
        admin = User.query.filter_by(email="admin@placementiq.ai").first()
        assert admin is not None
        assert admin.password_hash != "Admin@123"
        assert admin.check_password("Admin@123") is True
        assert admin.check_password("WrongPassword") is False


def test_login_student(client):
    """Verify student authentication and role session setup."""
    response = client.post("/login", data={
        "email": "rahul.sharma@campus.edu",
        "password": "Student@123"
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b"Rahul Sharma" in response.data
    assert b"Student Dashboard" in response.data or b"Placement Readiness" in response.data


def test_login_recruiter(client):
    """Verify recruiter authentication and redirect to recruiter portal."""
    response = client.post("/login", data={
        "email": "priya.recruiter@nexustech.com",
        "password": "Recruiter@123"
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b"Nexus Technologies" in response.data
    assert b"Active Job Drives" in response.data


def test_login_admin(client):
    """Verify admin authentication and redirect to placement command dashboard."""
    response = client.post("/login", data={
        "email": "admin@placementiq.ai",
        "password": "Admin@123"
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b"Placement Command Dashboard" in response.data
    assert b"Placement Rate" in response.data


def test_invalid_login(client):
    """Verify that bad credentials display an error."""
    response = client.post("/login", data={
        "email": "admin@placementiq.ai",
        "password": "WrongPassword999"
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b"Invalid email or password" in response.data


def test_logout(client):
    """Verify logout clears session and redirects to login."""
    # First log in
    client.post("/login", data={"email": "admin@placementiq.ai", "password": "Admin@123"})
    # Then logout
    response = client.get("/logout", follow_redirects=True)
    assert response.status_code == 200
    assert b"You have been safely logged out" in response.data


def test_role_restrictions_student_cannot_access_admin(client):
    """Ensure a student user gets a 403 Forbidden when accessing admin dashboard."""
    # Log in as Student
    client.post("/login", data={"email": "rahul.sharma@campus.edu", "password": "Student@123"})
    # Attempt to access Admin dashboard - should return 403
    response = client.get("/admin/dashboard")
    assert response.status_code == 403
    assert b"Access Forbidden" in response.data or b"403" in response.data


def test_role_restrictions_recruiter_cannot_access_student(client):
    """Ensure a recruiter user gets a 403 Forbidden when accessing student dashboard."""
    # Log in as Recruiter
    client.post("/login", data={"email": "priya.recruiter@nexustech.com", "password": "Recruiter@123"})
    # Attempt to access Student dashboard - should return 403
    response = client.get("/student/dashboard")
    assert response.status_code == 403
    assert b"Access Forbidden" in response.data or b"403" in response.data


def test_protected_routes_require_login(client):
    """Ensure unauthenticated users are redirected to login."""
    response = client.get("/student/dashboard", follow_redirects=True)
    assert response.status_code == 200
    assert b"Please log in" in response.data


def test_database_relationships(test_app):
    """Verify ORM relationships for students, jobs, skills, applications, interviews, and placements."""
    with test_app.app_context():
        rahul = Student.query.filter_by(roll_number="21CS001").first()
        assert rahul is not None
        assert rahul.department.code == "DS"
        assert len(rahul.student_skills) >= 5
        assert len(rahul.projects) >= 2

        # Check job relationship
        data_job = Job.query.filter(Job.title.ilike("%Data Analyst%")).first()
        assert data_job is not None
        assert data_job.company is not None
        assert len(data_job.job_skills) >= 4

        # Check that at least one application exists for the data job
        app = Application.query.filter_by(job_id=data_job.id).first()
        assert app is not None
        assert app.interviews is not None
