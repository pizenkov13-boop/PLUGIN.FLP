import type { Status } from "../types";
import { QUICK_PROMPTS } from "../types/ui";
import KitPreview from "./KitPreview";
import "./HomeView.css";

type Props = {
  prompt: string;
  onPromptChange: (value: string) => void;
  onSelectPrompt: (value: string) => void;
  onCreate: () => void;
  onOpenInFl: () => void;
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
  busy,
  canCreate,
  beatReady,
  error,
  status,
  filter,
}: Props) {
  const needle = filter.trim().toLowerCase();
  const cards = QUICK_PROMPTS.filter(
    (c) =>
      !needle ||
      c.title.toLowerCase().includes(needle) ||
      c.subtitle.toLowerCase().includes(needle) ||
      c.prompt.toLowerCase().includes(needle),
  );

  const quota = status?.quota;
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
          <p className="hero-banner__eyebrow">AI Beat Studio</p>
          <h1 className="hero-banner__title">Создай бит из промпта</h1>
          <p className="hero-banner__desc">
            prompt → beat → FL Studio. Опиши звук — получи готовую сессию.
          </p>
          <div className="hero-banner__stats">
            {quota && !quota.skipped && <span>{quota.label}</span>}
            <span>{library} samples in library</span>
          </div>
          <div className="hero-banner__actions">
            <button
              type="button"
              className={`cta cta--primary ${canCreate ? "cta--ready" : ""}`}
              onClick={onCreate}
              disabled={!canCreate}
            >
              {busy ? "Генерация…" : "Create beat"}
            </button>
            <button
              type="button"
              className={`cta cta--ghost ${beatReady ? "cta--ghost-ready" : ""}`}
              onClick={onOpenInFl}
              disabled={!beatReady || busy}
            >
              Open in FL
            </button>
          </div>
        </div>
      </section>

      <KitPreview prompt={prompt} libraryTotal={library} />

      <section className="prompt-panel">
        <label className="prompt-panel__label" htmlFor="beat-prompt">
          Твой промпт
        </label>
        <textarea
          id="beat-prompt"
          className="prompt-panel__input"
          value={prompt}
          onChange={(e) => onPromptChange(e.target.value)}
          placeholder="trap beat, dark melody, hard 808s..."
          rows={4}
          disabled={busy}
          spellCheck={false}
        />
        {error && <p className="prompt-panel__error">{error}</p>}
      </section>

      <section className="carousel-section">
        <div className="carousel-section__head">
          <h2>Для вдохновения</h2>
          <span>быстрые промпты</span>
        </div>
        <div className="carousel">
          {cards.map((card) => (
            <button
              key={card.title}
              type="button"
              className={`prompt-card prompt-card--${card.tone}`}
              onClick={() => onSelectPrompt(card.prompt)}
              disabled={busy}
            >
              <span className="prompt-card__title">{card.title}</span>
              <span className="prompt-card__sub">{card.subtitle}</span>
            </button>
          ))}
          {cards.length === 0 && (
            <p className="carousel__empty">Ничего не найдено — попробуй другой запрос</p>
          )}
        </div>
      </section>
    </div>
  );
}
