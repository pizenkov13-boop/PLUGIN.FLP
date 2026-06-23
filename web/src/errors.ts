import type { ApiResult, JobSnapshot } from "./types";

type ErrorCarrier = {
  error?: string | null;
  error_type?: string | null;
  result?: { error?: string; error_type?: string } | null;
};

export function resolveErrorType(target: ErrorCarrier): string | undefined {
  return (
    target.error_type ||
    (target.result?.error_type as string | undefined) ||
    undefined
  );
}

/** Map API / job error_type to a user-facing message. */
export function apiErrorMessage(
  result: ErrorCarrier & Pick<ApiResult, "error">,
  t: (key: string) => string,
): string {
  const type = resolveErrorType(result);
  if (type === "network" || type === "cloud") return t("errors.network");
  if (type === "auth") return result.error ?? t("errors.auth");
  if (type === "quota") return result.error ?? t("errors.quota");
  if (type === "subscription" || type === "billing") return result.error ?? t("errors.subscription");
  if (type === "device") return result.error ?? t("errors.device");
  if (type === "fl_not_found") return t("flOnboard.openFailed");
  if (type === "no_beat") return result.error ?? t("console.needBeat");
  if (type === "validation") return result.error ?? t("errors.validation");
  if (type === "config") return result.error ?? t("errors.config");
  if (type === "account") return result.error ?? t("errors.account");
  return result.error ?? t("common.error");
}

export function jobErrorMessage(final: JobSnapshot, t: (key: string) => string): string {
  return apiErrorMessage(
    {
      error: final.error ?? undefined,
      error_type: final.error_type,
      result: final.result as { error?: string; error_type?: string } | null,
    },
    t,
  );
}
