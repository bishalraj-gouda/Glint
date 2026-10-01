"""
Authentication & Role-Based Access Control (RBAC) Integration Tests.
Verifies Flask-Login, registration, login/logout, password hashing, and role protections.
"""
import pytest
from app import create_app
from extensions import db
from models.user import User
from models.student import Student
from models.recruiter import Recruiter
from models.company import Company
from models.role import ROLE_STUDENT, ROLE_RECRUITER, ROLE_ADMIN
from data.seed_data import seed_database


@pytest.fixture
def app():
    """Create test application context with in-memory database."""
    test_app = create_app("testing")
    with test_app.app_context():
        db.create_all()
        seed_database()
        
        # Ensure demo accounts exist
        if not User.query.filter_by(email="student@demo.com").first():
            u = User(email="student@demo.com", role=ROLE_STUDENT)
            u.set_password("Student@123")
            db.session.add(u)
            db.session.flush()
            s = Student(user_id=u.id, name="Demo Student", roll_number="DEMO-TEST", department_id=1, year=4, cgpa=8.5, target_role="Full Stack Developer")
            db.session.add(s)

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


def test_password_hashing(app):
    """Ensure user passwords are encrypted with bcrypt/werkzeug and never stored plain."""
    with app.app_context():
        student = User.query.filter_by(email="student@demo.com").first()
        assert student is not None
        assert student.password_hash != "Student@123"
        assert student.check_password("Student@123") is True
        assert student.check_password("WrongPassword") is False


def test_login_student_success(client):
    """Test student login and session setup."""
    response = client.post("/login", data={
        "email": "student@demo.com",
        "password": "Student@123"
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b"student" in response.data.lower()


def test_login_recruiter_success(client):
    """Test recruiter login and dashboard redirection."""
    response = client.post("/login", data={
        "email": "recruiter@demo.com",
        "password": "Recruiter@123"
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b"recruiter" in response.data.lower() or b"recruitment" in response.data.lower()


def test_login_invalid_credentials(client):
    """Test login failure on bad password."""
    response = client.post("/login", data={
        "email": "student@demo.com",
        "password": "IncorrectPassword"
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b"Invalid email or password" in response.data or b"danger" in response.data


def test_student_registration_flow(client, app):
    """Test registering a new student user."""
    reg_data = {
        "email": "newstudent@campus.edu",
        "password": "NewStudent@123",
        "confirm_password": "NewStudent@123",
        "role": "STUDENT",
        "name": "Jane Doe",
        "roll_number": "22CS999",
        "department_id": 1,
        "year": 3,
        "cgpa": 8.9,
        "target_role": "AI Engineer"
    }
    response = client.post("/register", data=reg_data, follow_redirects=True)
    assert response.status_code == 200

    with app.app_context():
        user = User.query.filter_by(email="newstudent@campus.edu").first()
        assert user is not None
        assert user.role.upper() == ROLE_STUDENT
        assert user.student_profile is not None
        assert user.student_profile.name == "Jane Doe"


def test_recruiter_registration_flow(client, app):
    """Test registering a new recruiter user."""
    reg_data = {
        "email": "newrecruiter@techcorp.com",
        "password": "Recruiter@123",
        "confirm_password": "Recruiter@123",
        "role": "RECRUITER",
        "name": "Alex Smith",
        "company_name": "TechCorp Innovations",
        "designation": "Hiring Director",
        "phone": "+91 91234 56789"
    }
    response = client.post("/register", data=reg_data, follow_redirects=True)
    assert response.status_code == 200

    with app.app_context():
        user = User.query.filter_by(email="newrecruiter@techcorp.com").first()
        assert user is not None
        assert user.role.upper() == ROLE_RECRUITER
        assert user.recruiter_profile is not None
        assert user.recruiter_profile.name == "Alex Smith"


def test_unauthorized_redirects_to_login(client):
    """Unauthenticated users should be redirected to login when accessing protected pages."""
    resp = client.get("/student/dashboard", follow_redirects=False)
    assert resp.status_code in (302, 401)
    if resp.status_code == 302:
        assert "/login" in resp.headers["Location"]


def test_rbac_student_blocked_from_recruiter_routes(client):
    """A student logged in must receive 403 Forbidden when accessing recruiter portal."""
    client.post("/login", data={
        "email": "student@demo.com",
        "password": "Student@123"
    }, follow_redirects=True)

    resp = client.get("/recruiter/dashboard")
    assert resp.status_code == 403


def test_rbac_recruiter_blocked_from_student_routes(client):
    """A recruiter logged in must receive 403 Forbidden when accessing student portal."""
    client.post("/login", data={
        "email": "recruiter@demo.com",
        "password": "Recruiter@123"
    }, follow_redirects=True)

    resp = client.get("/student/profile")
    assert resp.status_code == 403


def test_logout_clears_session(client):
    """Test that logout terminates session and blocks further protected access."""
    client.post("/login", data={
        "email": "student@demo.com",
        "password": "Student@123"
    }, follow_redirects=True)

    # Logout
    logout_resp = client.get("/logout", follow_redirects=True)
    assert logout_resp.status_code == 200

    # Protected page should now redirect to login
    prot_resp = client.get("/student/dashboard", follow_redirects=False)
    assert prot_resp.status_code in (302, 401)
