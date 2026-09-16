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

    # 1. Invalid domain format register (incomplete domain without TLD)
    status_inv, data_inv = post("/auth/register", {"email": "user@gmail", "password": PASSWORD})
    print(f"\n[1] POST /auth/register (invalid domain user@gmail) => {status_inv}")
    assert status_inv in (400, 422), f"Expected 400/422, got {status_inv}: {data_inv}"
    print("    Invalid email domain correctly rejected [OK]")

    # 2. Register valid user (should succeed and return token immediately)
    status, data = post("/auth/register", {"email": EMAIL, "password": PASSWORD})
    print(f"\n[2] POST /auth/register => {status}")
    assert status == 201, f"Expected 201, got {status}: {data}"
    reg_token = data.get("access_token")
    assert reg_token, "Expected access_token in registration response"
    print(f"    access_token: {reg_token[:20]}...")

    # 3. Duplicate register (should be rejected with clear message)
    status2, data2 = post("/auth/register", {"email": EMAIL, "password": PASSWORD})
    print(f"\n[3] POST /auth/register (duplicate) => {status2}")
    assert status2 == 400, f"Expected 400, got {status2}: {data2}"
    assert "already exists" in data2.get("detail", "").lower()
    print("    Duplicate email registration correctly rejected [OK]")

    # 4. Immediate Login without verification (should succeed)
    status, data = post("/auth/login", {"email": EMAIL, "password": PASSWORD})
    print(f"\n[4] POST /auth/login => {status}")
    assert status == 200, f"Expected 200, got {status}: {data}"
    token = data["access_token"]
    print(f"    access_token: {token[:30]}...")

    # 5. GET /auth/me
    status, data = get("/auth/me", token)
    print(f"\n[5] GET /auth/me => {status}")
    assert status == 200, f"Expected 200, got {status}"
    assert data["email_verified"] == True, "Expected email_verified=True"
    print(f"    email: {data['email']}, verified: {data['email_verified']} [OK]")

    # 6. Unauthorized access
    status, data = get("/auth/me")
    print(f"\n[6] GET /auth/me (no token) => {status}")
    assert status in (401, 403), f"Expected 401/403, got {status}"
    print(f"     Correctly blocked [OK]")

    # 7. Delete account
    status, data = delete("/auth/me", token)
    print(f"\n[7] DELETE /auth/me => {status}")
    assert status == 200, f"Expected 200, got {status}: {data}"
    print(f"    {data['message']}")

    # 8. Login after deletion should fail
    status, data = post("/auth/login", {"email": EMAIL, "password": PASSWORD})
    print(f"\n[8] POST /auth/login (deleted account) => {status}")
    assert status == 401, f"Expected 401, got {status}"
    print(f"     Correctly rejected [OK]")

    print("\n" + "=" * 60)
    print("ALL TESTS PASSED [OK]")
    print("=" * 60)

if __name__ == "__main__":
    run_auth_smoke_tests()
