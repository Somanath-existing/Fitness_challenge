"""
Authentication & JWT integration tests:
- Password hashing with bcrypt
- Login endpoint POST /login
- Signing JWT with SECRET_KEY
- Returning bearer token and httpOnly cookie
- Subsequent requests with Authorization: Bearer <token>
- verify_token() and get_current_user Depends()
- 401 Unauthorized on missing, expired, and bad signature tokens
"""
import pytest
from datetime import timedelta
from conftest import client
from app.services.auth import create_access_token, hash_password, verify_password


class TestBcryptHashing:
    def test_hash_and_verify(self):
        pw = "MySecurePassword123!"
        hashed = hash_password(pw)
        assert hashed != pw
        assert hashed.startswith("$2")  # bcrypt prefix
        assert verify_password(pw, hashed) is True
        assert verify_password("WrongPassword", hashed) is False

    def test_verify_empty_or_none(self):
        assert verify_password("", "somehash") is False
        assert verify_password("pw", None) is False


class TestJWTFlow:
    def test_register_with_password_and_login(self):
        # 1. Register with password
        reg_res = client.post("/api/users", json={
            "first_name": "Test",
            "last_name": "User",
            "username": "testuser",
            "email": "test@example.com",
            "password": "SecretPassword123!",
        })
        assert reg_res.status_code == 201
        user_id = reg_res.json()["user_id"]

        # 2. POST /login with correct password
        login_res = client.post("/login", json={
            "identifier": "testuser",
            "password": "SecretPassword123!",
        })
        assert login_res.status_code == 200
        data = login_res.json()

        # Token returned in response body
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["user"]["user_id"] == user_id
        token = data["access_token"]

        # Cookie returned in Set-Cookie header
        assert "access_token" in login_res.cookies

        # 3. Subsequent request with Authorization: Bearer <token>
        me_res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert me_res.status_code == 200
        assert me_res.json()["user_id"] == user_id
        assert me_res.json()["username"] == "testuser"

    def test_login_with_email(self):
        client.post("/api/users", json={
            "first_name": "Email",
            "last_name": "User",
            "email": "athlete@example.com",
            "password": "ValidPassword999!",
        })

        login_res = client.post("/api/auth/login", json={
            "identifier": "athlete@example.com",
            "password": "ValidPassword999!",
        })
        assert login_res.status_code == 200
        assert "access_token" in login_res.json()

    def test_login_wrong_password_fails_401(self):
        client.post("/api/users", json={
            "first_name": "Wrong",
            "last_name": "Pass",
            "username": "wrongpass_user",
            "password": "CorrectPassword123!",
        })

        login_res = client.post("/login", json={
            "identifier": "wrongpass_user",
            "password": "IncorrectPassword!",
        })
        assert login_res.status_code == 401
        assert login_res.json()["detail"]["error"] == "INVALID_CREDENTIALS"

    def test_login_nonexistent_user_fails_401(self):
        login_res = client.post("/login", json={
            "identifier": "ghost_user",
            "password": "SomePassword123!",
        })
        assert login_res.status_code == 401
        assert login_res.json()["detail"]["error"] == "INVALID_CREDENTIALS"

    def test_subsequent_request_with_cookie(self):
        client.post("/api/users", json={
            "first_name": "Cookie",
            "last_name": "Monster",
            "username": "cookiemonster",
            "password": "CookiePassword123!",
        })

        login_res = client.post("/login", json={
            "identifier": "cookiemonster",
            "password": "CookiePassword123!",
        })
        token = login_res.json()["access_token"]

        # Call endpoint passing cookie instead of header
        client.cookies.set("access_token", token)
        me_res = client.get("/api/auth/me")
        assert me_res.status_code == 200
        assert me_res.json()["username"] == "cookiemonster"
        client.cookies.clear()

    def test_missing_token_returns_401(self):
        res = client.get("/api/auth/me")
        assert res.status_code == 401
        assert res.json()["detail"]["error"] == "UNAUTHORIZED"

    def test_expired_token_returns_401(self):
        client.post("/api/users", json={
            "first_name": "Expired",
            "last_name": "User",
            "username": "expired_user",
            "password": "SomePassword123!",
        })
        # Generate token already expired (-10 minutes)
        expired_token = create_access_token(
            data={"sub": "any_id"},
            expires_delta=timedelta(minutes=-10),
        )

        res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {expired_token}"})
        assert res.status_code == 401
        assert res.json()["detail"]["error"] == "TOKEN_EXPIRED"

    def test_bad_signature_token_returns_401(self):
        # Token signed with completely different key
        import jwt
        fake_token = jwt.encode(
            {"sub": "fake_id"},
            "completely_wrong_secret_key_99999",
            algorithm="HS256",
        )

        res = client.get("/api/auth/me", headers={"Authorization": f"Bearer {fake_token}"})
        assert res.status_code == 401
        assert res.json()["detail"]["error"] == "INVALID_TOKEN"

    def test_logout_clears_cookie(self):
        res = client.post("/logout")
        assert res.status_code == 200
        # Cookie access_token should be deleted/expired
        cookie_header = res.headers.get("set-cookie", "")
        assert "access_token" in cookie_header
