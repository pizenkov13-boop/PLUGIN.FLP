// k6 smoke test — no auth required
// Usage: k6 run cloud/loadtest/k6-smoke.js -e BASE_URL=http://127.0.0.1:8787

import http from "k6/http";
import { check, sleep } from "k6";

export const options = {
  vus: 10,
  duration: "30s",
  thresholds: {
    http_req_failed: ["rate<0.01"],
    http_req_duration: ["p(95)<500"],
  },
};

const BASE = __ENV.BASE_URL || "http://127.0.0.1:8787";

export default function () {
  const health = http.get(`${BASE}/health`);
  check(health, { "health 200": (r) => r.status === 200 });

  const flags = http.get(`${BASE}/v1/flags`);
  check(flags, { "flags 200": (r) => r.status === 200 });

  const cfg = http.get(`${BASE}/v1/auth/config`);
  check(cfg, { "auth config 200": (r) => r.status === 200 });

  sleep(0.5);
}
