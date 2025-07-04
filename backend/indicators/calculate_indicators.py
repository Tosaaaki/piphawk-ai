from typing import Sequence

import numpy as np

from backend.utils import env_loader

try:
    import pandas as pd
except ImportError as e:
    raise ImportError(
        "Pandas is required for indicator calculations."
        " Install it with 'pip install pandas'."
    ) from e

from backend.indicators.adx import calculate_adx
from backend.indicators.atr import calculate_atr
from backend.indicators.ema import calculate_ema
from backend.indicators.rsi import calculate_rsi
from indicators.bollinger import calculate_bollinger_bands

try:
    from backend.indicators.adx import calculate_adx_bb_score
except Exception:  # pragma: no cover - fallback when stub lacks function
    calculate_adx_bb_score = lambda *_a, **_k: 0.0
try:
    from backend.indicators.adx import calculate_di
except Exception:  # pragma: no cover - fallback for older stubs
    calculate_di = None
from backend.indicators.macd import calculate_macd, calculate_macd_histogram
from backend.indicators.n_wave import calculate_n_wave_target
from backend.indicators.pivot import calculate_pivots
from backend.indicators.polarity import calculate_polarity
from backend.market_data.candle_fetcher import fetch_candles


def _percentile_rank(series: Sequence[float], value: float) -> float | None:
    """Return percentile rank of ``value`` within ``series`` (0-100)."""
    if not series:
        return None
    arr = pd.Series(series).dropna().to_numpy()
    if arr.size == 0:
        return None
    rank = np.searchsorted(np.sort(arr), value, side="right")
    return 100.0 * rank / arr.size

