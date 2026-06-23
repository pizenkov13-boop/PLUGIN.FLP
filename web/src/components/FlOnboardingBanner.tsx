import { installFlScripts, openDocument } from "../api";
import type { Status } from "../types";
import { useI18n } from "../i18n";
import "./FlOnboardingBanner.css";

type Props = {
  status: Status | null;
  onInstalled?: () => void;
};

export default function FlOnboardingBanner({ status, onInstalled }: Props) {
  const { t } = useI18n();

  if (!status) return null;
  if (status.fl_installed && status.fl_bridge_ready) return null;

  const missingFl = !status.fl_installed;
  const needsScripts = status.fl_installed && !status.fl_bridge_ready;

  async function onInstallScripts() {
    const result = await installFlScripts();
    if (result.ok) onInstalled?.();
  }

  return (
    <div className="fl-onboard" role="status">
      <div className="fl-onboard__body">
        <strong>{missingFl ? t("flOnboard.noFlTitle") : t("flOnboard.scriptsTitle")}</strong>
        <p>{missingFl ? t("flOnboard.noFlDesc") : t("flOnboard.scriptsDesc")}</p>
        {status.fl_version && (
          <p className="fl-onboard__meta">{t("flOnboard.detected", { version: status.fl_version })}</p>
        )}
      </div>
      <div className="fl-onboard__actions">
        <button type="button" className="page__btn page__btn--ghost" onClick={() => openDocument("fl_versions")}>
          {t("flOnboard.compatibility")}
        </button>
        {needsScripts && (
          <button type="button" className="page__btn page__btn--primary" onClick={onInstallScripts}>
            {t("tools.installScripts")}
          </button>
        )}
        {missingFl && (
          <button
            type="button"
            className="page__btn page__btn--primary"
            onClick={() => openDocument("start_here")}
          >
            {t("flOnboard.getFl")}
          </button>
        )}
      </div>
    </div>
  );
}
