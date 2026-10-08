---
company: Northwind Logistics
id: northwind
role: Senior Backend Engineer
location: Lisbon / Remote
start: 2021-04
end: present
domains: [logistics, e-commerce]
stack: [Python, FastAPI, PostgreSQL, Redis, Docker, Kubernetes, GCP Pub/Sub]
skills: [API design, event-driven architecture, mentoring, incident response]
---

## Context

Parcel-tracking platform for regional couriers. Backend team of 6.

## Records

### northwind-001 · Tracking API rewrite
- what: Led a team of 3 that rewrote the public tracking API from Django to
  FastAPI and moved reads to a Redis cache.
- stack: [FastAPI, Redis, PostgreSQL]
- metrics:
    - p95 latency 900 ms → 140 ms · verifiable (Grafana)
    - roughly 40 courier integrations migrated · estimate
- team: 3 backend engineers built it; I led the design and reviews
- jd-keywords: [REST API, API design, performance, migration, caching]

### northwind-002 · Event pipeline on Pub/Sub
- what: Designed the event pipeline that fans parcel status changes out to
  couriers and shops over GCP Pub/Sub, replacing nightly batch exports.
- stack: [GCP Pub/Sub, Python, PostgreSQL]
- metrics:
    - status delay from ~24 h to under 1 minute · verifiable (release notes)
- jd-keywords: [event-driven architecture, messaging, streaming, real-time]

### northwind-003 · On-call and mentoring
- what: Set up the on-call rotation and incident reviews; mentored two junior
  engineers through their first year.
- skills: [incident response, mentoring]
- jd-keywords: [on-call, mentoring, reliability]
