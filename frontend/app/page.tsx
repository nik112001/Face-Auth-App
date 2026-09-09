"use client";

import { useState, useRef, useCallback } from "react";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:5000";

type IdentifyResult = { user_id: string; score: number };
type AskResult = {
  answer: string | null;
  citations: string[];
  retrieved?: string[];
  note?: string;
};

export default function Home() {
  const [mode, setMode] = useState<"home" | "register" | "login" | "identify" | "ask" | "success">("home");
  const [username, setUsername] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [token, setToken] = useState("");
  const [loading, setLoading] = useState(false);
  const [identifyResult, setIdentifyResult] = useState<IdentifyResult | null>(null);
  const [question, setQuestion] = useState("");
  const [askResult, setAskResult] = useState<AskResult | null>(null);
  const [protectedMessage, setProtectedMessage] = useState("");
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const streamRef = useRef<MediaStream | null>(null);

  const startCamera = useCallback(async (): Promise<boolean> => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
      }
      return true;
    } catch {
      return false;
    }
  }, []);

  const stopCamera = useCallback(() => {
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
  }, []);

  const captureImage = (): string | null => {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas) return null;
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    canvas.getContext("2d")?.drawImage(video, 0, 0);
    return canvas.toDataURL("image/jpeg");
  };

  const handleRegister = async () => {
    if (!username) { setError("Please enter a username"); return; }
    setLoading(true);
    setError("");
    const image = captureImage();
    if (!image) { setError("Could not capture image"); setLoading(false); return; }
    try {
      const res = await fetch(`${API_BASE}/api/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, image }),
      });
      const data = await res.json();
      if (res.ok) { setMessage(data.message); stopCamera(); setMode("home"); }
      else setError(data.error);
    } catch {
      setError("Could not connect to server. Is Flask running?");
    }
    setLoading(false);
  };

  const handleLogin = async () => {
    if (!username) { setError("Please enter a username"); return; }
    setLoading(true);
    setError("");
    const image = captureImage();
    if (!image) { setError("Could not capture image"); setLoading(false); return; }
    try {
      const res = await fetch(`${API_BASE}/api/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, image }),
      });
      const data = await res.json();
      if (res.ok) { setToken(data.token); stopCamera(); setMode("success"); }
      else setError(data.error);
    } catch {
      setError("Could not connect to server. Is Flask running?");
    }
    setLoading(false);
  };

  const handleIdentify = async () => {
    setLoading(true);
    setError("");
    setIdentifyResult(null);
    const image = captureImage();
    if (!image) { setError("Could not capture image"); setLoading(false); return; }
    try {
      const res = await fetch(`${API_BASE}/api/identify`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ image }),
      });
      const data = await res.json();
      if (res.ok) { setIdentifyResult(data); stopCamera(); }
      else setError(data.error);
    } catch {
      setError("Could not connect to server. Is Flask running?");
    }
    setLoading(false);
  };

  const handleAsk = async () => {
    if (!question.trim()) { setError("Please enter a question"); return; }
    setLoading(true);
    setError("");
    setAskResult(null);
    try {
      const res = await fetch(`${API_BASE}/api/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question }),
      });
      const data = await res.json();
      if (res.ok) setAskResult(data);
      else setError(data.error);
    } catch {
      setError("Could not connect to server. Is Flask running?");
    }
    setLoading(false);
  };

  const callProtected = async () => {
    setLoading(true);
    setError("");
    try {
      const res = await fetch(`${API_BASE}/api/protected`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const data = await res.json();
      if (res.ok) setProtectedMessage(data.message);
      else setError(data.error);
    } catch {
      setError("Could not connect to server. Is Flask running?");
    }
    setLoading(false);
  };

  const goHome = () => {
    stopCamera();
    setMode("home");
    setError("");
    setMessage("");
    setUsername("");
    setIdentifyResult(null);
    setQuestion("");
    setAskResult(null);
    setProtectedMessage("");
  };

  const enterMode = async (m: "register" | "login" | "identify") => {
    setError("");
    setMessage("");
    setIdentifyResult(null);
    const ok = await startCamera();
    if (!ok) {
      setError("Could not access the camera. Check your browser's camera permission for this site and try again.");
      setMode("home");
      return;
    }
    setMode(m);
  };

  const enterAsk = () => {
    setMode("ask");
    setError("");
    setMessage("");
    setAskResult(null);
  };

  return (
    <div style={{ minHeight: "100vh", background: "#0c0c0e", color: "#e8e6e1", fontFamily: "monospace", display: "flex", alignItems: "center", justifyContent: "center" }}>
      <div style={{ width: "100%", maxWidth: "480px", padding: "40px", background: "#131316", border: "1px solid rgba(255,255,255,0.07)", borderRadius: "12px" }}>

        <h1 style={{ fontFamily: "serif", fontSize: "32px", marginBottom: "8px" }}>
          Face <span style={{ color: "#a78bfa", fontStyle: "italic" }}>Auth</span>
        </h1>
        <p style={{ color: "#666370", fontSize: "12px", marginBottom: "32px" }}>
          OpenCV · Flask · React · JWT
        </p>

        {message && <div style={{ background: "rgba(52,211,153,0.1)", border: "1px solid rgba(52,211,153,0.3)", borderRadius: "6px", padding: "12px", marginBottom: "16px", color: "#34d399", fontSize: "13px" }}>{message}</div>}
        {error && <div style={{ background: "rgba(239,68,68,0.1)", border: "1px solid rgba(239,68,68,0.3)", borderRadius: "6px", padding: "12px", marginBottom: "16px", color: "#f87171", fontSize: "13px" }}>{error}</div>}

        {mode === "home" && (
          <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
            <p style={{ color: "#666370", fontSize: "14px", marginBottom: "8px" }}>
              Register your face, log in, identify a face with no username, or ask about recent activity.
            </p>
            <button onClick={() => enterMode("register")} style={{ padding: "14px", background: "#a78bfa", color: "#0c0c0e", border: "none", borderRadius: "6px", fontSize: "14px", fontWeight: "600", cursor: "pointer" }}>
              Register Face
            </button>
            <button onClick={() => enterMode("login")} style={{ padding: "14px", background: "transparent", color: "#e8e6e1", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "6px", fontSize: "14px", cursor: "pointer" }}>
              Login with Face
            </button>
            <button onClick={() => enterMode("identify")} style={{ padding: "14px", background: "transparent", color: "#e8e6e1", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "6px", fontSize: "14px", cursor: "pointer" }}>
              Identify Face (1:N, no username)
            </button>
            <button onClick={enterAsk} style={{ padding: "14px", background: "transparent", color: "#e8e6e1", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "6px", fontSize: "14px", cursor: "pointer" }}>
              Ask About Recent Activity
            </button>
          </div>
        )}

        {(mode === "register" || mode === "login" || mode === "identify") && (
          <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
            <video ref={videoRef} autoPlay playsInline style={{ width: "100%", borderRadius: "8px", border: "1px solid rgba(255,255,255,0.07)" }} />
            <canvas ref={canvasRef} style={{ display: "none" }} />
            {mode !== "identify" && (
              <input
                type="text"
                placeholder="Enter your username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                style={{ padding: "12px", background: "#1c1c21", border: "1px solid rgba(255,255,255,0.07)", borderRadius: "6px", color: "#e8e6e1", fontSize: "14px", outline: "none" }}
              />
            )}
            {identifyResult && (
              <div style={{ background: "rgba(167,139,250,0.1)", border: "1px solid rgba(167,139,250,0.3)", borderRadius: "6px", padding: "12px", color: "#a78bfa", fontSize: "13px" }}>
                Matched: <b>{identifyResult.user_id}</b> (cosine score {identifyResult.score.toFixed(3)})
              </div>
            )}
            <button
              onClick={mode === "register" ? handleRegister : mode === "login" ? handleLogin : handleIdentify}
              disabled={loading}
              style={{ padding: "14px", background: "#a78bfa", color: "#0c0c0e", border: "none", borderRadius: "6px", fontSize: "14px", fontWeight: "600", cursor: "pointer" }}
            >
              {loading ? "Processing..." : mode === "register" ? "📸 Capture & Register" : mode === "login" ? "📸 Capture & Login" : "📸 Capture & Identify"}
            </button>
            <button onClick={goHome} style={{ padding: "10px", background: "transparent", color: "#666370", border: "none", fontSize: "13px", cursor: "pointer" }}>
              ← Back
            </button>
          </div>
        )}

        {mode === "ask" && (
          <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
            <textarea
              placeholder="e.g. did alice ever have a failed login?"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              rows={3}
              style={{ padding: "12px", background: "#1c1c21", border: "1px solid rgba(255,255,255,0.07)", borderRadius: "6px", color: "#e8e6e1", fontSize: "14px", outline: "none", fontFamily: "monospace", resize: "vertical" }}
            />
            <button
              onClick={handleAsk}
              disabled={loading}
              style={{ padding: "14px", background: "#a78bfa", color: "#0c0c0e", border: "none", borderRadius: "6px", fontSize: "14px", fontWeight: "600", cursor: "pointer" }}
            >
              {loading ? "Thinking..." : "Ask"}
            </button>

            {askResult && (
              <div style={{ background: "#1c1c21", border: "1px solid rgba(255,255,255,0.07)", borderRadius: "6px", padding: "14px", fontSize: "13px" }}>
                {askResult.answer && (
                  <>
                    <p style={{ color: "#e8e6e1", marginBottom: "10px" }}>{askResult.answer}</p>
                    {askResult.citations.length > 0 && (
                      <p style={{ color: "#666370", fontSize: "11px" }}>
                        Cited: {askResult.citations.join(", ")}
                      </p>
                    )}
                  </>
                )}
                {!askResult.answer && askResult.retrieved && (
                  <>
                    <p style={{ color: "#666370", fontSize: "11px", marginBottom: "8px" }}>{askResult.note}</p>
                    <ul style={{ margin: 0, paddingLeft: "18px", color: "#e8e6e1" }}>
                      {askResult.retrieved.map((snippet, i) => (
                        <li key={i} style={{ marginBottom: "6px" }}>{snippet}</li>
                      ))}
                    </ul>
                  </>
                )}
                {!askResult.answer && !askResult.retrieved && (
                  <p style={{ color: "#666370" }}>{askResult.note ?? "No relevant events found."}</p>
                )}
              </div>
            )}

            <button onClick={goHome} style={{ padding: "10px", background: "transparent", color: "#666370", border: "none", fontSize: "13px", cursor: "pointer" }}>
              ← Back
            </button>
          </div>
        )}

        {mode === "success" && (
          <div style={{ textAlign: "center" }}>
            <div style={{ fontSize: "48px", marginBottom: "16px" }}>✅</div>
            <h2 style={{ fontFamily: "serif", fontSize: "24px", marginBottom: "8px" }}>Welcome, {username}!</h2>
            <p style={{ color: "#666370", fontSize: "13px", marginBottom: "24px" }}>Face authentication successful.</p>
            <div style={{ background: "#1c1c21", border: "1px solid rgba(255,255,255,0.07)", borderRadius: "6px", padding: "12px", marginBottom: "16px", wordBreak: "break-all" }}>
              <p style={{ color: "#666370", fontSize: "10px", letterSpacing: "0.1em", marginBottom: "6px" }}>JWT TOKEN</p>
              <p style={{ color: "#a78bfa", fontSize: "11px" }}>{token}</p>
            </div>

            {protectedMessage ? (
              <div style={{ background: "rgba(52,211,153,0.1)", border: "1px solid rgba(52,211,153,0.3)", borderRadius: "6px", padding: "12px", marginBottom: "24px", color: "#34d399", fontSize: "13px" }}>
                {protectedMessage}
              </div>
            ) : (
              <button
                onClick={callProtected}
                disabled={loading}
                style={{ width: "100%", padding: "12px", marginBottom: "24px", background: "transparent", color: "#a78bfa", border: "1px solid rgba(167,139,250,0.4)", borderRadius: "6px", fontSize: "13px", cursor: "pointer" }}
              >
                {loading ? "Checking..." : "🔐 Call /api/protected with this token"}
              </button>
            )}

            <button onClick={goHome} style={{ padding: "12px 24px", background: "transparent", color: "#e8e6e1", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "6px", fontSize: "13px", cursor: "pointer" }}>
              ← Back to Home
            </button>
          </div>
        )}
      </div>
    </div>
  );
}