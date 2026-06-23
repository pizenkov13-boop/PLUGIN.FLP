import { useRef, useState } from "react";
import { useI18n } from "../i18n";
import { renderPreview } from "../api";
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
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const [rendering, setRendering] = useState(false);
  const [playing, setPlaying] = useState(false);

  async function onPreview() {
    const el = audioRef.current;
    if (!el || rendering) return;
    if (playing) {
      el.pause();
      return;
    }
    if (!el.src) {
      setRendering(true);
      try {
        const res = await renderPreview();
        if (res.ok && res.audio) el.src = res.audio as string;
        else return;
      } finally {
        setRendering(false);
      }
    }
    void el.play();
  }

  const previewLabel = rendering ? "…" : playing ? "⏸" : "▶";
  const previewTitle = rendering ? "Rendering…" : playing ? "Pause" : "Play preview";

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
        {beatReady && (
          <button
            type="button"
            className={`player__preview ${playing ? "player__preview--playing" : ""}`}
            onClick={onPreview}
            disabled={busy || rendering}
            title={previewTitle}
            aria-label={previewTitle}
          >
            {previewLabel}
          </button>
        )}
        <button
          type="button"
          className={`player__fl ${beatReady ? "player__fl--ready" : canCreate ? "player__fl--accent" : ""}`}
          onClick={primaryAction}
          disabled={!primaryAction}
        >
          {primaryLabel}
        </button>
      </div>
      <audio
        ref={audioRef}
        onPlay={() => setPlaying(true)}
        onPause={() => setPlaying(false)}
        onEnded={() => setPlaying(false)}
      />
    </footer>
  );
}
