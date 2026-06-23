import type { CSSProperties } from "react";
import "./WaveformStrip.css";

type Props = {
  active: boolean;
  ready?: boolean;
};

/** Studio meter — calm when idle, alive when generating or beat is ready. */
export default function WaveformStrip({ active, ready = false }: Props) {
  const bars = Array.from({ length: 72 }, (_, i) => {
    const wave = Math.sin(i * 0.22) * 0.35 + Math.cos(i * 0.11) * 0.25;
    const base = 0.18 + Math.abs(wave) * 0.62;
    return Math.min(1, base);
  });

  const mode = active ? "live" : ready ? "ready" : "idle";

  return (
    <div className={`meter meter--${mode}`} aria-hidden>
      <div className="meter__track">
        {bars.map((amp, i) => (
          <span
            key={i}
            className="meter__bar"
            style={{ "--amp": amp, "--i": i } as CSSProperties}
          />
        ))}
      </div>
      <div className="meter__fade meter__fade--left" />
      <div className="meter__fade meter__fade--right" />
    </div>
  );
}
