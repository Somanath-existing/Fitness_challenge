"""
API integration tests — uses FastAPI TestClient with an in-memory SQLite DB.
Tests cover the full request/response cycle through Pydantic validation + route handlers.

Run: cd apps/backend && python -m pytest ../../tests/test_api.py -v
"""
import pytest
from conftest import client


@pytest.fixture
def alice():
    """Create and return Alice's user data."""
    r = client.post("/api/users", json={
        "first_name": "Alice",
        "last_name": "Test",
        "timezone": "UTC",
    })
    assert r.status_code == 201
    return r.json()


# ── User registration ─────────────────────────────────────────────────────────

class TestUserRegistration:
    def test_register_valid(self):
        r = client.post("/api/users", json={
            "first_name": "Alice",
            "last_name": "Test",
            "timezone": "UTC",
        })
        assert r.status_code == 201
        data = r.json()
        assert data["first_name"] == "Alice"
        assert data["total_points"] == 0
        assert "user_id" in data

    def test_register_with_all_fields(self):
        r = client.post("/api/users", json={
            "first_name": "Bob",
            "last_name": "Jones",
            "email": "bob@example.com",
            "username": "bob_runs",
            "timezone": "Asia/Kolkata",
            "fitness_goal": 500,
            "bio": "Running every day",
        })
        assert r.status_code == 201

    def test_register_duplicate_name(self, alice):
        r = client.post("/api/users", json={
            "first_name": "Alice",
            "last_name": "Test",
        })
        assert r.status_code == 409
        assert r.json()["detail"]["error"] == "USER_EXISTS"

    def test_register_duplicate_name_case_insensitive(self, alice):
        r = client.post("/api/users", json={
            "first_name": "ALICE",
            "last_name": "TEST",
        })
        assert r.status_code == 409

    def test_register_whitespace_only_name(self):
        r = client.post("/api/users", json={
            "first_name": "   ",
            "last_name": "Test",
        })
        assert r.status_code == 422

    def test_register_invalid_email(self):
        r = client.post("/api/users", json={
            "first_name": "Eve",
            "last_name": "Test",
            "email": "not-an-email",
        })
        assert r.status_code == 422

    def test_register_invalid_timezone(self):
        r = client.post("/api/users", json={
            "first_name": "Eve",
            "last_name": "Test",
            "timezone": "Not/ATimezone",
        })
        assert r.status_code == 422

    def test_register_invalid_username_spaces(self):
        r = client.post("/api/users", json={
            "first_name": "Eve",
            "last_name": "Test",
            "username": "has spaces",
        })
        assert r.status_code == 422

    def test_register_invalid_username_uppercase(self):
        r = client.post("/api/users", json={
            "first_name": "Eve",
            "last_name": "Test",
            "username": "HasUpper",
        })
        assert r.status_code == 422

    def test_register_negative_fitness_goal(self):
        r = client.post("/api/users", json={
            "first_name": "Eve",
            "last_name": "Test",
            "fitness_goal": -100,
        })
        assert r.status_code == 422

    def test_get_user(self, alice):
        r = client.get(f"/api/users/{alice['user_id']}")
        assert r.status_code == 200
        assert r.json()["first_name"] == "Alice"

    def test_get_nonexistent_user(self):
        r = client.get("/api/users/00000000-0000-0000-0000-000000000000")
        assert r.status_code == 404


# ── Activity logging ──────────────────────────────────────────────────────────

