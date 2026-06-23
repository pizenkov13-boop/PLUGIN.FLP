import { useEffect, useState } from "react";
import {
  getStatus,
  pollJob,
  ready,
  startBeat,
  startOpenInFl,
} from "./api";
import type { BeatResult, JobSnapshot, Status } from "./types";
import type { View } from "./types/ui";
import HomeView from "./components/HomeView";
import SessionView from "./components/SessionView";
import SettingsView from "./components/SettingsView";
import Sidebar from "./components/Sidebar";
import TopBar from "./components/TopBar";
import PlayerBar from "./components/PlayerBar";
import "./App.css";

export default function App() {
  const [view, setView] = useState<View>("home");
  const [status, setStatus] = useState<Status | null>(null);
  const [prompt, setPrompt] = useState("");
  const [busy, setBusy] = useState(false);
  const [statusLine, setStatusLine] = useState("Loading…");
  const [error, setError] = useState<string | null>(null);
  const [lastBeat, setLastBeat] = useState<BeatResult | null>(null);

  useEffect(() => {
    ready().then(refreshStatus);
  }, []);

  async function refreshStatus() {
    const s = await getStatus();
    setStatus(s);
    if (!s.has_api_key) setStatusLine("Добавь API key в настройках");
    else if (s.beat_ready) setStatusLine("Beat ready — open in FL Studio");
    else setStatusLine("Ready — опиши бит");
  }

  function onJobUpdate(snap: JobSnapshot) {
    if (snap.status === "running") {
      const secs = Math.floor(snap.elapsed);
      const tail = secs >= 75 ? " — проверь интернет / API key" : "";
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
        const result = (final.result ?? { ok: true }) as unknown as BeatResult;
        if (result.ok) setLastBeat(result);
        setView("session");
        await refreshStatus();
        if (result.auto_open_fl) await onOpenInFl();
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
  const flReady = status?.fl_bridge_ready ?? false;
  const hasPrompt = Boolean(prompt.trim());
  const canCreate = hasPrompt && !busy;
  const showTopSearch = view === "home";

  return (
    <div className="shell">
      <Sidebar
        view={view}
        onNavigate={setView}
        beatReady={beatReady}
        flReady={flReady}
      />

      <div className="shell__main">
        {showTopSearch && (
          <TopBar
            value={prompt}
            onChange={setPrompt}
            onSubmit={onCreate}
            disabled={busy}
            provider={status?.provider}
          />
        )}

        <main className="shell__content">
          {view === "home" && (
            <HomeView
              prompt={prompt}
              onPromptChange={setPrompt}
              onSelectPrompt={setPrompt}
              onCreate={onCreate}
              onOpenInFl={onOpenInFl}
              busy={busy}
              canCreate={canCreate}
              beatReady={beatReady}
              error={error}
              status={status}
              filter={prompt}
            />
          )}
          {view === "session" && (
            <SessionView
              status={status}
              lastBeat={lastBeat}
              statusLine={statusLine}
              busy={busy}
              beatReady={beatReady}
              prompt={prompt}
              onOpenInFl={onOpenInFl}
              onCreate={onCreate}
              canCreate={canCreate}
            />
          )}
          {view === "settings" && <SettingsView onSaved={refreshStatus} />}
        </main>

        <PlayerBar
          busy={busy}
          beatReady={beatReady}
          statusLine={statusLine}
          quotaLabel={quota && !quota.skipped ? quota.label : undefined}
          onOpenInFl={onOpenInFl}
          onCreate={onCreate}
          canCreate={canCreate}
        />
      </div>
    </div>
  );
}
