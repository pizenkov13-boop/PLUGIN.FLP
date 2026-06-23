// Typed wrapper around the pywebview bridge (window.pywebview.api).
//
// pywebview injects `window.pywebview` once the page is ready and fires a
// `pywebviewready` event. Every api.<method> call returns a Promise that
// resolves with the dict plg_api returned. We add `ready()` to await injection
// and `pollJob()` to drive the start_* → get_job polling loop.

import type {
  ApiResult,
  AppInfo,
  BillingInfo,
  JobHandle,
  JobSnapshot,
  KitPreviewResult,
  PickResult,
  Quota,
  Settings,
  Status,
} from "./types";

interface PywebviewApi {
  get_status(): Promise<Status>;
  get_settings(): Promise<Settings>;
  save_settings(updates: Partial<Settings>): Promise<ApiResult>;
  get_quota(): Promise<Quota>;
  scan_library(): Promise<ApiResult>;
  preview_kit(prompt: string): Promise<KitPreviewResult>;

  start_beat(prompt: string, locale?: string | null): Promise<JobHandle>;
  start_regenerate(prompt?: string | null): Promise<JobHandle>;
  start_open_in_fl(): Promise<JobHandle>;
  start_stem_split(source: string): Promise<JobHandle>;
  get_job(jobId: string): Promise<JobSnapshot>;
  clear_finished_jobs(): Promise<ApiResult>;

  open_in_fl(): Promise<ApiResult>;
  install_fl_scripts(): Promise<ApiResult>;
  render_preview(): Promise<ApiResult & { audio?: string; seconds?: number; path?: string }>;
  reveal_path(path: string): Promise<ApiResult>;
  chaos_roll(): Promise<ApiResult>;
  flip_beat(): Promise<ApiResult>;
  bake_session(): Promise<ApiResult>;
  set_filth_mode(enabled: boolean): Promise<ApiResult>;
  get_producer_blueprint(): Promise<ApiResult & { steps?: { id: string; text: string }[] }>;

  import_kit_folder(source: string): Promise<ApiResult>;
  get_app_info(): Promise<AppInfo>;
  open_document(docId: string): Promise<ApiResult>;
  stems_status(): Promise<ApiResult & { available?: boolean; hint?: string }>;
  pick_folder(): Promise<PickResult>;
  pick_audio_file(): Promise<PickResult>;
  cloud_login(email: string, password: string): Promise<ApiResult>;
  cloud_signup(
    email: string,
    password: string,
    captchaToken?: string | null,
    inviteCode?: string | null,
    acceptTerms?: boolean,
    confirmAge?: boolean,
  ): Promise<ApiResult>;
  cloud_delete_account(): Promise<ApiResult>;
  cloud_logout(): Promise<ApiResult>;
  cloud_reset_password(email: string): Promise<ApiResult>;
  cloud_billing_status(): Promise<BillingStatusResult>;
  cloud_billing_checkout(priceTier?: string | null): Promise<ApiResult & { confirmation_url?: string; opened?: boolean }>;
  cloud_fetch_status(): Promise<CloudStatusResult>;
  cloud_submit_feedback(category: string, message: string, attachLog?: boolean): Promise<ApiResult & { message?: string }>;
  check_for_updates(): Promise<ApiResult & { update_available?: boolean; latest?: string; current?: string; notes?: string }>;
  download_update(): Promise<ApiResult & { path?: string; version?: string }>;
  apply_downloaded_update(): Promise<ApiResult>;
  open_external_url(url: string): Promise<ApiResult>;
  set_ui_locale(locale: string): Promise<ApiResult & { locale?: string }>;
  get_auth_status(): Promise<AuthStatus>;
}

export interface CloudStatusResult {
  ok: boolean;
  overall?: string;
  support?: {
    email?: string;
    telegram?: string;
    sla_hours?: string;
    updates_url?: string;
    status_url?: string;
  };
  error?: string;
}

export interface BillingStatusResult {
  ok: boolean;
  billing?: BillingInfo;
  error?: string;
}

export type { BillingInfo };

export interface AuthStatus {
  ok: boolean;
  cloud_mode: boolean;
  signed_in: boolean;
  email?: string | null;
  captcha_required?: boolean;
  captcha_site_key?: string | null;
  captcha_provider?: string | null;
  invite_required?: boolean;
  feature_flags?: Record<string, boolean>;
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
export const previewKit = (prompt: string) => api().preview_kit(prompt) as Promise<KitPreviewResult>;
export const startBeat = (prompt: string, locale?: string | null) =>
  api().start_beat(prompt, locale ?? null);
export const setUiLocale = (locale: string) => api().set_ui_locale(locale);
export const startRegenerate = (prompt?: string | null) => api().start_regenerate(prompt ?? null);
export const startOpenInFl = () => api().start_open_in_fl();
export const startStemSplit = (source: string) => api().start_stem_split(source);
export const installFlScripts = () => api().install_fl_scripts();
export const renderPreview = () => api().render_preview();
export const revealPath = (path: string) => api().reveal_path(path);
export const chaosRoll = () => api().chaos_roll();
export const flipBeat = () => api().flip_beat();
export const bakeSession = () => api().bake_session();
export const setFilthMode = (enabled: boolean) => api().set_filth_mode(enabled);
export const getProducerBlueprint = () => api().get_producer_blueprint();
export const importKitFolder = (source: string) => api().import_kit_folder(source);
export const getAppInfo = () => api().get_app_info();
export const openDocument = (docId: string) => api().open_document(docId);
export const stemsStatus = () => api().stems_status();
export const pickFolder = () => api().pick_folder();
export const pickAudioFile = () => api().pick_audio_file();
export const getAuthStatus = () => api().get_auth_status();
export const cloudLogin = (email: string, password: string) => api().cloud_login(email, password);
export const cloudSignup = (
  email: string,
  password: string,
  captchaToken?: string | null,
  inviteCode?: string | null,
  acceptTerms?: boolean,
  confirmAge?: boolean,
) => api().cloud_signup(email, password, captchaToken ?? null, inviteCode ?? null, acceptTerms ?? false, confirmAge ?? false);
export const cloudDeleteAccount = () => api().cloud_delete_account();
export const cloudLogout = () => api().cloud_logout();
export const cloudResetPassword = (email: string) => api().cloud_reset_password(email);
export const cloudBillingStatus = () => api().cloud_billing_status();
export const cloudBillingCheckout = (priceTier?: string | null) =>
  api().cloud_billing_checkout(priceTier ?? null);
export const cloudFetchStatus = () => api().cloud_fetch_status();
export const cloudSubmitFeedback = (category: string, message: string, attachLog = false) =>
  api().cloud_submit_feedback(category, message, attachLog);
export const checkForUpdates = () => api().check_for_updates();
export const downloadUpdate = () => api().download_update();
export const applyDownloadedUpdate = () => api().apply_downloaded_update();
export const openExternalUrl = (url: string) => api().open_external_url(url);

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
