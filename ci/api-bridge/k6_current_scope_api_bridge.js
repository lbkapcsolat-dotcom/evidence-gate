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

export default function () {
  const unique = `${__VU}-${__ITER}-${Date.now()}`;

  const health = http.get(`${BASE_URL}/health`);
  check(health, {
    'health returns 200': (r) => r.status === 200,
    'health body has OK status': (r) => String(r.body).includes('"status":"OK"') || String(r.body).includes('"status": "OK"'),
  });

  const safePayload = JSON.stringify({
    sensor_data: { '0': 200, '1': 150, '3': 50 },
    event_id: `k6-safe-${unique}`,
    source: 'K6_CURRENT_SCOPE',
    dry_run: true,
  });
  const safe = http.post(`${BASE_URL}/api/v1/telemetry/evaluate`, safePayload, jsonHeaders());
  check(safe, {
    'evaluate safe returns 200': (r) => r.status === 200,
    'evaluate safe body marks SAFE': (r) => String(r.body).includes('SAFE'),
  });

  const violationPayload = JSON.stringify({
    sensor_data: { '0': 200, '1': 150, '3': 190 },
    event_id: `k6-viol-${unique}`,
    source: 'K6_CURRENT_SCOPE',
    dry_run: true,
  });
  const violation = http.post(`${BASE_URL}/api/v1/telemetry/evaluate`, violationPayload, jsonHeaders());
  check(violation, {
    'evaluate violation returns 200': (r) => r.status === 200,
    'evaluate violation body marks VIOLATION': (r) => String(r.body).includes('VIOLATION'),
  });

  const intervenePayload = JSON.stringify({
    sensor_data: { '0': 200, '1': 150, '3': 190 },
    event_id: `k6-apply-${unique}`,
    source: 'K6_CURRENT_SCOPE',
    confirm_apply: true,
  });
  const intervene = http.post(`${BASE_URL}/api/v1/telemetry/intervene`, intervenePayload, jsonHeaders());
  check(intervene, {
    'intervene returns 200': (r) => r.status === 200,
    'intervene body applies symbolic intervention': (r) => String(r.body).includes('VIOLATION_INTERVENTION_APPLIED'),
  });
}
