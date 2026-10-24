import http from 'k6/http';
import { check } from 'k6';

export const options = {
  scenarios: {
    current_scope_capacity_smoke: {
      executor: 'constant-vus',
      vus: 2,
      duration: '20s',
      gracefulStop: '5s',
    },
  },
  thresholds: {
    http_req_failed: ['rate<0.01'],
    http_req_duration: ['p(95)<1000', 'p(99)<2000'],
    checks: ['rate==1.0'],
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://127.0.0.1:8001';

function jsonHeaders() {
  return { headers: { 'Content-Type': 'application/json' } };
}

function hasJsonBody(r) {
  try {
    r.json();
    return true;
  } catch (e) {
    return false;
  }
}

function boundedOkChecks(name) {
  return {
    [`${name} returns 200`]: (r) => r.status === 200,
    [`${name} returns JSON`]: (r) => hasJsonBody(r),
  };
}

export default function () {
  const unique = `${__VU}-${__ITER}-${Date.now()}`;

  const health = http.get(`${BASE_URL}/health`);
  check(health, boundedOkChecks('health'));

  const safePayload = JSON.stringify({
    sensor_data: { '0': 200, '1': 150, '3': 50 },
    event_id: `k6-safe-${unique}`,
    source: 'K6_CURRENT_SCOPE',
    dry_run: true,
  });
  const safe = http.post(`${BASE_URL}/api/v1/telemetry/evaluate`, safePayload, jsonHeaders());
  check(safe, boundedOkChecks('evaluate safe'));

  const violationPayload = JSON.stringify({
    sensor_data: { '0': 200, '1': 150, '3': 190 },
    event_id: `k6-viol-${unique}`,
    source: 'K6_CURRENT_SCOPE',
    dry_run: true,
  });
  const violation = http.post(`${BASE_URL}/api/v1/telemetry/evaluate`, violationPayload, jsonHeaders());
  check(violation, boundedOkChecks('evaluate violation'));

  const intervenePayload = JSON.stringify({
    sensor_data: { '0': 200, '1': 150, '3': 190 },
    event_id: `k6-apply-${unique}`,
    source: 'K6_CURRENT_SCOPE',
    confirm_apply: true,
  });
  const intervene = http.post(`${BASE_URL}/api/v1/telemetry/intervene`, intervenePayload, jsonHeaders());
  check(intervene, boundedOkChecks('intervene'));
}
