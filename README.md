# Face Auth App 👁️

A facial recognition authentication system built with **React**, **Flask**, **OpenCV**, and **JWT**. Register your face and log in — no password required.

---

## 🚀 Tech Stack
- **Frontend:** React (Next.js), TypeScript
- **Backend:** Python, Flask
- **Face Detection:** OpenCV (Haar Cascade Classifier)
- **Auth:** JWT (JSON Web Tokens)
- **Matching (v1):** A normalized 100×100 grayscale crop of the detected face is compared to the enrolled crop by L2 (sum of squared differences) distance. This is a deliberate baseline, not a learned face embedding — it's cheap to run and easy to reason about, but it is not robust to lighting, pose, or expression changes the way an embedding model would be. See [Roadmap](#-roadmap) for the planned upgrade.

---

## 📖 How It Works
1. **Register** → Webcam captures your face → Flask detects & encodes it → saved to `users.json`
2. **Login** → Webcam captures face again → Flask compares encoding → returns JWT token on match
3. **JWT Token** → Proves authentication for future protected requests
```
[React :3000]  ←→  [Flask :5000]  ←→  [users.json]
```

---

## ⚙️ Running Locally

**Backend:**
```bash
python -m venv venv

# macOS/Linux
source venv/bin/activate
# Windows
venv\Scripts\activate

cp .env.example .env
# then edit .env and set JWT_SECRET (see Security notes below)

pip install -r requirements.txt
python app.py
```

**Frontend:**
```bash
cd frontend
cp .env.local.example .env.local
npm install
npm run dev
```

---

## 🔌 API Endpoints
| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/register` | Register a new face |
| POST | `/api/login` | Login with face, returns JWT |
| GET | `/api/protected` | Protected route, requires JWT |

---

## 🔒 Security notes
- The JWT secret and the allowed frontend origin are both read from environment variables — the server refuses to start if `JWT_SECRET` is not set.
- `users.json` (enrolled face data) is git-ignored and must never be committed.
- Frames where zero or more than one face is detected are rejected rather than silently guessing which face to use.
- **Known limitation:** there is no liveness detection. A printed photo of an enrolled user's face will currently pass. Do not use this app as-is for real access control.

---

## 🗺️ Roadmap
1. Replace pixel-space matching with a learned face embedding (ArcFace / FaceNet), compare with cosine similarity, and calibrate the decision threshold on genuine-vs-impostor pairs.
2. Store embeddings in a vector index (FAISS or OpenSearch kNN) and identify users by nearest-neighbor search instead of username + verify.
3. Add a liveness check (blink / head-turn challenge).

---

## 👨‍💻 Author
**Nikhil Kotta** — [GitHub](https://github.com/nik112001) · [LinkedIn](https://www.linkedin.com/in/nikhil-kotta-85872019b)
