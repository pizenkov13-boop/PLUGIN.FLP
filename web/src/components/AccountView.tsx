import { useEffect, useState } from "react";
import {
  getQuota,
  cloudLogout,
  cloudBillingStatus,
  cloudBillingCheckout,
  cloudDeleteAccount,
  cloudSubmitFeedback,
  openDocument,
} from "../api";
import type { BillingInfo, Quota } from "../types";
import { formatQuotaLabel, useI18n } from "../i18n";
import { apiErrorMessage } from "../errors";
import "./SettingsView.css";
import "./PageView.css";
import "./AccountView.css";

const LEGAL_DOC_IDS = ["terms", "privacy", "refund"] as const;

type Props = {
  onSaved: () => void;
  cloudMode?: boolean;
  authEmail?: string | null;
};

export default function AccountView({ onSaved, cloudMode, authEmail }: Props) {
  const { t, locale, messages } = useI18n();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [quota, setQuota] = useState<Quota | null>(null);
  const [billing, setBilling] = useState<BillingInfo | null>(null);
  const [subscribing, setSubscribing] = useState(false);
  const [feedbackCategory, setFeedbackCategory] = useState("general");
  const [feedbackMessage, setFeedbackMessage] = useState("");
  const [feedbackAttachLog, setFeedbackAttachLog] = useState(true);
  const [feedbackSending, setFeedbackSending] = useState(false);

  useEffect(() => {
    getQuota()
      .then(setQuota)
      .finally(() => setLoading(false));

    if (cloudMode) {
      cloudBillingStatus().then((res) => {
        if (res.ok && res.billing) setBilling(res.billing);
      });
    }
  }, [cloudMode]);

  if (loading) {
    return <div className="settings settings--loading">{t("common.loading")}</div>;
  }

  const quotaLabel = quota && !quota.skipped ? formatQuotaLabel(t, quota) : "";
  const quotaPct =
    quota && !quota.skipped && quota.limit > 0
      ? Math.round((quota.remaining / quota.limit) * 100)
      : 0;

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
    <div className="settings account">
      <div className="settings__head">
        <h1>{t("account.title")}</h1>
        <p>{cloudMode ? t("account.desc") : t("account.localDesc")}</p>
      </div>

      {quota && !quota.skipped && (
        <div className="settings__card settings__card--quota">
          <div className="account__quota-head">
            <h2>{t("settings.accountQuota")}</h2>
            <span className="account__quota-badge">
              {quota.remaining}/{quota.limit}
            </span>
          </div>

          <div className="account__quota-bar-wrap">
            <div className="account__quota-bar-meta">
              <span>{t("quota.remaining")}</span>
              <span>{t("quota.daysReset")}</span>
            </div>
            <div className="account__quota-track" aria-hidden>
              <div className="account__quota-fill" style={{ width: `${quotaPct}%` }} />
            </div>
            <div className="account__quota-bar-nums">
              <span className="account__quota-num">
                <strong>{quota.remaining}</strong>
                <em>/{quota.limit}</em>
              </span>
              <span className="account__quota-num account__quota-num--dim">
                <strong>{quota.days_until_reset}</strong>
              </span>
            </div>
          </div>

          <div className="account__quota-metrics">
            <div className="account__quota-metric">
              <span className="account__quota-metric-label">{t("quota.remaining")}</span>
              <strong className="account__quota-metric-val">{quota.remaining}</strong>
            </div>
            <div className="account__quota-metric">
              <span className="account__quota-metric-label">{t("quota.used")}</span>
              <strong className="account__quota-metric-val">{quota.used}</strong>
            </div>
            <div className="account__quota-metric">
              <span className="account__quota-metric-label">{t("quota.daysReset")}</span>
              <strong className="account__quota-metric-val">{quota.days_until_reset}</strong>
            </div>
          </div>

          {quotaLabel && <p className="account__quota-foot">{quotaLabel}</p>}
        </div>
      )}

      {cloudMode && (
        <div className="settings__card settings__card--cloud">
          <h2 className="page__card-title">PLG Cloud</h2>
          <p className="account__email">{authEmail || t("auth.title")}</p>
          {billing && (
            <div className="account__plan">
              <h3 className="page__card-title">{t("settings.subscription")}</h3>
              <p className="account__plan-status">{billingStatusText()}</p>
              <p className="account__plan-desc">{t("settings.subscriptionDesc")}</p>
              {billing.can_subscribe && (
                <button
                  type="button"
                  className="page__btn"
                  onClick={onSubscribe}
                  disabled={subscribing}
                >
                  {subscribing
                    ? t("settings.subscribing")
                    : t("settings.subscribe", { price: billing.price_label ?? "899 ₽" })}
                </button>
              )}
            </div>
          )}
          <div className="account__actions">
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
          </div>
          <div className="account__legal">
            <h3 className="account__legal-title">{t("help.legal")}</h3>
            <ul className="account__legal-list">
              {LEGAL_DOC_IDS.map((id) => {
                const doc = messages.help.docs[id];
                if (!doc) return null;
                return (
                  <li key={id} className="account__legal-row">
                    <button
                      type="button"
                      className="account__legal-link"
                      onClick={() => openDocument(id)}
                    >
                      {doc.title}
                    </button>
                    <p className="account__legal-desc">{doc.desc}</p>
                  </li>
                );
              })}
            </ul>
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

      {error && <p className="settings__error">{error}</p>}
      {message && <p className="page__success">{message}</p>}
    </div>
  );
}
