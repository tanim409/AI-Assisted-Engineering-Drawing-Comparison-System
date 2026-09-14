"""
Quick smoke test for the auth API endpoints.
Run with: myenv\Scripts\python.exe test_auth.py
"""
import urllib.request
import urllib.error
import json
import time

BASE = "http://localhost:8000"

def post(path, body):
    req = urllib.request.Request(
        f"{BASE}{path}",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        r = urllib.request.urlopen(req)
        return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode())

def get(path, token=None):
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(f"{BASE}{path}", headers=headers)
    try:
        r = urllib.request.urlopen(req)
        return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode())

def delete(path, token=None):
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(f"{BASE}{path}", headers=headers, method="DELETE")
    try:
        r = urllib.request.urlopen(req)
        return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode())

def run_auth_smoke_tests():
    print("=" * 60)
    print("AUTH SMOKE TESTS")
    print("=" * 60)

    EMAIL = f"smoketest_{int(time.time())}@example.com"
    PASSWORD = "smoke1234"

    # 1. Register
    status, data = post("/auth/register", {"email": EMAIL, "password": PASSWORD})
    print(f"\n[1] POST /auth/register => {status}")
    assert status == 201, f"Expected 201, got {status}: {data}"
    v_token = data.get("verification_token")
    print(f"    verification_token: {v_token[:20]}...")

    # 2. Duplicate register
    status2, data2 = post("/auth/register", {"email": EMAIL, "password": PASSWORD})
    print(f"\n[2] POST /auth/register (duplicate) => {status2}")
    assert status2 == 400, f"Expected 400, got {status2}"

    # 3. Login before verification (should be rejected)
    status, data = post("/auth/login", {"email": EMAIL, "password": PASSWORD})
    print(f"\n[3] POST /auth/login (unverified) => {status}")
    assert status == 400, f"Expected 400, got {status}: {data}"
    assert "verify your email" in data.get("detail", "").lower()
    print("    Login correctly rejected prior to email verification [OK]")

    # 4. Verify email
    if v_token:
        status, data = post("/auth/verify-email", {"token": v_token})
        print(f"\n[4] POST /auth/verify-email => {status}")
        assert status == 200, f"Expected 200, got {status}: {data}"
        print(f"    {data['message']}")

    # 5. Login after verification (should succeed)
    status, data = post("/auth/login", {"email": EMAIL, "password": PASSWORD})
    print(f"\n[5] POST /auth/login (verified) => {status}")
    assert status == 200, f"Expected 200, got {status}: {data}"
    token = data["access_token"]
    print(f"    access_token: {token[:30]}...")

    # 6. GET /auth/me after verification
    status, data = get("/auth/me", token)
    print(f"\n[6] GET /auth/me => {status}")
    assert status == 200, f"Expected 200, got {status}"
    assert data["email_verified"] == True, "Expected email_verified=True"
    print(f"    email: {data['email']}, verified: {data['email_verified']} [OK]")

    # 7. Password reset flow
    status, data = post("/auth/request-password-reset", {"email": EMAIL})
    print(f"\n[7] POST /auth/request-password-reset => {status}")
    assert status == 200
    reset_token = data.get("reset_token")
    print(f"    reset_token: {reset_token[:20]}..." if reset_token else "    (no token)")

    if reset_token:
        NEW_PASS = "newpass5678"
        status, data = post("/auth/reset-password", {"token": reset_token, "new_password": NEW_PASS})
        print(f"\n[8] POST /auth/reset-password => {status}")
        assert status == 200, f"Expected 200, got {status}: {data}"
        print(f"    {data['message']}")

        # 9. Login with new password
        status, data = post("/auth/login", {"email": EMAIL, "password": NEW_PASS})
        print(f"\n[9] POST /auth/login (new password) => {status}")
        assert status == 200, f"Expected 200, got {status}: {data}"
        token = data["access_token"]
        print(f"    Login OK with new password [OK]")

    # 10. Unauthorized access
    status, data = get("/auth/me")
    print(f"\n[10] GET /auth/me (no token) => {status}")
    assert status == 403, f"Expected 403, got {status}"
    print(f"     Correctly blocked [OK]")

    # 11. Drawings endpoint requires auth
    status, data = get("/api/drawings")
    print(f"\n[11] GET /api/drawings (no token) => {status}")
    assert status in (401, 403), f"Expected 401/403, got {status}"
    print(f"     Correctly blocked [OK]")

    # 12. Delete account
    status, data = delete("/auth/me", token)
    print(f"\n[12] DELETE /auth/me => {status}")
    assert status == 200, f"Expected 200, got {status}: {data}"
    print(f"    {data['message']}")

    # 13. Login after deletion should fail
    status, data = post("/auth/login", {"email": EMAIL, "password": NEW_PASS if reset_token else PASSWORD})
    print(f"\n[13] POST /auth/login (deleted account) => {status}")
    assert status == 401, f"Expected 401, got {status}"
    print(f"     Correctly rejected [OK]")

    print("\n" + "=" * 60)
    print("ALL TESTS PASSED [OK]")
    print("=" * 60)

if __name__ == "__main__":
    run_auth_smoke_tests()
