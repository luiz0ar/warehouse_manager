from prometheus_client import Counter, Gauge, Histogram

WAREHOUSE_PICKING_DURATION_SECONDS = Histogram(
    "warehouse_picking_duration_seconds",
    "Time taken to compute picking recommendations in seconds",
    ["warehouse_id", "status"],
    buckets=(0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0),
)

WAREHOUSE_SYNC_LAG_SECONDS = Gauge(
    "warehouse_sync_lag_seconds",
    "Lag in seconds between event occurrence in legacy ERP and synchronization completion",
    ["warehouse_id"],
)

WAREHOUSE_SYNC_DEAD_LETTERS_TOTAL = Counter(
    "warehouse_sync_dead_letters_total",
    "Total number of unrecoverable sync events routed to the Dead Letter Queue",
    ["warehouse_id", "reason"],
)

WAREHOUSE_SYNC_MOVEMENTS_TOTAL = Counter(
    "warehouse_sync_movements_total",
    "Total number of ERP movement events processed",
    ["warehouse_id", "movement_type", "status"],
)
