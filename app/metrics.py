from prometheus_client import Counter, Histogram

request_count = Counter(
    'ai_request_count', 'Total requests',
    ['task', 'provider', 'status']
)

error_count = Counter(
    'ai_error_count', 'Total errors',
    ['provider']
)

provider_latency = Histogram(
    'ai_provider_latency_ms', 'Provider latency in milliseconds',
    ['provider'],
    buckets=[50, 100, 250, 500, 1000, 2500, 5000, 10000]
)

failover_count = Counter(
    'ai_failover_count', 'Provider failovers',
    ['from_provider', 'to_provider']
)
