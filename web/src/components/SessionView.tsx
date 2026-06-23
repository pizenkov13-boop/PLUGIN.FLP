import type { ApiResult, BeatResult, Status } from "../types";
import { IconRegenerate } from "./icons";
import { revealPath } from "../api";
import { useI18n } from "../i18n";
import BlueprintChecklist from "./BlueprintChecklist";
import ProducerConsole from "./ProducerConsole";
import "./SessionView.css";

type Props = {
  status: Status | null;
  lastBeat: BeatResult | null;
  statusLine: string;
  busy: boolean;
  beatReady: boolean;
  prompt: string;
  onOpenInFl: () => void;
  onCreate: () => void;
  onRegenerate?: () => void;
  canCreate: boolean;
  onToolResult: (result: ApiResult) => void;
  onToolError: (message: string) => void;
  onRefresh: () => void;
};

export default function SessionView({
  status,
  lastBeat,
  statusLine,
  busy,
  beatReady,
  prompt,
  onOpenInFl,
  onCreate,
  onRegenerate,
  canCreate,
  onToolResult,
  onToolError,
  onRefresh,
}: Props) {
  const { t } = useI18n();
  const last = status?.last_prompt?.trim();
  const bpm = lastBeat?.bpm ?? status?.bpm;
  const style = lastBeat?.style ?? status?.style;
  const stemSession = lastBeat?.stem_session ?? status?.stem_session;
  const stemFiles = lastBeat?.stem_files?.length ? lastBeat.stem_files : status?.stem_files;
  const blueprint = lastBeat?.mix_blueprint ?? status?.mix_blueprint;
  const chop = status?.sample_chop;
  const filthMode = Boolean(lastBeat?.filth_mode ?? status?.filth_mode);
  const blueprintKey = stemSession || `${bpm ?? 0}-${style ?? "beat"}`;

  async function openPath(path: string | null | undefined) {
    if (!path) return;
    await revealPath(path);
  }

  function handleToolResult(result: ApiResult) {
    onToolResult(result);
    onRefresh();
  }

  return (
    <div className="session">
      <div className="session__head">
        <h1>{t("session.title")}</h1>
        <p>{t("session.desc")}</p>
      </div>

      <div className={`session__card ${beatReady ? "session__card--ready" : ""}`}>
        <div className="session__status-row">
          <span className={`session__pill ${beatReady ? "session__pill--ready" : ""}`}>
            {beatReady ? t("session.beatReady") : busy ? t("session.generating") : t("session.noBeat")}
          </span>
          <span className="session__line">{statusLine}</span>
        </div>

        <div className="session__prompt">
          <span className="session__label">{t("session.prompt")}</span>
          <p>{prompt.trim() || last || t("common.dash")}</p>
        </div>

        <div className="session__meta">
          <span>
            {t("session.provider")} · {status?.provider ?? t("common.dash")}
          </span>
          <span>
            FL · {status?.fl_bridge_ready ? t("session.connected") : t("session.offline")}
          </span>
          {bpm != null && (
            <span>
              {t("session.bpm")} · {bpm}
            </span>
          )}
          {style && (
            <span>
              {t("session.style")} · {style}
            </span>
          )}
        </div>

        {chop?.chop_count != null && (
          <div className="session__export">
            <span className="session__label">{t("session.sampleChop")}</span>
            <p className="session__export-note">
              {t("session.chopDetail", {
                count: chop.chop_count,
                pitch: chop.pitch_semitones ?? 0,
                ratio: chop.tempo_ratio ?? 1,
              })}
            </p>
          </div>
        )}

        {stemSession && (
          <div className="session__export">
            <span className="session__label">{t("session.stemExport")}</span>
            <p className="session__export-path">{stemSession}</p>
            {stemFiles && stemFiles.length > 0 && (
              <ul className="session__stems">
                {stemFiles.map((name) => (
                  <li key={name}>{name}</li>
                ))}
              </ul>
            )}
            <button type="button" className="cta cta--ghost cta--small" onClick={() => openPath(stemSession)}>
              {t("session.openStems")}
            </button>
          </div>
        )}

        {blueprint && (
          <div className="session__export">
            <span className="session__label">{t("session.mixBlueprint")}</span>
            <p className="session__export-path">READ_ME_IMBA.txt</p>
            <button type="button" className="cta cta--ghost cta--small" onClick={() => openPath(blueprint)}>
              {t("session.openMixGuide")}
            </button>
          </div>
        )}

        {status?.sample_picks && Object.keys(status.sample_picks).length > 0 && (
          <div className="session__kit">
            <span className="session__label">{t("session.matchedKit")}</span>
            <ul>
              {Object.entries(status.sample_picks).map(([role, name]) => (
                <li key={role}>
                  <strong>{role}</strong> · {name}
                </li>
              ))}
            </ul>
          </div>
        )}

        <ProducerConsole
          beatReady={beatReady}
          busy={busy}
          filthMode={filthMode}
          onUpdated={handleToolResult}
          onError={onToolError}
        />

        <BlueprintChecklist beatReady={beatReady} sessionKey={blueprintKey} />

        <div className="session__actions">
          <button
            type="button"
            className={`cta cta--primary ${beatReady ? "cta--ready" : ""}`}
            onClick={onOpenInFl}
            disabled={!beatReady || busy}
          >
            {busy ? "…" : t("session.openInFl")}
          </button>
          {beatReady && onRegenerate && (
            <button
              type="button"
              className="cta cta--ghost cta--ghost-ready session__regen"
              onClick={onRegenerate}
              disabled={busy}
              title={t("regenerate.minusOne")}
            >
              <IconRegenerate />
              <span>{t("regenerate.button")}</span>
              <span className="session__regen-cost">{t("regenerate.minusOne")}</span>
            </button>
          )}
          <button
            type="button"
            className={`cta cta--ghost ${canCreate ? "cta--ghost-ready" : ""}`}
            onClick={onCreate}
            disabled={!canCreate}
          >
            {busy ? t("home.generating") : t("session.newBeat")}
          </button>
        </div>
      </div>
    </div>
  );
}
