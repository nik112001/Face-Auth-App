from flask import Flask, request, jsonify
from flask_cors import CORS
import cv2
import numpy as np
import jwt
import datetime
import os
import json
import base64

app = Flask(__name__)
CORS(app)

SECRET_KEY = "your-secret-key-change-in-production"
USERS_FILE = "users.json"

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

# Decode base64 image from frontend
def decode_image(base64_string):
    if "," in base64_string:
        base64_string = base64_string.split(",")[1]
    img_bytes = base64.b64decode(base64_string)
    np_arr = np.frombuffer(img_bytes, np.uint8)
    img = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
    return img

# Detect face and return encoding using OpenCV
def get_face_encoding(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    face_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    )
    faces = face_cascade.detectMultiScale(gray, 1.1, 4)
    if len(faces) == 0:
        return None
    x, y, w, h = faces[0]
    face_img = gray[y:y+h, x:x+w]
    face_resized = cv2.resize(face_img, (100, 100))
    encoding = face_resized.flatten().tolist()
    return encoding

# Compare two face encodings
def compare_faces(enc1, enc2, threshold=5000000):
    a = np.array(enc1)
    b = np.array(enc2)
    diff = np.sum((a - b) ** 2)
    return diff < threshold

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
    encoding = get_face_encoding(img)

    if encoding is None:
        return jsonify({"error": "No face detected. Please try again."}), 400

    users[username] = {"encoding": encoding}
    save_users(users)

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
    encoding = get_face_encoding(img)

    if encoding is None:
        return jsonify({"error": "No face detected. Please try again."}), 400

    match = compare_faces(users[username]["encoding"], encoding)

    if match:
        token = jwt.encode(
            {
                "username": username,
                "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=1),
            },
            SECRET_KEY,
            algorithm="HS256",
        )
        return jsonify({"message": "Login successful!", "token": token})
    else:
        return jsonify({"error": "Face does not match. Access denied."}), 401

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
    app.run(debug=True, port=5000)