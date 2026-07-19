"""Smallest checks that fail if the triage routing or auth breaks."""
import app as app_module
from app import CATEGORIES, app
from setup_data import data


def test_every_category_has_a_resource():
    all_tags = {tag for place in data for tag in place["tags"]}
    missing = [c for c in CATEGORIES if c not in all_tags]
    assert not missing, f"No resource seeded for categories: {missing}"


def test_resources_have_required_fields():
    for place in data:
        assert place.get("name") and place.get("phone") and place.get("tags")


def test_sms_rejects_forged_request_when_token_set(monkeypatch):
    monkeypatch.setenv("TWILIO_AUTH_TOKEN", "fake-token")
    resp = app.test_client().post("/sms", data={"Body": "I have a fever", "From": "+15550001"})
    assert resp.status_code == 403


def test_sms_allows_request_when_token_unset(monkeypatch):
    # No token configured -> validation is skipped so the route still runs.
    monkeypatch.delenv("TWILIO_AUTH_TOKEN", raising=False)
    monkeypatch.setattr(app_module, "ask_gemini", lambda _t: "student")
    resp = app.test_client().post("/sms", data={"Body": "I have a fever", "From": "+15550002"})
    assert resp.status_code == 200
