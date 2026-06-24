-- PLG Supabase — full setup (new project). Paste in SQL Editor and Run.


-- ========== schema.sql ==========

-- PLG Cloud schema for Supabase (SQL Editor в†’ New query в†’ Run)

-- Auth users live in auth.users (Supabase Auth handles signup / magic link / reset).



create table if not exists public.profiles (

  id uuid primary key references auth.users (id) on delete cascade,

  plan text not null default 'base' check (plan in ('base', 'premium')),

  status text not null default 'trial' check (status in ('trial', 'active', 'expired', 'cancelled', 'grace')),

  price_tier text not null default 'cis' check (price_tier in ('cis', 'intl')),

  billing_provider text check (billing_provider is null or billing_provider in ('yookassa', 'stripe', 'paddle', 'robokassa', 'boosty')),

  external_customer_id text,

  external_subscription_id text,

  subscription_ends_at timestamptz,

  grace_until timestamptz,

  trial_beats_used int not null default 0,

  period_start timestamptz not null default now(),

  beats_used int not null default 0,

  beats_today int not null default 0,

  daily_reset date not null default current_date,

  created_at timestamptz not null default now(),

  updated_at timestamptz not null default now()

);



create table if not exists public.user_devices (

  id uuid primary key default gen_random_uuid(),

  user_id uuid not null references auth.users (id) on delete cascade,

  device_id text not null,

  device_name text,

  last_seen timestamptz not null default now(),

  created_at timestamptz not null default now(),

  unique (user_id, device_id)

);



create table if not exists public.generation_logs (

  id uuid primary key default gen_random_uuid(),

  user_id uuid not null references auth.users (id) on delete cascade,

  model text not null,

  prompt_chars int not null default 0,

  tokens_in int,

  tokens_out int,

  cost_usd numeric(12, 6),

  created_at timestamptz not null default now()

);



create table if not exists public.payment_events (

  id uuid primary key default gen_random_uuid(),

  provider text not null,

  idempotency_key text not null,

  event_type text not null,

  user_id uuid references auth.users (id) on delete set null,

  amount_cents int,

  currency text,

  external_id text,

  payload jsonb,

  processed_at timestamptz not null default now(),

  unique (provider, idempotency_key)

);



create index if not exists payment_events_user_id_idx on public.payment_events (user_id);

create index if not exists payment_events_external_id_idx on public.payment_events (external_id);



create table if not exists public.kill_switch (

  id int primary key default 1 check (id = 1),

  daily_spend_cap_usd numeric(12, 2) not null default 500,

  today_spend_usd numeric(12, 6) not null default 0,

  spend_reset date not null default current_date,

  enabled boolean not null default true

);



insert into public.kill_switch (id) values (1) on conflict (id) do nothing;



-- Auto-create profile on signup (trial: 3 free beats before paywall)

create or replace function public.handle_new_user()

returns trigger

language plpgsql

security definer

set search_path = public

as $$

begin

  insert into public.profiles (id, status) values (new.id, 'trial') on conflict (id) do nothing;

  return new;

end;

$$;



drop trigger if exists on_auth_user_created on auth.users;

create trigger on_auth_user_created

  after insert on auth.users

  for each row execute function public.handle_new_user();



-- RLS: users read own profile only; service role bypasses for API server

alter table public.profiles enable row level security;

alter table public.user_devices enable row level security;

alter table public.generation_logs enable row level security;

alter table public.payment_events enable row level security;



create policy "profiles_select_own" on public.profiles

  for select using (auth.uid() = id);



create policy "devices_select_own" on public.user_devices

  for select using (auth.uid() = user_id);



create policy "logs_select_own" on public.generation_logs

  for select using (auth.uid() = user_id);



-- ========== 002_payments.sql ==========

-- Phase 2: payments (run after schema.sql on existing projects)

