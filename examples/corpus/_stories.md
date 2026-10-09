# Interview stories (fictional example)

STAR + Reflection. Each story retells the records in `anchors` and nothing more.

## Stories

### st-001 · Making the tracking API fast without a big-bang rewrite
- anchors: [northwind-001]
- tags: [performance, leadership, migration]
- situation: Northwind's public tracking API was a Django service; couriers
  polled it constantly and p95 latency sat at 900 ms.
- task: I led a team of 3 backend engineers asked to make it fast without
  breaking roughly 40 courier integrations.
- action: I designed the FastAPI replacement and the Redis read cache and
  reviewed every change; the three engineers built it. We migrated the
  integrations one by one instead of switching everyone at once.
- result: p95 latency went from 900 ms to 140 ms (Grafana).
- reflection: Leading the design and reviews rather than writing the code was
  the right call for a team of three; next time I'd agree the migration order
  with the biggest couriers earlier.
