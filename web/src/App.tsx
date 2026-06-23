import { useEffect, useState } from "react";
import {
  getStatus,
  pollJob,
  ready,
  startBeat,
  startOpenInFl,
} from "./api";
import type { JobSnapshot, Status } from "./types";

// NOTE: zero design here on purpose — just enough markup to prove the bridge
// end-to-end (prompt → CREATE BEAT → OPEN IN FL → status → quota). The opium ×
// apple visual pass (logo, Anton, theme) is a separate later step.

const PLACEHOLDER = "trap beat, dark melody, hard 808s...";

export default function App() {
  const [status, setStatus] = useState<Status | null>(null);
  const [prompt, setPrompt] = useState("");
  const [busy, setBusy] = useState(false);
  const [statusLine, setStatusLine] = useState("Loading…");
  const [error, setError] = useState<string | null>(null);

  // Wait for the bridge, then load initial status.
  useEffect(() => {
    ready().then(refreshStatus);
  }, []);

  async function refreshStatus() {
    const s = await getStatus();
    setStatus(s);
    if (!s.has_api_key) setStatusLine("Add an API key in Settings to generate beats");
    else if (s.beat_ready) setStatusLine("Beat ready — open in FL Studio");
    else setStatusLine("Ready — describe your beat");
  }

  function onJobUpdate(snap: JobSnapshot) {
    if (snap.status === "running") {
      const secs = Math.floor(snap.elapsed);
      const tail = secs >= 75 ? " — check internet / API key" : "";
      setStatusLine(`Generating · ${secs}s · ${snap.phase}${tail}`);
    }
  }

  async function onCreate() {
    const text = prompt.trim();
    if (!text || busy) return;
    setBusy(true);
    setError(null);
    setStatusLine("Starting…");
    try {
      const handle = await startBeat(text);
      const final = await pollJob(handle.job_id, onJobUpdate);
      if (final.status === "error") {
        setError(final.error ?? "Generation failed.");
        setStatusLine("Error");
      } else {
        setStatusLine("Beat ready");
        await refreshStatus();
        const result = final.result as { auto_open_fl?: boolean } | null;
        if (result?.auto_open_fl) await onOpenInFl();
      }
    } finally {
      setBusy(false);
    }
  }

  async function onOpenInFl() {
    if (busy) return;
    setBusy(true);
    setError(null);
    setStatusLine("Opening FL Studio…");
    try {
      const handle = await startOpenInFl();
      const final = await pollJob(handle.job_id);
      if (final.status === "error") {
        setError(final.error ?? "Could not open FL.");
        setStatusLine("FL error");
      } else {
        const result = final.result as { message?: string } | null;
        setStatusLine(result?.message ?? "FL Studio opened");
        await refreshStatus();
      }
    } finally {
      setBusy(false);
    }
  }

  const quota = status?.quota;
  const beatReady = status?.beat_ready ?? false;

  return (
    <div style={{ fontFamily: "system-ui, sans-serif", color: "#eee", background: "#0a0a0a", minHeight: "100vh", padding: 24 }}>
      <header style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 24 }}>
        <strong style={{ fontSize: 22 }}>PLG</strong>
        <span style={{ fontSize: 12, opacity: 0.7 }}>
          {status?.provider ?? "—"} · FL Bridge: {status?.fl_bridge_ready ? "Connected" : "Not connected"}
        </span>
      </header>

      <label style={{ display: "block", fontSize: 11, letterSpacing: 1, opacity: 0.6, marginBottom: 6 }}>
        DESCRIBE YOUR BEAT
      </label>
      <textarea
        value={prompt}
        onChange={(e) => setPrompt(e.target.value)}
        placeholder={PLACEHOLDER}
        rows={4}
        disabled={busy}
        style={{ width: "100%", boxSizing: "border-box", background: "#141414", color: "#eee", border: "1px solid #333", borderRadius: 6, padding: 12, fontSize: 14, resize: "vertical" }}
      />

      <div style={{ display: "flex", gap: 12, marginTop: 16 }}>
        <button onClick={onCreate} disabled={busy || !prompt.trim()} style={{ padding: "10px 20px" }}>
          {busy ? "GENERATING…" : "CREATE BEAT"}
        </button>
        <button onClick={onOpenInFl} disabled={busy || !beatReady} style={{ padding: "10px 20px" }}>
          OPEN IN FL
        </button>
      </div>

      {error && (
        <p style={{ color: "#ff5c5c", fontSize: 13, marginTop: 16, whiteSpace: "pre-wrap" }}>{error}</p>
      )}

      <footer style={{ display: "flex", justifyContent: "space-between", marginTop: 32, fontSize: 12, opacity: 0.7 }}>
        <span>{statusLine}</span>
        <span>{quota && !quota.skipped ? quota.label : ""}</span>
      </footer>
    </div>
  );
}
