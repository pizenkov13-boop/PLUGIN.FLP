import { useI18n, promptIdeas } from "../i18n";
import "./PromptIdeas.css";

type Props = {
  onSelect: (prompt: string) => void;
  disabled?: boolean;
};

export default function PromptIdeas({ onSelect, disabled }: Props) {
  const { t, messages } = useI18n();
  const ideas = promptIdeas(messages);

  return (
    <div className="ideas">
      <span className="ideas__label typo-label">{t("home.ideas")}</span>
      <div className="ideas__chips" role="list">
        {ideas.map((idea) => (
          <button
            key={idea.id}
            type="button"
            role="listitem"
            className="ideas__chip"
            disabled={disabled}
            title={idea.prompt}
            onClick={() => onSelect(idea.prompt)}
          >
            {idea.title}
          </button>
        ))}
      </div>
    </div>
  );
}
