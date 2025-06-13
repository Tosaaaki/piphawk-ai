
"""Kafka と Prometheus へメトリクスを送信するユーティリティ."""
"""Publish metrics to Kafka and expose Prometheus gauges."""

import json
import logging
from datetime import datetime

try:
    from kafka import KafkaProducer
except Exception:  # pragma: no cover - Kafka optional
    KafkaProducer = None
from prometheus_client import Gauge

from backend.utils import env_loader

logger = logging.getLogger(__name__)

# 環境変数名の揺れを吸収するため複数キーをチェック
KAFKA_SERVERS = (
    env_loader.get_env("KAFKA_SERVERS")
    or env_loader.get_env("KAFKA_BROKERS")
    or env_loader.get_env("KAFKA_BROKER_URL")
    or env_loader.get_env("KAFKA_BOOTSTRAP_SERVERS")
    or "localhost:9092"
)
METRICS_TOPIC = env_loader.get_env("METRICS_TOPIC", "metrics")

# Kafka producer is initialized lazily so unit tests can run without Kafka.
_producer = None
_gauges: dict[str, Gauge] = {}


def _get_producer() -> KafkaProducer | None:
    global _producer
    if _producer is None:
        try:
            _producer = KafkaProducer(
                bootstrap_servers=KAFKA_SERVERS.split(","),
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            )
        except Exception as exc:  # pragma: no cover - Kafka optional
            logger.debug(f"Kafka producer init failed: {exc}")
            _producer = None
    return _producer


def publish(metric: str, value: float, labels: dict | None = None) -> None:
    """Send metric to Kafka and update Prometheus gauge."""
    labels = labels or {}
    data = {
        "metric": metric,
        "value": value,
        "labels": labels,
        "timestamp": datetime.utcnow().isoformat(),
    }
    producer = _get_producer()
    if producer:
        try:
            producer.send(METRICS_TOPIC, data)
        except Exception as exc:  # pragma: no cover
            logger.debug(f"Kafka publish failed: {exc}")
    gauge_key = metric + "_" + "_".join(sorted(labels))
    if gauge_key not in _gauges:
        _gauges[gauge_key] = Gauge(metric, metric, labelnames=list(labels))
    try:
        _gauges[gauge_key].labels(**labels).set(value)
    except Exception as exc:  # pragma: no cover - avoid crash
        logger.debug(f"Gauge update failed: {exc}")


def record_latency(metric: str, start: float, end: float) -> None:
    """Processing timeをmsで計測して出力する."""
    latency = (end - start) * 1000
    publish(metric, latency)
