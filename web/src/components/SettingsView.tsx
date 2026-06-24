import { useEffect, useState } from "react";
import {
  getAppInfo,
  getSettings,
  installFlScripts,
  revealPath,
  saveSettings,
  checkForUpdates,
  downloadUpdate,
  applyDownloadedUpdate,
} from "../api";
import type { AppInfo } from "../types";
import { useI18n } from "../i18n";
import { apiErrorMessage } from "../errors";
import type { Locale } from "../i18n/types";
import "./SettingsView.css";
import "./PageView.css";

type Props = {
  onSaved: () => void;
};

export default function SettingsView({ onSaved }: Props) {
  const { t, locale, setLocale, localeOptions } = useI18n();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [installing, setInstalling] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [appInfo, setAppInfo] = useState<AppInfo | null>(null);
  const [samplesDir, setSamplesDir] = useState("");
  const [autoOpenFl, setAutoOpenFl] = useState(false);
  const [updateInfo, setUpdateInfo] = useState<string | null>(null);
  const [checkingUpdate, setCheckingUpdate] = useState(false);

  useEffect(() => {
    Promise.all([getSettings(), getAppInfo()])
      .then(([s, info]) => {
        setSamplesDir(s.samples_dir || "");
        setAutoOpenFl(Boolean(s.auto_open_fl));
        setAppInfo(info);
      })
      .finally(() => setLoading(false));
  }, []);

  async function onSave() {
    setSaving(true);
    setError(null);
    setMessage(null);
    const result = await saveSettings({
      samples_dir: samplesDir,
      auto_open_fl: autoOpenFl,
    });
    setSaving(false);
    if (!result.ok) {
      setError(apiErrorMessage(result, t));
      return;
    }
    setMessage(t("settings.saved"));
    onSaved();
    const info = await getAppInfo();
    setAppInfo(info);
  }

  async function onInstallScripts() {
    setInstalling(true);
    setError(null);
    const result = await installFlScripts();
    setInstalling(false);
    if (!result.ok) {
      setError(apiErrorMessage(result, t));
      return;
    }
    setMessage(result.message?.toString() ?? t("settings.scriptsInstalled"));
    const info = await getAppInfo();
    setAppInfo(info);
    onSaved();
  }

  async function onCheckUpdates() {
    setCheckingUpdate(true);
    setError(null);
    setUpdateInfo(null);
    const result = await checkForUpdates();
    setCheckingUpdate(false);
    if (!result.ok) {
      setError(apiErrorMessage(result, t));
      return;
    }
    if (result.update_available) {
      setUpdateInfo(t("updates.available", { version: result.latest ?? "?" }));
    } else {
      setUpdateInfo(t("updates.upToDate"));
    }
  }

  async function onDownloadUpdate() {
    setCheckingUpdate(true);
    const result = await downloadUpdate();
    setCheckingUpdate(false);
    if (!result.ok) {
      setError(apiErrorMessage(result, t));
      return;
    }
    setMessage(result.message?.toString() ?? t("updates.download"));
  }

  async function onApplyUpdate() {
    const result = await applyDownloadedUpdate();
    if (!result.ok) {
      setError(apiErrorMessage(result, t));
    }
  }

  if (loading) {
    return <div className="settings settings--loading">{t("common.loading")}</div>;
  }

  return (
    <div className="settings">
      <div className="settings__head">
        <h1>{t("settings.title")}</h1>
        <p>{t("settings.desc")}</p>
      </div>

      {appInfo && (
        <div className="settings__card">
          <div className="page__stat-grid page__stat-grid--2">
            <div className="page__stat">
              <strong>v{appInfo.version}</strong>
              <span>{t("common.version")}</span>
            </div>
            <div className="page__stat">
              <strong>{appInfo.fl_bridge_ready ? "OK" : t("common.dash")}</strong>
              <span>FL Bridge</span>
            </div>
          </div>
        </div>
      )}

      <div className="settings__card">
        <h2 className="page__card-title">{t("settings.language")}</h2>
        <label className="settings__field">
          <span>{t("settings.language")}</span>
          <select value={locale} onChange={(e) => setLocale(e.target.value as Locale)}>
            {localeOptions.map((opt) => (
              <option key={opt.id} value={opt.id}>
                {opt.label}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="settings__card">
        <h2 className="page__card-title">{t("settings.flStudio")}</h2>
        <div className="page__row">
          <span className={`page__pill ${appInfo?.fl_bridge_ready ? "page__pill--ok" : ""}`}>
            {appInfo?.fl_bridge_ready ? t("fl.online") : t("fl.offline")}
          </span>
        </div>
        <p className="page__path">{appInfo?.fl_executable || t("settings.flNotFound")}</p>
        <label className="settings__check">
          <input
            type="checkbox"
            checked={autoOpenFl}
            onChange={(e) => setAutoOpenFl(e.target.checked)}
          />
          <span>{t("settings.autoOpenFl")}</span>
        </label>
        <button type="button" className="page__btn page__btn--ghost" onClick={onInstallScripts} disabled={installing}>
          {installing ? t("settings.installing") : t("tools.installScripts")}
        </button>
      </div>

      <div className="settings__card">
        <h2 className="page__card-title">{t("settings.sampleLibrary")}</h2>
        <label className="settings__field">
          <span>{t("settings.libraryFolder")}</span>
          <input
            type="text"
            value={samplesDir}
            onChange={(e) => setSamplesDir(e.target.value)}
            spellCheck={false}
          />
        </label>
        {samplesDir && (
          <button type="button" className="page__btn page__btn--ghost" onClick={() => revealPath(samplesDir)}>
            {t("common.openExplorer")}
          </button>
        )}
      </div>

      {appInfo?.starter && (
        <div className="settings__card">
          <h2 className="page__card-title">{t("settings.starterSounds")}</h2>
          <p className="page__card-desc">
            {t("settings.starterDesc", { source: appInfo.starter.source })}
          </p>
          <div className="page__row">
            <button
              type="button"
              className="page__btn page__btn--ghost"
              onClick={() => revealPath(appInfo.starter.bundle_dir)}
            >
              {t("settings.bundledPool")}
            </button>
            <button
              type="button"
              className="page__btn page__btn--ghost"
              onClick={() => revealPath(appInfo.starter.dir)}
            >
              {t("settings.starterKit")}
            </button>
            <button
              type="button"
              className="page__btn page__btn--ghost"
              onClick={() => revealPath(appInfo.starter.incoming_dir)}
            >
              {t("settings.incomingDrops")}
            </button>
          </div>
        </div>
      )}

      <div className="settings__card">
        <h2 className="page__card-title">{t("updates.title")}</h2>
        <p className="page__path">PLUGIN.FLP v{appInfo?.version ?? t("common.dash")}</p>
        {updateInfo && <p className="page__card-desc">{updateInfo}</p>}
        <div className="page__row">
          <button type="button" className="page__btn page__btn--ghost" onClick={onCheckUpdates} disabled={checkingUpdate}>
            {checkingUpdate ? t("updates.checking") : t("updates.check")}
          </button>
          <button type="button" className="page__btn page__btn--ghost" onClick={onDownloadUpdate} disabled={checkingUpdate}>
            {t("updates.download")}
          </button>
          <button type="button" className="page__btn page__btn--ghost" onClick={onApplyUpdate}>
            {t("updates.apply")}
          </button>
        </div>
      </div>

      <div className="settings__card">
        <h2 className="page__card-title">{t("settings.about")}</h2>
        <p className="page__path">{appInfo?.project_dir}</p>
        {error && <p className="settings__error">{error}</p>}
        {message && <p className="page__success">{message}</p>}
        <button type="button" className="settings__save" onClick={onSave} disabled={saving}>
          {saving ? t("common.saving") : t("common.save")}
        </button>
      </div>
    </div>
  );
}