class TestActivityLogging:
    def test_log_running(self, alice):
        r = client.post("/api/activities", json={
            "user_id": alice["user_id"],
            "sport": "running",
            "metric": {"type": "distance_km", "value": 5.0},
        })
        assert r.status_code == 201
        data = r.json()
        assert data["points_awarded"] == 500
        assert data["user_total_points"] == 500

    def test_log_walking_floor(self, alice):
        r = client.post("/api/activities", json={
            "user_id": alice["user_id"],
            "sport": "walking",
            "metric": {"type": "distance_km", "value": 1.55},
        })
        assert r.status_code == 201
        assert r.json()["points_awarded"] == 77

    def test_log_gym(self, alice):
        r = client.post("/api/activities", json={
            "user_id": alice["user_id"],
            "sport": "gym",
            "metric": {"type": "duration_minsec", "value": "45:30"},
        })
        assert r.status_code == 201
        assert r.json()["points_awarded"] == 225

    def test_log_steps_399(self, alice):
        r = client.post("/api/activities", json={
            "user_id": alice["user_id"],
            "sport": "steps",
            "metric": {"type": "count", "value": 399},
        })
        assert r.status_code == 201
        assert r.json()["points_awarded"] == 3

    def test_sport_metric_mismatch(self, alice):
        r = client.post("/api/activities", json={
            "user_id": alice["user_id"],
            "sport": "running",
            "metric": {"type": "count", "value": 1000},
        })
        assert r.status_code == 422  # Pydantic catches this

    def test_future_logged_at_rejected(self, alice):
        r = client.post("/api/activities", json={
            "user_id": alice["user_id"],
            "sport": "running",
            "metric": {"type": "distance_km", "value": 5.0},
            "logged_at": "2099-01-01T00:00:00",
        })
        assert r.status_code == 422

    def test_nonexistent_user(self):
        r = client.post("/api/activities", json={
            "user_id": "00000000-0000-0000-0000-000000000000",
            "sport": "running",
            "metric": {"type": "distance_km", "value": 5.0},
        })
        assert r.status_code == 404

    def test_points_accumulate(self, alice):
        uid = alice["user_id"]
        client.post("/api/activities", json={
            "user_id": uid, "sport": "running",
            "metric": {"type": "distance_km", "value": 5.0},
        })
        r2 = client.post("/api/activities", json={
            "user_id": uid, "sport": "walking",
            "metric": {"type": "distance_km", "value": 2.0},
        })
        assert r2.json()["user_total_points"] == 600  # 500 + 100

    def test_personal_best_flagged(self, alice):
        uid = alice["user_id"]
        r1 = client.post("/api/activities", json={
            "user_id": uid, "sport": "running",
            "metric": {"type": "distance_km", "value": 3.0},
        })
        assert r1.json()["is_personal_best"] is True  # first ever = PB

        r2 = client.post("/api/activities", json={
            "user_id": uid, "sport": "running",
            "metric": {"type": "distance_km", "value": 5.0},
        })
        assert r2.json()["is_personal_best"] is True  # 500 > 300

        r3 = client.post("/api/activities", json={
            "user_id": uid, "sport": "running",
            "metric": {"type": "distance_km", "value": 1.0},
        })
        assert r3.json()["is_personal_best"] is False  # 100 < 500

    def test_first_step_badge_awarded(self, alice):
        r = client.post("/api/activities", json={
            "user_id": alice["user_id"],
            "sport": "running",
            "metric": {"type": "distance_km", "value": 1.0},
        })
        assert "first_step" in r.json()["new_badges"]

    def test_zero_distance_accepted(self, alice):
        r = client.post("/api/activities", json={
            "user_id": alice["user_id"],
            "sport": "running",
            "metric": {"type": "distance_km", "value": 0},
        })
        assert r.status_code == 201
        assert r.json()["points_awarded"] == 0

    def test_zero_steps_accepted(self, alice):
        r = client.post("/api/activities", json={
            "user_id": alice["user_id"],
            "sport": "steps",
            "metric": {"type": "count", "value": 0},
        })
        assert r.status_code == 201
        assert r.json()["points_awarded"] == 0


# ── Leaderboard ───────────────────────────────────────────────────────────────

