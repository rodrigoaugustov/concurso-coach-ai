# backend/tests/security/test_headers_and_limits.py

import io
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_security_headers_present_on_health():
    r = client.get("/health")
    assert r.status_code == 200
    h = r.headers
    assert "Strict-Transport-Security" in h
    assert h.get("X-Frame-Options") == "DENY"
    assert h.get("X-Content-Type-Options") == "nosniff"
    assert h.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    assert "Content-Security-Policy" in h


@pytest.mark.parametrize("payload,ctype", [
    (b"not-a-pdf", "application/pdf"),
])
def test_upload_rejects_non_pdf(monkeypatch, payload, ctype):
    # Mock auth and GCS interactions
    def fake_get_current_user():
        class U: id = 1; email = "u@e.com"
        return U()
    monkeypatch.setattr("app.users.auth.get_current_user", lambda: fake_get_current_user())

    # Mock GCS client to avoid network
    class FakeBlob:
        def upload_from_file(self, f, content_type=None):
            pass
        @property
        def public_url(self):
            return "https://example.com/fake.pdf"
    class FakeBucket:
        def blob(self, name):
            return FakeBlob()
    class FakeClient:
        def __init__(self, project=None):
            pass
        def bucket(self, name):
            return FakeBucket()
    monkeypatch.setattr("app.contests.router.storage.Client", FakeClient)

    files = {"file": ("doc.pdf", io.BytesIO(payload), ctype)}
    r = client.post("/api/v1/contests/upload", files=files)
    assert r.status_code in (400, 422)
    body = r.json()
    # detail may be dict or error structure; validate presence
    assert "error" in body or "detail" in body


def test_upload_accepts_small_valid_pdf(monkeypatch):
    def fake_get_current_user():
        class U: id = 1; email = "u@e.com"
        return U()
    monkeypatch.setattr("app.users.auth.get_current_user", lambda: fake_get_current_user())

    class FakeBlob:
        def upload_from_file(self, f, content_type=None):
            assert content_type == "application/pdf"
        @property
        def public_url(self):
            return "https://example.com/fake.pdf"
    class FakeBucket:
        def blob(self, name):
            return FakeBlob()
    class FakeClient:
        def __init__(self, project=None):
            pass
        def bucket(self, name):
            return FakeBucket()
    monkeypatch.setattr("app.contests.router.storage.Client", FakeClient)

    # Minimal PDF bytes with EOF near end
    pdf_bytes = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\n%%EOF"
    files = {"file": ("ok.pdf", io.BytesIO(pdf_bytes), "application/pdf")}
    r = client.post("/api/v1/contests/upload", files=files)
    # 201 on success
    assert r.status_code in (201, 200)


def test_login_rejects_invalid_email(monkeypatch):
    # No DB hit needed; validation happens first
    data = {"username": "bad-email", "password": "Strong1Pass"}
    r = client.post("/api/v1/token", data=data)
    assert r.status_code in (400, 422)


def test_login_rejects_weak_password(monkeypatch):
    data = {"username": "user@example.com", "password": "weak"}
    r = client.post("/api/v1/token", data=data)
    assert r.status_code in (400, 422)


def test_study_generate_plan_id_validation(monkeypatch):
    def fake_get_current_user():
        class U: id = 1; email = "u@e.com"
        return U()
    monkeypatch.setattr("app.users.auth.get_current_user", lambda: fake_get_current_user())

    r = client.post("/api/v1/study/user-contests/0/generate-plan")
    assert r.status_code in (400, 422)
