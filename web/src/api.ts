// Typed wrapper around the pywebview bridge (window.pywebview.api).
//
// pywebview injects `window.pywebview` once the page is ready and fires a
// `pywebviewready` event. Every api.<method> call returns a Promise that
// resolves with the dict plg_api returned. We add `ready()` to await injection
// and `pollJob()` to drive the start_* → get_job polling loop.

import type {
  ApiResult,
  JobHandle,
  JobSnapshot,
  Settings,
  Status,
} from "./types";

interface PywebviewApi {
  get_status(): Promise<Status>;
  get_settings(): Promise<Settings>;
  save_settings(updates: Partial<Settings>): Promise<ApiResult>;
  get_quota(): Promise<Status["quota"]>;
  scan_library(): Promise<ApiResult>;

  start_beat(prompt: string): Promise<JobHandle>;
  start_regenerate(prompt?: string | null): Promise<JobHandle>;
  start_open_in_fl(): Promise<JobHandle>;
  start_stem_split(source: string): Promise<JobHandle>;
  get_job(jobId: string): Promise<JobSnapshot>;
  clear_finished_jobs(): Promise<ApiResult>;

  open_in_fl(): Promise<ApiResult>;
  install_fl_scripts(): Promise<ApiResult>;
}

declare global {
  interface Window {
    pywebview?: { api: PywebviewApi };
  }
}

/** Resolve once the pywebview bridge is available. */
export function ready(): Promise<void> {
  return new Promise((resolve) => {
    if (window.pywebview?.api) {
      resolve();
      return;
    }
    window.addEventListener("pywebviewready", () => resolve(), { once: true });
  });
}

function api(): PywebviewApi {
  if (!window.pywebview?.api) {
    throw new Error("pywebview bridge not ready — call ready() first.");
  }
  return window.pywebview.api;
}

// Direct passthroughs ------------------------------------------------------
export const getStatus = () => api().get_status();
export const getSettings = () => api().get_settings();
export const saveSettings = (u: Partial<Settings>) => api().save_settings(u);
export const getQuota = () => api().get_quota();
export const scanLibrary = () => api().scan_library();
export const startBeat = (prompt: string) => api().start_beat(prompt);
export const startRegenerate = (prompt?: string | null) => api().start_regenerate(prompt ?? null);
export const startOpenInFl = () => api().start_open_in_fl();
export const startStemSplit = (source: string) => api().start_stem_split(source);
export const installFlScripts = () => api().install_fl_scripts();

/**
 * Poll a job until it finishes. `onUpdate` fires on every tick (running too),
 * so the UI can show phase/elapsed live. Resolves with the final snapshot.
 */
export async function pollJob(
  jobId: string,
  onUpdate?: (snap: JobSnapshot) => void,
  intervalMs = 500,
): Promise<JobSnapshot> {
  return new Promise((resolve, reject) => {
    const tick = async () => {
      try {
        const snap = await api().get_job(jobId);
        onUpdate?.(snap);
        if (snap.status === "done" || snap.status === "error" || snap.status === "unknown") {
          resolve(snap);
          return;
        }
        setTimeout(tick, intervalMs);
      } catch (err) {
        reject(err);
      }
    };
    tick();
  });
}
