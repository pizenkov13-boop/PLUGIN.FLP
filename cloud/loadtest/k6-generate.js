// k6 generate load — requires JWT + device (run against staging only)
// Usage:
//   k6 run cloud/loadtest/k6-generate.js \
//     -e BASE_URL=https://plg-api-staging.fly.dev \
//     -e TOKEN=eyJ... \
//     -e DEVICE_ID=your-device-uuid

import http from "k6/http";
import { check, sleep } from "k6";

export const options = {
  stages: [
    { duration: "1m", target: 5 },
    { duration: "3m", target: 20 },
    { duration: "1m", target: 0 },
  ],
  thresholds: {
    http_req_failed: ["rate<0.05"],
    http_req_duration: ["p(95)<30000"],
  },
};

const BASE = __ENV.BASE_URL || "http://127.0.0.1:8787";
const TOKEN = __ENV.TOKEN || "";
const DEVICE = __ENV.DEVICE_ID || "k6-load-test-device";

export default function () {
  if (!TOKEN) {
    console.warn("Set TOKEN env var — skipping generate");
    sleep(1);
    return;
  }

  const res = http.post(
    `${BASE}/v1/generate`,
    JSON.stringify({
      prompt: "dark trap beat 140 bpm",
      device_id: DEVICE,
    }),
    {
      headers: {
        Authorization: `Bearer ${TOKEN}`,
        "Content-Type": "application/json",
        "X-PLG-Version": "1.0.0",
        "X-PLG-Device": DEVICE,
      },
      timeout: "120s",
    }
  );

  check(res, {
    "not 5xx": (r) => r.status < 500,
  });

  sleep(15); // respect 1 gen / 15s limit
}
