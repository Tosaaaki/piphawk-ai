from types import SimpleNamespace

import monitoring.metrics_publisher as mp


class DummyProducer:
    def __init__(self):
        self.sent = []

    def send(self, topic, value):
        self.sent.append((topic, value))


class DummyGauge:
    def __init__(self, *a, **k):
        self.values = {}

    def labels(self, **labels):
        def setter(v):
            self.values[tuple(labels.items())] = v
        return SimpleNamespace(set=setter)


def setup_module(module):
    mp._gauges.clear()
    mp._producer = None


def test_publish(monkeypatch):
    prod = DummyProducer()
    monkeypatch.setattr(mp, "_get_producer", lambda: prod)
    monkeypatch.setattr(mp, "Gauge", DummyGauge)
    mp.publish("test", 2.0, {"k": "v"})
    assert prod.sent
    topic, data = prod.sent[0]
    assert topic == mp.METRICS_TOPIC
    assert data["metric"] == "test"
    gauge = mp._gauges["test_k"]
    assert list(gauge.values.values())[0] == 2.0


def test_record_latency(monkeypatch):
    prod = DummyProducer()
    monkeypatch.setattr(mp, "_get_producer", lambda: prod)
    monkeypatch.setattr(mp, "Gauge", DummyGauge)
    mp.record_latency("lat", 0.0, 0.01)
    assert prod.sent
