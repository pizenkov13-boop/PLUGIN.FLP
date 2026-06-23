import { useState } from "react";
import { bakeSession, chaosRoll, flipBeat, setFilthMode } from "../api";
import type { ApiResult } from "../types";
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
        <h3>Producer Console</h3>
        {filthMode && (
          <span className="console__filth-banner" aria-live="polite">
            CLIPPER ACTIVE // MAX FILTH
          </span>
        )}
      </div>

      <div className="console__grid">
        <button
          type="button"
          className="console__btn console__btn--fire"
          disabled={locked}
          onClick={() => run(bakeSession, "Bake")}
          title="Export stems, write .flp, refresh mix guide"
        >
          <span className="console__icon">⚡</span>
          <span>Bake Stems</span>
        </button>

        <button
          type="button"
          className="console__btn"
          disabled={locked}
          onClick={() => run(flipBeat, "Flip")}
          title="Reverse melody + re-chop samples"
        >
          <span className="console__icon">🔀</span>
          <span>Flip Beat</span>
        </button>

        <button
          type="button"
          className="console__btn"
          disabled={locked}
          onClick={() => run(chaosRoll, "Chaos")}
          title="New hat rolls 1/32–1/64 before snare"
        >
          <span className="console__icon">🎲</span>
          <span>Chaos Roll</span>
        </button>

        <button
          type="button"
          className={`console__btn console__btn--toggle ${filthMode ? "console__btn--on" : ""}`}
          disabled={locked}
          onClick={() => run(() => setFilthMode(!filthMode), "Filth")}
          title="Opium mix preset — configure Soft Clipper in FL"
        >
          <span className="console__icon">🔌</span>
          <span>{filthMode ? "Filth ON" : "Route Filth"}</span>
        </button>
      </div>

      {toolBusy && <p className="console__hint">Applying…</p>}
      {!beatReady && <p className="console__hint">Сгенерируй бит, чтобы открыть пульт.</p>}
    </section>
  );
}
