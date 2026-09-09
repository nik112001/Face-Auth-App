import base64
import os

from conftest import FIXTURES_DIR
from app import app as flask_app


def _b64(name):
    with open(os.path.join(FIXTURES_DIR, name), "rb") as f:
        return "data:image/jpeg;base64," + base64.b64encode(f.read()).decode()


def test_identify_returns_enrolled_user_for_their_own_face():
    client = flask_app.test_client()
    face = _b64("face1.jpg")

    register_resp = client.post(
        "/api/register", json={"username": "identify_test_user", "image": face}
    )
    assert register_resp.status_code == 200

    identify_resp = client.post("/api/identify", json={"image": face})
    assert identify_resp.status_code == 200

    body = identify_resp.get_json()
    assert body["user_id"] == "identify_test_user"
    assert body["score"] >= 0.5
