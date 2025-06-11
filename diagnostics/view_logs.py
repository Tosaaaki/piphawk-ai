from diagnostics import diagnostics

for ts, dtype, resp, metrics in diagnostics.fetch_all():
    print(f"{ts} [{dtype}] {resp} {metrics}")
