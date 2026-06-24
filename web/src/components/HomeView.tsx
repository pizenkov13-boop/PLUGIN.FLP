import type { ApiResult, BeatResult, Status } from "../types";
import { useI18n } from "../i18n";
import BeatComposer from "./BeatComposer";
import BeatDock from "./BeatDock";
import GeneratingState from "./GeneratingState";
import ProducerConsole from "./ProducerConsole";
import BlueprintChecklist from "./BlueprintChecklist";
import "./HomeView.css";

type Props = {
  prompt: string;
  onPromptChange: (value: string) => void;
  onCreate: () => void;
  onOpenInFl: () => void;
  onRegenerate?: () => void;
  busy: boolean;
  canCreate: boolean;
  showBeatReady: boolean;
  error: string | null;
  statusLine: string;
  status: Status | null;
  lastBeat: BeatResult | null;
  onToolResult: (result: ApiResult) => void;
  onToolError: (message: string) => void;
  onRefresh: () => void;
};

export default function HomeView({
  prompt,
  onPromptChange,
  onCreate,
  onOpenInFl,
  onRegenerate,
  busy,
  canCreate,
  showBeatReady,
  error,
  statusLine,
  status,
  lastBeat,
  onToolResult,
  onToolError,
  onRefresh,
}: Props) {
  const { t } = useI18n();
  const filthMode = Boolean(lastBeat?.filth_mode ?? status?.filth_mode);
  const stemSession = lastBeat?.stem_session ?? status?.stem_session;
  const bpm = lastBeat?.bpm ?? status?.bpm;
  const style = lastBeat?.style ?? status?.style;
  const blueprintKey = stemSession || `${bpm ?? 0}-${style ?? "beat"}`;

  function handleToolResult(result: ApiResult) {
    onToolResult(result);
    onRefresh();
  }

  return (
    <div className="home">
      {busy ? (
        <GeneratingState label={t("session.generating")} detail={statusLine} />
      ) : (
        <>
          <BeatComposer
            prompt={prompt}
            onPromptChange={onPromptChange}
            onCreate={onCreate}
            busy={busy}
            canCreate={canCreate}
            error={error}
          />

          {showBeatReady && (
            <div className="home__below">
              <BeatDock
                status={status}
                lastBeat={lastBeat}
                busy={busy}
                onOpenInFl={onOpenInFl}
                onRegenerate={onRegenerate}
              />

              <ProducerConsole
                beatReady={showBeatReady}
                busy={busy}
                filthMode={filthMode}
                onUpdated={handleToolResult}
                onError={onToolError}
              />

              <BlueprintChecklist beatReady={showBeatReady} sessionKey={blueprintKey} />
            </div>
          )}
        </>
      )}
    </div>
  );
}