class TestLeaderboard:
    def test_leaderboard_sorted_desc(self):
        # Create two users with different points
        u1 = client.post("/api/users", json={"first_name": "High", "last_name": "Scorer"}).json()
        u2 = client.post("/api/users", json={"first_name": "Low", "last_name": "Scorer"}).json()

        client.post("/api/activities", json={
            "user_id": u1["user_id"], "sport": "running",
            "metric": {"type": "distance_km", "value": 10.0},
        })
        client.post("/api/activities", json={
            "user_id": u2["user_id"], "sport": "walking",
            "metric": {"type": "distance_km", "value": 1.0},
        })

        r = client.get("/api/leaderboard")
        assert r.status_code == 200
        data = r.json()["data"]
        assert len(data) >= 2
        # Ranks should be ascending
        ranks = [e["rank"] for e in data]
        assert ranks == sorted(ranks)
        # Points should be descending
        points = [e["total_points"] for e in data]
        assert points == sorted(points, reverse=True)

    def test_leaderboard_has_tier(self):
        client.post("/api/users", json={"first_name": "Solo", "last_name": "User"})
        r = client.get("/api/leaderboard")
        assert r.status_code == 200
        entry = r.json()["data"][0]
        assert "tier" in entry

    def test_leaderboard_friends_requires_user_id(self):
        r = client.get("/api/leaderboard?scope=friends")
        assert r.status_code == 400

    def test_leaderboard_pagination(self):
        for i in range(5):
            client.post("/api/users", json={"first_name": f"User{i}", "last_name": "Test"})
        r = client.get("/api/leaderboard?limit=2&offset=0")
        assert r.status_code == 200
        assert len(r.json()["data"]) == 2


# ── Health check ──────────────────────────────────────────────────────────────

class TestHealth:
    def test_health_ok(self):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"


# ── Friends ───────────────────────────────────────────────────────────────────

class TestFriends:
    def test_self_friend_rejected(self, alice):
        r = client.post(
            "/api/friends/request",
            json={"addressee_id": alice["user_id"]},
            params={"requester_id": alice["user_id"]},
        )
        assert r.status_code == 400
        assert r.json()["detail"]["error"] == "SELF_FRIEND"

    def test_send_and_accept_friend_request(self, alice):
        bob = client.post("/api/users", json={"first_name": "Bob", "last_name": "Test"}).json()

        # Send request
        r = client.post(
            "/api/friends/request",
            json={"addressee_id": bob["user_id"]},
            params={"requester_id": alice["user_id"]},
        )
        assert r.status_code == 201

        # List friends — Alice has none yet (pending only)
        r = client.get("/api/friends", params={"user_id": alice["user_id"]})
        assert r.json()["count"] == 0

    def test_duplicate_friend_request(self, alice):
        bob = client.post("/api/users", json={"first_name": "Bob2", "last_name": "Test"}).json()
        payload = {"addressee_id": bob["user_id"]}
        params = {"requester_id": alice["user_id"]}

        client.post("/api/friends/request", json=payload, params=params)
        r = client.post("/api/friends/request", json=payload, params=params)
        assert r.status_code == 409


# ── CORS ──────────────────────────────────────────────────────────────────────

class TestCORS:
    def test_vercel_preview_origin_allowed(self):
        origin = "https://fitness-challenge-rimy7w1ol-somanath-existings-projects.vercel.app"
        r = client.options(
            "/api/leaderboard?limit=100&scope=global",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "authorization,content-type",
            },
        )
        assert r.status_code == 200
        assert r.headers.get("access-control-allow-origin") == origin
        assert r.headers.get("access-control-allow-credentials") == "true"

    def test_vercel_get_request_cors_headers(self):
        origin = "https://fitness-challenge-rimy7w1ol-somanath-existings-projects.vercel.app"
        r = client.get(
            "/api/leaderboard?limit=100&scope=global",
            headers={"Origin": origin},
        )
        assert r.status_code == 200
        assert r.headers.get("access-control-allow-origin") == origin
        assert r.headers.get("access-control-allow-credentials") == "true"

    def test_localhost_origin_allowed(self):
        origin = "http://localhost:5173"
        r = client.options(
            "/api/leaderboard?limit=100&scope=global",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "GET",
            },
        )
        assert r.status_code == 200
        assert r.headers.get("access-control-allow-origin") == origin

    def test_disallowed_origin_rejected(self):
        r = client.options(
            "/api/leaderboard?limit=100&scope=global",
            headers={
                "Origin": "https://malicious-site.com",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert r.status_code == 400

