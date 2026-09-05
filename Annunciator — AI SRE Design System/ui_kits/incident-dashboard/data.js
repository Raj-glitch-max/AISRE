const INCIDENTS = [
  {
    id: "INC-4471",
    service: "checkout-api",
    title: "Checkout latency regression",
    status: "pending_approval",
    opened: "14:01:07 UTC",
    updated: "14:02:18 UTC",
    confidence: 94,
    step: 3,
    metric: { label: "p95 latency", value: "2,410 ms", threshold: "threshold 800 ms" },
    cause:
      "The connection pool on checkout-api saturated at 14:01 UTC after deploy 8f31c raised per-request pool checkout from one connection to three. Latency crossed the p95 threshold ninety seconds later.",
    evidence: [
      ["pool.active / pool.max", "48 / 48 for 214 s"],
      ["deploy 8f31c", "merged 13:57:40 UTC"],
      ["upstream auth-gateway", "nominal, 41 ms p95"],
      ["error rate", "0.4% — no 5xx spike"],
    ],
    remediation: "Roll back deploy 8f31c and restart the checkout-api pool (3 replicas, rolling).",
  },
  {
    id: "INC-4470",
    service: "auth-gateway",
    title: "Token refresh backlog",
    status: "verifying",
    opened: "13:44:52 UTC",
    updated: "14:00:02 UTC",
    confidence: 88,
    step: 5,
    metric: { label: "queue depth", value: "1,118", threshold: "threshold 400" },
    cause:
      "Token refresh workers fell behind after a Redis failover at 13:44 UTC. The backlog drained once workers reconnected; verification is confirming queue depth stays under threshold for five minutes.",
    evidence: [
      ["redis failover", "13:44:41 UTC"],
      ["worker reconnects", "6 / 6 healthy"],
      ["queue depth", "1,118 → 62"],
    ],
    remediation: "Restart the refresh worker deployment (6 replicas).",
  },
  {
    id: "INC-4468",
    service: "ledger-worker",
    title: "Duplicate settlement writes",
    status: "failed",
    opened: "11:20:14 UTC",
    updated: "11:38:57 UTC",
    confidence: 41,
    step: 4,
    metric: { label: "dup writes", value: "37", threshold: "threshold 0" },
    cause:
      "Idempotency keys collided across two ledger-worker replicas. A rolling restart was approved and executed, but duplicate writes resumed within ninety seconds — health did not recover.",
    evidence: [
      ["duplicate writes", "37 after restart"],
      ["restart", "completed 11:36:12 UTC"],
      ["idempotency cache", "hit rate 12%"],
    ],
    remediation: "Roll restart ledger-worker (2 replicas).",
  },
  {
    id: "INC-4465",
    service: "search-indexer",
    title: "Index lag on shard 3",
    status: "resolved",
    opened: "09:02:31 UTC",
    updated: "09:19:08 UTC",
    confidence: 97,
    step: 6,
    metric: { label: "index lag", value: "911 s", threshold: "threshold 120 s" },
    cause:
      "Shard 3 fell behind after a node eviction. A single replica restart cleared the lag and index freshness returned to under twenty seconds.",
    evidence: [
      ["node eviction", "09:01:55 UTC"],
      ["index lag", "911 s → 18 s"],
      ["shards", "4 / 4 nominal"],
    ],
    remediation: "Restart the shard-3 indexer replica.",
  },
  {
    id: "INC-4462",
    service: "notify-fanout",
    title: "Webhook retry storm",
    status: "investigating",
    opened: "08:41:09 UTC",
    updated: "08:44:30 UTC",
    confidence: 62,
    step: 1,
    metric: { label: "retries/min", value: "8,204", threshold: "threshold 1,000" },
    cause:
      "Retry volume to a single downstream endpoint is climbing. The agent is still correlating the spike against the endpoint's response codes; no verdict yet.",
    evidence: [
      ["retries / min", "8,204 and rising"],
      ["downstream 4xx", "under review"],
    ],
    remediation: "Pending — no remediation proposed yet.",
  },
];

const STEP_LABELS = ["DETECT", "TRIAGE", "DIAGNOSE", "APPROVE", "EXECUTE", "VERIFY"];

Object.assign(window, { INCIDENTS, STEP_LABELS });