alter table public.profiles
  add column if not exists price_tier text not null default 'cis'
    check (price_tier in ('cis', 'intl')),
  add column if not exists billing_provider text
    check (billing_provider is null or billing_provider in ('yookassa', 'stripe', 'paddle', 'robokassa', 'boosty')),
  add column if not exists external_customer_id text,
  add column if not exists external_subscription_id text,
  add column if not exists subscription_ends_at timestamptz,
  add column if not exists grace_until timestamptz,
  add column if not exists trial_beats_used int not null default 0;

alter table public.profiles drop constraint if exists profiles_status_check;
alter table public.profiles add constraint profiles_status_check
  check (status in ('trial', 'active', 'expired', 'cancelled', 'grace'));

create table if not exists public.payment_events (
  id uuid primary key default gen_random_uuid(),
  provider text not null,
  idempotency_key text not null,
  event_type text not null,
  user_id uuid references auth.users (id) on delete set null,
  amount_cents int,
  currency text,
  external_id text,
  payload jsonb,
  processed_at timestamptz not null default now(),
  unique (provider, idempotency_key)
);

create index if not exists payment_events_user_id_idx on public.payment_events (user_id);
create index if not exists payment_events_external_id_idx on public.payment_events (external_id);

alter table public.payment_events enable row level security;

-- Service role only (no client policies)

create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
begin
  insert into public.profiles (id, status)
  values (new.id, 'trial')
  on conflict (id) do nothing;
  return new;
end;
$$;

-- ========== 003_security.sql ==========

-- Phase 3: abuse, bots, bans, trial farming protection

create table if not exists public.security_bans (
  id uuid primary key default gen_random_uuid(),
  ban_type text not null check (ban_type in ('user', 'device', 'ip', 'fingerprint')),
  ban_value text not null,
  reason text,
  banned_by text,
  expires_at timestamptz,
  created_at timestamptz not null default now(),
  unique (ban_type, ban_value)
);

create index if not exists security_bans_lookup_idx on public.security_bans (ban_type, ban_value);

create table if not exists public.device_trial_claims (
  device_id text primary key,
  first_user_id uuid not null references auth.users (id) on delete cascade,
  claimed_at timestamptz not null default now()
);

create table if not exists public.abuse_alerts (
  id uuid primary key default gen_random_uuid(),
  alert_type text not null,
  ip_address text,
  user_id uuid references auth.users (id) on delete set null,
  details jsonb not null default '{}',
  acknowledged boolean not null default false,
  created_at timestamptz not null default now()
);

create index if not exists abuse_alerts_created_idx on public.abuse_alerts (created_at desc);

alter table public.generation_logs
  add column if not exists ip_address text,
  add column if not exists device_id text;

alter table public.profiles
  add column if not exists banned boolean not null default false,
  add column if not exists ban_reason text;

alter table public.security_bans enable row level security;
alter table public.device_trial_claims enable row level security;
alter table public.abuse_alerts enable row level security;

-- ========== 004_infra.sql ==========

-- Phase 4: infra вЂ” feature flags, waitlist, invite ramp

create table if not exists public.feature_flags (
  key text primary key,
  enabled boolean not null default false,
  description text,
  rollout_pct int not null default 100 check (rollout_pct between 0 and 100),
  metadata jsonb not null default '{}',
  updated_at timestamptz not null default now()
);

insert into public.feature_flags (key, enabled, description) values
  ('regenerate_ui', true, 'Show regenerate button in desktop UI'),
  ('premium_plan', false, 'Enable premium Sonnet plan'),
  ('stem_split', true, 'Stem split tool'),
  ('filth_mode', true, 'Filth mode toggle'),
  ('waitlist_gate', false, 'Block signup without invite code'),
  ('maintenance_mode', false, 'Read-only maintenance banner')
on conflict (key) do nothing;

