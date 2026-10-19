# HTTP observability

The generic template owns app instrumentation, correlation and structured HTTP logs.
platformInfra owns collection/storage/dashboard provisioning; serviceTemplate supplies service
identity. There is no telemetry account or network exporter in the request path.

Each app factory owns its own prometheus-client registry and one independent stderr logger.
The supported ASGI instrumentator counts requests by route template/status, measures
latency in seconds and in-flight requests. Unmatched paths group as `none`. IDs, raw URL/query,
tokens and bodies never become metric labels or structured log fields. Static service_id and
validated environment are bounded scrape-target labels on all series, including process metrics.
ProcessCollector reports process CPU seconds, resident/virtual bytes and open descriptors on
Linux. It does not claim host/container CPU or memory collection.

Latency buckets in seconds are 0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5,
0.75, 1, 2.5, 5, 7.5, 10 and +Inf. Metrics use the standard client histogram and are exposed at internal `/metrics`.
Inspect the actual bucket boundaries in the scrape; dashboards use seconds. Health routes
remain separate. Requests preserve one valid bounded X-Request-ID, replace invalid/duplicate IDs,
return it, and log it in JSON with time/level/service_id/environment/operation/status/duration.
Collectors parse JSON and keep request_id as content, never a stream label.

Run one Uvicorn worker per container and scale containers/pods: each is scraped independently.
This keeps counters and process resource identity correct. Multiple processes must not share a
single load-balanced scrape endpoint; this template does not pretend to aggregate their process
metrics. A future multiworker deployment must use the official prometheus-client multiprocess
mode and its own lifecycle/directory policy before activation. Repeated factories never share
registries/handlers or open telemetry sockets. Shutdown closes application resources normally.

`<PREFIX>_METRICS_ENABLED=false` is an explicit opt-out; it needs no credentials and is not full
observability acceptance. `<PREFIX>_ENVIRONMENT` is local/dev/ci/remote. Collection uses standard
Docker nonblocking syslog and Alloy in the platform, not privileged host log mounts.

Instrumentation is pinned to 8.1.0 with FastAPI 0.143.3. The instrumentator's optional
global in-flight gauge is disabled; a small lifecycle adapter uses the official client Gauge
with the app-owned registry across the complete response. No exporter/histogram is reimplemented.
Uvicorn access logs are disabled in the runtime image; structured HTTP logs omit URL/query/body.
