import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import type { Locale, Messages, LocalePack } from "./types";
import { LOCALE_OPTIONS, RTL_LOCALES } from "./types";
import { en } from "./locales/en";
import { ru } from "./locales/ru";
import { es } from "./locales/es";
import { pt } from "./locales/pt";
import { zh } from "./locales/zh";
import { ja } from "./locales/ja";
import { fr } from "./locales/fr";
import { de } from "./locales/de";
import { ar } from "./locales/ar";
import type { Quota } from "../types";

const STORAGE_KEY = "plg_locale";

const RAW: Record<Locale, Messages | LocalePack> = {
  en,
  ru,
  es,
  pt,
  zh,
  ja,
  fr,
  de,
  ar,
};

const MESSAGES: Record<Locale, Messages> = Object.fromEntries(
  Object.entries(RAW).map(([locale, pack]) => [
    locale,
    {
      ...pack,
      auth: { ...en.auth, ...pack.auth },
      settings: { ...en.settings, ...pack.settings },
      offline: { ...en.offline, ...pack.offline },
      regenerate: { ...en.regenerate, ...pack.regenerate },
      flOnboard: { ...en.flOnboard, ...pack.flOnboard },
      updates: { ...en.updates, ...pack.updates },
      help: {
        ...en.help,
        ...pack.help,
        docs: { ...en.help.docs, ...(pack.help?.docs ?? {}) },
      },
    },
  ]),
) as Record<Locale, Messages>;

function detectLocale(): Locale {
  const saved = localStorage.getItem(STORAGE_KEY) as Locale | null;
  if (saved && saved in MESSAGES) return saved;

  const lang = (navigator.language || "en").toLowerCase();
  if (lang.startsWith("ru")) return "ru";
  if (lang.startsWith("es")) return "es";
  if (lang.startsWith("pt")) return "pt";
  if (lang.startsWith("zh")) return "zh";
  if (lang.startsWith("ja")) return "ja";
  if (lang.startsWith("fr")) return "fr";
  if (lang.startsWith("de")) return "de";
  if (lang.startsWith("ar")) return "ar";
  return "en";
}

function getByPath(obj: unknown, path: string): string | undefined {
  const parts = path.split(".");
  let cur: unknown = obj;
  for (const part of parts) {
    if (cur == null || typeof cur !== "object") return undefined;
    cur = (cur as Record<string, unknown>)[part];
  }
  return typeof cur === "string" ? cur : undefined;
}

export type TParams = Record<string, string | number>;

function interpolate(text: string, params?: TParams): string {
  if (!params) return text;
  return text.replace(/\{(\w+)\}/g, (_, key: string) => String(params[key] ?? ""));
}

type I18nContextValue = {
  locale: Locale;
  setLocale: (locale: Locale) => void;
  t: (key: string, params?: TParams) => string;
  messages: Messages;
  dir: "ltr" | "rtl";
  localeOptions: typeof LOCALE_OPTIONS;
};

const I18nContext = createContext<I18nContextValue | null>(null);

export function I18nProvider({ children }: { children: ReactNode }) {
  const [locale, setLocaleState] = useState<Locale>(() => detectLocale());

  const setLocale = useCallback((next: Locale) => {
    setLocaleState(next);
    localStorage.setItem(STORAGE_KEY, next);
  }, []);

  const messages = MESSAGES[locale];
  const dir: "ltr" | "rtl" = RTL_LOCALES.includes(locale) ? "rtl" : "ltr";

  useEffect(() => {
    document.documentElement.lang = locale;
    document.documentElement.dir = dir;
  }, [locale, dir]);

  const t = useCallback(
    (key: string, params?: TParams) => {
      const text = getByPath(messages, key) ?? getByPath(en, key) ?? key;
      return interpolate(text, params);
    },
    [messages],
  );

  const value = useMemo(
    () => ({ locale, setLocale, t, messages, dir, localeOptions: LOCALE_OPTIONS }),
    [locale, setLocale, t, messages, dir],
  );

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n() {
  const ctx = useContext(I18nContext);
  if (!ctx) throw new Error("useI18n must be used within I18nProvider");
  return ctx;
}

export function formatQuotaLabel(t: I18nContextValue["t"], quota: Quota): string {
  if (quota.skipped) return "";
  return t("quota.label", {
    remaining: quota.remaining,
    limit: quota.limit,
    days: quota.days_until_reset,
  });
}

export function promptCards(messages: Messages) {
  return [
    { id: "darkTrap", tone: "violet" as const, ...messages.prompts.darkTrap },
    { id: "rageMelody", tone: "rose" as const, ...messages.prompts.rageMelody },
    { id: "pluggnb", tone: "blue" as const, ...messages.prompts.pluggnb },
    { id: "detroit", tone: "amber" as const, ...messages.prompts.detroit },
    { id: "melodic", tone: "mint" as const, ...messages.prompts.melodic },
  ];
}
