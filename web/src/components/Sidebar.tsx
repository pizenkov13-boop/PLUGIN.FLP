import type { View } from "../types/ui";
import { useI18n } from "../i18n";
import { IconFl, IconHelp, IconHome, IconLibrary, IconSettings, IconTools, IconWave } from "./icons";
import logoImg from "../../../assets/logo.png";
import "./Sidebar.css";

const NAV: { id: View; icon: typeof IconHome }[] = [
  { id: "home", icon: IconHome },
  { id: "session", icon: IconWave },
  { id: "library", icon: IconLibrary },
  { id: "tools", icon: IconTools },
  { id: "help", icon: IconHelp },
  { id: "settings", icon: IconSettings },
];

type Props = {
  view: View;
  onNavigate: (view: View) => void;
  beatReady: boolean;
  flReady: boolean;
  quotaLabel?: string;
};

export default function Sidebar({ view, onNavigate, beatReady, flReady, quotaLabel }: Props) {
  const { t } = useI18n();

  return (
    <aside className="sidebar">
      <div className="sidebar__brand">
        <img className="sidebar__logo" src={logoImg} alt="PLG" />
        <span className="sidebar__name">PLUGIN.FLP</span>
      </div>

      <nav className="sidebar__nav">
        {NAV.map(({ id, icon: Icon }) => (
          <button
            key={id}
            type="button"
            className={`sidebar__item ${view === id ? "sidebar__item--active" : ""}`}
            onClick={() => onNavigate(id)}
          >
            <Icon />
            <span>{t(`nav.${id}`)}</span>
            {id === "session" && beatReady && <span className="sidebar__badge" />}
          </button>
        ))}
      </nav>

      <div className="sidebar__footer">
        {quotaLabel && <div className="sidebar__quota">{quotaLabel}</div>}
        <div className={`sidebar__fl ${flReady ? "sidebar__fl--ok" : ""}`}>
          <IconFl />
          <span>{flReady ? t("fl.online") : t("fl.offline")}</span>
        </div>
      </div>
    </aside>
  );
}
