"use client";

import { useState, useRef, useCallback } from "react";

export default function Home() {
  const [mode, setMode] = useState<"home" | "register" | "login" | "success">("home");
  const [username, setUsername] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [token, setToken] = useState("");
  const [loading, setLoading] = useState(false);
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const streamRef = useRef<MediaStream | null>(null);

  const startCamera = useCallback(async () => {
    const stream = await navigator.mediaDevices.getUserMedia({ video: true });
    streamRef.current = stream;
    if (videoRef.current) {
      videoRef.current.srcObject = stream;
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
      const res = await fetch("http://localhost:5000/api/register", {
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
      const res = await fetch("http://localhost:5000/api/login", {
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

  const goHome = () => {
    stopCamera();
    setMode("home");
    setError("");
    setMessage("");
    setUsername("");
  };

  const enterMode = async (m: "register" | "login") => {
    setMode(m);
    setError("");
    setMessage("");
    await startCamera();
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
              Register your face or log in using facial recognition.
            </p>
            <button onClick={() => enterMode("register")} style={{ padding: "14px", background: "#a78bfa", color: "#0c0c0e", border: "none", borderRadius: "6px", fontSize: "14px", fontWeight: "600", cursor: "pointer" }}>
              Register Face
            </button>
            <button onClick={() => enterMode("login")} style={{ padding: "14px", background: "transparent", color: "#e8e6e1", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "6px", fontSize: "14px", cursor: "pointer" }}>
              Login with Face
            </button>
          </div>
        )}

        {(mode === "register" || mode === "login") && (
          <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
            <video ref={videoRef} autoPlay playsInline style={{ width: "100%", borderRadius: "8px", border: "1px solid rgba(255,255,255,0.07)" }} />
            <canvas ref={canvasRef} style={{ display: "none" }} />
            <input
              type="text"
              placeholder="Enter your username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              style={{ padding: "12px", background: "#1c1c21", border: "1px solid rgba(255,255,255,0.07)", borderRadius: "6px", color: "#e8e6e1", fontSize: "14px", outline: "none" }}
            />
            <button
              onClick={mode === "register" ? handleRegister : handleLogin}
              disabled={loading}
              style={{ padding: "14px", background: "#a78bfa", color: "#0c0c0e", border: "none", borderRadius: "6px", fontSize: "14px", fontWeight: "600", cursor: "pointer" }}
            >
              {loading ? "Processing..." : mode === "register" ? "📸 Capture & Register" : "📸 Capture & Login"}
            </button>
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
            <div style={{ background: "#1c1c21", border: "1px solid rgba(255,255,255,0.07)", borderRadius: "6px", padding: "12px", marginBottom: "24px", wordBreak: "break-all" }}>
              <p style={{ color: "#666370", fontSize: "10px", letterSpacing: "0.1em", marginBottom: "6px" }}>JWT TOKEN</p>
              <p style={{ color: "#a78bfa", fontSize: "11px" }}>{token}</p>
            </div>
            <button onClick={goHome} style={{ padding: "12px 24px", background: "transparent", color: "#e8e6e1", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "6px", fontSize: "13px", cursor: "pointer" }}>
              ← Back to Home
            </button>
          </div>
        )}
      </div>
    </div>
  );
}