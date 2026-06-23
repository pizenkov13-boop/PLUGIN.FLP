import { useEffect, useState } from "react";
import { getAppInfo, openDocument, revealPath, cloudFetchStatus, openExternalUrl } from "../api";
import type { AppInfo } from "../types";
import { useI18n } from "../i18n";
import { faqForLocale } from "../i18n/faq";
import "./PageView.css";

const DOC_IDS = ["start_here", "fl_bridge", "fl_scripts", "fl_workflows"] as const;
const LEGAL_DOC_IDS = ["terms", "privacy", "refund"] as const;

type SupportInfo = {
  email?: string;
  telegram?: string;
  sla_hours?: string;
  updates_url?: string;
  status_url?: string;
};

export default function HelpView() {
  const { t, locale, messages } = useI18n();
  const [info, setInfo] = useState<AppInfo | null>(null);
  const [support, setSupport] = useState<SupportInfo | null>(null);
  const [openFaq, setOpenFaq] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getAppInfo().then(setInfo);
    cloudFetchStatus().then((res) => {
      if (res.ok && res.support) setSupport(res.support);
    });
  }, []);

  async function onOpenDoc(id: string) {
    setError(null);
    const result = await openDocument(id);
    if (!result.ok) setError(result.error ?? t("help.openDocFailed"));
  }

  async function onRevealProject() {
    if (!info?.project_dir) return;
    await revealPath(info.project_dir);
  }

  async function onOpenLink(url?: string) {
    if (!url) return;
    await openExternalUrl(url);
  }

  const availableDocs = DOC_IDS.filter((id) => info?.docs?.[id]);
  const legalDocs = LEGAL_DOC_IDS.filter((id) => info?.docs?.[id]);
  const faqItems = faqForLocale(locale);

  return (
    <div className="page">
      <div className="page__head">
        <h1>{t("help.title")}</h1>
        <p>{t("help.desc")}</p>
      </div>

      <div className="page__card">
        <h2 className="page__card-title">{t("help.quickFlow")}</h2>
        <ol className="page__list" style={{ listStyle: "decimal", paddingLeft: 20, gap: 10 }}>
          {messages.help.steps.map((step) => (
            <li key={step} style={{ fontSize: 13, color: "var(--text-2)", lineHeight: 1.5 }}>
              {step}
            </li>
          ))}
        </ol>
      </div>

      <div className="page__card">
        <h2 className="page__card-title">{t("help.faq")}</h2>
        <ul className="page__list page__faq">
          {faqItems.map((item) => {
            const open = openFaq === item.id;
            return (
              <li key={item.id} className="page__faq-item">
                <button
                  type="button"
                  className="page__faq-q"
                  aria-expanded={open}
                  onClick={() => setOpenFaq(open ? null : item.id)}
                >
                  {item.q}
                </button>
                {open && <p className="page__faq-a">{item.a}</p>}
              </li>
            );
          })}
        </ul>
      </div>

      <div className="page__card">
        <h2 className="page__card-title">{t("help.support")}</h2>
        <p className="page__card-desc">{t("help.supportDesc")}</p>
        <p className="page__card-desc">{t("help.supportSla", { hours: support?.sla_hours ?? "24-48" })}</p>
        <div className="page__row" style={{ flexWrap: "wrap", gap: 8 }}>
          {support?.email && (
            <button type="button" className="page__btn page__btn--ghost" onClick={() => onOpenLink(`mailto:${support.email}`)}>
              {support.email}
            </button>
          )}
          {support?.telegram && (
            <button type="button" className="page__btn page__btn--ghost" onClick={() => onOpenLink(support.telegram)}>
              Telegram
            </button>
          )}
          {support?.status_url && (
            <button type="button" className="page__btn page__btn--ghost" onClick={() => onOpenLink(support.status_url)}>
              {t("help.statusPage")}
            </button>
          )}
          {support?.updates_url && (
            <button type="button" className="page__btn page__btn--ghost" onClick={() => onOpenLink(support.updates_url)}>
              {t("help.updatesChannel")}
            </button>
          )}
        </div>
      </div>

      <div className="page__card">
        <h2 className="page__card-title">{t("help.documents")}</h2>
        <ul className="page__list">
          {availableDocs.map((id) => {
            const doc = messages.help.docs[id];
            return (
              <li key={id} className="page__list-item">
                <div>
                  <strong>{doc.title}</strong>
                  <br />
                  <span>{doc.desc}</span>
                </div>
                <button type="button" className="page__btn page__btn--ghost" onClick={() => onOpenDoc(id)}>
                  {t("common.open")}
                </button>
              </li>
            );
          })}
          {availableDocs.length === 0 && <li className="page__card-desc">{t("help.docsMissing")}</li>}
        </ul>
      </div>

      {legalDocs.length > 0 && (
        <div className="page__card">
          <h2 className="page__card-title">{t("help.legal")}</h2>
          <p className="page__card-desc">{t("help.legalDesc")}</p>
          <ul className="page__list">
            {legalDocs.map((id) => {
              const doc = messages.help.docs[id as keyof typeof messages.help.docs];
              if (!doc) return null;
              return (
                <li key={id} className="page__list-item">
                  <div>
                    <strong>{doc.title}</strong>
                    <br />
                    <span>{doc.desc}</span>
                  </div>
                  <button type="button" className="page__btn page__btn--ghost" onClick={() => onOpenDoc(id)}>
                    {t("common.open")}
                  </button>
                </li>
              );
            })}
          </ul>
        </div>
      )}

      {info && (
        <div className="page__card">
          <h2 className="page__card-title">{t("help.about")}</h2>
          <div className="page__stat-grid">
            <div className="page__stat">
              <strong>v{info.version}</strong>
              <span>{t("common.version")}</span>
            </div>
            <div className="page__stat">
              <strong>{info.fl_bridge_ready ? "OK" : t("common.dash")}</strong>
              <span>FL Bridge</span>
            </div>
            <div className="page__stat">
              <strong>{info.demucs_available ? "OK" : t("common.dash")}</strong>
              <span>Demucs</span>
            </div>
          </div>
          <p className="page__path">{info.project_dir}</p>
          <button type="button" className="page__btn page__btn--ghost" onClick={onRevealProject}>
            {t("help.openProject")}
          </button>
        </div>
      )}

      {error && <p className="page__error">{error}</p>}
    </div>
  );
}
