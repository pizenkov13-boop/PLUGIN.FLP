import { useState } from "react";
import { bakeSession, chaosRoll, flipBeat, setFilthMode } from "../api";
import type { ApiResult } from "../types";
import { useI18n } from "../i18n";
import "./ProducerConsole.css";

type Props = {
  beatReady: boolean;
  busy: boolean;
  filthMode?: boolean;
  onUpdated: (result: ApiResult) => void;
  onError: (message: string) => void;
};

export default function ProducerConsole({
  beatReady,
  busy,
  filthMode = false,
  onUpdated,
  onError,
}: Props) {
  const { t } = useI18n();
  const [toolBusy, setToolBusy] = useState(false);

  async function run(action: () => Promise<ApiResult>, label: string) {
    if (!beatReady || busy || toolBusy) return;
    setToolBusy(true);
    try {
      const result = await action();
      if (!result.ok) {
        onError(result.error ?? `${label} failed`);
        return;
      }
      onUpdated(result);
    } finally {
      setToolBusy(false);
    }
  }

  const locked = !beatReady || busy || toolBusy;

  return (
    <section className="console">
      <div className="console__head">
        <h3>{t("console.title")}</h3>
        {filthMode && (
          <span className="console__filth-banner" aria-live="polite">
            {t("console.filthBanner")}
          </span>
        )}
      </div>

      <div className="console__grid">
        <button
          type="button"
          className="console__btn console__btn--fire"
          disabled={locked}
          onClick={() => run(bakeSession, "Bake")}
        >
          <span className="console__icon">⚡</span>
          <span>{t("console.bake")}</span>
        </button>

        <button
          type="button"
          className="console__btn"
          disabled={locked}
          onClick={() => run(flipBeat, "Flip")}
        >
          <span className="console__icon">🔀</span>
          <span>{t("console.flip")}</span>
        </button>

        <button
          type="button"
          className="console__btn"
          disabled={locked}
          onClick={() => run(chaosRoll, "Chaos")}
        >
          <span className="console__icon">🎲</span>
          <span>{t("console.chaos")}</span>
        </button>

        <button
          type="button"
          className={`console__btn console__btn--toggle ${filthMode ? "console__btn--on" : ""}`}
          disabled={locked}
          onClick={() => run(() => setFilthMode(!filthMode), "Filth")}
        >
          <span className="console__icon">🔌</span>
          <span>{filthMode ? t("console.filthOn") : t("console.filthRoute")}</span>
        </button>
      </div>

      {toolBusy && <p className="console__hint">{t("console.applying")}</p>}
      {!beatReady && <p className="console__hint">{t("console.needBeat")}</p>}
    </section>
  );
}
