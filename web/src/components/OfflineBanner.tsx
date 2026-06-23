import { useI18n } from "../i18n";
import "./OfflineBanner.css";

type Props = {
  online: boolean;
  cloudMode?: boolean;
};

export default function OfflineBanner({ online, cloudMode }: Props) {
  const { t } = useI18n();
  if (!cloudMode || online) return null;

  return (
    <div className="offline-banner" role="alert">
      <strong>{t("offline.title")}</strong>
      <span>{t("offline.desc")}</span>
    </div>
  );
}
