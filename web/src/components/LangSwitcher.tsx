import { useEffect, useRef, useState } from "react";
import { useI18n } from "../i18n";
import "./LangSwitcher.css";

type Props = {
  /** Menu opens upward — for sidebar footer placement. */
  dropUp?: boolean;
  /** Flat trigger — inside sidebar deck panel (no outer border). */
  panel?: boolean;
};

export default function LangSwitcher({ dropUp = false, panel = false }: Props) {
  const { locale, setLocale, localeOptions, t } = useI18n();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement | null>(null);
  const current = localeOptions.find((o) => o.id === locale);

  useEffect(() => {
    if (!open) return;
    function onDown(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    document.addEventListener("mousedown", onDown);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onDown);
      document.removeEventListener("keydown", onKey);
    };
  }, [open]);

  return (
    <div className={`lang ${dropUp ? "lang--up" : ""} ${panel ? "lang--panel" : ""}`} ref={ref}>
      <button
        type="button"
        className={`lang__trigger ${open ? "lang__trigger--open" : ""}`}
        onClick={() => setOpen((v) => !v)}
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-label={t("settings.language")}
      >
        <span className="lang__current">{locale.toUpperCase()}</span>
        <span className="lang__name">{current?.label ?? locale}</span>
        <span className={`lang__chev ${open ? "lang__chev--open" : ""}`} aria-hidden>
          ▾
        </span>
      </button>

      {open && (
        <ul className="lang__menu" role="listbox">
          {localeOptions.map((opt) => (
            <li key={opt.id}>
              <button
                type="button"
                role="option"
                aria-selected={opt.id === locale}
                className={`lang__option ${opt.id === locale ? "lang__option--active" : ""}`}
                onClick={() => {
                  setLocale(opt.id);
                  setOpen(false);
                }}
              >
                <span className="lang__option-code">{opt.id}</span>
                <span className="lang__option-label">{opt.label}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
