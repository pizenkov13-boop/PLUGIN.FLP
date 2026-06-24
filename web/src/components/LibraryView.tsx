import { useEffect, useState } from "react";
import { getSettings, importKitFolder, pickFolder, revealPath, scanLibrary } from "../api";
import type { ApiResult } from "../types";
import { useI18n } from "../i18n";
import { apiErrorMessage } from "../errors";
import "./PageView.css";

type ScanData = ApiResult & {
  root?: string;
  total?: number;
  audio_total?: number;
  audio?: Record<string, number>;
};

export default function LibraryView() {
  const { t } = useI18n();
  const [loading, setLoading] = useState(true);
  const [scanning, setScanning] = useState(false);
  const [importing, setImporting] = useState(false);
  const [samplesDir, setSamplesDir] = useState("");
  const [scan, setScan] = useState<ScanData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    getSettings()
      .then((s) => setSamplesDir(s.samples_dir || ""))
      .finally(() => setLoading(false));
  }, []);

  async function onScan() {
    setScanning(true);
    setError(null);
    setMessage(null);
    const result = (await scanLibrary()) as ScanData;
    setScanning(false);
    if (!result.ok) {
      setError(apiErrorMessage(result, t));
      return;
    }
    setScan(result);
    setMessage(t("library.scanDone", { count: result.audio_total ?? 0 }));
  }

  async function onImport() {
    setError(null);
    setMessage(null);
    const pick = await pickFolder();
    if (!pick.ok) {
      if (!pick.cancelled) setError(apiErrorMessage(pick, t));
      return;
    }
    if (!pick.path) return;

    setImporting(true);
    const result = await importKitFolder(pick.path);
    setImporting(false);
    if (!result.ok) {
      setError(apiErrorMessage(result, t));
      return;
    }
    setMessage(result.message?.toString() ?? t("library.importFailed"));
    await onScan();
  }

  async function openLibrary() {
    const path = scan?.root || samplesDir;
    if (!path) return;
    await revealPath(path);
  }

  const audioBreakdown = scan?.audio ? Object.entries(scan.audio).sort((a, b) => b[1] - a[1]) : [];

  if (loading) {
    return <div className="page page--loading">{t("common.loading")}</div>;
  }

  return (
    <div className="page">
      <div className="page__head">
        <h1>{t("library.title")}</h1>
        <p>{t("library.desc")}</p>
      </div>

      <div className="page__card">
        <h2 className="page__card-title">{t("library.folder")}</h2>
        <p className="page__path">{scan?.root || samplesDir || t("common.dash")}</p>
        <div className="page__row">
          <button type="button" className="page__btn" onClick={onScan} disabled={scanning}>
            {scanning ? t("library.scanning") : t("library.scan")}
          </button>
          <button type="button" className="page__btn page__btn--ghost" onClick={openLibrary}>
            {t("common.openExplorer")}
          </button>
          <button type="button" className="page__btn page__btn--ghost" onClick={onImport} disabled={importing}>
            {importing ? t("library.importing") : t("library.importKit")}
          </button>
        </div>
        {error && <p className="page__error">{error}</p>}
        {message && <p className="page__success">{message}</p>}
      </div>

      {scan?.ok && (
        <div className="page__card">
          <h2 className="page__card-title">{t("library.stats")}</h2>
          <div className="page__stat-grid page__stat-grid--2">
            <div className="page__stat">
              <strong>{scan.audio_total ?? 0}</strong>
              <span>{t("library.audio")}</span>
            </div>
            <div className="page__stat">
              <strong>{scan.total ?? 0}</strong>
              <span>{t("library.totalFiles")}</span>
            </div>
          </div>
          {audioBreakdown.length > 0 && (
            <ul className="page__list">
              {audioBreakdown.map(([cat, count]) => (
                <li key={cat} className="page__list-item">
                  <strong>{cat}</strong>
                  <span>
                    {count} {t("common.files")}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      <div className="page__card">
        <h2 className="page__card-title">{t("library.howToImport")}</h2>
        <p className="page__card-desc">{t("library.howToImportDesc")}</p>
      </div>
    </div>
  );
}
