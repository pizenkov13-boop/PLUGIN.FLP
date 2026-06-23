import { useI18n } from "../i18n";
import { IconSearch } from "./icons";
import "./TopBar.css";

type Props = {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  disabled?: boolean;
  provider?: string;
};

export default function TopBar({ value, onChange, onSubmit, disabled, provider }: Props) {
  const { t } = useI18n();

  return (
    <header className="topbar">
      <div className="topbar__search">
        <IconSearch />
        <input
          className="topbar__input"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              onSubmit();
            }
          }}
          placeholder={t("topbar.placeholder")}
          disabled={disabled}
          spellCheck={false}
        />
        <kbd className="topbar__hint">Enter</kbd>
      </div>
      {provider && <span className="topbar__provider">{provider}</span>}
    </header>
  );
}
