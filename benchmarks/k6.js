import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';

const searchErrorRate = new Rate('search_errors');
const searchLatency = new Trend('search_latency_ms');

export const options = {
  stages: [
    { duration: '30s', target: 10 },
    { duration: '30s', target: 50 },
    { duration: '30s', target: 100 },
    { duration: '30s', target: 0 },
  ],
  thresholds: {
    search_errors: ['rate<0.05'],
    search_latency_ms: ['p(95)<500'],
    http_req_duration: ['p(95)<1000'],
  },
};

const QUERIES = [
  'example domain',
  'hello world',
  'python programming',
  'search engine',
  'web crawler',
  'machine learning',
  'open source',
  'database index',
  'http server',
  'api design',
];

export default function () {
  const q = QUERIES[Math.floor(Math.random() * QUERIES.length)];
  const res = http.get(`http://localhost:8000/search?q=${encodeURIComponent(q)}&top_k=10`);

  const ok = check(res, {
    'status is 200': (r) => r.status === 200,
    'has results field': (r) => JSON.parse(r.body).hasOwnProperty('results'),
  });

  searchErrorRate.add(!ok);
  searchLatency.add(res.timings.duration);

  sleep(0.5);
}