def calculate_indicators(
    market_data,
    *,
    pair: str | None = None,
    history_days: int = 90,
    allow_incomplete: bool | None = None,
) -> dict:
    """Calculate trading indicators and recent-percentile stats."""
    if allow_incomplete is None:
        allow_incomplete = env_loader.get_env("USE_INCOMPLETE_BARS", "false").lower() == "true"
    close_prices = [
        float(c['mid']['c'])
        for c in market_data
        if allow_incomplete or c.get('complete')
    ]
    high_prices = [
        float(c['mid']['h'])
        for c in market_data
        if allow_incomplete or c.get('complete')
    ]
    low_prices = [
        float(c['mid']['l'])
        for c in market_data
        if allow_incomplete or c.get('complete')
    ]

    # --- 出来高関連の計算 -------------------------------------------
    vol_last = 0.0
    if market_data and not market_data[-1].get('complete'):
        vol_last = float(market_data[-1].get('volume', 0))
        complete_vols = [
            float(c.get('volume', 0))
            for c in market_data[:-1]
            if c.get('complete')
        ]
    else:
        complete_vols = [float(c.get('volume', 0)) for c in market_data if c.get('complete')]
    recent_vols = complete_vols[-6:]
    vol_avg = sum(recent_vols) / len(recent_vols) if recent_vols else 0.0
    # 平均値が得られない場合は 0.5 を用いる
    vol_ratio = (vol_last / vol_avg) if vol_avg else 0.5
    weight_last = 0.5 + 0.5 * vol_ratio

    import logging
    logger = logging.getLogger(__name__)
    # 最近の終値をデバッグレベルで出力
    logger.debug(f"Latest close prices: {close_prices[-15:]}")

    ema_fast_period = int(env_loader.get_env("EMA_FAST_PERIOD", "9"))
    ema_slow_period = int(env_loader.get_env("EMA_SLOW_PERIOD", "21"))

    # --- Bollinger Bands (DataFrame) ---
    bb_df = calculate_bollinger_bands(close_prices)

    # --- ADX (trend strength) and DI lines ---
    adx_period = int(env_loader.get_env("ADX_PERIOD", "12"))
    adx_series = calculate_adx(high_prices, low_prices, close_prices, period=adx_period)
    if calculate_di:
        plus_di, minus_di = calculate_di(high_prices, low_prices, close_prices)
    else:  # pragma: no cover - fallback when calculate_di is absent
        plus_di = minus_di = pd.Series([None] * len(close_prices))

    # EMAの計算
    ema_fast_series = calculate_ema(close_prices, period=ema_fast_period)
    ema_slow_series = calculate_ema(close_prices, period=ema_slow_period)
    # EMAの傾き計算
    ema_slope_series = ema_fast_series.diff()
    macd_series, macd_signal_series = calculate_macd(close_prices)
    macd_hist_series = calculate_macd_histogram(close_prices)

    indicators = {
        'rsi': calculate_rsi(close_prices),
        'ema_fast': ema_fast_series,
        'ema_slow': ema_slow_series,
        'ema_slope': ema_slope_series,
        'macd': macd_series,
        'macd_signal': macd_signal_series,
        'macd_hist': macd_hist_series,
        'atr': calculate_atr(high_prices, low_prices, close_prices),
        'n_wave_target': calculate_n_wave_target(close_prices),
        # Spread Bollinger components so filters can access them directly
        'bb_upper': bb_df['upper_band'],
        'bb_lower': bb_df['lower_band'],
        'bb_middle': bb_df['middle_band'],
        'adx': adx_series,
        'plus_di': plus_di,
        'minus_di': minus_di,
        'polarity': calculate_polarity(close_prices),
        'weight_last': weight_last,
    }

    try:
        score = calculate_adx_bb_score(
            adx_series,
            bb_df['upper_band'],
            bb_df['lower_band'],
        )
    except Exception:
        score = 0.0
    indicators['adx_bb_score'] = score

    if high_prices and low_prices and close_prices:
        piv = calculate_pivots(high_prices[-1], low_prices[-1], close_prices[-1])
        indicators.update(
            {
                'pivot': piv['pivot'],
                'pivot_r1': piv['r1'],
                'pivot_s1': piv['s1'],
                'pivot_r2': piv['r2'],
                'pivot_s2': piv['s2'],
            }
        )

    # 各指標の欠損値を前後の値で補完
    for key, series in indicators.items():
        if isinstance(series, pd.Series):
            indicators[key] = series.ffill().bfill()

    # --- Percentile stats from historical daily data --------------------
    if pair is None:
        pair = env_loader.get_env("DEFAULT_PAIR")
    try:
        history = fetch_candles(pair, granularity="D", count=history_days)
    except Exception:
        history = []

    if history:
        h_close = [float(c['mid']['c']) for c in history if c.get('complete')]
        h_high = [float(c['mid']['h']) for c in history if c.get('complete')]
        h_low = [float(c['mid']['l']) for c in history if c.get('complete')]

        hist_bb = calculate_bollinger_bands(h_close)
        hist_bb_width = (hist_bb['upper_band'] - hist_bb['lower_band']).tolist()
        hist_atr = calculate_atr(h_high, h_low, h_close).tolist()

        current_bb_width = (
            indicators['bb_upper'].iloc[-1] - indicators['bb_lower'].iloc[-1]
        )
        current_atr = indicators['atr'].iloc[-1]

        indicators['bb_width_pct'] = _percentile_rank(hist_bb_width, current_bb_width)
        indicators['atr_pct'] = _percentile_rank(hist_atr, current_atr)
    else:
        indicators['bb_width_pct'] = None
        indicators['atr_pct'] = None

    return indicators



def calculate_indicators_multi(
    market_data_dict: dict[str, list], *, pair: str | None = None, history_days: int = 90, allow_incomplete: bool | None = None
) -> dict[str, dict]:
    """Calculate indicators for multiple timeframes."""
    result = {}
    for tf, data in market_data_dict.items():
        result[tf] = calculate_indicators(
            data,
            pair=pair,
            history_days=history_days,
            allow_incomplete=allow_incomplete,
        )
    return result


