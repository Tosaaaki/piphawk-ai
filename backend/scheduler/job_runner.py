from datetime import datetime, timedelta
import time
import logging
import os

from backend.market_data.tick_fetcher import fetch_tick_data
from backend.market_data.candle_fetcher import fetch_candles
from backend.indicators.calculate_indicators import calculate_indicators
from backend.strategy.entry_logic import process_entry
from backend.strategy.exit_logic import process_exit
from backend.orders.position_manager import check_current_position
from backend.orders.order_manager import OrderManager
from backend.utils.openai_client import ask_openai
from backend.strategy.signal_filter import pass_entry_filter
from backend.strategy.exit_ai_decision import evaluate as ai_exit_evaluate
from backend.strategy.higher_tf_analysis import analyze_higher_tf
from dotenv import load_dotenv
from backend.logs.update_oanda_trades import update_oanda_trades
def build_exit_context(position, tick_data, indicators) -> dict:
    """Compose a minimal context dict for AI exit evaluation."""
    bid = float(tick_data["prices"][0]["bids"][0]["price"])
    ask = float(tick_data["prices"][0]["asks"][0]["price"])
    pip_size = float(os.getenv("PIP_SIZE", "0.01"))
    unrealized_pl_pips = float(position["unrealizedPL"]) / float(os.getenv("PIP_VALUE_JPY", "100"))
    context = {
        "side": "long" if position.get("long") else "short",
        "units": abs(int(position["long"]["units"] if position.get("long") else position["short"]["units"])),
        "avg_price": float(position["long"]["averagePrice"] if position.get("long") else position["short"]["averagePrice"]),
        "unrealized_pl_pips": unrealized_pl_pips,
        "bid": bid,
        "ask": ask,
        "spread_pips": (ask - bid) / pip_size,
        "atr_pips": indicators["atr"][-1],
        "rsi": indicators["rsi"][-1],
        "ema_slope": indicators["ema_slope"][-1],
    }
    return context

log_level = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=getattr(logging, log_level, logging.INFO),
                    format="%(levelname)s:%(name)s:%(message)s")
logger = logging.getLogger(__name__)

order_mgr = OrderManager()


DEFAULT_PAIR = os.getenv('DEFAULT_PAIR', 'USD_JPY')

# POSITION_REVIEW_ENABLED : "true" | "false"  – enable/disable periodic position reviews (default "true")
# POSITION_REVIEW_SEC     : seconds between AI reviews while holding a position   (default 60)
# AIに利益確定を問い合わせる閾値（TP目標の何割以上で問い合わせるか）
AI_PROFIT_TRIGGER_RATIO = float(os.getenv('AI_PROFIT_TRIGGER_RATIO', '0.5'))

