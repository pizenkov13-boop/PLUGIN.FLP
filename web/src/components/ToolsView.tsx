import { useEffect, useState } from "react";
import {
  bakeSession,
  getStatus,
  installFlScripts,
  pickAudioFile,
  pickFolder,
  pollJob,
  revealPath,
  scanLibrary,
  startStemSplit,
  stemsStatus,
  importKitFolder,
} from "../api";
import type { JobSnapshot, Status } from "../types";
import { useI18n } from "../i18n";
import "./PageView.css";

export default function ToolsView() {
  const { t } = useI18n();
  const [status, setStatus] = useState<Status | null>(null);
  const [demucs, setDemucs] = useState<{ available: boolean; hint: string } | null>(null);
  const [stemFile, setStemFile] = useState<string | null>(null);
  const [stemBusy, setStemBusy] = useState(false);
  const [stemLine, setStemLine] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    getStatus().then(setStatus);
    stemsStatus().then((s) => {
      if (s.ok) setDemucs({ available: Boolean(s.available), hint: String(s.hint ?? "") });
    });
  }, []);

  function onStemUpdate(snap: JobSnapshot) {
    if (snap.status === "running") {
      setStemLine(`${snap.phase} · ${Math.floor(snap.elapsed)}s`);
    }
  }

  async function onPickStemFile() {
    setError(null);
    const pick = await pickAudioFile();
    if (!pick.ok) {
      if (!pick.cancelled) setError(pick.error ?? t("library.pickFailed"));
      return;
    }
    setStemFile(pick.path ?? null);
  }

  async function onStemSplit() {
    if (!stemFile || stemBusy) return;
    setStemBusy(true);
    setError(null);
    setMessage(null);
    setStemLine(t("status.starting"));
    try {
      const handle = await startStemSplit(stemFile);
      const final = await pollJob(handle.job_id, onStemUpdate);
      if (final.status === "error") {
        setError(final.error ?? t("common.error"));
        setStemLine("");
      } else {
        const out = final.result as { output_dir?: string; message?: string } | null;
        setMessage(out?.message ?? t("common.updated"));
        if (out?.output_dir) await revealPath(out.output_dir);
        setStemLine("");
      }
    } finally {
      setStemBusy(false);
    }
  }

  async function onInstallScripts() {
    setBusy(true);
    setError(null);
    setMessage(null);
    const result = await installFlScripts();
    setBusy(false);
    if (!result.ok) {
      setError(result.error ?? t("settings.installFailed"));
      return;
    }
    setMessage(result.message?.toString() ?? t("settings.scriptsInstalled"));
    const s = await getStatus();
    setStatus(s);
  }

  async function onBake() {
    setBusy(true);
    setError(null);
    setMessage(null);
    const result = await bakeSession();
    setBusy(false);
    if (!result.ok) {
      setError(result.error ?? t("common.error"));
      return;
    }
    setMessage(result.message?.toString() ?? t("common.updated"));
    const s = await getStatus();
    setStatus(s);
  }

  async function onScanLibrary() {
    setBusy(true);
    setError(null);
    const result = await scanLibrary();
    setBusy(false);
    if (!result.ok) {
      setError(result.error ?? t("library.scanFailed"));
      return;
    }
    setMessage(t("tools.libraryCount", { count: Number(result.audio_total ?? 0) }));
  }

  async function onImportKit() {
    setError(null);
    const pick = await pickFolder();
    if (!pick.ok || !pick.path) {
      if (!pick.cancelled && !pick.ok) setError(pick.error ?? t("library.pickFailed"));
      return;
    }
    setBusy(true);
    const result = await importKitFolder(pick.path);
    setBusy(false);
    if (!result.ok) {
      setError(result.error ?? t("library.importFailed"));
      return;
    }
    setMessage(result.message?.toString() ?? t("common.updated"));
  }

  const beatReady = status?.beat_ready ?? false;

  return (
    <div className="page">
      <div className="page__head">
        <h1>{t("tools.title")}</h1>
        <p>{t("tools.desc")}</p>
      </div>

      <div className="page__card">
        <h2 className="page__card-title">{t("tools.stemSplit")}</h2>
        <p className="page__card-desc">{t("tools.stemSplitDesc")}</p>
        <div className="page__row">
          <span className={`page__pill ${demucs?.available ? "page__pill--ok" : "page__pill--warn"}`}>
            {demucs?.available ? t("tools.demucsReady") : t("tools.demucsOffline")}
          </span>
          {!demucs?.available && demucs?.hint && <span className="page__path">{demucs.hint}</span>}
        </div>
        <p className="page__path">{stemFile ?? t("tools.noFile")}</p>
        <div className="page__row">
          <button type="button" className="page__btn page__btn--ghost" onClick={onPickStemFile}>
            {t("tools.pickAudio")}
          </button>
          <button
            type="button"
            className="page__btn"
            onClick={onStemSplit}
            disabled={!stemFile || stemBusy || !demucs?.available}
          >
            {stemBusy ? t("tools.splitting") : t("tools.splitStems")}
          </button>
        </div>
        {stemLine && <p className="page__card-desc">{stemLine}</p>}
      </div>

      <div className="page__card">
        <h2 className="page__card-title">{t("tools.flBridge")}</h2>
        <p className="page__card-desc">{t("tools.flBridgeDesc")}</p>
        <div className="page__row">
          <span className={`page__pill ${status?.fl_bridge_ready ? "page__pill--ok" : ""}`}>
            {status?.fl_bridge_ready ? t("fl.online") : t("fl.offline")}
          </span>
        </div>
        <button type="button" className="page__btn" onClick={onInstallScripts} disabled={busy}>
          {t("tools.installScripts")}
        </button>
      </div>

      <div className="page__card">
        <h2 className="page__card-title">{t("tools.sessionLibrary")}</h2>
        <div className="page__row">
          <button type="button" className="page__btn" onClick={onBake} disabled={busy || !beatReady}>
            {t("tools.rebake")}
          </button>
          <button type="button" className="page__btn page__btn--ghost" onClick={onScanLibrary} disabled={busy}>
            {t("tools.scanLibrary")}
          </button>
          <button type="button" className="page__btn page__btn--ghost" onClick={onImportKit} disabled={busy}>
            {t("tools.importKit")}
          </button>
        </div>
        {!beatReady && <p className="page__card-desc">{t("tools.rebakeHint")}</p>}
      </div>

      {error && <p className="page__error">{error}</p>}
      {message && <p className="page__success">{message}</p>}
    </div>
  );
}
