import os
import pandas as pd
import numpy as np

def calculate_rsi(prices, period: int = None):
    if period is None:
        period = int(os.getenv('RSI_PERIOD', 14))

    prices = pd.Series(prices)
    delta = prices.diff(1)

    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(window=period, min_periods=period).mean().iloc[:period+1]
    avg_loss = loss.rolling(window=period, min_periods=period).mean().iloc[:period+1]

    gain = gain.iloc[period+1:]
    loss = loss.iloc[period+1:]

    for i in range(len(gain)):
        avg_gain = pd.concat([avg_gain, pd.Series(
            (avg_gain.iloc[-1] * (period - 1) + gain.iloc[i]) / period
        )], ignore_index=True)

        avg_loss = pd.concat([avg_loss, pd.Series(
            (avg_loss.iloc[-1] * (period - 1) + loss.iloc[i]) / period
        )], ignore_index=True)

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    rsi.index = prices.index[-len(rsi):]
    return rsi
