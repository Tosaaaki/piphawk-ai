from typing import Sequence, Optional


def calculate_n_wave_target(
    prices: Sequence[float], *, lookback: int = 20, pivot_range: int = 3
) -> Optional[float]:
    """Return projected N-wave target price if detectable."""
    if len(prices) < pivot_range * 2 + 3:
        return None
    data = list(prices[-lookback:])

    def _find_pivots(arr: list[float]) -> list[tuple[int, float]]:
        piv = [(0, arr[0])]
        direction = 0
        for i in range(1, len(arr)):
            diff = arr[i] - arr[i - 1]
            dir_now = 1 if diff > 0 else (-1 if diff < 0 else direction)
            if direction != 0 and dir_now != direction:
                piv.append((i - 1, arr[i - 1]))
            direction = dir_now
        piv.append((len(arr) - 1, arr[-1]))
        return piv

    pivots = _find_pivots(data)
    if len(pivots) < 3:
        return None
    if len(pivots) >= 4:
        a, b, c = pivots[-4][1], pivots[-3][1], pivots[-2][1]
    else:
        a, b, c = pivots[0][1], pivots[1][1], pivots[2][1]
    if b > a and c > a and c < b:
        return c + (b - a)
    if b < a and c < a and c > b:
        return c - (a - b)
    return None
