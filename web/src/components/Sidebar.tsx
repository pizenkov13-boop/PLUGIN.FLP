import type { View } from "../types/ui";
import type { Quota } from "../types";
import { useI18n } from "../i18n";
import PlgLogo from "./PlgLogo";
import LangSwitcher from "./LangSwitcher";
import { IconAccount, IconHelp, IconHome, IconLibrary, IconSettings, IconTools } from "./icons";
import "./Sidebar.css";

const NAV: { id: View; icon: typeof IconHome }[] = [
  { id: "home", icon: IconHome },
  { id: "library", icon: IconLibrary },
  { id: "tools", icon: IconTools },
  { id: "help", icon: IconHelp },
];

type Props = {
  view: View;
  onNavigate: (view: View) => void;
  quota?: Quota | null;
  authEmail?: string | null;
};

export default function Sidebar({ view, onNavigate, quota, authEmail }: Props) {
  const { t } = useI18n();
  const showQuota = quota && !quota.skipped;
  const pct = showQuota ? Math.round((quota.remaining / quota.limit) * 100) : 0;

  return (
    <aside className="sidebar">
      <div className="sidebar__brand" aria-hidden>
        <PlgLogo className="sidebar__logo" />
      </div>

      <div className="sidebar__stack">
        <nav className="sidebar__nav" aria-label="Main">
          {NAV.map(({ id, icon: Icon }) => (
            <button
              key={id}
              type="button"
              className={`sidebar__item ${view === id ? "sidebar__item--active" : ""}`}
              onClick={() => onNavigate(id)}
            >
              <Icon />
              <span>{t(`nav.${id}`)}</span>
            </button>
          ))}
        </nav>

        <div className="sidebar__foot">
          {showQuota && (
            <div
              className="sidebar__quota"
              title={t("quota.label", {
                remaining: quota.remaining,
                limit: quota.limit,
                days: quota.days_until_reset,
              })}
            >
              <span className="sidebar__quota-label">{t("quota.remaining")}</span>
              <div className="sidebar__quota-nums">
                <strong>{quota.remaining}</strong>
                <span className="sidebar__quota-dim">/{quota.limit}</span>
              </div>
              <div className="sidebar__quota-track" aria-hidden>
                <div className="sidebar__quota-fill" style={{ width: `${pct}%` }} />
              </div>
            </div>
          )}

          <LangSwitcher dropUp />

          <button
            type="button"
            className={`sidebar__item ${view === "account" ? "sidebar__item--active" : ""}`}
            onClick={() => onNavigate("account")}
            title={authEmail ?? undefined}
          >
            <IconAccount />
            <span>{t("nav.account")}</span>
          </button>

          <button
            type="button"
            className={`sidebar__item ${view === "settings" ? "sidebar__item--active" : ""}`}
            onClick={() => onNavigate("settings")}
          >
            <IconSettings />
            <span>{t("nav.settings")}</span>
          </button>
        </div>
      </div>
    </aside>
  );
}
