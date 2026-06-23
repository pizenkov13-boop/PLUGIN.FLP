import WaveformStrip from "./WaveformStrip";
import { IconPlay } from "./icons";
import "./PlayerBar.css";

type Props = {
  busy: boolean;
  beatReady: boolean;
  statusLine: string;
  quotaLabel?: string;
  onOpenInFl: () => void;
  onCreate: () => void;
  canCreate: boolean;
};

export default function PlayerBar({
  busy,
  beatReady,
  statusLine,
  quotaLabel,
  onOpenInFl,
  onCreate,
  canCreate,
}: Props) {
  return (
    <footer className="player">
      <button
        type="button"
        className={`player__play ${busy ? "player__play--busy" : ""}`}
        onClick={canCreate ? onCreate : beatReady ? onOpenInFl : undefined}
        disabled={!canCreate && !beatReady}
        title={canCreate ? "Create beat" : beatReady ? "Open in FL" : "Describe a beat first"}
      >
        <IconPlay />
      </button>

      <div className="player__center">
        <WaveformStrip active={busy} ready={beatReady} />
        <p className={`player__status ${busy ? "player__status--busy" : ""}`}>{statusLine}</p>
      </div>

      <div className="player__right">
        {quotaLabel && <span className="player__quota">{quotaLabel}</span>}
        <button
          type="button"
          className={`player__fl ${beatReady ? "player__fl--ready" : ""}`}
          onClick={onOpenInFl}
          disabled={!beatReady || busy}
        >
          Open in FL
        </button>
      </div>
    </footer>
  );
}
