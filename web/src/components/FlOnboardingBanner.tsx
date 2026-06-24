import { installFlScripts, openExternalUrl } from "../api";
import type { Status } from "../types";
import { useI18n } from "../i18n";
import "./FlOnboardingBanner.css";

const FL_STUDIO_URL = "https://www.image-line.com/fl-studio/";
const FL_VERSIONS_URL = "https://www.image-line.com/fl-studio/compare-editions/";

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
        <button type="button" className="page__btn page__btn--ghost" onClick={() => openExternalUrl(FL_VERSIONS_URL)}>
          {t("flOnboard.compatibility")}
        </button>
        {needsScripts && (
          <button type="button" className="page__btn page__btn--primary" onClick={onInstallScripts}>
            {t("tools.installScripts")}
          </button>
        )}
        {missingFl && (
          <button type="button" className="page__btn page__btn--primary" onClick={() => openExternalUrl(FL_STUDIO_URL)}>
            {t("flOnboard.getFl")}
          </button>
        )}
      </div>
    </div>
  );
}
