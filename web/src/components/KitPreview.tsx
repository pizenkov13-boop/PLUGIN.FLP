import { useEffect, useState } from "react";
import { previewKit } from "../api";
import "./KitPreview.css";

const LABELS: Record<string, string> = {
  kick: "Kick",
  snare: "Snare",
  clap: "Clap",
  sub_808: "808",
  hi_hats: "Hats",
  melody_lead: "Melody",
};

const ORDER = ["sub_808", "kick", "snare", "clap", "hi_hats", "melody_lead"];

type Props = {
  prompt: string;
  libraryTotal: number;
};

export default function KitPreview({ prompt, libraryTotal }: Props) {
  const [picks, setPicks] = useState<Record<string, { name: string }>>({});
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const text = prompt.trim();
    if (!text || libraryTotal <= 0) {
      setPicks({});
      return;
    }

    setLoading(true);
    const timer = window.setTimeout(() => {
      previewKit(text)
        .then((res) => {
          if (res.ok && res.picks) setPicks(res.picks);
          else setPicks({});
        })
        .catch(() => setPicks({}))
        .finally(() => setLoading(false));
    }, 450);

    return () => window.clearTimeout(timer);
  }, [prompt, libraryTotal]);

  if (libraryTotal <= 0 || !prompt.trim()) return null;

  return (
    <section className="kit-preview">
      <div className="kit-preview__head">
        <h3>Подбор кита</h3>
        <span>{loading ? "матчинг…" : "из твоей библиотеки"}</span>
      </div>
      <div className="kit-preview__grid">
        {ORDER.map((key) => (
          <div key={key} className="kit-preview__chip">
            <span className="kit-preview__role">{LABELS[key]}</span>
            <span className="kit-preview__file">{picks[key]?.name ?? "starter"}</span>
          </div>
        ))}
      </div>
    </section>
  );
}
