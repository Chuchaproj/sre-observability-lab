import http from 'k6/http';
import { check, sleep } from 'k6';
export const options = {
  vus: 5,
  duration: '2m',
  thresholds: {http_req_failed: ['rate<0.01'], http_req_duration: ['p(95)<500']},
};
export default function () {
  const result = http.get('http://nginx:8080/items');
  check(result, {'API returns 200': (r) => r.status === 200});
  sleep(0.2);
}
