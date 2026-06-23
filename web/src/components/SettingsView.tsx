import { useEffect, useState } from "react";
import {
  getAppInfo,
  getQuota,
  getSettings,
  installFlScripts,
  revealPath,
  saveSettings,
  cloudLogout,
  cloudBillingStatus,
  cloudBillingCheckout,
  cloudDeleteAccount,
  cloudSubmitFeedback,
  checkForUpdates,
  downloadUpdate,
  applyDownloadedUpdate,
  openDocument,
} from "../api";
import type { AppInfo, BillingInfo, Quota } from "../types";
import { formatQuotaLabel, useI18n } from "../i18n";
import { apiErrorMessage } from "../errors";
import type { Locale } from "../i18n/types";
import "./SettingsView.css";
import "./PageView.css";

type Props = {
  onSaved: () => void;
  cloudMode?: boolean;
  authEmail?: string | null;
};

export default function SettingsView({ onSaved, cloudMode, authEmail }: Props) {
  const { t, locale, setLocale, localeOptions } = useI18n();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [installing, setInstalling] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [quota, setQuota] = useState<Quota | null>(null);
  const [appInfo, setAppInfo] = useState<AppInfo | null>(null);
  const [provider, setProvider] = useState("gemini");
  const [geminiKey, setGeminiKey] = useState("");
  const [anthropicKey, setAnthropicKey] = useState("");
  const [samplesDir, setSamplesDir] = useState("");
  const [autoOpenFl, setAutoOpenFl] = useState(false);
  const [billing, setBilling] = useState<BillingInfo | null>(null);
  const [subscribing, setSubscribing] = useState(false);
  const [feedbackCategory, setFeedbackCategory] = useState("general");
  const [feedbackMessage, setFeedbackMessage] = useState("");
  const [feedbackAttachLog, setFeedbackAttachLog] = useState(true);
  const [feedbackSending, setFeedbackSending] = useState(false);
  const [updateInfo, setUpdateInfo] = useState<string | null>(null);
  const [checkingUpdate, setCheckingUpdate] = useState(false);

  useEffect(() => {
    Promise.all([getSettings(), getQuota(), getAppInfo()])
      .then(([s, q, info]) => {
        setProvider(s.provider || "gemini");
        setGeminiKey(s.gemini_key || "");
        setAnthropicKey(s.anthropic_key || "");
        setSamplesDir(s.samples_dir || "");
        setAutoOpenFl(Boolean(s.auto_open_fl));
        setQuota(q);
        setAppInfo(info);
      })
      .finally(() => setLoading(false));

    if (cloudMode) {
      cloudBillingStatus().then((res) => {
        if (res.ok && res.billing) setBilling(res.billing);
      });
    }
  }, [cloudMode]);

  async function onSave() {
    setSaving(true);
    setError(null);
    setMessage(null);
    const result = await saveSettings({
      provider,
      gemini_key: geminiKey,
      anthropic_key: anthropicKey,
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

  if (loading) {
    return <div className="settings settings--loading">{t("common.loading")}</div>;
  }

  const quotaLabel = quota && !quota.skipped ? formatQuotaLabel(t, quota) : "";

  function billingStatusText(): string {
    if (!billing) return "";
    if (billing.status === "trial") {
      return t("settings.subscriptionTrial", { remaining: billing.trial_remaining ?? 0 });
    }
    if (billing.status === "grace") {
      return t("settings.subscriptionGrace", { days: billing.grace_days_left ?? 0 });
    }
    if (billing.status === "active") {
      return t("settings.subscriptionActive", { days: billing.days_until_renewal ?? 0 });
    }
    return t("settings.subscriptionExpired");
  }

  async function onSubscribe() {
    setSubscribing(true);
    setError(null);
    const tier = locale === "ru" ? "cis" : undefined;
    const result = await cloudBillingCheckout(tier);
    setSubscribing(false);
    if (!result.ok) {
      setError(apiErrorMessage(result, t));
      return;
    }
    const refreshed = await cloudBillingStatus();
    if (refreshed.ok && refreshed.billing) setBilling(refreshed.billing);
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

  async function onSendFeedback() {
    if (!feedbackMessage.trim()) return;
    setFeedbackSending(true);
    setError(null);
    setMessage(null);
    const result = await cloudSubmitFeedback(
      feedbackCategory,
      feedbackMessage.trim(),
      feedbackAttachLog,
    );
    setFeedbackSending(false);
    if (!result.ok) {
      setError(apiErrorMessage(result, t));
      return;
    }
    setMessage(t("settings.feedbackSent"));
    setFeedbackMessage("");
  }

  return (
    <div className="settings">
      <div className="settings__head">
        <h1>{t("settings.title")}</h1>
        <p>{t("settings.desc")}</p>
      </div>

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

      {quota && !quota.skipped && (
        <div className="settings__card">
          <h2 className="page__card-title">{t("settings.accountQuota")}</h2>
          <div className="page__stat-grid">
            <div className="page__stat">
              <strong>{quota.remaining}</strong>
              <span>{t("quota.remaining")}</span>
            </div>
            <div className="page__stat">
              <strong>{quota.used}</strong>
              <span>{t("quota.used")}</span>
            </div>
            <div className="page__stat">
              <strong>{quota.days_until_reset}</strong>
              <span>{t("quota.daysReset")}</span>
            </div>
          </div>
          <p className="page__card-desc">{quotaLabel}</p>
        </div>
      )}

      {cloudMode && (
        <div className="settings__card">
          <h2 className="page__card-title">PLG Cloud</h2>
          <p className="page__card-desc">{authEmail || t("auth.title")}</p>
          {billing && (
            <>
              <h3 className="page__card-title">{t("settings.subscription")}</h3>
              <p className="page__card-desc">{t("settings.subscriptionDesc")}</p>
              <p className="page__card-desc">{billingStatusText()}</p>
              {billing.can_subscribe && (
                <button
                  type="button"
                  className="page__btn page__btn--primary"
                  onClick={onSubscribe}
                  disabled={subscribing}
                >
                  {subscribing
                    ? t("settings.subscribing")
                    : t("settings.subscribe", { price: billing.price_label ?? "899 ₽" })}
                </button>
              )}
            </>
          )}
          <button
            type="button"
            className="page__btn page__btn--ghost"
            onClick={async () => {
              await cloudLogout();
              onSaved();
            }}
          >
            {t("auth.logout")}
          </button>
          <div className="settings__legal">
            <p className="page__card-desc">{t("settings.aiDisclaimer")}</p>
            <div className="page__row">
              <button type="button" className="page__btn page__btn--ghost" onClick={() => openDocument("terms")}>
                {t("settings.terms")}
              </button>
              <button type="button" className="page__btn page__btn--ghost" onClick={() => openDocument("privacy")}>
                {t("settings.privacy")}
              </button>
              <button type="button" className="page__btn page__btn--ghost" onClick={() => openDocument("refund")}>
                {t("settings.refund")}
              </button>
            </div>
          </div>
          <button
            type="button"
            className="page__btn page__btn--danger"
            onClick={async () => {
              if (!window.confirm(t("settings.deleteConfirm"))) return;
              setError(null);
              const result = await cloudDeleteAccount();
              if (!result.ok) {
                setError(apiErrorMessage(result, t));
                return;
              }
              onSaved();
            }}
          >
            {t("settings.deleteAccount")}
          </button>
          <div className="settings__feedback">
            <h3 className="page__card-title">{t("settings.feedback")}</h3>
            <p className="page__card-desc">{t("settings.feedbackDesc")}</p>
            <label className="settings__field">
              <span>{t("settings.feedbackCategory")}</span>
              <select value={feedbackCategory} onChange={(e) => setFeedbackCategory(e.target.value)}>
                <option value="general">{t("settings.feedbackCatGeneral")}</option>
                <option value="bug">{t("settings.feedbackCatBug")}</option>
                <option value="billing">{t("settings.feedbackCatBilling")}</option>
                <option value="feature">{t("settings.feedbackCatFeature")}</option>
              </select>
            </label>
            <label className="settings__field">
              <span>{t("settings.feedbackMessage")}</span>
              <textarea
                rows={4}
                value={feedbackMessage}
                onChange={(e) => setFeedbackMessage(e.target.value)}
                spellCheck
              />
            </label>
            <label className="settings__check">
              <input
                type="checkbox"
                checked={feedbackAttachLog}
                onChange={(e) => setFeedbackAttachLog(e.target.checked)}
              />
              <span>{t("settings.feedbackAttachLog")}</span>
            </label>
            <button
              type="button"
              className="page__btn page__btn--primary"
              onClick={onSendFeedback}
              disabled={feedbackSending || !feedbackMessage.trim()}
            >
              {feedbackSending ? t("settings.feedbackSending") : t("settings.feedbackSend")}
            </button>
          </div>
        </div>
      )}

      {!cloudMode && (
      <div className="settings__card">
        <h2 className="page__card-title">{t("settings.aiProvider")}</h2>
        <label className="settings__field">
          <span>{t("settings.provider")}</span>
          <select value={provider} onChange={(e) => setProvider(e.target.value)}>
            <option value="gemini">Gemini</option>
            <option value="anthropic">Anthropic</option>
          </select>
        </label>

        <label className="settings__field">
          <span>{t("settings.geminiKey")}</span>
          <input
            type="password"
            value={geminiKey}
            onChange={(e) => setGeminiKey(e.target.value)}
            autoComplete="off"
          />
        </label>

        <label className="settings__field">
          <span>{t("settings.anthropicKey")}</span>
          <input
            type="password"
            value={anthropicKey}
            onChange={(e) => setAnthropicKey(e.target.value)}
            autoComplete="off"
          />
        </label>
      </div>
      )}

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
