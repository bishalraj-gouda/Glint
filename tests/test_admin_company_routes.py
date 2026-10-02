"""
Tests for Admin Partner Company Onboarding & Management module.
Verifies GET /admin/companies/add, POST HTML form onboarding,
POST /admin/api/companies/create AJAX endpoint, duplicate checks,
and recruiter liaison provisioning.
"""
import pytest
from app import create_app
from extensions import db
from models.user import User
from models.company import Company
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


def login_admin(client):
    """Authenticate administrator session."""
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


def test_add_company_unauthenticated_redirect(client):
    """Verify unauthenticated requests redirect to login."""
    res = client.get("/admin/companies/add")
    assert res.status_code == 302
    assert "/login" in res.headers["Location"]


def test_add_company_view_render(client):
    """Verify admin can view the Add Partner Company page."""
    login_admin(client)
    res = client.get("/admin/companies/add")
    assert res.status_code == 200
    assert b"Onboard Partner Company" in res.data
    assert b"Company Fundamentals" in res.data
    assert b"Live Card Preview" in res.data


def test_add_company_form_submission(client):
    """Verify admin can register a partner company via HTML form."""
    login_admin(client)
    res = client.post("/admin/companies/add", data={
        "name": "Acme Robotics Corp",
        "industry": "Artificial Intelligence",
        "location": "Bangalore",
        "website": "https://acmerobotics.example.com",
        "logo_url": "https://acme.example.com/logo.png",
        "description": "Next-generation autonomous robotics and AI systems."
    }, follow_redirects=True)

    assert res.status_code == 200
    assert b"Acme Robotics Corp" in res.data

    # Verify company exists in database
    comp = Company.query.filter_by(name="Acme Robotics Corp").first()
    assert comp is not None
    assert comp.industry == "Artificial Intelligence"
    assert comp.location == "Bangalore"
    assert comp.website == "https://acmerobotics.example.com"


def test_add_company_duplicate_prevention(client):
    """Verify duplicate company names are prevented."""
    login_admin(client)
    # Nexus Technologies already exists in seed data
    res = client.post("/admin/companies/add", data={
        "name": "Nexus Technologies",
        "industry": "Technology",
    }, follow_redirects=True)

    assert res.status_code == 200
    assert b"already exists" in res.data


def test_api_create_company_ajax(client):
    """Verify AJAX JSON endpoint registers company and returns JSON."""
    login_admin(client)
    res = client.post("/admin/api/companies/create", json={
        "name": "HyperScale Labs",
        "industry": "SaaS & Cloud",
        "location": "Hyderabad",
        "website": "https://hyperscale.io",
        "description": "Cloud native infrastructure solutions."
    })

    assert res.status_code == 201
    json_data = res.get_json()
    assert json_data["success"] is True
    assert json_data["company"]["name"] == "HyperScale Labs"
    assert json_data["company"]["industry"] == "SaaS & Cloud"

    comp = Company.query.filter_by(name="HyperScale Labs").first()
    assert comp is not None


def test_add_company_with_recruiter_provisioning(client):
    """Verify creating a company simultaneously provisions the corporate recruiter liaison account."""
    login_admin(client)
    res = client.post("/admin/companies/add", data={
        "name": "FinEdge Capital Tech",
        "industry": "Fintech & Banking",
        "location": "Mumbai",
        "create_recruiter": "on",
        "recruiter_name": "Rohan Deshmukh",
        "recruiter_email": "rohan.d@finedge.com",
        "recruiter_designation": "Head of University Hiring",
        "recruiter_phone": "+91 9988776655",
        "recruiter_password": "FinEdgePass@123"
    }, follow_redirects=True)

    assert res.status_code == 200

    comp = Company.query.filter_by(name="FinEdge Capital Tech").first()
    assert comp is not None

    rec_user = User.query.filter_by(email="rohan.d@finedge.com").first()
    assert rec_user is not None
    assert rec_user.is_recruiter()
    assert rec_user.check_password("FinEdgePass@123")

    rec_profile = Recruiter.query.filter_by(user_id=rec_user.id).first()
    assert rec_profile is not None
    assert rec_profile.name == "Rohan Deshmukh"
    assert rec_profile.company_id == comp.id
    assert rec_profile.designation == "Head of University Hiring"
