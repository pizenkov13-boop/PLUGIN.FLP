import "./PlayerBar.css";

type Props = {
  busy: boolean;
  beatReady: boolean;
  statusLine: string;
  quotaLabel?: string;
  canCreate: boolean;
  onOpenInFl: () => void;
  onCreate: () => void;
};

export default function PlayerBar({
  busy,
  beatReady,
  statusLine,
  quotaLabel,
  canCreate,
  onOpenInFl,
  onCreate,
}: Props) {
  const primaryLabel = busy
    ? "Working…"
    : beatReady
      ? "Open in FL Studio"
      : canCreate
        ? "Create beat"
        : "Describe a beat";

  const primaryAction = beatReady && !busy ? onOpenInFl : canCreate && !busy ? onCreate : undefined;

  return (
    <footer className="player">
      <div className="player__center">
        <p className={`player__status ${busy ? "player__status--busy" : ""}`}>{statusLine}</p>
        <p className="player__hint">Слушай и своди в FL Studio — PLG готовит сессию и stems.</p>
      </div>

      <div className="player__right">
        {quotaLabel && <span className="player__quota">{quotaLabel}</span>}
        <button
          type="button"
          className={`player__fl ${beatReady ? "player__fl--ready" : canCreate ? "player__fl--accent" : ""}`}
          onClick={primaryAction}
          disabled={!primaryAction}
        >
          {primaryLabel}
        </button>
      </div>
    </footer>
  );
}