create table if not exists public.waitlist_entries (
  id uuid primary key default gen_random_uuid(),
  email text not null unique,
  status text not null default 'pending'
    check (status in ('pending', 'invited', 'activated', 'rejected')),
  ramp_tier text not null default 'wave_200',
  invite_code text,
  metadata jsonb not null default '{}',
  created_at timestamptz not null default now(),
  invited_at timestamptz
);

create index if not exists waitlist_status_idx on public.waitlist_entries (status);

create table if not exists public.invite_codes (
  code text primary key,
  ramp_tier text not null default 'wave_200',
  max_uses int,
  uses int not null default 0,
  expires_at timestamptz,
  created_at timestamptz not null default now()
);

alter table public.profiles
  add column if not exists ramp_tier text,
  add column if not exists invite_code text;

alter table public.feature_flags enable row level security;
alter table public.waitlist_entries enable row level security;
alter table public.invite_codes enable row level security;

-- ========== 005_legal.sql ==========

-- Phase 5: legal / GDPR

alter table public.profiles
  add column if not exists terms_version text,
  add column if not exists terms_accepted_at timestamptz,
  add column if not exists privacy_version text,
  add column if not exists age_confirmed_at timestamptz,
  add column if not exists deletion_requested_at timestamptz,
  add column if not exists data_region text default 'eu' check (data_region in ('eu', 'us', 'cis'));

create table if not exists public.legal_acceptances (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users (id) on delete cascade,
  doc_type text not null check (doc_type in ('terms', 'privacy', 'age')),
  doc_version text not null,
  accepted_at timestamptz not null default now(),
  ip_address text,
  user_agent text
);

create index if not exists legal_acceptances_user_idx on public.legal_acceptances (user_id);

-- Prompt text must NOT be stored; generation_logs keeps metadata only.
-- Retention purge deletes rows older than PLG_PROMPT_LOG_RETENTION_DAYS.

alter table public.legal_acceptances enable row level security;

-- ========== 006_ops.sql ==========

-- Phase 6: ops вЂ” feedback, attribution, notifications, analytics

create table if not exists public.feedback_submissions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users (id) on delete set null,
  email text,
  category text not null default 'general',
  message text not null,
  app_version text,
  platform text,
  log_excerpt text,
  created_at timestamptz not null default now()
);

create table if not exists public.notification_log (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users (id) on delete set null,
  channel text not null check (channel in ('email', 'telegram')),
  template text not null,
  recipient text not null,
  status text not null default 'queued' check (status in ('queued', 'sent', 'failed')),
  error text,
  metadata jsonb not null default '{}',
  created_at timestamptz not null default now()
);

create table if not exists public.analytics_events (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references auth.users (id) on delete set null,
  event_name text not null,
  properties jsonb not null default '{}',
  created_at timestamptz not null default now()
);

create index if not exists analytics_events_name_idx on public.analytics_events (event_name, created_at desc);
create index if not exists analytics_events_user_idx on public.analytics_events (user_id);

create table if not exists public.status_incidents (
  id uuid primary key default gen_random_uuid(),
  component text not null,
  status text not null check (status in ('investigating', 'degraded', 'outage', 'resolved')),
  title text not null,
  message text,
  started_at timestamptz not null default now(),
  resolved_at timestamptz
);

alter table public.profiles
  add column if not exists utm_source text,
  add column if not exists utm_medium text,
  add column if not exists utm_campaign text,
  add column if not exists utm_content text,
  add column if not exists referrer text,
  add column if not exists first_beat_at timestamptz;

alter table public.feedback_submissions enable row level security;
alter table public.notification_log enable row level security;
alter table public.analytics_events enable row level security;
alter table public.status_incidents enable row level security;

-- ========== 007_intl_billing_flag.sql ==========

-- Phase 7 polish: international billing behind feature flag

insert into public.feature_flags (key, enabled, description) values
  ('intl_billing', false, 'Stripe/Paddle international checkout ($14.99/mo)')
on conflict (key) do nothing;
