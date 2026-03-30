# Face Auth App 👁️

A facial recognition authentication system built with **React**, **Flask**, **OpenCV**, and **JWT**. Register your face and log in — no password required.

---

## 🚀 Tech Stack
- **Frontend:** React (Next.js), TypeScript
- **Backend:** Python, Flask
- **Face Detection:** OpenCV (Haar Cascade Classifier)
- **Auth:** JWT (JSON Web Tokens)

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
venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

**Frontend:**
```bash
cd frontend
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

## 👨‍💻 Author
**Nikhil Kotta** — [GitHub](https://github.com/nik112001) · [LinkedIn](https://www.linkedin.com/in/nikhil-kotta-85872019b)
