import type { BeatResult, Status } from "../types";
import { revealPath } from "../api";
import { useI18n } from "../i18n";
import { IconFl, IconFolder, IconRegenerate } from "./icons";
import Waveform from "./Waveform";
import "./BeatDock.css";

type Props = {
  status: Status | null;
  lastBeat: BeatResult | null;
  busy: boolean;
  onOpenInFl: () => void;
  onRegenerate?: () => void;
};

export default function BeatDock({
  status,
  lastBeat,
  busy,
  onOpenInFl,
  onRegenerate,
}: Props) {
  const { t } = useI18n();
  const bpm = lastBeat?.bpm ?? status?.bpm;
  const style = lastBeat?.style ?? status?.style;
  const stemSession = lastBeat?.stem_session ?? status?.stem_session;
  const blueprint = lastBeat?.mix_blueprint ?? status?.mix_blueprint;
  const stemFiles = lastBeat?.stem_files?.length ? lastBeat.stem_files : status?.stem_files;

  async function openPath(path: string | null | undefined) {
    if (!path) return;
    await revealPath(path);
  }

  return (
    <section className="beat-dock" aria-label={t("home.yourBeat")}>
      <div className="beat-dock__head">
        <div className="beat-dock__ready">
          <span className="beat-dock__dot" aria-hidden />
          {t("session.beatReady")}
        </div>
        {(bpm != null || style) && (
          <div className="beat-dock__meta">
            {bpm != null && (
              <span>
                {t("session.bpm")} · {bpm}
              </span>
            )}
            {style && <span>{style}</span>}
          </div>
        )}
      </div>

      <div className="beat-dock__monitor" aria-hidden>
        <Waveform bars={48} />
      </div>

      <div className="beat-dock__grid">
        <button
          type="button"
          className="beat-dock__tile beat-dock__tile--hero"
          onClick={onOpenInFl}
          disabled={busy}
        >
          <IconFl />
          <span className="beat-dock__tile-label">{t("home.openInFl")}</span>
        </button>

        {stemSession && (
          <button
            type="button"
            className="beat-dock__tile"
            onClick={() => openPath(stemSession)}
            disabled={busy}
          >
            <IconFolder />
            <span className="beat-dock__tile-label">{t("home.openFolder")}</span>
          </button>
        )}

        {blueprint && (
          <button
            type="button"
            className="beat-dock__tile"
            onClick={() => openPath(blueprint)}
            disabled={busy}
          >
            <IconDoc />
            <span className="beat-dock__tile-label">{t("home.openMix")}</span>
          </button>
        )}

        {onRegenerate && (
          <button
            type="button"
            className="beat-dock__tile beat-dock__tile--quiet"
            onClick={onRegenerate}
            disabled={busy}
            title={t("regenerate.minusOne")}
          >
            <IconRegenerate />
            <span className="beat-dock__tile-label">{t("regenerate.button")}</span>
          </button>
        )}
      </div>

      {stemFiles && stemFiles.length > 0 && (
        <ul className="beat-dock__stems" aria-label={t("session.stemExport")}>
          {stemFiles.map((name) => (
            <li key={name}>{name}</li>
          ))}
        </ul>
      )}
    </section>
  );
}

function IconDoc() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" aria-hidden>
      <path
        d="M8 4h6l4 4v12a1 1 0 0 1-1 1H8a1 1 0 0 1-1-1V5a1 1 0 0 1 1-1Z"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinejoin="round"
      />
      <path d="M14 4v4h4M9 13h6M9 17h4" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
    </svg>
  );
}
