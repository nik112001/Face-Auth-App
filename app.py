from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import cv2
import numpy as np
import jwt
import datetime
import os
import json
import base64

from embeddings import embed_face
from vector_store import get_store
from rag import answer_question

load_dotenv()

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 10MB -- a single webcam JPEG frame is a few hundred KB

FRONTEND_ORIGIN = os.environ.get("FRONTEND_ORIGIN", "http://localhost:3000")
CORS(app, origins=[FRONTEND_ORIGIN])

MAX_QUESTION_LENGTH = 2000

SECRET_KEY = os.environ.get("JWT_SECRET")
if not SECRET_KEY:
    raise RuntimeError("JWT_SECRET is not set. Copy .env.example to .env and set a random value.")

USERS_FILE = os.environ.get("USERS_FILE", "users.json")
EVENTS_LOG = os.environ.get("EVENTS_LOG", "events.log")

# 0.5 is a reasonable starting point for facenet-pytorch's VGGFace2-trained
# cosine-similarity space (ArcFace/insightface embeddings typically need a
# lower ~0.35 for the same decision on their own space). Not yet calibrated
# against this project's own genuine-vs-impostor pairs -- see Roadmap.
MATCH_THRESHOLD = float(os.environ.get("MATCH_THRESHOLD", "0.5"))

store = get_store()

# Load users from file
def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    return {}

# Save users to file
def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f)

# Append-only audit trail. Read back by the RAG endpoint in rag.py.
def log_event(action, user_id, score, outcome):
    with open(EVENTS_LOG, "a") as f:
        f.write(json.dumps({
            "timestamp": datetime.datetime.utcnow().isoformat(),
            "action": action,
            "user_id": user_id,
            "score": score,
            "outcome": outcome,
        }) + "\n")

# Decode base64 image from frontend
def decode_image(base64_string):
    if "," in base64_string:
        base64_string = base64_string.split(",")[1]
    img_bytes = base64.b64decode(base64_string)
    np_arr = np.frombuffer(img_bytes, np.uint8)
    img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    return img

# Detect the single face in img and return its embedding as a plain list
# (JSON-serializable) for storage. None if zero or multiple faces are found.
def get_face_encoding(img):
    embedding = embed_face(img)
    if embedding is None:
        return None
    return embedding.tolist()

# Cosine-similarity match decision against a user's enrolled vector.
# Delegated to the vector store (rather than comparing two arrays directly)
# so the same code path works whether vectors live in the local numpy
# fallback or in OpenSearch.
def compare_faces(username, vector):
    score = store.verify(username, vector)
    return score >= MATCH_THRESHOLD, score

@app.route("/api/register", methods=["POST"])
def register():
    data = request.json
    username = data.get("username")
    image_data = data.get("image")

    if not username or not image_data:
        return jsonify({"error": "Username and image required"}), 400

    users = load_users()
    if username in users:
        return jsonify({"error": "User already exists"}), 400

    img = decode_image(image_data)
    if img is None:
        log_event("register", username, None, "rejected_bad_image")
        return jsonify({"error": "Image could not be decoded."}), 400

    encoding = get_face_encoding(img)
    if encoding is None:
        log_event("register", username, None, "rejected_ambiguous_face")
        return jsonify({"error": "Expected exactly one face. Please try again."}), 400

    store.enroll(username, encoding)
    users[username] = {"registered_at": datetime.datetime.utcnow().isoformat()}
    save_users(users)
    log_event("register", username, None, "success")

    return jsonify({"message": f"User {username} registered successfully!"})

@app.route("/api/login", methods=["POST"])
def login():
    data = request.json
    username = data.get("username")
    image_data = data.get("image")

    if not username or not image_data:
        return jsonify({"error": "Username and image required"}), 400

    users = load_users()
    if username not in users:
        return jsonify({"error": "User not found"}), 404

    img = decode_image(image_data)
    if img is None:
        log_event("login", username, None, "rejected_bad_image")
        return jsonify({"error": "Image could not be decoded."}), 400

    encoding = get_face_encoding(img)
    if encoding is None:
        log_event("login", username, None, "rejected_ambiguous_face")
        return jsonify({"error": "Expected exactly one face. Please try again."}), 400

    match, score = compare_faces(username, encoding)

    if match:
        token = jwt.encode(
            {
                "username": username,
                "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1),
            },
            SECRET_KEY,
            algorithm="HS256",
        )
        log_event("login", username, score, "success")
        return jsonify({"message": "Login successful!", "token": token, "score": score})
    else:
        log_event("login", username, score, "denied")
        return jsonify({"error": "Face does not match. Access denied."}), 401

@app.route("/api/identify", methods=["POST"])
def identify():
    data = request.json
    image_data = data.get("image")

    if not image_data:
        return jsonify({"error": "Image required"}), 400

    img = decode_image(image_data)
    if img is None:
        log_event("identify", None, None, "rejected_bad_image")
        return jsonify({"error": "Image could not be decoded."}), 400

    encoding = get_face_encoding(img)
    if encoding is None:
        log_event("identify", None, None, "rejected_ambiguous_face")
        return jsonify({"error": "Expected exactly one face. Please try again."}), 400

    user_id, score = store.identify(encoding)

    if user_id is not None and score >= MATCH_THRESHOLD:
        log_event("identify", user_id, score, "success")
        return jsonify({"user_id": user_id, "score": score})
    else:
        log_event("identify", user_id, score, "no_match")
        return jsonify({"error": "No match found."}), 401

@app.route("/api/ask", methods=["POST"])
def ask():
    data = request.json
    question = data.get("question")

    if not question:
        return jsonify({"error": "Question required"}), 400
    if len(question) > MAX_QUESTION_LENGTH:
        return jsonify({"error": f"Question is too long (max {MAX_QUESTION_LENGTH} characters)."}), 400

    result = answer_question(question, EVENTS_LOG)
    return jsonify(result)

@app.route("/api/protected", methods=["GET"])
def protected():
    token = request.headers.get("Authorization", "").replace("Bearer ", "")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return jsonify({"message": f"Welcome {payload['username']}! You are authenticated."})
    except jwt.ExpiredSignatureError:
        return jsonify({"error": "Token expired"}), 401
    except jwt.InvalidTokenError:
        return jsonify({"error": "Invalid token"}), 401

if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG") == "1", port=int(os.environ.get("PORT", "5000")))