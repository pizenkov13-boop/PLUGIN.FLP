import { useEffect, useState } from "react";
import { getSettings, saveSettings } from "../api";
import type { Settings } from "../types";
import "./SettingsView.css";

type Props = {
  onSaved: () => void;
};

export default function SettingsView({ onSaved }: Props) {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [provider, setProvider] = useState("gemini");
  const [geminiKey, setGeminiKey] = useState("");
  const [anthropicKey, setAnthropicKey] = useState("");
  const [samplesDir, setSamplesDir] = useState("");
  const [autoOpenFl, setAutoOpenFl] = useState(false);

  useEffect(() => {
    getSettings()
      .then((s: Settings) => {
        setProvider(s.provider || "gemini");
        setGeminiKey(s.gemini_key || "");
        setAnthropicKey(s.anthropic_key || "");
        setSamplesDir(s.samples_dir || "");
        setAutoOpenFl(Boolean(s.auto_open_fl));
      })
      .finally(() => setLoading(false));
  }, []);

  async function onSave() {
    setSaving(true);
    setError(null);
    const result = await saveSettings({
      provider,
      gemini_key: geminiKey,
      anthropic_key: anthropicKey,
      samples_dir: samplesDir,
      auto_open_fl: autoOpenFl,
    });
    setSaving(false);
    if (!result.ok) {
      setError(result.error ?? "Could not save settings.");
      return;
    }
    onSaved();
  }

  if (loading) {
    return <div className="settings settings--loading">Загрузка…</div>;
  }

  return (
    <div className="settings">
      <div className="settings__head">
        <h1>Настройки</h1>
        <p>API keys хранятся локально в .env — не в облаке.</p>
      </div>

      <div className="settings__card">
        <label className="settings__field">
          <span>AI provider</span>
          <select value={provider} onChange={(e) => setProvider(e.target.value)}>
            <option value="gemini">Gemini</option>
            <option value="anthropic">Anthropic</option>
          </select>
        </label>

        <label className="settings__field">
          <span>Gemini API key</span>
          <input
            type="password"
            value={geminiKey}
            onChange={(e) => setGeminiKey(e.target.value)}
            autoComplete="off"
          />
        </label>

        <label className="settings__field">
          <span>Anthropic API key</span>
          <input
            type="password"
            value={anthropicKey}
            onChange={(e) => setAnthropicKey(e.target.value)}
            autoComplete="off"
          />
        </label>

        <label className="settings__field">
          <span>Sample library folder</span>
          <input
            type="text"
            value={samplesDir}
            onChange={(e) => setSamplesDir(e.target.value)}
            spellCheck={false}
          />
        </label>

        <label className="settings__check">
          <input
            type="checkbox"
            checked={autoOpenFl}
            onChange={(e) => setAutoOpenFl(e.target.checked)}
          />
          <span>Открывать FL Studio после Create beat</span>
        </label>

        {error && <p className="settings__error">{error}</p>}

        <button type="button" className="settings__save" onClick={onSave} disabled={saving}>
          {saving ? "Сохранение…" : "Сохранить"}
        </button>
      </div>
    </div>
  );
}
