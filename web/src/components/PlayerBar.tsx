/* Minimal audition strip — play preview only when a beat exists. No FL / quota noise. */

import { useRef, useState } from "react";
import { renderPreview } from "../api";
import { IconPlay } from "./icons";
import "./PlayerBar.css";

type Props = {
  busy: boolean;
  showBeatReady: boolean;
};

export default function PlayerBar({ busy, showBeatReady }: Props) {
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const [rendering, setRendering] = useState(false);
  const [playing, setPlaying] = useState(false);

  if (!showBeatReady) return null;

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

  const previewTitle = rendering ? "Rendering…" : playing ? "Pause" : "Play preview";

  return (
    <footer className="strip">
      <button
        type="button"
        className={`strip__preview ${playing ? "strip__preview--playing" : ""}`}
        onClick={onPreview}
        disabled={busy || rendering}
        title={previewTitle}
        aria-label={previewTitle}
      >
        {rendering ? <span className="strip__preview-dim">…</span> : <IconPlay />}
      </button>
      <audio
        ref={audioRef}
        onPlay={() => setPlaying(true)}
        onPause={() => setPlaying(false)}
        onEnded={() => setPlaying(false)}
      />
    </footer>
  );
}
