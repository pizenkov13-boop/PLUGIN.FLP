import { IconRegenerate } from "./icons";
import type { Status } from "../types";
import { formatQuotaLabel, promptCards, useI18n } from "../i18n";
import KitPreview from "./KitPreview";
import "./HomeView.css";

type Props = {
  prompt: string;
  onPromptChange: (value: string) => void;
  onSelectPrompt: (value: string) => void;
  onCreate: () => void;
  onOpenInFl: () => void;
  onRegenerate?: () => void;
  busy: boolean;
  canCreate: boolean;
  beatReady: boolean;
  error: string | null;
  status: Status | null;
  filter: string;
};

export default function HomeView({
  prompt,
  onPromptChange,
  onSelectPrompt,
  onCreate,
  onOpenInFl,
  onRegenerate,
  busy,
  canCreate,
  beatReady,
  error,
  status,
  filter,
}: Props) {
  const { t, messages } = useI18n();
  const needle = filter.trim().toLowerCase();
  const quota = status?.quota;
  const quotaLabel = quota && !quota.skipped ? formatQuotaLabel(t, quota) : null;
  const cards = promptCards(messages).filter(
    (c) =>
      !needle ||
      c.title.toLowerCase().includes(needle) ||
      c.subtitle.toLowerCase().includes(needle) ||
      c.prompt.toLowerCase().includes(needle),
  );

  const library = status?.library_audio_total ?? 0;

  return (
    <div className="home">
      <section className="hero-banner">
        <div className="hero-banner__art" aria-hidden>
          <div className="hero-banner__orb hero-banner__orb--a" />
          <div className="hero-banner__orb hero-banner__orb--b" />
          <div className="hero-banner__grid" />
        </div>
        <div className="hero-banner__content">
          <p className="hero-banner__eyebrow">{t("home.eyebrow")}</p>
          <h1 className="hero-banner__title">{t("home.title")}</h1>
          <p className="hero-banner__desc">{t("home.desc")}</p>
          <div className="hero-banner__stats">
            {quotaLabel && <span>{quotaLabel}</span>}
            <span>{t("home.samplesInLibrary", { count: library })}</span>
          </div>
          <div className="hero-banner__actions">
            <button
              type="button"
              className={`cta cta--primary ${canCreate ? "cta--ready" : ""}`}
              onClick={onCreate}
              disabled={!canCreate}
            >
              {busy ? t("home.generating") : t("home.createBeat")}
            </button>
            <button
              type="button"
              className={`cta cta--ghost ${beatReady ? "cta--ghost-ready" : ""}`}
              onClick={onOpenInFl}
              disabled={!beatReady || busy}
            >
              {t("home.openInFl")}
            </button>
            {beatReady && onRegenerate && (
              <button
                type="button"
                className="cta cta--ghost cta--ghost-ready home__regen"
                onClick={onRegenerate}
                disabled={busy}
                title={t("regenerate.minusOne")}
              >
                <IconRegenerate />
                <span>{t("regenerate.button")}</span>
                <span className="home__regen-cost">{t("regenerate.minusOne")}</span>
              </button>
            )}
          </div>
        </div>
      </section>

      <KitPreview prompt={prompt} libraryTotal={library} />

      <section className="prompt-panel">
        <label className="prompt-panel__label" htmlFor="beat-prompt">
          {t("home.yourPrompt")}
        </label>
        <textarea
          id="beat-prompt"
          className="prompt-panel__input"
          value={prompt}
          onChange={(e) => onPromptChange(e.target.value)}
          placeholder={t("home.promptPlaceholder")}
          rows={4}
          disabled={busy}
          spellCheck={false}
        />
        {error && <p className="prompt-panel__error">{error}</p>}
      </section>

      <section className="carousel-section">
        <div className="carousel-section__head">
          <h2>{t("home.inspiration")}</h2>
          <span>{t("home.quickPrompts")}</span>
        </div>
        <div className="carousel">
          {cards.map((card) => (
            <button
              key={card.id}
              type="button"
              className={`prompt-card prompt-card--${card.tone}`}
              onClick={() => onSelectPrompt(card.prompt)}
              disabled={busy}
            >
              <span className="prompt-card__title">{card.title}</span>
              <span className="prompt-card__sub">{card.subtitle}</span>
            </button>
          ))}
          {cards.length === 0 && <p className="carousel__empty">{t("home.noResults")}</p>}
        </div>
      </section>
    </div>
  );
}
