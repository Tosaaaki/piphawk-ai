"""簡易ティックパイプラインベンチマーク."""
import time
from statistics import quantiles

from core.ring_buffer import RingBuffer
from fast_metrics import calc_mid_spread


def generate_tick(i: int) -> dict:
    price = 100 + i * 0.001
    return {"bid": price, "ask": price + 0.02}


def main() -> None:
    buf = RingBuffer(100)
    lat = []
    for i in range(5000):
        start = time.perf_counter()
        tick = generate_tick(i)
        buf.append(tick)
        calc_mid_spread(buf)
        end = time.perf_counter()
        lat.append((end - start) * 1000)
    lat.sort()
    p95 = quantiles(lat, n=100)[94]
    print(f"p95 latency: {p95:.2f} ms")


if __name__ == "__main__":
    main()
