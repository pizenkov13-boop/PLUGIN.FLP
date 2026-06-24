/* Studio loading moment — animated white equalizer, Syne headline with elapsed
   seconds, quiet phase line below. Parses the live statusLine from job poll
   (no logic changes — display only). */

import Waveform from "./Waveform";
import "./GeneratingState.css";

type Props = {
  label: string;
  detail: string;
};

/** Pull seconds + phase from status strings like "Generating · 12s · arranging". */
function parseGeneratingDetail(detail: string): { secs: string | null; phase: string; tail: string } {
  const secsMatch = detail.match(/·\s*(\d+)\s*\S+\s*·/u);
  const secs = secsMatch?.[1] ?? null;

  let phase = detail;
  let tail = "";

  if (secsMatch) {
    const afterSecs = detail.slice(secsMatch.index! + secsMatch[0].length).trim();
    const dashIdx = afterSecs.indexOf(" — ");
    if (dashIdx >= 0) {
      phase = afterSecs.slice(0, dashIdx).trim();
      tail = afterSecs.slice(dashIdx + 3).trim();
    } else {
      phase = afterSecs;
    }
  }

  return { secs, phase, tail };
}

export default function GeneratingState({ label, detail }: Props) {
  const { secs, phase, tail } = parseGeneratingDetail(detail);
  const headline = secs != null ? `${label} · ${secs}s` : label;

  return (
    <section className="generating" aria-live="polite" aria-busy="true">
      <Waveform animated bars={52} className="generating__wave" />
      <p className="generating__label">{headline}</p>
      {(phase || tail) && (
        <p className="generating__detail">
          {phase}
          {tail && <span className="generating__tail"> — {tail}</span>}
        </p>
      )}
    </section>
  );
}
