import type { View } from "../types/ui";
import { IconFl, IconHome, IconSettings, IconWave } from "./icons";
import logoImg from "../../../assets/logo.png";
import "./Sidebar.css";

const NAV: { id: View; label: string; icon: typeof IconHome }[] = [
  { id: "home", label: "Главная", icon: IconHome },
  { id: "session", label: "Сессия", icon: IconWave },
  { id: "settings", label: "Настройки", icon: IconSettings },
];

type Props = {
  view: View;
  onNavigate: (view: View) => void;
  beatReady: boolean;
  flReady: boolean;
};

export default function Sidebar({ view, onNavigate, beatReady, flReady }: Props) {
  return (
    <aside className="sidebar">
      <div className="sidebar__brand">
        <img className="sidebar__logo" src={logoImg} alt="PLG" />
        <span className="sidebar__name">PLUGIN.FLP</span>
      </div>

      <nav className="sidebar__nav">
        {NAV.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            type="button"
            className={`sidebar__item ${view === id ? "sidebar__item--active" : ""}`}
            onClick={() => onNavigate(id)}
          >
            <Icon />
            <span>{label}</span>
            {id === "session" && beatReady && <span className="sidebar__badge" />}
          </button>
        ))}
      </nav>

      <div className="sidebar__footer">
        <div className={`sidebar__fl ${flReady ? "sidebar__fl--ok" : ""}`}>
          <IconFl />
          <span>{flReady ? "FL Bridge online" : "FL Bridge offline"}</span>
        </div>
      </div>
    </aside>
  );
}
