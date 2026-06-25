// TypeScript shapes mirroring the dicts plg_api returns. Kept loose on purpose
// (optional fields) so the UI never crashes if the backend adds keys.

export interface Quota {
  used: number;
  limit: number;
  remaining: number;
  days_until_reset: number;
  period_days?: number;
  skipped: boolean;
  label: string;
}

export interface BillingInfo {
  status: string;
  price_tier?: string;
  price_label?: string;
  trial_remaining?: number;
  grace_days_left?: number;
  days_until_renewal?: number;
  can_subscribe?: boolean;
  needs_payment?: boolean;
}

export interface Status {
  ok: boolean;
  cloud_mode?: boolean;
  release_build?: boolean;
  signed_in?: boolean;
  auth_email?: string | null;
  app_version?: string;
  network_online?: boolean;
  provider: string;
  has_api_key: boolean;
  fl_bridge_ready: boolean;
  fl_installed?: boolean;
  fl_version?: string | null;
  fl_executable: string | null;
  beat_ready: boolean;
  auto_open_fl: boolean;
  library_audio_total: number;
  last_prompt: string;
  sample_picks?: Record<string, string>;
  bpm?: number;
  style?: string;
  stem_session?: string;
  stem_files?: string[];
  mix_blueprint?: string | null;
  sample_chop?: { chop_count?: number; pitch_semitones?: number; tempo_ratio?: number };
  filth_mode?: boolean;
  beat_id?: string;
  beat_rating?: number;
  quality_score?: number;
  reward_learning?: boolean;
  reward_model_ready?: boolean;
  reward_ratings?: number;
  quota: Quota;
}

export interface Settings {
  ok: boolean;
  provider: string;
  gemini_key: string;
  anthropic_key: string;
  has_gemini_key: boolean;
  has_anthropic_key: boolean;
  samples_dir: string;
  gemini_model: string;
  claude_model: string;
  auto_open_fl: boolean;
}

// Result payload of a successful create_beat / open_in_fl job.
export interface BeatResult {
  ok: boolean;
  bpm?: number;
  style?: string;
  note_count?: number;
  sample_count?: number;
  provider?: string;
  auto_open_fl?: boolean;
  sample_picks?: Record<string, string>;
  stem_session?: string;
  stem_files?: string[];
  mix_blueprint?: string;
  filth_mode?: boolean;
  beat_id?: string;
  beat_rating?: number;
  quality_score?: number;
  quota?: Quota;
}

export type JobStatus = "running" | "done" | "error" | "unknown";

export interface JobSnapshot {
  ok: boolean;
  job_id: string;
  kind: string;
  status: JobStatus;
  phase: string;
  progress: number;
  message: string;
  result: Record<string, unknown> | null;
  error: string | null;
  error_type: string | null;
  started_at: number;
  elapsed: number;
}

// Generic error/ok envelope returned by sync actions.
export interface ApiResult {
  ok: boolean;
  error?: string;
  error_type?: string;
  [key: string]: unknown;
}

export interface KitPreviewResult {
  ok: boolean;
  audio_total?: number;
  picks?: Record<string, { name: string; path: string }>;
  error?: string;
}

export interface JobHandle {
  ok: boolean;
  job_id: string;
  kind: string;
  status: JobStatus;
}

export interface PickResult {
  ok: boolean;
  path?: string;
  cancelled?: boolean;
  error?: string;
}

export interface AppInfo {
  ok: boolean;
  version: string;
  project_dir: string;
  fl_executable: string | null;
  fl_bridge_ready: boolean;
  demucs_available: boolean;
  starter: {
    dir: string;
    bundle_dir: string;
    source: string;
    bundled: boolean;
    incoming_dir: string;
  };
  docs: Record<string, string>;
  quota: Quota;
}
