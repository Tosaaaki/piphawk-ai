"""Dynamic pullback threshold calculation."""

from backend.utils import env_loader


def calculate_dynamic_pullback(indicators: dict, recent_high: float, recent_low: float) -> float:
    """Return dynamic pullback threshold in pips."""
    pip_size = float(env_loader.get_env("PIP_SIZE", "0.01"))
    atr = indicators.get("atr")
    adx = indicators.get("adx")
    noise = indicators.get("noise")
    if atr is None or adx is None or noise is None:
        return float(env_loader.get_env("PULLBACK_PIPS", "5"))

    atr_val = float(atr.iloc[-1]) / pip_size
    adx_val = float(adx.iloc[-1])
    noise_val = float(noise.iloc[-1])
    last_leg = abs(recent_low - recent_high) / pip_size

    thr_atr = atr_val * (1.2 if adx_val < 30 else 0.9)
    thr_noise = 0.15 * noise_val
    thr_fibo = 0.236 * last_leg

    pullback = max(thr_atr, thr_noise, thr_fibo)
    pullback = min(max(pullback, 3), 15)
    return pullback
