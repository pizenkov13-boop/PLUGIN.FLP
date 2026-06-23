import type { BeatResult, Status } from "../types";
import { revealPath } from "../api";
import "./SessionView.css";

type Props = {
  status: Status | null;
  lastBeat: BeatResult | null;
  statusLine: string;
  busy: boolean;
  beatReady: boolean;
  prompt: string;
  onOpenInFl: () => void;
  onCreate: () => void;
  canCreate: boolean;
};

export default function SessionView({
  status,
  lastBeat,
  statusLine,
  busy,
  beatReady,
  prompt,
  onOpenInFl,
  onCreate,
  canCreate,
}: Props) {
  const last = status?.last_prompt?.trim();
  const bpm = lastBeat?.bpm ?? status?.bpm;
  const style = lastBeat?.style ?? status?.style;
  const stemSession = lastBeat?.stem_session ?? status?.stem_session;
  const stemFiles = lastBeat?.stem_files?.length ? lastBeat.stem_files : status?.stem_files;
  const blueprint = lastBeat?.mix_blueprint ?? status?.mix_blueprint;
  const chop = status?.sample_chop;

  async function openPath(path: string | null | undefined) {
    if (!path) return;
    await revealPath(path);
  }

  return (
    <div className="session">
      <div className="session__head">
        <h1>Сессия</h1>
        <p>Текущий бит и статус экспорта в FL Studio.</p>
      </div>

      <div className={`session__card ${beatReady ? "session__card--ready" : ""}`}>
        <div className="session__status-row">
          <span className={`session__pill ${beatReady ? "session__pill--ready" : ""}`}>
            {beatReady ? "Beat ready" : busy ? "Generating" : "No beat yet"}
          </span>
          <span className="session__line">{statusLine}</span>
        </div>

        <div className="session__prompt">
          <span className="session__label">Промпт</span>
          <p>{prompt.trim() || last || "—"}</p>
        </div>

        <div className="session__meta">
          <span>Provider · {status?.provider ?? "—"}</span>
          <span>FL · {status?.fl_bridge_ready ? "Connected" : "Offline"}</span>
          {bpm != null && <span>BPM · {bpm}</span>}
          {style && <span>Style · {style}</span>}
        </div>

        {chop?.chop_count != null && (
          <div className="session__export">
            <span className="session__label">Sample chop</span>
            <p className="session__export-note">
              {chop.chop_count} slices · pitch {chop.pitch_semitones ?? 0} st · tempo ×
              {chop.tempo_ratio ?? 1}
            </p>
          </div>
        )}

        {stemSession && (
          <div className="session__export">
            <span className="session__label">Stem export</span>
            <p className="session__export-path">{stemSession}</p>
            {stemFiles && stemFiles.length > 0 && (
              <ul className="session__stems">
                {stemFiles.map((name) => (
                  <li key={name}>{name}</li>
                ))}
              </ul>
            )}
            <button type="button" className="cta cta--ghost cta--small" onClick={() => openPath(stemSession)}>
              Open stems folder
            </button>
          </div>
        )}

        {blueprint && (
          <div className="session__export">
            <span className="session__label">Mix blueprint</span>
            <p className="session__export-path">READ_ME_IMBA.txt</p>
            <button type="button" className="cta cta--ghost cta--small" onClick={() => openPath(blueprint)}>
              Open mix guide
            </button>
          </div>
        )}

        {status?.sample_picks && Object.keys(status.sample_picks).length > 0 && (
          <div className="session__kit">
            <span className="session__label">Matched kit</span>
            <ul>
              {Object.entries(status.sample_picks).map(([role, name]) => (
                <li key={role}>
                  <strong>{role}</strong> · {name}
                </li>
              ))}
            </ul>
          </div>
        )}

        <div className="session__actions">
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
    </div>
  );
}
