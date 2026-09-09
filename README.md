# Face Auth App 👁️

A facial recognition authentication system built with **React**, **Flask**, **OpenCV**, and **JWT**. Register your face and log in — no password required.

---

## 🚀 Tech Stack
- **Frontend:** React (Next.js), TypeScript
- **Backend:** Python, Flask
- **Face Detection & Embedding:** OpenCV (frame decode) + facenet-pytorch (MTCNN detection, InceptionResnetV1/FaceNet embedding)
- **Vector Search:** OpenSearch k-NN (HNSW), with a zero-setup local numpy fallback
- **RAG:** sentence-transformers (all-MiniLM-L6-v2) + hybrid semantic/lexical retrieval over the auth event log, answered by Claude with an agentic tool call
- **Auth:** JWT (JSON Web Tokens)
- **Matching (v1, historical):** the original baseline compared a normalized 100×100 grayscale crop by L2 distance. Replaced -- see [Done](#-done) and [DESIGN.md](DESIGN.md) for why.

---

## 📖 How It Works
1. **Register** → Webcam captures your face → Flask detects it and computes a 512-d embedding → embedding enrolled in the vector store, username recorded in `users.json`
2. **Login (1:1 verify)** → Webcam captures face again → compared by cosine similarity to *this username's* enrolled vector → returns JWT token on match
3. **Identify (1:N)** → `/api/identify` takes a frame with no username, searches the vector store for the nearest enrolled user, and returns them if the score clears the threshold
4. **Ask** → `/api/ask` answers questions about the auth event log by retrieving relevant events (hybrid search) and letting an LLM call a `search_events` tool to look them up, citing timestamps
```
[React :3000]  ←→  [Flask :5000]  ←→  [vector store: local | OpenSearch]
                          ↓
                    [events.log]  ←→  [rag.py: retrieval + search_events tool]
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

**With OpenSearch (optional):**
```bash
JWT_SECRET=$(python -c "import secrets;print(secrets.token_hex(32))") docker compose up
```
This runs a single-node OpenSearch plus the Flask app with `VECTOR_BACKEND=opensearch`. Without Docker, the app runs fine with the local numpy fallback (`VECTOR_BACKEND=local`, the default) -- no OpenSearch required.

**Environment variables:**
| Variable | Default | Purpose |
|---|---|---|
| `JWT_SECRET` | *(required)* | Signs auth tokens; server refuses to start without it |
| `FRONTEND_ORIGIN` | `http://localhost:3000` | Allowed CORS origin |
| `VECTOR_BACKEND` | `local` | `local` (numpy fallback) or `opensearch` |
| `OPENSEARCH_URL` | `http://localhost:9200` | Used when `VECTOR_BACKEND=opensearch` |
| `MATCH_THRESHOLD` | `0.5` | Cosine similarity cutoff for a face match |
| `ANTHROPIC_API_KEY` | *(optional)* | Enables LLM generation in `/api/ask`; without it, raw retrieved snippets are returned instead |

---

## 🔌 API Endpoints
| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/register` | Register a new face |
| POST | `/api/login` | Login with face + username (1:1 verify), returns JWT |
| POST | `/api/identify` | Identify a face with no username (1:N search) |
| POST | `/api/ask` | Ask a question about the auth event log (RAG + agentic tool call) |
| GET | `/api/protected` | Protected route, requires JWT |

---

## 🔒 Security notes
- The JWT secret and the allowed frontend origin are both read from environment variables — the server refuses to start if `JWT_SECRET` is not set.
- `users.json`, enrolled face vectors (local store or OpenSearch), and `events.log` are all git-ignored and must never be committed.
- Frames where zero or more than one face is detected are rejected rather than silently guessing which face to use.
- **Known gap:** `/api/identify` and `/api/ask` have no authorization check of their own -- anyone who can reach the API can run a 1:N face search or query the event log. See [DESIGN.md](DESIGN.md#access-control-before-retrieval).
- **Known limitation:** there is no liveness detection. A printed photo of an enrolled user's face will currently pass. Do not use this app as-is for real access control.

---

## ✅ Done
- Replaced pixel-space matching with a learned face embedding (FaceNet, cosine similarity). See [DESIGN.md](DESIGN.md) for why, and why FaceNet over ArcFace.
- Vector index (OpenSearch k-NN / HNSW, with a local fallback) and 1:N identification (`/api/identify`) instead of only username + verify.
- RAG over the auth event log with hybrid retrieval and one agentic tool call (`search_events`), instead of stuffing the whole log into a prompt.

## 🗺️ Roadmap
1. Calibrate `MATCH_THRESHOLD` and `RELEVANCE_THRESHOLD` against a real genuine-vs-impostor dataset, not the single sanity-check pair each currently relies on.
2. Add authorization in front of `/api/identify` and `/api/ask` (see Security notes above).
3. Add a liveness check (blink / head-turn challenge) -- still the biggest open security gap; see [DESIGN.md](DESIGN.md#the-open-security-gap-liveness).

---

## 👨‍💻 Author
**Nikhil Kotta** — [GitHub](https://github.com/nik112001) · [LinkedIn](https://www.linkedin.com/in/nikhil-kotta-85872019b)
