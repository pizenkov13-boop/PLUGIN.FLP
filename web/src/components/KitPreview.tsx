import { useEffect, useState } from "react";
import { previewKit } from "../api";
import { useI18n } from "../i18n";
import "./KitPreview.css";

const ORDER = ["sub_808", "kick", "snare", "clap", "hi_hats", "melody_lead"];

type Props = {
  prompt: string;
  libraryTotal: number;
};

export default function KitPreview({ prompt, libraryTotal }: Props) {
  const { t, messages } = useI18n();
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
        <h3>{t("kit.title")}</h3>
        <span>{loading ? t("kit.matching") : t("kit.fromLibrary")}</span>
      </div>
      <div className="kit-preview__grid">
        {ORDER.map((key) => (
          <div key={key} className="kit-preview__chip">
            <span className="kit-preview__role">{messages.kit.roles[key] ?? key}</span>
            <span className="kit-preview__file">{picks[key]?.name ?? t("kit.starter")}</span>
          </div>
        ))}
      </div>
    </section>
  );
}
