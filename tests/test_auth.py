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
    """Test student login and session setup, including role-tailored What's New release popup."""
    response = client.post("/login", data={
        "email": "student@demo.com",
        "password": "Student@123"
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b"student" in response.data.lower()
    # Verify What's New modal presence and auto-open trigger
    assert b"What&#39;s New in Glint" in response.data or b"What's New in Glint" in response.data
    assert b"Enhanced Student Interviews" in response.data
    assert b"Collapsible Sidebar &amp; Navigation" in response.data or b"Collapsible Sidebar & Navigation" in response.data
    # Verify student does NOT see admin database changes
    assert b"Admin Database Manager" not in response.data
    assert b"shouldShowFromServer = true" in response.data


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


def test_registration_disabled_and_redirects_to_login(client):
    """Test that public registration endpoint redirects to login since account creation is managed by admin."""
    # Test GET /register
    get_resp = client.get("/register", follow_redirects=False)
    assert get_resp.status_code == 302
    assert "/login" in get_resp.headers["Location"]

    # Test POST /register
    post_resp = client.post("/register", data={
        "email": "intruder@campus.edu",
        "password": "Password@123",
        "role": "STUDENT",
        "name": "Intruder Doe"
    }, follow_redirects=True)
    assert post_resp.status_code == 200
    assert b"Public account registration is disabled" in post_resp.data or b"disabled" in post_resp.data


def test_admin_edit_student_recruiter_company(client, app):
    """Test admin ability to edit students, recruiters, and companies via database manager API."""
    # Log in as admin
    client.post("/login", data={
        "email": "admin@placementiq.ai",
        "password": "Admin@123"
    }, follow_redirects=True)

    with app.app_context():
        student = Student.query.first()
        recruiter = Recruiter.query.first()
        company = Company.query.first()
        student_id = student.id
        recruiter_id = recruiter.id
        company_id = company.id

    # 1. Edit Student
    resp_student = client.post(f"/admin/api/database/students/{student_id}/update", json={
        "name": "Updated Student Name",
        "cgpa": "9.45",
        "target_role": "Lead Architect",
        "phone": "+91 99999 88888"
    })
    assert resp_student.status_code == 200
    assert resp_student.get_json()["success"] is True

    # 2. Edit Recruiter
    resp_recruiter = client.post(f"/admin/api/database/recruiters/{recruiter_id}/update", json={
        "name": "Updated Recruiter Lead",
        "designation": "VP of Talent",
        "phone": "+91 98888 77777"
    })
    assert resp_recruiter.status_code == 200
    assert resp_recruiter.get_json()["success"] is True

    # 3. Edit Company
    resp_company = client.post(f"/admin/api/database/companies/{company_id}/update", json={
        "name": "Updated Enterprise Corp",
        "industry": "Artificial Intelligence",
        "location": "Hyderabad, India"
    })
    assert resp_company.status_code == 200
    assert resp_company.get_json()["success"] is True

    # Verify changes in DB
    with app.app_context():
        updated_s = Student.query.get(student_id)
        assert updated_s.name == "Updated Student Name"
        assert updated_s.cgpa == 9.45

        updated_r = Recruiter.query.get(recruiter_id)
        assert updated_r.name == "Updated Recruiter Lead"
        assert updated_r.designation == "VP of Talent"

        updated_c = Company.query.get(company_id)
        assert updated_c.name == "Updated Enterprise Corp"
        assert updated_c.industry == "Artificial Intelligence"


def test_admin_create_student_and_recruiter(client, app):
    """Test admin ability to provision new student and recruiter accounts and verify their login capability."""
    # 1. Log in as Admin
    client.post("/login", data={
        "email": "admin@placementiq.ai",
        "password": "Admin@123"
    }, follow_redirects=True)

    # 2. Provision new Student via Database Manager API
    student_payload = {
        "name": "Admin Added Student",
        "roll_number": "ADMIN_STU_99",
        "email": "admin_student@campus.edu",
        "password": "Student@Password123",
        "department_id": 1,
        "cgpa": "8.85",
        "year": "4",
        "graduation_year": "2026",
        "target_role": "Cloud Architect",
        "phone": "+91 91111 22222"
    }
    resp_student = client.post("/admin/api/database/students/create", json=student_payload)
    assert resp_student.status_code == 201
    assert resp_student.get_json()["success"] is True

    # 3. Provision new Recruiter via Database Manager API
    with app.app_context():
        comp = Company.query.first()
        comp_id = comp.id

    recruiter_payload = {
        "name": "Admin Added Recruiter",
        "email": "admin_recruiter@partner.com",
        "password": "Recruiter@Password123",
        "company_id": comp_id,
        "designation": "Principal Recruiter",
        "phone": "+91 93333 44444"
    }
    resp_recruiter = client.post("/admin/api/database/recruiters/create", json=recruiter_payload)
    assert resp_recruiter.status_code == 201
    assert resp_recruiter.get_json()["success"] is True

    # 4. Verify the provisioned Student can log in successfully
    client.get("/logout", follow_redirects=True)
    login_stu = client.post("/login", data={
        "email": "admin_student@campus.edu",
        "password": "Student@Password123"
    }, follow_redirects=False)
    assert login_stu.status_code == 302
    assert "/student" in login_stu.headers["Location"]

    # 5. Verify the provisioned Recruiter can log in successfully
    client.get("/logout", follow_redirects=True)
    login_rec = client.post("/login", data={
        "email": "admin_recruiter@partner.com",
        "password": "Recruiter@Password123"
    }, follow_redirects=False)
    assert login_rec.status_code == 302
    assert "/recruiter" in login_rec.headers["Location"]


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
