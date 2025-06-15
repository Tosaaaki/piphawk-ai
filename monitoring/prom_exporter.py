from __future__ import annotations

"""Prometheus メトリクスエクスポーター."""

from fastapi import FastAPI, Response
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Histogram,
    generate_latest,
)

registry = CollectorRegistry()

trade_mode_count_total = Counter(
    "trade_mode_count_total",
    "Total trade mode counts",
    ["mode"],
    registry=registry,
)

ai_confidence_bucket = Histogram(
    "ai_confidence_bucket",
    "Distribution of AI confidence scores",
    buckets=[0.0, 0.2, 0.4, 0.6, 0.8, 1.0],
    registry=registry,
)

rl_override_total = Counter(
    "rl_override_total",
    "Number of RL overrides",
    registry=registry,
)


pattern_filter_pass_total = Counter(
    "pattern_filter_pass_total",
    "Number of pattern filter passes",
    registry=registry,
)

position_max_age_seconds = Histogram(
    "position_max_age_seconds",
    "Distribution of max open position age",
    buckets=[0, 60, 300, 900, 3600, 7200],

ai_pattern_model_missing_total = Counter(
    "ai_pattern_model_missing_total",
    "Number of times CNN pattern model missing",

    registry=registry,
)

app = FastAPI()


@app.get("/metrics")
def metrics() -> Response:
    """Prometheus メトリクスを出力するエンドポイント."""
    data = generate_latest(registry)
    return Response(content=data, media_type=CONTENT_TYPE_LATEST)


def increment_trade_mode(mode: str) -> None:
    """trade_mode_count_total をインクリメントする."""
    trade_mode_count_total.labels(mode=mode).inc()


def record_ai_confidence(value: float) -> None:
    """ai_confidence_bucket に値を記録する."""
    ai_confidence_bucket.observe(value)


def increment_rl_override() -> None:
    """rl_override_total をインクリメントする."""
    rl_override_total.inc()


def increment_pattern_filter_pass() -> None:
    """pattern_filter_pass_total をインクリメントする."""
    pattern_filter_pass_total.inc()


def record_position_age(age: float) -> None:
    """position_max_age_seconds に値を記録する."""
    position_max_age_seconds.observe(age)

def increment_pattern_model_missing() -> None:
    """ai_pattern_model_missing_total をインクリメントする."""
    ai_pattern_model_missing_total.inc()


def start(port: int = 8001) -> None:
    """UVicorn でサーバーを起動する."""
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=port)


if __name__ == "__main__":
    start()