class JobRunner:
    def __init__(self, interval_seconds=1):
        self.interval_seconds = interval_seconds
        self.last_run = None
        # --- AI cooldown values ---------------------------------------
        #   * AI_COOLDOWN_SEC_OPEN : seconds between AI calls while holding a position
        #   * AI_COOLDOWN_SEC_FLAT : seconds between AI calls while flat (no position)
        self.ai_cooldown_open = int(os.getenv("AI_COOLDOWN_SEC_OPEN", "30"))
        self.ai_cooldown_flat = int(os.getenv("AI_COOLDOWN_SEC_FLAT", "60"))
        # Current effective cooldown (updated each loop iteration)
        self.ai_cooldown = self.ai_cooldown_flat
        # --- position review (巡回) settings ----------------------------
        self.review_enabled = os.getenv("POSITION_REVIEW_ENABLED", "true").lower() == "true"
        self.review_sec = int(os.getenv("POSITION_REVIEW_SEC", "60"))
        # Toggle for higher‑timeframe reference levels (daily / H4)
        self.higher_tf_enabled = os.getenv("HIGHER_TF_ENABLED", "true").lower() == "true"
        self.last_position_review_ts = None  # datetime of last position review
        # Epoch timestamp of last AI call (seconds)
        self.last_ai_call = datetime.min
        # Entry cooldown: time in seconds after a close during which new entries are skipped
        self.entry_cooldown_sec = int(os.getenv("ENTRY_COOLDOWN_SEC", "30"))
        self.last_close_ts: datetime | None = None

    def run(self):
        logger.info("Job Runner started.")
        while True:
            try:
                now = datetime.utcnow()
                # Hot‑reload .env each cycle so updated thresholds take effect without restart
                load_dotenv(override=True)
                logger.debug("[JobRunner] .env reloaded")
                # Refresh POSITION_REVIEW_SEC dynamically each loop
                self.review_sec = int(os.getenv("POSITION_REVIEW_SEC", self.review_sec))
                logger.debug(f"review_sec={self.review_sec}")
                # Refresh HIGHER_TF_ENABLED dynamically
                self.higher_tf_enabled = os.getenv("HIGHER_TF_ENABLED", "true").lower() == "true"
                if self.last_run is None or (now - self.last_run) >= timedelta(seconds=self.interval_seconds):
                    logger.info(f"Running job at {now.isoformat()}")

                    # ティックデータ取得（発注用）
                    tick_data = fetch_tick_data(DEFAULT_PAIR)
                    logger.info(f"Tick data fetched: {tick_data}")
                    logger.info(f"Tick data details: {tick_data}")

                    # ローソク足データ取得（指標計算用）
                    candles = fetch_candles(DEFAULT_PAIR, granularity='M5', count=50)
                    logger.info(f"Candle data fetched: {candles[-1] if candles else 'No candles'}")
                    logger.info(f"Last candle details: {candles[-1] if candles else 'No candles retrieved'}")

                    # -------- Higher‑timeframe reference levels --------
                    higher_tf = {}
                    if self.higher_tf_enabled:
                        higher_tf = analyze_higher_tf(DEFAULT_PAIR)
                        logger.debug(f"Higher‑TF levels: {higher_tf}")

                    # 指標計算
                    indicators = calculate_indicators(candles)
                    logger.info("Indicators calculation successful.")

                    # ポジション確認
                    has_position = check_current_position(DEFAULT_PAIR)
                    logger.info(f"Current position status: {has_position}")
                    logger.info(f"Has open position for {DEFAULT_PAIR}: {has_position}")

                    # ---- Dynamic cooldown (OPEN / FLAT) ---------------
                    if has_position:
                        self.ai_cooldown = self.ai_cooldown_open
                    else:
                        self.ai_cooldown = self.ai_cooldown_flat

                    # Determine position_side for further logic
                    if has_position and has_position.get("long") and int(has_position["long"]["units"]) > 0:
                        position_side = "long"
                    elif has_position and has_position.get("short") and int(has_position["short"]["units"]) < 0:
                        position_side = "short"
                    else:
                        position_side = None

                    # Inserted logic for dynamic SL management and AI profit-taking consultation
                    if has_position and position_side:
                        current_price = float(tick_data['prices'][0]['bids'][0]['price']) if position_side == 'long' else float(tick_data['prices'][0]['asks'][0]['price'])
                        entry_price = float(has_position[position_side]['averagePrice'])

                        pip_size = float(os.getenv("PIP_SIZE", "0.01"))
                        current_profit_pips = (current_price - entry_price) / pip_size if position_side == 'long' else (entry_price - current_price) / pip_size

                        BE_TRIGGER_PIPS = float(os.getenv("BE_TRIGGER_PIPS", "5"))
                        TP_PIPS = float(os.getenv("INIT_TP_PIPS", "30"))
                        AI_PROFIT_TRIGGER_RATIO = float(os.getenv("AI_PROFIT_TRIGGER_RATIO", "0.5"))

                        if current_profit_pips >= BE_TRIGGER_PIPS:
                            new_sl_price = entry_price
                            trade_id = has_position[position_side]['tradeIDs'][0]
                            order_mgr.update_trade_sl(trade_id, DEFAULT_PAIR, new_sl_price)
                            logger.info(f"SL updated to entry price to secure minimum profit: {new_sl_price}")

                        if current_profit_pips >= TP_PIPS * AI_PROFIT_TRIGGER_RATIO:
                            decision_prompt = (
                                f"現在、{DEFAULT_PAIR}で{position_side}ポジションを保持しています。\n"
                                f"現在の利益は{current_profit_pips:.1f}pipsで、目標TPまであと{TP_PIPS - current_profit_pips:.1f}pipsです。\n"
                                "現在の市場状況を考慮して、利益をここで確定すべきでしょうか？それともさらに伸ばすべきでしょうか？"
                            )

                            ai_decision = ask_openai(decision_prompt)

                            if "確定" in ai_decision or "exit" in ai_decision.lower():
                                order_mgr.close_position(DEFAULT_PAIR, side=position_side if position_side else "both")
                                self.last_close_ts = datetime.utcnow()
                                logger.info("Position closed based on AI recommendation.")
                            elif "伸ばす" in ai_decision or "hold" in ai_decision.lower():
                                atr_value = indicators["atr"][-1]
                                ATR_SL_MULTIPLIER = float(os.getenv("ATR_SL_MULTIPLIER", 1.5))
                                dynamic_sl_pips = atr_value * ATR_SL_MULTIPLIER
                                new_sl_price = current_price - dynamic_sl_pips * pip_size if position_side == 'long' else current_price + dynamic_sl_pips * pip_size
                                order_mgr.update_trade_sl(trade_id, DEFAULT_PAIR, new_sl_price)
                                logger.info(f"SL dynamically updated to protect profits at: {new_sl_price}")

                    # ---- Position‑review timing -----------------------------
                    due_for_review = False
                    if has_position and self.review_enabled:
                        if self.last_position_review_ts is None:
                            due_for_review = True
                        else:
                            elapsed_review = (now - self.last_position_review_ts).total_seconds()
                            due_for_review = elapsed_review >= self.review_sec

                    # --- Cool‑down check ------------------------------------
                    elapsed_seconds = (datetime.now() - self.last_ai_call).total_seconds()
                    if (not due_for_review) and elapsed_seconds < self.ai_cooldown:
                        logger.info(f"AI cooldown active ({elapsed_seconds:.1f}s < {self.ai_cooldown}s). Skipping AI call.")
                        self.last_run = now
                        # Update OANDA trade history every second
                        update_oanda_trades()
                        time.sleep(self.interval_seconds)
                        continue

                    # AIによるエントリー/エグジット判断
                    if not has_position:
                        # 1) Entry cooldown check
                        if self.last_close_ts and (datetime.utcnow() - self.last_close_ts).total_seconds() < self.entry_cooldown_sec:
                            logger.info(f"Entry cooldown active ({(datetime.utcnow() - self.last_close_ts).total_seconds():.1f}s < {self.entry_cooldown_sec}s). Skipping entry.")
                            self.last_run = now
                            update_oanda_trades()
                            time.sleep(self.interval_seconds)
                            continue

                        # 2) Pivot-based suppression: avoid entries within 5 pips of daily pivot
                        if self.higher_tf_enabled and higher_tf.get("pivot_d") is not None:
                            current_price = float(tick_data["prices"][0]["bids"][0]["price"])
                            pip_size = float(os.getenv("PIP_SIZE", "0.01"))
                            pivot = higher_tf["pivot_d"]
                            if abs((current_price - pivot) / pip_size) <= 5:
                                logger.info(f"Pivot suppression: price {current_price} within 5 pips of daily pivot {pivot}. Skipping entry.")
                                self.last_run = now
                                update_oanda_trades()
                                time.sleep(self.interval_seconds)
                                continue

                        # ── Entry side ───────────────────────────────
                        if pass_entry_filter(indicators):
                            logger.info("Filter OK → Processing entry decision with AI.")
                            result = process_entry(indicators, tick_data, candles)
                            if not result:
                                logger.info("process_entry returned False → aborting entry and continuing loop")
                                self.last_run = now
                                update_oanda_trades()
                                time.sleep(self.interval_seconds)
                                continue
                            self.last_ai_call = datetime.now()  # AI呼び出し時刻を明示的に記録（クールダウン用）
                        else:
                            logger.info("Filter NG → AI entry decision skipped.")
                            self.last_position_review_ts = None
                    # (removed: periodic exit check block)
                # Update OANDA trade history every second
                self.last_run = now

                update_oanda_trades()
                time.sleep(self.interval_seconds)

            except Exception as e:
                logger.error(f"Error occurred during job execution: {e}", exc_info=True)
                time.sleep(self.interval_seconds)

if __name__ == "__main__":
    runner = JobRunner(interval_seconds=1)
    runner.run()
