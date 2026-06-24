import { useEffect, useState } from "react";
import {
  bakeSession,
  getStatus,
  installFlScripts,
  pickFolder,
  scanLibrary,
  importKitFolder,
} from "../api";
import type { Status } from "../types";
import { useI18n } from "../i18n";
import { apiErrorMessage } from "../errors";
import "./PageView.css";

export default function ToolsView() {
  const { t } = useI18n();
  const [status, setStatus] = useState<Status | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    getStatus().then(setStatus);
  }, []);

  async function onInstallScripts() {
    setBusy(true);
    setError(null);
    setMessage(null);
    const result = await installFlScripts();
    setBusy(false);
    if (!result.ok) {
      setError(apiErrorMessage(result, t));
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
      setError(apiErrorMessage(result, t));
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
      setError(apiErrorMessage(result, t));
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
      setError(apiErrorMessage(result, t));
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
