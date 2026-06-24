import { useEffect, useState } from "react";
import {
  getStatus,
  pollJob,
  ready,
  startBeat,
  startOpenInFl,
  startRegenerate,
} from "./api";
import type { ApiResult, BeatResult, JobSnapshot, Status } from "./types";
import type { View } from "./types/ui";
import { useI18n } from "./i18n";
import { setUiLocale } from "./api";
import AuthView from "./components/AuthView";
import HomeView from "./components/HomeView";
import LibraryView from "./components/LibraryView";
import ToolsView from "./components/ToolsView";
import HelpView from "./components/HelpView";
import AccountView from "./components/AccountView";
import SettingsView from "./components/SettingsView";
import Sidebar from "./components/Sidebar";
import PlayerBar from "./components/PlayerBar";
import OfflineBanner from "./components/OfflineBanner";
import FlOnboardingBanner from "./components/FlOnboardingBanner";
import { jobErrorMessage, resolveErrorType } from "./errors";
import "./App.css";

export default function App() {
  const { t, locale } = useI18n();
  const [view, setView] = useState<View>("home");
  const [status, setStatus] = useState<Status | null>(null);
  const [prompt, setPrompt] = useState("");
  const [busy, setBusy] = useState(false);
  const [statusLine, setStatusLine] = useState(t("status.loading"));
  const [error, setError] = useState<string | null>(null);
  const [lastBeat, setLastBeat] = useState<BeatResult | null>(null);

  useEffect(() => {
    ready().then(() => {
      setUiLocale(locale);
      refreshStatus();
    });
    const timer = window.setInterval(() => {
      if (status?.cloud_mode) refreshStatus();
    }, 45000);
    return () => window.clearInterval(timer);
  }, [status?.cloud_mode]);

  useEffect(() => {
    ready().then(() => setUiLocale(locale));
  }, [locale]);

  async function refreshStatus() {
    const s = await getStatus();
    setStatus(s);
    setPrompt((prev) => (prev.trim() ? prev : s.last_prompt?.trim() ?? ""));
    if (s.cloud_mode && !s.signed_in) {
      setStatusLine(t("auth.title"));
      return;
    }
    if (s.cloud_mode && s.network_online === false) {
      setStatusLine(t("offline.title"));
      return;
    }
    if (!s.cloud_mode && !s.has_api_key) setStatusLine(t("status.needApiKey"));
    else if (s.beat_ready) setStatusLine(t("status.readyOpenFl"));
    else setStatusLine(t("status.readyDescribe"));
  }

  function phaseLabel(phase: string): string {
    const key = `status.phases.${phase}`;
    const label = t(key);
    return label !== key ? label : phase;
  }

  function onJobUpdate(snap: JobSnapshot) {
    if (snap.status === "running") {
      const secs = Math.floor(snap.elapsed);
      const tail =
        secs >= 75 ? (status?.cloud_mode ? t("status.longWait") : t("status.checkNetwork")) : "";
      setStatusLine(t("status.generating", { secs, phase: phaseLabel(snap.phase) }) + tail);
    }
  }

  async function finishBeatJob(final: JobSnapshot) {
    if (final.status === "error") {
      setError(jobErrorMessage(final, t));
      setStatusLine(t("status.error"));
      return;
    }
    setStatusLine(t("status.baked"));
    const result = (final.result ?? { ok: true }) as unknown as BeatResult;
    if (result.ok) setLastBeat(result);
    await refreshStatus();
    if (result.auto_open_fl) await onOpenInFl();
  }

  async function onCreate() {
    const text = prompt.trim();
    if (!text || busy) return;
    if (status?.cloud_mode && status.network_online === false) {
      setError(t("offline.generationFailed"));
      return;
    }
    setBusy(true);
    setError(null);
    setStatusLine(t("status.starting"));
    try {
      const handle = await startBeat(text, locale);
      const final = await pollJob(handle.job_id, onJobUpdate);
      await finishBeatJob(final);
    } finally {
      setBusy(false);
    }
  }

  async function onRegenerate() {
    if (!status?.beat_ready || busy) return;
    if (status.cloud_mode && status.network_online === false) {
      setError(t("offline.generationFailed"));
      return;
    }
    const q = status.quota;
    if (q && !q.skipped) {
      const ok = window.confirm(
        t("regenerate.confirm", {
          remaining: q.remaining,
          limit: q.limit,
          days: q.days_until_reset,
        }),
      );
      if (!ok) return;
    }
    const regenPrompt = prompt.trim() || status.last_prompt || undefined;
    setBusy(true);
    setError(null);
    setStatusLine(t("status.starting"));
    try {
      const handle = await startRegenerate(regenPrompt || null);
      const final = await pollJob(handle.job_id, onJobUpdate);
      await finishBeatJob(final);
    } finally {
      setBusy(false);
    }
  }

  async function onOpenInFl() {
    if (busy) return;
    setBusy(true);
    setError(null);
    setStatusLine(t("status.openingFl"));
    try {
      const handle = await startOpenInFl();
      const final = await pollJob(handle.job_id);
      if (final.status === "error") {
        setError(jobErrorMessage(final, t));
        if (resolveErrorType(final) === "fl_not_found") setView("settings");
        setStatusLine(t("status.flError"));
      } else {
        const result = final.result as { message?: string } | null;
        setStatusLine(result?.message ?? t("status.flOpened"));
        await refreshStatus();
      }
    } finally {
      setBusy(false);
    }
  }

  const quota = status?.quota;
  const beatReady = status?.beat_ready ?? false;
  const hasSession = Boolean(status?.last_prompt?.trim() || lastBeat);
  const showBeatReady = beatReady && hasSession;
  const hasPrompt = Boolean(prompt.trim());
  const canCreate = hasPrompt && !busy && !(status?.cloud_mode && status.network_online === false);
  const needsAuth = Boolean(status?.cloud_mode && !status?.signed_in);
  const networkOnline = status?.network_online !== false;

  if (needsAuth) {
    return (
      <div className="shell shell--auth">
        <AuthView onAuthed={refreshStatus} />
      </div>
    );
  }

  return (
    <div className="shell shell--app">
      <Sidebar
        view={view}
        onNavigate={setView}
        quota={quota}
        authEmail={status?.auth_email}
      />

      <div className="shell__stage">
        <div className="shell__main">
        <div className="shell__banners">
          <OfflineBanner online={networkOnline} cloudMode={status?.cloud_mode} />
          {(view === "home") && (
            <FlOnboardingBanner status={status} onInstalled={refreshStatus} />
          )}
        </div>

        <main className={`shell__content ${view === "home" ? "shell__content--focus" : ""}`}>
          {view === "home" && (
            <HomeView
              prompt={prompt}
              onPromptChange={setPrompt}
              onCreate={onCreate}
              onOpenInFl={onOpenInFl}
              onRegenerate={onRegenerate}
              busy={busy}
              canCreate={canCreate}
              showBeatReady={showBeatReady}
              error={error}
              statusLine={statusLine}
              status={status}
              lastBeat={lastBeat}
              onToolResult={(result) => {
                setLastBeat(result as unknown as BeatResult);
                setStatusLine((result as ApiResult).message?.toString() ?? t("common.updated"));
              }}
              onToolError={(msg) => setError(msg)}
              onRefresh={refreshStatus}
            />
          )}
          {view === "account" && (
            <AccountView
              onSaved={refreshStatus}
              cloudMode={status?.cloud_mode}
              authEmail={status?.auth_email}
            />
          )}
          {view === "settings" && <SettingsView onSaved={refreshStatus} />}
          {view === "library" && <LibraryView />}
          {view === "tools" && <ToolsView />}
          {view === "help" && <HelpView />}
        </main>

        <PlayerBar busy={busy} showBeatReady={showBeatReady} />
      </div>
      </div>
    </div>
  );
}
