import { useI18n } from "../i18n";
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
  const { t } = useI18n();

  const primaryLabel = busy
    ? t("player.working")
    : beatReady
      ? t("player.openInFl")
      : canCreate
        ? t("player.createBeat")
        : t("player.describeBeat");

  const primaryAction = beatReady && !busy ? onOpenInFl : canCreate && !busy ? onCreate : undefined;

  return (
    <footer className="player">
      <div className="player__center">
        <p className={`player__status ${busy ? "player__status--busy" : ""}`}>{statusLine}</p>
        <p className="player__hint">{t("player.hint")}</p>
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
