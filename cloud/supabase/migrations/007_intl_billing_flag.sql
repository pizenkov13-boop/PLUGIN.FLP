-- Phase 7 polish: international billing behind feature flag

insert into public.feature_flags (key, enabled, description) values
  ('intl_billing', false, 'Stripe/Paddle international checkout ($14.99/mo)')
on conflict (key) do nothing;
