import os
from backend.indicators.rsi import calculate_rsi
from backend.indicators.ema import calculate_ema
from backend.indicators.atr import calculate_atr
from backend.indicators.bollinger import calculate_bollinger_bands
from backend.indicators.adx import calculate_adx

def calculate_indicators(market_data):
    close_prices = [float(candle['mid']['c']) for candle in market_data if candle['complete']]
    high_prices = [float(candle['mid']['h']) for candle in market_data if candle['complete']]
    low_prices = [float(candle['mid']['l']) for candle in market_data if candle['complete']]

    ema_fast_period = int(os.getenv("EMA_FAST_PERIOD", "9"))
    ema_slow_period = int(os.getenv("EMA_SLOW_PERIOD", "21"))

    # --- Bollinger Bands (DataFrame) ---
    bb_df = calculate_bollinger_bands(close_prices)

    # --- ADX (trend strength) ---
    adx_series = calculate_adx(high_prices, low_prices, close_prices)

    indicators = {
        'rsi': calculate_rsi(close_prices),
        'ema_fast': calculate_ema(close_prices, period=ema_fast_period),
        'ema_slow': calculate_ema(close_prices, period=ema_slow_period),
        'atr': calculate_atr(high_prices, low_prices, close_prices),
        # Spread Bollinger components so filters can access them directly
        'bb_upper': bb_df['upper_band'],
        'bb_lower': bb_df['lower_band'],
        'bb_middle': bb_df['middle_band'],
        'adx': adx_series,
    }

    return indicators
