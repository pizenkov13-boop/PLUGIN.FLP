import { useI18n } from "../i18n";
import PromptIdeas from "./PromptIdeas";
import "./BeatComposer.css";

type Props = {
  prompt: string;
  onPromptChange: (value: string) => void;
  onCreate: () => void;
  busy: boolean;
  canCreate: boolean;
  error: string | null;
};

export default function BeatComposer({
  prompt,
  onPromptChange,
  onCreate,
  busy,
  canCreate,
  error,
}: Props) {
  const { t } = useI18n();

  return (
    <section className="beat-card" aria-labelledby="beat-prompt-label">
      <div className="beat-card__prompt">
        <header className="beat-card__head">
          <h2 id="beat-prompt-label" className="beat-card__label typo-label">
            {t("home.describeBeat")}
          </h2>
        </header>

        <textarea
          id="beat-prompt"
          className="beat-card__input"
          value={prompt}
          onChange={(e) => onPromptChange(e.target.value)}
          placeholder={t("home.promptPlaceholder")}
          rows={4}
          spellCheck={false}
          autoFocus
        />
      </div>

      <PromptIdeas
        disabled={busy}
        onSelect={(text) => {
          onPromptChange(text);
          requestAnimationFrame(() => {
            const el = document.getElementById("beat-prompt") as HTMLTextAreaElement | null;
            el?.focus();
          });
        }}
      />

      {error && (
        <div className="beat-card__error" role="alert">
          {error}
        </div>
      )}

      <button
        type="button"
        className={`cta cta--primary cta--create ${canCreate ? "cta--ready" : ""}`}
        onClick={onCreate}
        disabled={!canCreate || busy}
      >
        {t("home.createBeat")}
      </button>
    </section>
  );
}
