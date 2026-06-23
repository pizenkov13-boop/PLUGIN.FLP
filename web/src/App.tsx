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
import { formatQuotaLabel, useI18n } from "./i18n";
import { setUiLocale } from "./api";
import AuthView from "./components/AuthView";
import HomeView from "./components/HomeView";
import SessionView from "./components/SessionView";
import LibraryView from "./components/LibraryView";
import ToolsView from "./components/ToolsView";
import HelpView from "./components/HelpView";
import SettingsView from "./components/SettingsView";
import Sidebar from "./components/Sidebar";
import TopBar from "./components/TopBar";
import PlayerBar from "./components/PlayerBar";
import OfflineBanner from "./components/OfflineBanner";
import FlOnboardingBanner from "./components/FlOnboardingBanner";
import "./App.css";

function jobErrorMessage(final: JobSnapshot, t: (k: string) => string): string {
  const type = final.error_type || (final.result?.error_type as string | undefined);
  if (type === "network" || type === "cloud") return t("offline.generationFailed");
  if (type === "auth") return final.error ?? t("auth.title");
  if (type === "quota" || type === "subscription") return final.error ?? t("status.generationFailed");
  return final.error ?? t("status.generationFailed");
}

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
    if (s.cloud_mode && !s.signed_in) {
      setStatusLine(t("auth.title"));
      return;
    }
    if (s.cloud_mode && s.network_online === false) {
      setStatusLine(t("offline.title"));
      return;
    }
    if (!s.has_api_key) setStatusLine(t("status.needApiKey"));
    else if (s.beat_ready) setStatusLine(t("status.readyOpenFl"));
    else setStatusLine(t("status.readyDescribe"));
  }

  function onJobUpdate(snap: JobSnapshot) {
    if (snap.status === "running") {
      const secs = Math.floor(snap.elapsed);
      const tail = secs >= 75 ? t("status.checkNetwork") : "";
      setStatusLine(t("status.generating", { secs, phase: snap.phase }) + tail);
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
    setView("session");
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
        const type = final.error_type || (final.result?.error_type as string | undefined);
        if (type === "fl_not_found") {
          setError(t("flOnboard.openFailed"));
          setView("settings");
        } else {
          setError(final.error ?? t("status.flError"));
        }
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
  const quotaLabel = quota && !quota.skipped ? formatQuotaLabel(t, quota) : undefined;
  const beatReady = status?.beat_ready ?? false;
  const flReady = status?.fl_bridge_ready ?? false;
  const hasPrompt = Boolean(prompt.trim());
  const canCreate = hasPrompt && !busy && !(status?.cloud_mode && status.network_online === false);
  const showTopSearch = view === "home";
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
    <div className="shell">
      <Sidebar
        view={view}
        onNavigate={setView}
        beatReady={beatReady}
        flReady={flReady}
        quotaLabel={quotaLabel}
      />

      <div className="shell__main">
        <OfflineBanner online={networkOnline} cloudMode={status?.cloud_mode} />
        {(view === "home" || view === "session") && (
          <FlOnboardingBanner status={status} onInstalled={refreshStatus} />
        )}

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
              onRegenerate={onRegenerate}
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
              onRegenerate={onRegenerate}
              canCreate={canCreate}
              onToolResult={(result) => {
                setLastBeat(result as unknown as BeatResult);
                setStatusLine((result as ApiResult).message?.toString() ?? t("common.updated"));
              }}
              onToolError={(msg) => setError(msg)}
              onRefresh={refreshStatus}
            />
          )}
          {view === "settings" && (
            <SettingsView onSaved={refreshStatus} cloudMode={status?.cloud_mode} authEmail={status?.auth_email} />
          )}
          {view === "library" && <LibraryView />}
          {view === "tools" && <ToolsView />}
          {view === "help" && <HelpView />}
        </main>

        <PlayerBar
          busy={busy}
          beatReady={beatReady}
          statusLine={statusLine}
          quotaLabel={quotaLabel}
          canCreate={canCreate}
          onOpenInFl={onOpenInFl}
          onCreate={onCreate}
        />
      </div>
    </div>
  );
}
