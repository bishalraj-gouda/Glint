import requests

BASE_URL = "http://127.0.0.1:5000"

def test_live_server():
    s = requests.Session()

    print("1. Testing Landing Page...")
    r = s.get(f"{BASE_URL}/")
    assert r.status_code == 200, f"Landing failed: {r.status_code}"
    assert "campus talent" in r.text or "Glint" in r.text
    print("   [OK] Landing page rendered successfully.")

    print("2. Testing Login Page...")
    r = s.get(f"{BASE_URL}/login")
    assert r.status_code == 200
    assert "Welcome to Glint" in r.text or "Sign In" in r.text
    print("   [OK] Login page rendered successfully.")

    print("3. Testing Register Page...")
    r = s.get(f"{BASE_URL}/register")
    assert r.status_code == 200
    assert "Create Your Account" in r.text
    print("   [OK] Register page rendered successfully.")

    print("4. Testing Protected Route Redirect (Unauthenticated)...")
    r = s.get(f"{BASE_URL}/student/dashboard", allow_redirects=False)
    assert r.status_code in (301, 302)
    print("   [OK] Unauthenticated route redirected correctly.")

    print("5. Testing Student Login & Dashboard Access...")
    r = s.post(f"{BASE_URL}/login", data={
        "email": "rahul.sharma@campus.edu",
        "password": "Student@123"
    }, allow_redirects=True)
    assert r.status_code == 200
    assert "Rahul Sharma" in r.text
    assert "Open Drives" in r.text or "Active Campus" in r.text
    print("   [OK] Student logged in and dashboard rendered.")

    print("6. Testing Student Unauthorized Access to Admin...")
    r = s.get(f"{BASE_URL}/admin/dashboard")
    assert r.status_code == 403
    assert "Access Forbidden" in r.text or "403" in r.text
    print("   [OK] Student role restriction strictly enforced.")

    print("7. Testing Logout...")
    r = s.get(f"{BASE_URL}/logout", allow_redirects=True)
    assert "You have been safely logged out" in r.text
    print("   [OK] Logout successful.")

    print("8. Testing Recruiter Login & Dashboard Access...")
    r = s.post(f"{BASE_URL}/login", data={
        "email": "priya.recruiter@nexustech.com",
        "password": "Recruiter@123"
    }, allow_redirects=True)
    assert r.status_code == 200
    assert "Nexus Technologies" in r.text
    assert "Active Job Drives" in r.text
    print("   [OK] Recruiter logged in and dashboard rendered.")

    print("9. Testing Admin Login & Dashboard Access...")
    s2 = requests.Session()
    r = s2.post(f"{BASE_URL}/login", data={
        "email": "admin@placementiq.ai",
        "password": "Admin@123"
    }, allow_redirects=True)
    assert r.status_code == 200
    assert "Placement Command Dashboard" in r.text
    assert "Placement Rate" in r.text
    print("   [OK] Admin logged in and command dashboard rendered.")

    print("10. Testing 404 Page...")
    r = s.get(f"{BASE_URL}/non-existent-route-999")
    assert r.status_code == 404
    assert "404" in r.text
    print("   [OK] Custom 404 page rendered.")

    print("\nALL LIVE END-TO-END SERVER CHECKS PASSED PERFECTLY!")


if __name__ == "__main__":
    test_live_server()
