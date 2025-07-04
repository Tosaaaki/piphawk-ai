import json
import logging
import os
import sys
import time
import uuid
from pathlib import Path

if __package__ is None or __package__ == "":
    # スクリプト実行時にリポジトリルートをパスへ追加
    sys.path.append(str(Path(__file__).resolve().parents[2]))
from datetime import datetime, timedelta, timezone
from logging import getLogger
from typing import Any

try:
    from prometheus_client import start_http_server
except Exception:  # pragma: no cover - optional dependency or test stub

    def start_http_server(*_args, **_kwargs):
        return None


from backend.core.ai_throttle import get_cooldown
from backend.utils import env_loader, trade_age_seconds
from backend.utils.openai_client import reset_call_counter, set_call_limit
from backend.utils.restart_guard import can_restart
from maintenance.disk_guard import maybe_cleanup
from monitoring import metrics_publisher
from monitoring.safety_trigger import SafetyTrigger

try:
    from config import params_loader

    last_mode = getattr(params_loader, "load_last_mode", lambda: None)()
    force_scalp = env_loader.get_env("SCALP_MODE", "").lower() == "true"
    if force_scalp or last_mode in ("scalp", "scalp_momentum", "micro_scalp"):
        params_loader.load_params(path="config/scalp_params.yml")
    elif last_mode == "trend_follow":
        params_loader.load_params(path="config/trend.yml")
    else:
        params_loader.load_params()
except Exception:
    pass

from backend.indicators.calculate_indicators import calculate_indicators_multi
from backend.market_data.candle_fetcher import fetch_multiple_timeframes
from backend.market_data.tick_fetcher import fetch_tick_data

try:
    from backend.strategy.entry_logic import _pending_limits, process_entry
except Exception:  # pragma: no cover - test stubs may remove module

    def process_entry(*_a, **_k):
        return None

    _pending_limits: dict = {}

try:
    from backend.strategy.exit_logic import process_exit
except Exception:  # pragma: no cover - test stubs may remove module

    def process_exit(*_a, **_k):
        return None


try:
    from backend.strategy.exit_ai_decision import evaluate as evaluate_exit_ai
except Exception:  # pragma: no cover - test stubs may remove module

    def evaluate_exit_ai(*_a, **_k):
        return None


try:
    from backend.orders.position_manager import (
        check_current_position,
        get_margin_used,
        get_position_details,
    )
except ImportError:  # tests may stub position_manager without helpers
    from backend.orders.position_manager import check_current_position

    def get_margin_used(*_args, **_kwargs):
        return None

    def get_position_details(*_args, **_kwargs):
        return None


try:
    from backend.orders.order_manager import OrderManager
except Exception:  # pragma: no cover - test stubs may remove module

    class OrderManager:
        def __getattr__(self, _name):
            def _noop(*_a, **_k):
                return None

            return _noop


from backend.logs.perf_stats_logger import PerfTimer

try:
    from ai.scalp_trend_classifier import MarketRegimeClassifier
    from ai.tp_sl_calculator import calc_tp_sl
    from backend.strategy.signal_filter import (
        consecutive_higher_highs,
        consecutive_lower_lows,
        counter_trend_block,
        detect_climax_reversal,
        filter_pre_ai,
        pass_entry_filter,
        pass_exit_filter,
    )
    from filters.session_filter import apply_filters
except Exception:  # pragma: no cover - test stubs may lack filter_pre_ai
    from backend.strategy.signal_filter import pass_entry_filter

    def filter_pre_ai(*_args, **_kwargs):
        return False

    def detect_climax_reversal(*_a, **_k):
        return None

    def counter_trend_block(*_a, **_k):
        return False

try:
    from backend.strategy.llm_exit import propose_exit_adjustment
except Exception:  # pragma: no cover - optional during tests
    def propose_exit_adjustment(*_a, **_k):
        return {"action": "HOLD", "tp": None, "sl": None}

try:
    from backend.logs.log_manager import count_exit_adjust_calls, log_exit_adjust
except Exception:  # pragma: no cover
    def log_exit_adjust(*_a, **_k) -> None:
        pass

    def count_exit_adjust_calls(*_a, **_k) -> int:
        return 0

try:
    from backend.strategy.openai_analysis import (
        get_market_condition,
        get_trade_plan,
        should_convert_limit_to_market,
    )
except Exception:  # pragma: no cover - test stubs may remove module

    def get_market_condition(*_a, **_k):
        return None

    def get_trade_plan(*_a, **_k):
        return None

    def should_convert_limit_to_market(*_a, **_k):
        return False


from backend.strategy import pattern_scanner
from backend.strategy.higher_tf_analysis import analyze_higher_tf
from backend.strategy.momentum_follow import follow_breakout
from piphawk_ai.tech_arch.pipeline import run_cycle as tech_run_cycle

try:
    from piphawk_ai.analysis.signal_filter import is_multi_tf_aligned
except Exception:  # pragma: no cover - optional during tests

    def is_multi_tf_aligned(*_a, **_k):
        return None

try:
    from analysis.atmosphere.market_air_sensor import MarketSnapshot
    from piphawk_ai.vote_arch.entry_buffer import PlanBuffer
    from piphawk_ai.vote_arch.pipeline import (
        PipelineResult,
    )
    from piphawk_ai.vote_arch.pipeline import run_cycle as vote_run_cycle
    from piphawk_ai.vote_arch.regime_detector import MarketMetrics
except Exception:  # pragma: no cover - optional module
    vote_run_cycle = lambda *_a, **_k: PipelineResult(None, "", "", False)

    class PlanBuffer:
        def __init__(self) -> None:
            pass

    class MarketMetrics:
        def __init__(self, adx_m5: float, ema_fast: float, ema_slow: float, bb_width_m5: float) -> None:
            self.adx_m5 = adx_m5
            self.ema_fast = ema_fast
            self.ema_slow = ema_slow
            self.bb_width_m5 = bb_width_m5

    class MarketSnapshot:
        def __init__(self, atr: float, news_score: float, oi_bias: float) -> None:
            self.atr = atr
            self.news_score = news_score
            self.oi_bias = oi_bias

# Backward compatibility: unified pipeline runner
def run_cycle(*args, **kwargs):
    """Run the selected pipeline based on USE_VOTE_PIPELINE."""
    if env_loader.get_env("USE_VOTE_PIPELINE", "false").lower() == "true":
        return vote_run_cycle(*args, **kwargs)
    tech_run_cycle(*args, **kwargs)
    if RUNNER_INSTANCE is not None:
        RUNNER_INSTANCE._stop = True
    return PipelineResult(None, "", "", True)

try:
    from piphawk_ai.tech_arch.pipeline import run_cycle as tech_run_cycle
except Exception:  # pragma: no cover - optional module
    def tech_run_cycle(*_a, **_k):
        return None
import requests

try:
    from signals.composite_mode import decide_trade_mode_detail
except Exception:  # pragma: no cover - test stubs may remove module

    def decide_trade_mode_detail(*_a, **_k):
        return "scalp_momentum", 0.0, []


from backend.strategy.risk_manager import calc_lot_size
from risk.portfolio_risk_manager import PortfolioRiskManager

try:
    from backend.orders.position_manager import (
        get_account_balance,
        get_open_positions,
    )
except Exception:  # テストでスタブが残っている場合のフォールバック

    def get_account_balance():
        return 0.0

    def get_open_positions():
        return []


from backend.logs.trade_logger import ExitReason, log_trade
from backend.scheduler.policy_updater import PolicyUpdater
from backend.utils.notification import send_line_message
from strategies import (
    ScalpStrategy,
    StrategySelector,
    StrongTrendStrategy,
    TrendStrategy,
)
from strategies.context_builder import (
    build_context,
    recent_strategy_performance,
)

try:
    from backend.logs.log_manager import (
        clear_last_entry_info,
        get_last_entry_info,
        log_policy_transition,
        set_last_entry_info,
    )
except Exception:  # pragma: no cover - test stubs may remove

    def log_policy_transition(*_a, **_k):
        return None


from backend.logs.info_logger import info

try:
    from backend.logs.log_manager import log_entry_skip
except Exception:  # pragma: no cover - test stubs may omit log_entry_skip

    def log_entry_skip(*_args, **_kwargs):
        return None


#
# optional helper for pending LIMIT look‑up;
# provide stub if module is absent in current build
try:
    from backend.utils.oanda_client import get_pending_entry_order  # type: ignore
except ModuleNotFoundError:

    def get_pending_entry_order(instrument: str):
        return None


from backend.logs.update_oanda_trades import fetch_trade_details, update_oanda_trades


def build_exit_context(position, tick_data, indicators, indicators_m1=None) -> dict:
    """Compose a minimal context dict for AI exit evaluation."""
    bid = float(tick_data["prices"][0]["bids"][0]["price"])
    ask = float(tick_data["prices"][0]["asks"][0]["price"])
    pip_size = float(env_loader.get_env("PIP_SIZE", "0.01"))
    unrealized_pl_pips = float(position["unrealizedPL"]) / float(
        env_loader.get_env("PIP_VALUE_JPY", "100")
    )
    side = "long" if int(position.get("long", {}).get("units", 0)) != 0 else "short"
    context = {
        "side": side,
        "units": abs(int(position[side].get("units", 0))),
        "avg_price": float(position[side].get("averagePrice", 0.0)),
        "unrealized_pl_pips": unrealized_pl_pips,
        "bid": bid,
        "ask": ask,
        "spread_pips": (ask - bid) / pip_size,
        "atr_pips": (
            indicators["atr"].iloc[-1]
            if hasattr(indicators["atr"], "iloc")
            else indicators["atr"][-1]
        ),
        "rsi": (
            indicators["rsi"].iloc[-1]
            if hasattr(indicators["rsi"], "iloc")
            else indicators["rsi"][-1]
        ),
        "ema_slope": (
            indicators["ema_slope"].iloc[-1]
            if hasattr(indicators["ema_slope"], "iloc")
            else indicators["ema_slope"][-1]
        ),
    }
    if indicators_m1:
        context["indicators_m1"] = {
            k: (v.iloc[-1] if hasattr(v, "iloc") else v[-1])
            for k, v in indicators_m1.items()
            if isinstance(v, (list, tuple)) or hasattr(v, "iloc")
        }
    return context


# ログフォーマットとレベルを統一
log_level = env_loader.get_env("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    format="%(asctime)s %(levelname)s %(message)s",
    level=getattr(logging, log_level, logging.INFO),
)
log = getLogger(__name__)

order_mgr = OrderManager()

# Currently active JobRunner instance (if any)
RUNNER_INSTANCE = None


DEFAULT_PAIR = env_loader.get_env("DEFAULT_PAIR", "USD_JPY")
ENTRY_USE_AI = env_loader.get_env("ENTRY_USE_AI", "true").lower() == "true"
USE_LLM_REGIME = env_loader.get_env("USE_LLM_REGIME", "true").lower() == "true"
USE_LLM_MARKET_COND = (
    env_loader.get_env("USE_LLM_MARKET_COND", "true").lower() == "true"
)

# Comma-separated chart pattern names used for AI analysis
PATTERN_NAMES = [
    p.strip()
    for p in env_loader.get_env(
        "PATTERN_NAMES",
        "double_bottom,double_top",
    ).split(",")
    if p.strip()
]

OANDA_API_KEY = env_loader.get_env("OANDA_API_KEY")
OANDA_ACCOUNT_ID = env_loader.get_env("OANDA_ACCOUNT_ID")
MARGIN_WARNING_THRESHOLD = float(env_loader.get_env("MARGIN_WARNING_THRESHOLD", "0"))
# Additional lot size for scaling into an existing position
SCALE_LOT_SIZE = float(env_loader.get_env("SCALE_LOT_SIZE", "0.5"))
SCALE_MAX_POS = int(env_loader.get_env("SCALE_MAX_POS", "0"))
SCALE_TRIGGER_ATR = float(env_loader.get_env("SCALE_TRIGGER_ATR", "0"))
# ----- limit‑order housekeeping ------------------------------------
MAX_LIMIT_AGE_SEC = int(env_loader.get_env("MAX_LIMIT_AGE_SEC", "180"))
# seconds before a pending LIMIT is cancelled
PENDING_GRACE_MIN = int(env_loader.get_env("PENDING_GRACE_MIN", "3"))
SL_COOLDOWN_SEC = int(env_loader.get_env("SL_COOLDOWN_SEC", "300"))
MAX_AI_EXIT_CALLS = int(env_loader.get_env("MAX_AI_EXIT_CALLS", "1"))

# POSITION_REVIEW_ENABLED : "true" | "false"  – enable/disable periodic position reviews (default "true")
# POSITION_REVIEW_SEC     : seconds between AI reviews while holding a position   (default 60)
# AIに利益確定を問い合わせる閾値（TP目標の何割以上で問い合わせるか）
AI_PROFIT_TRIGGER_RATIO = float(env_loader.get_env("AI_PROFIT_TRIGGER_RATIO", "0.3"))
TP_EXTENSION_ENABLED = (
    env_loader.get_env("TP_EXTENSION_ENABLED", "false").lower() == "true"
)
TP_EXTENSION_ADX_MIN = float(env_loader.get_env("TP_EXTENSION_ADX_MIN", "25"))
TP_EXTENSION_ATR_MULT = float(env_loader.get_env("TP_EXTENSION_ATR_MULT", "1.0"))
TP_REDUCTION_ENABLED = (
    env_loader.get_env("TP_REDUCTION_ENABLED", "false").lower() == "true"
)
TP_REDUCTION_ADX_MAX = float(env_loader.get_env("TP_REDUCTION_ADX_MAX", "20"))
TP_REDUCTION_MIN_SEC = int(env_loader.get_env("TP_REDUCTION_MIN_SEC", "900"))
TP_REDUCTION_ATR_MULT = float(env_loader.get_env("TP_REDUCTION_ATR_MULT", "1.0"))

# Peak profit exit settings
PEAK_EXIT_ENABLED = env_loader.get_env("PEAK_EXIT_ENABLED", "false").lower() == "true"
MM_DRAW_MAX_ATR_RATIO = float(env_loader.get_env("MM_DRAW_MAX_ATR_RATIO", "2.0"))


# ───────────────────────────────────────────────────────────
#  Check if the instrument is currently tradeable via OANDA
# ───────────────────────────────────────────────────────────
def instrument_is_tradeable(instrument: str) -> bool:
    if not OANDA_API_KEY or not OANDA_ACCOUNT_ID:
        return True  # assume open if credentials missing

    url = f"https://api-fxtrade.oanda.com/v3/accounts/{OANDA_ACCOUNT_ID}/instruments"
    headers = {"Authorization": f"Bearer {OANDA_API_KEY}"}
    params = {"instruments": instrument}
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=5)
        resp.raise_for_status()
        instruments = resp.json().get("instruments", [])
        if instruments:
            return str(instruments[0].get("tradeable", "true")).lower() == "true"
    except requests.RequestException as exc:
        log.warning(f"instrument_is_tradeable: {exc}")
    return False


class JobRunner:
    def __init__(self, interval_seconds=1):
        self.interval_seconds = interval_seconds
        self.last_run = None
        self._stop = False
        # Start Prometheus metrics server
        metrics_port = int(env_loader.get_env("METRICS_PORT", "8001"))
        try:
            start_http_server(metrics_port)
            log.info("Prometheus metrics server running on port %s", metrics_port)
        except Exception as exc:  # pragma: no cover - metrics optional
            log.warning(f"Metrics server start failed: {exc}")
        loss_lim = float(env_loader.get_env("LOSS_LIMIT", "0"))
        err_lim = int(env_loader.get_env("ERROR_LIMIT", "0"))
        self.safety = SafetyTrigger(loss_limit=loss_lim, error_limit=err_lim)
        self.safety.attach(self.stop)
        bal = get_account_balance()
        if bal is None:
            bal = float(env_loader.get_env("ACCOUNT_BALANCE", "10000"))
        self.account_balance = bal
        max_cvar = float(env_loader.get_env("MAX_CVAR", "0"))
        self.risk_mgr = (
            PortfolioRiskManager(max_cvar=max_cvar) if max_cvar > 0 else None
        )
        self.classifier = MarketRegimeClassifier()
        # --- AI cooldown values ---------------------------------------
        #   * AI_COOLDOWN_SEC_OPEN : エントリー用クールダウン時間
        #   * AI_COOLDOWN_SEC_FLAT : エグジット用クールダウン時間
        self.ai_cooldown_open = int(env_loader.get_env("AI_COOLDOWN_SEC_OPEN", "60"))
        self.ai_cooldown_flat = int(env_loader.get_env("AI_COOLDOWN_SEC_FLAT", "60"))
        # 現在のクールダウン（ループ毎に更新）
        self.ai_cooldown = self.ai_cooldown_open
        # --- position review (巡回) settings ----------------------------
        self.review_enabled = (
            env_loader.get_env("POSITION_REVIEW_ENABLED", "true").lower() == "true"
        )
        self.review_sec = int(env_loader.get_env("POSITION_REVIEW_SEC", "60"))
        # LIMIT order age threshold
        self.max_limit_age_sec = MAX_LIMIT_AGE_SEC
        self.pending_grace_sec = PENDING_GRACE_MIN * 60
        self.current_policy = None
        self.policy_updater = None
        if env_loader.get_env("USE_OFFLINE_POLICY", "false").lower() == "true":
            try:
                self.policy_updater = PolicyUpdater(self)
                self.policy_updater.start()
            except Exception as exc:  # pragma: no cover - optional
                log.warning(f"PolicyUpdater start failed: {exc}")
        # ----- Additional runtime state --------------------------------
        # Toggle for higher‑timeframe reference levels (daily / H4)
        self.higher_tf_enabled = (
            env_loader.get_env("HIGHER_TF_ENABLED", "true").lower() == "true"
        )
        self.last_position_review_ts = None  # datetime of last position review
        # Epoch timestamp of last AI call (seconds)
        self.last_ai_call = datetime.min
        self.cluster_regime = None
        # Entry cooldown settings
        self.entry_cooldown_sec = int(env_loader.get_env("ENTRY_COOLDOWN_SEC", "30"))
        self.last_close_ts: datetime | None = None
        # --- last stop-loss info ----------------------------------
        self.last_sl_side: str | None = None
        self.last_sl_time: datetime | None = None
        self.sl_cooldown_sec = SL_COOLDOWN_SEC
        # Storage for latest indicators by timeframe
        self.indicators_M1: dict | None = None
        self.indicators_S10: dict | None = None
        self.indicators_M5: dict | None = None
        self.indicators_M15: dict | None = None
        self.indicators_H1: dict | None = None
        self.indicators_H4: dict | None = None
        self.indicators_D: dict | None = None
        # Flags for breakeven and SL management
        self.breakeven_reached: bool = False
        self.sl_reset_done: bool = False
        self.tp_extended: bool = False
        self.tp_reduced: bool = False
        # Latest detected chart patterns by timeframe
        self.patterns_by_tf: dict[str, str | None] = {}
        # Highest profit observed since entry
        self.max_profit_pips: float = 0.0
        # Count of additional SCALE entries for current position
        self.scale_count: int = 0
        # recent M5 candles for peak detection
        self.last_candles_m5: list[dict] | None = None

        # SCALP_MODE 時に市場判断へ使う時間足
        self.scalp_cond_tf = env_loader.get_env("SCALP_COND_TF", "M1").upper()

        # 現在のトレードモード（scalp / trend_follow / none）

        self.trade_mode: str | None
        self.current_params_file: str
        mode_env = env_loader.get_env("SCALP_MODE")
        # 空文字や未設定の場合は None と同等に扱う
        if not mode_env:
            self.trade_mode = None
            self.current_params_file = "config/strategy.yml"
        elif mode_env.lower() == "true":
            self.trade_mode = "scalp"
            self.current_params_file = "config/scalp_params.yml"
        else:
            self.trade_mode = "trend_follow"
            self.current_params_file = "config/trend.yml"
        self.mode_reason = ""
        # set initial AI call limit based on mode
        default_limit = int(env_loader.get_env("MAX_AI_CALLS_PER_LOOP", "1"))
        set_call_limit(
            4 if self.trade_mode in ("scalp_momentum", "micro_scalp") else default_limit
        )

        # Majority-vote pipeline selection
        default_vote = "false" if self.trade_mode == "scalp" else "true"
        self.use_vote_arch = env_loader.get_env("USE_VOTE_ARCH", "true").lower() == "true"
        self.use_vote_pipeline = (
            env_loader.get_env("USE_VOTE_PIPELINE", default_vote).lower() == "true"
        )
        self.plan_buffer = (
            PlanBuffer() if self.use_vote_arch and self.use_vote_pipeline else None
        )
        log.info(
            "USE_VOTE_PIPELINE=%s → %s pipeline active",
            self.use_vote_pipeline,
            "vote_arch" if self.use_vote_pipeline else "tech_arch",
        )

        # Restore TP adjustment flags based on existing TP order comment
        try:
            pos = get_position_details(DEFAULT_PAIR)
            if pos:
                er_raw = pos.get("entry_regime")
                tp_comment = pos.get("tp_comment")
                if er_raw and tp_comment:
                    er = json.loads(er_raw)
                    entry_uuid = er.get("entry_uuid")
                    if entry_uuid and entry_uuid in tp_comment:
                        self.tp_extended = True
                        self.tp_reduced = True
        except Exception as exc:  # pragma: no cover - ignore init failures
            log.debug(f"TP flag restore failed: {exc}")

        token = env_loader.get_env("LINE_CHANNEL_TOKEN", "")
        user_id = env_loader.get_env("LINE_USER_ID", "")
        log.info(
            "JobRunner startup - LINE token set: %s, user ID set: %s",
            bool(token),
            bool(user_id),
        )
        # 初期の SCALP_MODE 設定をログへ記録
        scalp_active = env_loader.get_env("SCALP_MODE", "false").lower() == "true"

        log.info("Initial SCALP_MODE is %s", "ON" if scalp_active else "OFF")

        # 初期化時に戦略セレクターを設定
        use_policy = env_loader.get_env("USE_OFFLINE_POLICY", "false").lower() == "true"
        self.strategy_selector = StrategySelector(
            {
                "scalp": ScalpStrategy(),
                "trend": TrendStrategy(),
                "strong_trend": StrongTrendStrategy(),
            },
            use_offline_policy=False,
        )
        if use_policy and self.current_policy is not None:
            self.strategy_selector.offline_policy = self.current_policy
        ctx, strat = get_last_entry_info()
        self.last_entry_context = ctx
        self.last_entry_strategy = strat
        self.current_context = None
        self.current_strategy_name = None

        info(
            "startup",
            mode=self.trade_mode or "none",
            scalp_mode=scalp_active,
            ai_version=env_loader.get_env("AI_VERSION", "unknown"),
        )

        # expose instance for management API to update settings
        global RUNNER_INSTANCE
        RUNNER_INSTANCE = self

    def _get_recent_trade_pl(self, limit: int = 50) -> list[float]:
        from backend.logs.log_manager import get_db_connection

        try:
            with get_db_connection() as conn:
                cur = conn.cursor()
                cur.execute(
                    "SELECT profit_loss FROM trades ORDER BY trade_id DESC LIMIT ?",
                    (limit,),
                )
                rows = cur.fetchall()
            return [float(r[0]) for r in rows if r[0] is not None]
        except Exception as exc:  # pragma: no cover
            log.warning(f"fetch PL failed: {exc}")
            return []

    def _update_portfolio_risk(self) -> None:
        if not self.risk_mgr:
            return
        trade_pl = self._get_recent_trade_pl()
        open_pl: list[float] = []
        try:
            positions = get_open_positions() or []
            for pos in positions:
                try:
                    open_pl.append(float(pos.get("unrealizedPL", 0.0)))
                except Exception:
                    pass
        except Exception as exc:  # pragma: no cover
            log.debug(f"open position fetch failed: {exc}")
        self.risk_mgr.update_risk_metrics(trade_pl, open_pl)
        if self.risk_mgr.check_stop_conditions():
            log.warning("Portfolio CVaR limit exceeded")
            if env_loader.get_env("FORCE_CLOSE_ON_RISK", "false").lower() == "true":
                try:
                    order_mgr.close_all_positions()
                except Exception as exc:  # pragma: no cover
                    log.error(f"Force close failed: {exc}")

    def _get_cond_indicators(self) -> dict:
        """Return indicators for market condition check."""
        tf = env_loader.get_env("TREND_COND_TF", "M5").upper()
        if self.trade_mode in ("scalp", "scalp_momentum", "micro_scalp"):
            tf = env_loader.get_env("SCALP_COND_TF", self.scalp_cond_tf).upper()
        return getattr(self, f"indicators_{tf}", {}) or {}

    def _evaluate_market_condition(
        self,
        candles_m1: list,
        candles_m5: list,
        candles_d1: list,
        higher_tf: dict,
    ) -> dict:
        """Return market condition using precomputed indicators."""
        if not USE_LLM_MARKET_COND:
            return {"summary": "", "market_condition": "unknown"}
        if not USE_LLM_REGIME:
            return {}
        cond_ind = self._get_cond_indicators()
        ctx = {
            "indicators": {
                k: (
                    float(val.iloc[-1])
                    if hasattr(val, "iloc") and val.iloc[-1] is not None
                    else float(val) if val is not None else None
                )
                for k, val in cond_ind.items()
            },
            "indicators_h1": {
                k: (
                    float(v.iloc[-1])
                    if hasattr(v, "iloc") and v.iloc[-1] is not None
                    else float(v) if v is not None else None
                )
                for k, v in (self.indicators_H1 or {}).items()
            },
            "indicators_h4": {
                k: (
                    float(v.iloc[-1])
                    if hasattr(v, "iloc") and v.iloc[-1] is not None
                    else float(v) if v is not None else None
                )
                for k, v in (self.indicators_H4 or {}).items()
            },
            "candles_m1": candles_m1,
            "candles_m5": candles_m5,
            "candles_d1": candles_d1,
        }
        try:
            return get_market_condition(ctx, higher_tf)
        except Exception as exc:  # pragma: no cover - optional dependency
            log.warning(f"get_market_condition failed: {exc}")
            return {}

    def reload_params_for_mode(self, mode: str) -> None:
        """Load YAML parameters for the given mode and optionally restart."""
        file_map = {
            "scalp": "config/scalp_params.yml",
            "scalp_momentum": "config/scalp_params.yml",
            "micro_scalp": "config/scalp_params.yml",
            "trend_follow": "config/trend.yml",
        }
        path = file_map.get(mode, "config/strategy.yml")
        try:
            params_loader.save_last_mode(mode)
        except Exception:
            pass
        if self.current_params_file == path:
            return
        try:
            log.info("Reloading params from %s", path)
            params_loader.load_params(path=path)
            # update AI cooldown values after reload
            self.refresh_ai_cooldowns()
            default_limit = int(env_loader.get_env("MAX_AI_CALLS_PER_LOOP", "1"))
            set_call_limit(4 if mode in ("scalp_momentum", "micro_scalp") else default_limit)
            self.current_params_file = path
        except Exception as exc:
            log.error("Param reload failed: %s", exc)
            return
        if env_loader.get_env("AUTO_RESTART", "false").lower() == "true":
            interval = float(env_loader.get_env("RESTART_MIN_INTERVAL", "60"))
            if can_restart(interval):
                log.info("AUTO_RESTART enabled – restarting process")
                python = sys.executable
                os.execv(
                    python,
                    [python, "-m", "backend.scheduler.job_runner", *sys.argv[1:]],
                )
            else:
                log.info("Restart suppressed to avoid rapid restarts")

    def _record_strategy_result(self, reward: float) -> None:
        if self.last_entry_context and self.last_entry_strategy:
            try:
                log_policy_transition(
                    json.dumps(self.last_entry_context),
                    self.last_entry_strategy,
                    float(reward),
                )
                self.strategy_selector.update(
                    self.last_entry_strategy, self.last_entry_context, float(reward)
                )
            except Exception as exc:
                log.warning(f"Strategy update failed: {exc}")
            clear_last_entry_info()
            self.last_entry_context = None
            self.last_entry_strategy = None

    # ────────────────────────────────────────────────────────────
    #  Poll & renew pending LIMIT orders
    # ────────────────────────────────────────────────────────────
    def _manage_pending_limits(
        self, instrument: str, indicators: dict, candles: list, tick_data: dict
    ):
        """Cancel stale LIMIT orders and optionally renew them."""
        MAX_LIMIT_RETRY = int(env_loader.get_env("MAX_LIMIT_RETRY", "3"))
        pend = get_pending_entry_order(instrument)
        if not pend:
            # purge any local record if OANDA reports none
            for key, rec in list(_pending_limits.items()):
                if rec.get("instrument") == instrument:
                    _pending_limits.pop(key, None)
            return

        local_info = None
        for key, rec in _pending_limits.items():
            if rec.get("order_id") == pend.get("order_id"):
                local_info = rec | {"key": key}
                break

        if local_info:
            pip_size = float(env_loader.get_env("PIP_SIZE", "0.01"))
            price = (
                float(tick_data["prices"][0]["bids"][0]["price"])
                if local_info.get("side") == "long"
                else float(tick_data["prices"][0]["asks"][0]["price"])
            )
            limit_price = float(local_info.get("limit_price", price))
            diff_pips = abs(price - limit_price) / pip_size

            atr_series = indicators.get("atr")
            if atr_series is not None and len(atr_series):
                atr_val = (
                    atr_series.iloc[-1]
                    if hasattr(atr_series, "iloc")
                    else atr_series[-1]
                )
                atr_pips = float(atr_val) / pip_size
            else:
                atr_pips = 0.0

            threshold_ratio = float(
                env_loader.get_env("LIMIT_THRESHOLD_ATR_RATIO", "0.3")
            )
            adx_series = indicators.get("adx")
            adx_val = (
                adx_series.iloc[-1]
                if adx_series is not None and len(adx_series)
                else 0.0
            )

            # --- gather additional indicators for AI decision -----------------
            rsi_series = indicators.get("rsi")
            rsi_val = (
                rsi_series.iloc[-1]
                if rsi_series is not None and len(rsi_series)
                else None
            )

            ema_slope_series = indicators.get("ema_slope")
            ema_slope_val = (
                ema_slope_series.iloc[-1]
                if ema_slope_series is not None and len(ema_slope_series)
                else None
            )

            bb_upper = indicators.get("bb_upper")
            bb_lower = indicators.get("bb_lower")
            bb_width_pips = None
            if (
                bb_upper is not None
                and bb_lower is not None
                and len(bb_upper)
                and len(bb_lower)
            ):
                bb_width_pips = (bb_upper.iloc[-1] - bb_lower.iloc[-1]) / pip_size

            if atr_pips and diff_pips >= atr_pips * threshold_ratio and adx_val >= 25:
                ctx = {
                    "diff_pips": diff_pips,
                    "atr_pips": atr_pips,
                    "adx": adx_val,
                    "rsi": rsi_val,
                    "ema_slope": ema_slope_val,
                    "bb_width_pips": bb_width_pips,
                    "side": local_info.get("side"),
                }
                try:
                    allow = should_convert_limit_to_market(ctx)
                except Exception as exc:
                    log.warning(f"AI check failed: {exc}")
                    allow = False

                if allow:
                    try:
                        log.info(
                            f"Switching LIMIT {pend['order_id']} to market (diff {diff_pips:.1f} pips)"
                        )
                        order_mgr.cancel_order(pend["order_id"])
                        try:
                            candles_dict = {"M5": candles}
                            indicators_multi = {"M5": indicators}
                            plan = get_trade_plan(
                                tick_data,
                                indicators_multi or {},
                                candles_dict or {},
                                patterns=PATTERN_NAMES,
                                detected_patterns=self.patterns_by_tf,
                                trade_mode=self.trade_mode,
                                mode_reason=self.mode_reason,
                            )
                            plan = parse_trade_plan(plan)
                            risk = plan.get("risk", {})
                            ai_raw = json.dumps(plan, ensure_ascii=False)
                        except Exception as exc:
                            log.warning(f"get_trade_plan failed: {exc}")
                            risk = {}
                            ai_raw = None

                        try:
                            cond_ind = self._get_cond_indicators()
                            ctx = {
                                "indicators": {
                                    k: (
                                        float(val.iloc[-1])
                                        if hasattr(val, "iloc")
                                        and val.iloc[-1] is not None
                                        else float(val) if val is not None else None
                                    )
                                    for k, val in cond_ind.items()
                                },
                                "indicators_h1": {
                                    k: (
                                        float(v.iloc[-1])
                                        if hasattr(v, "iloc") and v.iloc[-1] is not None
                                        else float(v) if v is not None else None
                                    )
                                    for k, v in (self.indicators_H1 or {}).items()
                                },
                                "indicators_h4": {
                                    k: (
                                        float(v.iloc[-1])
                                        if hasattr(v, "iloc") and v.iloc[-1] is not None
                                        else float(v) if v is not None else None
                                    )
                                    for k, v in (self.indicators_H4 or {}).items()
                                },
                            }
                            market_cond = get_market_condition(ctx, {})
                        except Exception as exc:
                            log.warning(f"get_market_condition failed: {exc}")
                            market_cond = None

                        params = {
                            "instrument": instrument,
                            "side": local_info.get("side"),
                            "tp_pips": risk.get("tp_pips"),
                            "sl_pips": risk.get("sl_pips"),
                            "mode": "market",
                            "limit_price": None,
                            "market_cond": market_cond,
                            "ai_response": ai_raw,
                        }
                        sl_val = params.get("sl_pips") or float(
                            env_loader.get_env("INIT_SL_PIPS", "20")
                        )
                        risk_pct = float(env_loader.get_env("ENTRY_RISK_PCT", "0.01"))
                        pip_val = float(env_loader.get_env("PIP_VALUE_JPY", "100"))
                        lot = calc_lot_size(
                            self.account_balance,
                            risk_pct,
                            float(sl_val),
                            pip_val,
                            risk_engine=self.risk_mgr,
                        )
                        result = order_mgr.enter_trade(
                            side=local_info.get("side"),
                            lot_size=lot if lot > 0 else 0.0,
                            market_data=tick_data,
                            strategy_params=params,
                        )
                    except Exception as exc:
                        log.warning(f"Failed to convert to market order: {exc}")
                    else:
                        if result:
                            _pending_limits.pop(local_info["key"], None)
                    return

        age = time.time() - pend["ts"]
        if age < self.max_limit_age_sec:
            return

        try:
            log.info(f"Stale LIMIT order {pend['order_id']} ({age:.0f}s) → cancelling")
            order_mgr.cancel_order(pend["order_id"])
        except Exception as exc:
            log.warning(f"Failed to cancel LIMIT order: {exc}")
            return

        retry_count = 0
        for key, rec in list(_pending_limits.items()):
            if rec.get("order_id") == pend["order_id"]:
                retry_count = rec.get("retry_count", 0)
                _pending_limits.pop(key, None)

        if retry_count >= MAX_LIMIT_RETRY:
            log.info("LIMIT retry count exceeded – not placing new order.")
            return

        # consult AI for potential renewal
        try:
            candles_dict = {"M5": candles}
            indicators_multi = {"M5": indicators}
            plan = get_trade_plan(
                tick_data,
                indicators_multi or {},
                candles_dict or {},
                patterns=PATTERN_NAMES,
                detected_patterns=self.patterns_by_tf,
                trade_mode=self.trade_mode,
                mode_reason=self.mode_reason,
            )
            plan = parse_trade_plan(plan)
        except Exception as exc:
            log.warning(f"get_trade_plan failed: {exc}")
            return

        entry = plan.get("entry", {})
        risk = plan.get("risk", {})
        side = entry.get("side", "no").lower()
        if side not in ("long", "short") or entry.get("mode") != "limit":
            log.info("AI does not propose renewing the LIMIT order.")
            return

        limit_price = entry.get("limit_price")
        if limit_price is None:
            log.info("AI proposed LIMIT without price – skipping renewal.")
            return

        entry_uuid = str(uuid.uuid4())[:8]
        params = {
            "instrument": instrument,
            "side": side,
            "tp_pips": risk.get("tp_pips"),
            "sl_pips": risk.get("sl_pips"),
            "mode": "limit",
            "limit_price": limit_price,
            "entry_uuid": entry_uuid,
            "valid_for_sec": int(entry.get("valid_for_sec", self.max_limit_age_sec)),
            "risk": risk,
        }
        sl_val = params.get("sl_pips") or float(
            env_loader.get_env("INIT_SL_PIPS", "20")
        )
        risk_pct = float(env_loader.get_env("ENTRY_RISK_PCT", "0.01"))
        pip_val = float(env_loader.get_env("PIP_VALUE_JPY", "100"))
        lot = calc_lot_size(
            self.account_balance,
            risk_pct,
            float(sl_val),
            pip_val,
            risk_engine=self.risk_mgr,
        )
        result = order_mgr.enter_trade(
            side=side,
            lot_size=lot if lot > 0 else 0.0,
            market_data=tick_data,
            strategy_params=params,
        )
        if result:
            _pending_limits[entry_uuid] = {
                "instrument": instrument,
                "order_id": result.get("order_id"),
                "ts": int(datetime.now(timezone.utc).timestamp()),
                "limit_price": limit_price,
                "side": side,
                "retry_count": retry_count + 1,
            }
            log.info(f"Renewed LIMIT order {result.get('order_id')}")

    def _maybe_extend_tp(
        self, position: dict, indicators: dict, side: str, pip_size: float
    ):
        if self.tp_extended or not TP_EXTENSION_ENABLED:
            return
        adx_series = indicators.get("adx")
        atr_series = indicators.get("atr")
        if adx_series is None or atr_series is None:
            return
        adx_val = adx_series.iloc[-1] if hasattr(adx_series, "iloc") else adx_series[-1]
        if adx_val < TP_EXTENSION_ADX_MIN:
            return
        atr_val = atr_series.iloc[-1] if hasattr(atr_series, "iloc") else atr_series[-1]
        ext_pips = (atr_val / pip_size) * TP_EXTENSION_ATR_MULT
        try:
            entry_price = float(position[side].get("averagePrice", 0.0))
            trade_id = position[side]["tradeIDs"][0]
            er_raw = position.get("entry_regime")
            entry_uuid = None
            if er_raw:
                try:
                    entry_uuid = json.loads(er_raw).get("entry_uuid")
                except Exception:
                    entry_uuid = None
        except Exception:
            return
        new_tp = (
            entry_price + ext_pips * pip_size
            if side == "long"
            else entry_price - ext_pips * pip_size
        )
        current_tp = None
        if hasattr(order_mgr, "get_current_tp"):
            current_tp = order_mgr.get_current_tp(trade_id)
        if current_tp is not None and abs(current_tp - new_tp) < pip_size * 0.1:
            return
        try:
            res = order_mgr.adjust_tp_sl(
                DEFAULT_PAIR,
                trade_id,
                new_tp=new_tp,
                entry_uuid=entry_uuid,
            )
            if res is not None:
                log.info(
                    f"TP extended from {current_tp} to {new_tp} ({ext_pips:.1f}pips) due to strong trend"
                )
                self.tp_extended = True
        except Exception as exc:
            log.warning(f"TP extension failed: {exc}")

    def _maybe_reduce_tp(
        self, position: dict, indicators: dict, side: str, pip_size: float
    ):
        if self.tp_reduced or not TP_REDUCTION_ENABLED:
            return
        adx_series = indicators.get("adx")
        atr_series = indicators.get("atr")
        if adx_series is None or atr_series is None:
            return
        adx_val = adx_series.iloc[-1] if hasattr(adx_series, "iloc") else adx_series[-1]
        if adx_val > TP_REDUCTION_ADX_MAX:
            return
        entry_ts = position.get("entry_time") or position.get("openTime")
        if entry_ts:
            try:
                et = datetime.fromisoformat(entry_ts.replace("Z", "+00:00"))
                held_sec = (datetime.now(timezone.utc) - et).total_seconds()
                if held_sec < TP_REDUCTION_MIN_SEC:
                    return
            except Exception:
                pass
        atr_val = atr_series.iloc[-1] if hasattr(atr_series, "iloc") else atr_series[-1]
        red_pips = (atr_val / pip_size) * TP_REDUCTION_ATR_MULT
        try:
            entry_price = float(position[side].get("averagePrice", 0.0))
            trade_id = position[side]["tradeIDs"][0]
            er_raw = position.get("entry_regime")
            entry_uuid = None
            if er_raw:
                try:
                    entry_uuid = json.loads(er_raw).get("entry_uuid")
                except Exception:
                    entry_uuid = None
        except Exception:
            return
        new_tp = (
            entry_price + red_pips * pip_size
            if side == "long"
            else entry_price - red_pips * pip_size
        )
        current_tp = None
        if hasattr(order_mgr, "get_current_tp"):
            current_tp = order_mgr.get_current_tp(trade_id)
        if current_tp is not None and abs(current_tp - new_tp) < pip_size * 0.1:
            return
        try:
            res = order_mgr.adjust_tp_sl(
                DEFAULT_PAIR,
                trade_id,
                new_tp=new_tp,
                entry_uuid=entry_uuid,
            )
            if res is not None:
                log.info(
                    f"TP reduced from {current_tp} to {new_tp} ({red_pips:.1f}pips) due to weak trend"
                )
                self.tp_reduced = True
        except Exception as exc:
            log.warning(f"TP reduction failed: {exc}")

    def _maybe_exit_adjustment(
        self,
        position: dict,
        indicators: dict,
        side: str,
        pip_size: float,
        tick_data: dict,
        profit_pips: float,
        entry_price: float,
    ) -> None:
        trade_id = position[side]["tradeIDs"][0]
        if count_exit_adjust_calls(trade_id) >= MAX_AI_EXIT_CALLS:
            return
        ctx = build_exit_context(position, tick_data, indicators, indicators_m1=self.indicators_M1)
        ctx["profit_pips"] = profit_pips
        ctx["trade_id"] = trade_id
        result = propose_exit_adjustment(ctx)
        log_exit_adjust(trade_id, result.get("action"), result.get("tp"), result.get("sl"))
        entry_uuid = None
        er_raw = position.get("entry_regime")
        if er_raw:
            try:
                entry_uuid = json.loads(er_raw).get("entry_uuid")
            except Exception:
                entry_uuid = None
        if result.get("action") == "MOVE_BE":
            order_mgr.update_trade_sl(trade_id, DEFAULT_PAIR, entry_price)
            self.breakeven_reached = True
        if result.get("action") == "REDUCE_TP" and result.get("tp") is not None:
            order_mgr.adjust_tp_sl(
                DEFAULT_PAIR,
                trade_id,
                new_tp=float(result["tp"]),
                entry_uuid=entry_uuid,
            )
        if result.get("action") == "SHRINK_SL" and result.get("sl") is not None:
            order_mgr.update_trade_sl(trade_id, DEFAULT_PAIR, float(result["sl"]))

    # ────────────────────────────────────────────────────────────
    #  Trailing-stop settings update based on calendar/quiet hours
    # ────────────────────────────────────────────────────────────
    def get_calendar_volatility_level(self) -> int:
        try:
            return int(env_loader.get_env("CALENDAR_VOLATILITY_LEVEL", "0"))
        except (TypeError, ValueError):
            return 0

    def _refresh_trailing_status(self) -> None:
        """Update trailing-stop enable flag based on time or event level."""
        from backend.strategy import exit_logic

        quiet_start = float(env_loader.get_env("QUIET_START_HOUR_JST", "3"))
        quiet_end = float(env_loader.get_env("QUIET_END_HOUR_JST", "7"))
        quiet2_enabled = env_loader.get_env("QUIET2_ENABLED", "false").lower() == "true"
        if quiet2_enabled:
            quiet2_start = float(env_loader.get_env("QUIET2_START_HOUR_JST", "23"))
            quiet2_end = float(env_loader.get_env("QUIET2_END_HOUR_JST", "1"))
        else:
            quiet2_start = quiet2_end = None

        now_jst = datetime.now(timezone.utc) + timedelta(hours=9)
        current_time = now_jst.hour + now_jst.minute / 60.0

        def _in_range(start: float | None, end: float | None) -> bool:
            if start is None or end is None:
                return False
            return (
                (start < end and start <= current_time < end)
                or (start > end and (current_time >= start or current_time < end))
                or (start == end)
            )

        in_quiet_hours = _in_range(quiet_start, quiet_end) or _in_range(
            quiet2_start, quiet2_end
        )

        if in_quiet_hours or self.get_calendar_volatility_level() >= 3:
            exit_logic.TRAIL_ENABLED = False
        else:
            exit_logic.TRAIL_ENABLED = (
                env_loader.get_env("TRAIL_ENABLED", "true").lower() == "true"
            )

    def refresh_ai_cooldowns(self) -> None:
        """Reload AI cooldown values from environment variables."""
        self.ai_cooldown_open = int(
            env_loader.get_env("AI_COOLDOWN_SEC_OPEN", str(self.ai_cooldown_open))
        )
        self.ai_cooldown_flat = int(
            env_loader.get_env("AI_COOLDOWN_SEC_FLAT", str(self.ai_cooldown_flat))
        )

    def _should_peak_exit(
        self, side: str, indicators: dict, current_profit: float
    ) -> bool:
        if not PEAK_EXIT_ENABLED:
            return False
        atr_val = indicators.get("atr")
        if hasattr(atr_val, "iloc"):
            atr_val = float(atr_val.iloc[-1])
        if atr_val is None:
            return False
        pip_size = 0.01 if DEFAULT_PAIR.endswith("_JPY") else 0.0001
        allowed_draw = (atr_val / pip_size) * MM_DRAW_MAX_ATR_RATIO
        if (self.max_profit_pips - current_profit) < allowed_draw:
            return False

        from backend.strategy.signal_filter import detect_peak_reversal

        if detect_peak_reversal(self.last_candles_m5 or [], side):
            return True

        ema_fast = indicators.get("ema_fast")
        ema_slow = indicators.get("ema_slow")
        if ema_fast is None or ema_slow is None:
            return False
        if hasattr(ema_fast, "iloc"):
            if len(ema_fast) < 2 or len(ema_slow) < 2:
                return False
            prev_fast = float(ema_fast.iloc[-2])
            latest_fast = float(ema_fast.iloc[-1])
            prev_slow = float(ema_slow.iloc[-2])
            latest_slow = float(ema_slow.iloc[-1])
        else:
            if len(ema_fast) < 2 or len(ema_slow) < 2:
                return False
            prev_fast = float(ema_fast[-2])
            latest_fast = float(ema_fast[-1])
            prev_slow = float(ema_slow[-2])
            latest_slow = float(ema_slow[-1])
        cross_down = prev_fast >= prev_slow and latest_fast < latest_slow
        cross_up = prev_fast <= prev_slow and latest_fast > latest_slow
        return (side == "long" and cross_down) or (side == "short" and cross_up)

    def run(self, *, max_loops: int | None = None) -> None:
        """Run the job loop until ``stop`` is called or ``max_loops`` reached."""
        log.info("Job Runner started.")
        loops = 0
        while not self._stop:
            try:
                reset_call_counter()
                maybe_cleanup()
                timer = PerfTimer("job_loop")
                now = datetime.now(timezone.utc)
                # ---- Market‑hours guard ---------------------------------
                if not instrument_is_tradeable(DEFAULT_PAIR):
                    log.info(f"{DEFAULT_PAIR} market closed – sleeping 60 s")
                    time.sleep(60)
                    self.last_run = datetime.now(timezone.utc)
                    timer.stop()
                    continue
                self._update_portfolio_risk()
                # Refresh POSITION_REVIEW_SEC dynamically each loop
                self.review_sec = int(
                    env_loader.get_env("POSITION_REVIEW_SEC", str(self.review_sec))
                )
                log.debug(f"review_sec={self.review_sec}")
                # Refresh HIGHER_TF_ENABLED dynamically
                self.higher_tf_enabled = (
                    env_loader.get_env("HIGHER_TF_ENABLED", "true").lower() == "true"
                )
                # Refresh AI cooldown values
                self.refresh_ai_cooldowns()
                # Update trailing-stop enable flag each loop
                self._refresh_trailing_status()
                if self.last_run is None or (now - self.last_run) >= timedelta(
                    seconds=self.interval_seconds
                ):
                    log.info(f"Running job at {now.isoformat()}")

                    # ティックデータ取得（発注用）
                    tick_data = fetch_tick_data(DEFAULT_PAIR, include_liquidity=True)
                    # ティックデータ詳細はDEBUGレベルで出力
                    log.debug(f"Tick data fetched: {tick_data}")
                    try:
                        price = float(tick_data["prices"][0]["bids"][0]["price"])
                        bid_liq = float(
                            tick_data["prices"][0]["bids"][0].get("liquidity", 0)
                        )
                        ask_liq = float(
                            tick_data["prices"][0]["asks"][0].get("liquidity", 0)
                        )
                        tick = {
                            "high": price,
                            "low": price,
                            "close": price,
                            "volume": bid_liq + ask_liq,
                        }
                        if self.cluster_regime:
                            cr_res = self.cluster_regime.update(tick)
                            if cr_res.get("transition"):
                                self.last_ai_call = datetime.min
                    except Exception as exc:
                        log.debug(f"RegimeDetector update failed: {exc}")

                    # ---- Market closed guard (price feed says non‑tradeable) ----
                    try:
                        if (
                            not tick_data["prices"][0].get("tradeable", True)
                        ) or tick_data["prices"][0].get("status") == "non-tradeable":
                            log.info(
                                f"{DEFAULT_PAIR} price feed marked non‑tradeable – sleeping 120 s"
                            )
                            time.sleep(120)
                            self.last_run = datetime.now(timezone.utc)
                            timer.stop()
                            continue
                    except (IndexError, KeyError, TypeError):
                        # if structure unexpected, fall back to old check
                        pass

                    # ローソク足データ取得は一度だけ行い、後続処理で再利用する
                    candles_dict = fetch_multiple_timeframes(DEFAULT_PAIR)

                    # ---- Chart pattern detection per timeframe ----
                    self.patterns_by_tf = pattern_scanner.scan(
                        candles_dict, PATTERN_NAMES
                    )

                    candles_s10 = candles_dict.get("S10", [])
                    candles_m1 = candles_dict.get("M1", [])
                    candles_m5 = candles_dict.get("M5", [])
                    candles_h1 = candles_dict.get("H1", [])
                    candles_h4 = candles_dict.get("H4", [])
                    candles_d1 = candles_dict.get("D", [])
                    self.last_candles_m5 = candles_m5
                    candles = candles_m5  # backward compatibility
                    log.info(
                        f"Candle M5 last: {candles_m5[-1] if candles_m5 else 'No candles'}"
                    )

                    # -------- Higher‑timeframe reference levels --------
                    higher_tf = {}
                    if self.higher_tf_enabled:
                        higher_tf = analyze_higher_tf(DEFAULT_PAIR)
                        log.debug(f"Higher‑TF levels: {higher_tf}")

                    # 指標計算
                    indicators_multi = calculate_indicators_multi(
                        candles_dict,
                        allow_incomplete=True,
                    )
                    self.indicators_S10 = indicators_multi.get("S10")
                    self.indicators_M1 = indicators_multi.get("M1")
                    self.indicators_M5 = indicators_multi.get("M5")
                    self.indicators_M15 = indicators_multi.get("M15")
                    self.indicators_H1 = indicators_multi.get("H1")
                    self.indicators_H4 = indicators_multi.get("H4")
                    self.indicators_D = indicators_multi.get("D")
                    indicators = dict(self.indicators_M5 or {})
                    if self.indicators_H1:
                        indicators["ema_slope_h1"] = self.indicators_H1.get("ema_slope")
                        indicators["adx_h1"] = self.indicators_H1.get("adx")
                    if self.indicators_H4:
                        indicators["ema_slope_h4"] = self.indicators_H4.get("ema_slope")
                        indicators["adx_h4"] = self.indicators_H4.get("adx")

                    if self.indicators_M1:
                        indicators["M1"] = self.indicators_M1
                    if self.indicators_S10:
                        indicators["S10"] = self.indicators_S10

                    pip_size = float(env_loader.get_env("PIP_SIZE", "0.01"))
                    ask = float(tick_data["prices"][0]["asks"][0]["price"])
                    bid = float(tick_data["prices"][0]["bids"][0]["price"])
                    spread_pips = (ask - bid) / pip_size
                    tf = env_loader.get_env("SCALP_COND_TF", self.scalp_cond_tf).upper()
                    src = getattr(self, f"indicators_{tf}", None) or self.indicators_M1
                    try:
                        atr_val = (
                            src.get("atr").iloc[-1]
                            if hasattr(src.get("atr"), "iloc")
                            else src.get("atr", [0])[-1]
                        )
                        atr_pips = float(atr_val) / pip_size
                    except Exception:
                        atr_pips = 0.0
                    try:
                        bw = (
                            self.indicators_M1["bb_upper"].iloc[-1]
                            - self.indicators_M1["bb_lower"].iloc[-1]
                        )
                        price = float(tick_data["prices"][0]["bids"][0]["price"])
                        bb_pct = float(bw) / price * 100
                    except Exception:
                        bb_pct = 0.0

                    tradeable = instrument_is_tradeable(DEFAULT_PAIR)
                    allow_trade, filter_ctx, reason = apply_filters(
                        atr_pips,
                        bb_pct,
                        spread_pips,
                        tradeable=tradeable,
                    )
                    if not allow_trade:
                        log.info(f"Entry blocked by session filter ({reason})")
                        log_entry_skip(DEFAULT_PAIR, None, reason)
                        self.last_ai_call = datetime.min
                        self.last_run = now
                        update_oanda_trades()
                        time.sleep(self.interval_seconds)
                        timer.stop()
                        continue

                    current_price = bid

                    entry_ctx: dict[str, str] = {}
                    if env_loader.get_env("ALWAYS_ENTRY", "false").lower() == "true":
                        filter_pass = True
                    else:
                        filter_pass = pass_entry_filter(
                            indicators,
                            current_price,
                            self.indicators_M1,
                            self.indicators_M15,
                            self.indicators_H1,
                            mode=self.trade_mode,
                            context=entry_ctx,
                        )

                    if not filter_pass:
                        reason = entry_ctx.get("reason", "unknown")
                        log.info(
                            f"Entry blocked by filter ({reason}) → skip any AI calls."
                        )
                        self.last_ai_call = datetime.min
                        self.last_position_review_ts = None
                        self.last_run = now
                        update_oanda_trades()
                        time.sleep(self.interval_seconds)
                        timer.stop()
                        continue

                    skip_align = self.trade_mode in (
                        "scalp",
                        "scalp_momentum",
                        "micro_scalp",
                        "scalp_range",
                    )
                    if skip_align:
                        align = None
                        log.debug("Multi‑TF alignment skipped in scalp mode")
                    else:
                        align = is_multi_tf_aligned(
                            {
                                "M1": self.indicators_M1 or {},
                                "M5": self.indicators_M5 or {},
                                "H1": self.indicators_H1 or {},
                            }
                        )
                        if (
                            align is None
                            and env_loader.get_env(
                                "ALIGN_STRICT",
                                env_loader.get_env("STRICT_TF_ALIGN", "false"),
                            ).lower()
                            == "true"
                        ):
                            log.info("Multi‑TF alignment missing → skip entry")
                            log_entry_skip(DEFAULT_PAIR, None, "tf_align")
                            self.last_run = now
                            update_oanda_trades()
                            time.sleep(self.interval_seconds)
                            timer.stop()
                            continue
                        log.info(f"Multi‑TF alignment: {align}")

                    log.info("Indicators calculation successful.")

                    # 指標からトレードモードを判定
                    new_mode, _score, reasons = decide_trade_mode_detail(
                        indicators, candles_m5
                    )
                    log.debug(
                        "Trade mode reasons:\n%s",
                        "\n".join(reasons),
                    )
                    perf = recent_strategy_performance()
                    self.current_context = build_context(
                        indicators, perf
                    )
                    selected = self.strategy_selector.select(self.current_context)
                    self.current_strategy_name = selected.name
                    selected_mode = (
                        "trend_follow" if selected.name == "trend" else selected.name
                    )
                    if selected_mode != self.trade_mode:
                        self.reload_params_for_mode(selected_mode)
                        self.trade_mode = selected_mode
                    if new_mode != self.trade_mode:
                        info(
                            "regime_change",
                            new=new_mode,
                            old=self.trade_mode,
                            score=_score,
                        )
                        self.reload_params_for_mode(new_mode)
                        self.trade_mode = new_mode
                    self.mode_reason = "\n".join(f"- {r}" for r in reasons)
                    log.info("Current trade mode: %s", self.trade_mode)

                    pend_info = get_pending_entry_order(DEFAULT_PAIR)
                    if pend_info:
                        age = time.time() - pend_info.get("ts", 0)
                        if age < self.pending_grace_sec:
                            log.info(
                                f"Pending LIMIT active ({age:.0f}s) – skip entry check"
                            )
                            log_entry_skip(
                                DEFAULT_PAIR,
                                None,
                                "pending_limit",
                                f"{age:.0f}s < {self.pending_grace_sec}s",
                            )
                            self.last_run = now
                            update_oanda_trades()
                            time.sleep(self.interval_seconds)
                            timer.stop()
                            continue


                    has_position = check_current_position(DEFAULT_PAIR)

                    due_for_review = False
                    elapsed_review = None
                    if has_position and self.review_enabled:
                        if self.last_position_review_ts is None:
                            due_for_review = True
                        else:
                            elapsed_review = (
                                now - self.last_position_review_ts
                            ).total_seconds()
                            due_for_review = elapsed_review >= self.review_sec
                        log.debug(
                            "review check: ts=%s elapsed=%s review_sec=%s due=%s",
                            self.last_position_review_ts,
                            (
                                f"{elapsed_review:.1f}"
                                if elapsed_review is not None
                                else "N/A"
                            ),
                            self.review_sec,
                            due_for_review,
                        )

                    if has_position:
                        self.ai_cooldown = self.ai_cooldown_flat
                    else:
                        self.ai_cooldown = self.ai_cooldown_open

                    elapsed_seconds = (
                        datetime.now() - self.last_ai_call
                    ).total_seconds()
                    mode_cd = get_cooldown(self.trade_mode or "")
                    cooldown = min(self.ai_cooldown, mode_cd)
                    if (not due_for_review) and elapsed_seconds < cooldown:
                        log.info(
                            f"AI cooldown active ({elapsed_seconds:.1f}s < {cooldown}s). Skipping AI call."
                        )
                        self.last_run = now
                        update_oanda_trades()
                        time.sleep(self.interval_seconds)
                        timer.stop()
                        continue
                        
                    # --- manage pending LIMIT orders *after* all entry filters pass
                    self._manage_pending_limits(
                        DEFAULT_PAIR, indicators, candles_m5, tick_data
                    )

                    market_cond = self._evaluate_market_condition(
                        candles_m1,
                        candles_m5,
                        candles_d1,
                        higher_tf,
                    )
                    log.debug(f"Market condition: {market_cond}")
                    regime_hint = (filter_ctx or {}).get("regime_hint")
                    MIN_HOLD_SECONDS = int(env_loader.get_env("MIN_HOLD_SECONDS", "0"))

                    secs_since_entry = (
                        trade_age_seconds(has_position) if has_position else None
                    )

                    if not has_position:
                        self.breakeven_reached = False
                        self.sl_reset_done = False
                        self.tp_extended = False
                        self.tp_reduced = False
                        self.max_profit_pips = 0.0
                        self.scale_count = 0


                    # Determine position_side for further logic
                    if (
                        has_position
                        and int(has_position.get("long", {}).get("units", 0)) != 0
                    ):
                        position_side = "long"
                    elif (
                        has_position
                        and int(has_position.get("short", {}).get("units", 0)) != 0
                    ):
                        position_side = "short"
                    else:
                        position_side = None

                    # Inserted logic for dynamic SL management and AI profit-taking consultation
                    if has_position and position_side:
                        current_price = (
                            float(tick_data["prices"][0]["bids"][0]["price"])
                            if position_side == "long"
                            else float(tick_data["prices"][0]["asks"][0]["price"])
                        )
                        entry_price = float(
                            has_position[position_side].get("averagePrice", 0.0)
                        )

                        pip_size = float(env_loader.get_env("PIP_SIZE", "0.01"))
                        current_profit_pips = (
                            (current_price - entry_price) / pip_size
                            if position_side == "long"
                            else (entry_price - current_price) / pip_size
                        )
                        self.max_profit_pips = max(
                            self.max_profit_pips, current_profit_pips
                        )

                        BE_TRIGGER_PIPS = float(
                            env_loader.get_env("BE_TRIGGER_PIPS", "10")
                        )
                        BE_ATR_TRIGGER_MULT = float(
                            env_loader.get_env("BE_ATR_TRIGGER_MULT", "0")
                        )
                        BE_TRIGGER_R = float(env_loader.get_env("BE_TRIGGER_R", "0"))
                        atr_val = (
                            indicators["atr"].iloc[-1]
                            if hasattr(indicators["atr"], "iloc")
                            else indicators["atr"][-1]
                        )
                        atr_pips = atr_val / pip_size
                        if BE_ATR_TRIGGER_MULT > 0:
                            be_trigger = max(
                                BE_TRIGGER_PIPS, atr_pips * BE_ATR_TRIGGER_MULT
                            )
                        else:
                            be_trigger = BE_TRIGGER_PIPS
                        if BE_TRIGGER_R > 0:
                            sl_pips_val = has_position.get("sl_pips")
                            if sl_pips_val is not None:
                                try:
                                    sl_pips_val = float(sl_pips_val)
                                    be_trigger = max(
                                        be_trigger, sl_pips_val * BE_TRIGGER_R
                                    )
                                except Exception:
                                    pass
                        TP_PIPS = float(env_loader.get_env("INIT_TP_PIPS", "30"))
                        AI_PROFIT_TRIGGER_RATIO = float(
                            env_loader.get_env("AI_PROFIT_TRIGGER_RATIO", "0.3")
                        )

                        log.info(
                            f"profit_pips={current_profit_pips:.1f}, "
                            f"BE_trigger={be_trigger}, "
                            f"AI_trigger={TP_PIPS * AI_PROFIT_TRIGGER_RATIO}"
                        )

                        if (
                            current_profit_pips >= be_trigger
                            and not self.breakeven_reached
                        ):
                            adx_series = indicators.get("adx")
                            adx_val = (
                                adx_series.iloc[-1]
                                if adx_series is not None
                                and hasattr(adx_series, "iloc")
                                else adx_series[-1] if adx_series else 0.0
                            )
                            vol_adx_min = float(
                                env_loader.get_env("BE_VOL_ADX_MIN", "30")
                            )
                            vol_sl_mult = float(
                                env_loader.get_env("BE_VOL_SL_MULT", "2.0")
                            )
                            if adx_val >= vol_adx_min:
                                if position_side == "long":
                                    new_sl_price = entry_price - atr_val * vol_sl_mult
                                else:
                                    new_sl_price = entry_price + atr_val * vol_sl_mult
                            else:
                                new_sl_price = entry_price
                            trade_id = has_position[position_side]["tradeIDs"][0]
                            result = order_mgr.update_trade_sl(
                                trade_id, DEFAULT_PAIR, new_sl_price
                            )
                            if result is not None:
                                log.info(
                                    f"SL updated to entry price to secure minimum profit: {new_sl_price}"
                                )
                                self.breakeven_reached = True
                                self.sl_reset_done = False
                                # SLが実行された向きと時間を記録
                                self.last_sl_side = position_side
                                self.last_sl_time = datetime.now(timezone.utc)

                        if self.breakeven_reached and not self.sl_reset_done:
                            trade_id = has_position[position_side]["tradeIDs"][0]
                            sl_missing = True
                            try:
                                trade_info = fetch_trade_details(trade_id) or {}
                                trade = trade_info.get("trade", {})
                                sl_price = float(
                                    trade.get("stopLossOrder", {}).get("price", 0)
                                )
                                sl_missing = sl_price == 0
                            except Exception as exc:
                                log.warning(f"Failed to fetch trade details: {exc}")
                            if sl_missing:
                                atr_val = (
                                    indicators["atr"].iloc[-1]
                                    if hasattr(indicators["atr"], "iloc")
                                    else indicators["atr"][-1]
                                )
                                if position_side == "long":
                                    new_sl_price = entry_price - atr_val * 2
                                else:
                                    new_sl_price = entry_price + atr_val * 2
                                result = order_mgr.update_trade_sl(
                                    trade_id, DEFAULT_PAIR, new_sl_price
                                )
                                if result is not None:
                                    log.info(f"SL reapplied at {new_sl_price}")
                                    self.sl_reset_done = True
                                    # SLが実行された向きと時間を記録
                                    self.last_sl_side = position_side
                                    self.last_sl_time = datetime.now(timezone.utc)

                        self._maybe_extend_tp(
                            has_position, indicators, position_side, pip_size
                        )
                        self._maybe_reduce_tp(
                            has_position, indicators, position_side, pip_size
                        )

                        if self._should_peak_exit(
                            position_side, indicators, current_profit_pips
                        ):
                            log.info("Peak exit triggered → closing position.")
                            try:
                                order_mgr.close_position(
                                    DEFAULT_PAIR, side=position_side
                                )
                                exit_time = datetime.now(timezone.utc).isoformat()
                                log_trade(
                                    instrument=DEFAULT_PAIR,
                                    entry_time=has_position.get(
                                        "entry_time",
                                        has_position.get("openTime", exit_time),
                                    ),
                                    entry_price=entry_price,
                                    units=(
                                        int(has_position[position_side]["units"])
                                        if position_side == "long"
                                        else -int(has_position[position_side]["units"])
                                    ),
                                    exit_time=exit_time,
                                    exit_price=current_price,
                                    profit_loss=float(
                                        has_position.get(
                                            "pl_corrected", has_position.get("pl", 0)
                                        )
                                    ),
                                    ai_reason="peak exit",
                                    exit_reason=ExitReason.RISK,
                                    is_manual=False,
                                )
                                pl = float(
                                    has_position.get(
                                        "pl_corrected", has_position.get("pl", 0)
                                    )
                                )
                                self.safety.record_loss(pl)
                                metrics_publisher.publish(
                                    "trade_pl",
                                    pl,
                                    {"reason": "peak"},
                                )
                                self.last_close_ts = datetime.now(timezone.utc)
                                send_line_message(
                                    f"【PEAK EXIT】{DEFAULT_PAIR} {current_price} で決済しました。PL={current_profit_pips:.1f}pips"
                                )
                                self._record_strategy_result(current_profit_pips)
                            except Exception as exc:
                                log.warning(f"Peak exit failed: {exc}")
                            self.max_profit_pips = 0.0
                            self.breakeven_reached = False
                            self.sl_reset_done = False
                            update_oanda_trades()
                            time.sleep(self.interval_seconds)
                            timer.stop()
                            continue

                        if current_profit_pips >= TP_PIPS * AI_PROFIT_TRIGGER_RATIO:
                            if (
                                secs_since_entry is not None
                                and secs_since_entry < MIN_HOLD_SECONDS
                            ):
                                log.info(
                                    f"Hold time {secs_since_entry:.1f}s < {MIN_HOLD_SECONDS}s → skip exit call"
                                )
                            else:
                                # EXITフィルターを評価し、フィルターNGの場合はAIの決済判断をスキップ
                                self._maybe_exit_adjustment(
                                    has_position,
                                    indicators,
                                    position_side,
                                    pip_size,
                                    tick_data,
                                    current_profit_pips,
                                    entry_price,
                                )
                                if pass_exit_filter(indicators, position_side):
                                    log.info(
                                        "Filter OK → Processing exit decision with AI."
                                    )
                                    self.last_ai_call = datetime.now()
                                    log.debug(f"Market condition (exit): {market_cond}")
                                    exit_ctx = build_exit_context(
                                        has_position,
                                        tick_data,
                                        indicators,
                                        indicators_m1=self.indicators_M1,
                                    )
                                    try:
                                        ai_dec = evaluate_exit_ai(exit_ctx)
                                    except Exception as exc:
                                        log.warning(f"exit AI evaluation failed: {exc}")
                                        ai_dec = None
                                    if ai_dec and ai_dec.action == "SCALE":
                                        pip_size = float(
                                            env_loader.get_env("PIP_SIZE", "0.01")
                                        )
                                        entry_price = float(
                                            has_position[position_side].get(
                                                "averagePrice", 0.0
                                            )
                                        )
                                        cur_price = (
                                            float(
                                                tick_data["prices"][0]["bids"][0][
                                                    "price"
                                                ]
                                            )
                                            if position_side == "long"
                                            else float(
                                                tick_data["prices"][0]["asks"][0][
                                                    "price"
                                                ]
                                            )
                                        )
                                        diff_pips = (
                                            (cur_price - entry_price) / pip_size
                                            if position_side == "long"
                                            else (entry_price - cur_price) / pip_size
                                        )
                                        atr_val = (
                                            indicators["atr"].iloc[-1]
                                            if hasattr(indicators.get("atr"), "iloc")
                                            else indicators.get("atr", [0])[-1]
                                        )
                                        allow_scale = True
                                        if (
                                            SCALE_MAX_POS > 0
                                            and self.scale_count >= SCALE_MAX_POS
                                        ):
                                            log.info(
                                                "Scale limit reached → ignoring SCALE signal"
                                            )
                                            allow_scale = False
                                        if (
                                            allow_scale
                                            and SCALE_TRIGGER_ATR > 0
                                            and diff_pips
                                            < (atr_val / pip_size) * SCALE_TRIGGER_ATR
                                        ):
                                            log.info(
                                                f"Scale trigger {diff_pips:.1f} < {(atr_val / pip_size) * SCALE_TRIGGER_ATR:.1f} pips"
                                            )
                                            allow_scale = False
                                        if allow_scale:
                                            try:
                                                risk_pct = float(
                                                    env_loader.get_env(
                                                        "ENTRY_RISK_PCT", "0.01"
                                                    )
                                                )
                                                pip_val = float(
                                                    env_loader.get_env(
                                                        "PIP_VALUE_JPY", "100"
                                                    )
                                                )
                                                base_lot = calc_lot_size(
                                                    self.account_balance,
                                                    risk_pct,
                                                    float(
                                                        env_loader.get_env(
                                                            "INIT_SL_PIPS", "20"
                                                        )
                                                    ),
                                                    pip_val,
                                                    risk_engine=self.risk_mgr,
                                                )
                                                lot_sz = min(SCALE_LOT_SIZE, base_lot)
                                                order_mgr.enter_trade(
                                                    side=position_side,
                                                    lot_size=lot_sz,
                                                    market_data=tick_data,
                                                    strategy_params={
                                                        "instrument": DEFAULT_PAIR,
                                                        "mode": "market",
                                                    },
                                                )
                                                log.info(
                                                    f"Scaled into position ({position_side}) by {SCALE_LOT_SIZE} lots"
                                                )
                                                self.scale_count += 1
                                                has_position = check_current_position(
                                                    DEFAULT_PAIR
                                                )
                                            except Exception as exc:
                                                log.warning(
                                                    f"Failed to scale position: {exc}"
                                                )
                                            exit_executed = False
                                        else:
                                            exit_executed = process_exit(
                                                indicators,
                                                tick_data,
                                                market_cond,
                                                higher_tf,
                                                indicators_m1=self.indicators_M1,
                                                patterns=PATTERN_NAMES,
                                                pattern_names=self.patterns_by_tf,
                                            )
                                    else:
                                        exit_executed = process_exit(
                                            indicators,
                                            tick_data,
                                            market_cond,
                                            higher_tf,
                                            indicators_m1=self.indicators_M1,
                                            patterns=PATTERN_NAMES,
                                            pattern_names=self.patterns_by_tf,
                                        )
                                    if exit_executed:
                                        self.last_close_ts = datetime.now(timezone.utc)
                                        log.info(
                                            "Position closed based on AI recommendation."
                                        )
                                        send_line_message(
                                            f"【EXIT】{DEFAULT_PAIR} {current_price} で決済しました。PL={current_profit_pips:.1f}pips"
                                        )
                                        self._record_strategy_result(
                                            current_profit_pips
                                        )
                                        self.scale_count = 0
                                        info(
                                            "exit",
                                            pair=DEFAULT_PAIR,
                                            reason="AI",
                                            price=current_price,
                                            pnl=current_profit_pips,
                                        )
                                    else:
                                        log.info(
                                            "AI decision was HOLD → No exit executed."
                                        )
                                else:
                                    log.info("Filter blocked → AI exit decision skipped.")

                    # ---- Position‑review timing -----------------------------

                    # Periodic exit review
                    if has_position and due_for_review:
                        self.last_position_review_ts = now
                        log.debug(
                            "last_position_review_ts updated to %s",
                            self.last_position_review_ts,
                        )
                        if position_side:
                            cur_price = (
                                float(tick_data["prices"][0]["bids"][0]["price"])
                                if position_side == "long"
                                else float(tick_data["prices"][0]["asks"][0]["price"])
                            )
                            entry_price = float(
                                has_position[position_side].get("averagePrice", 0.0)
                            )
                            pip_size = float(env_loader.get_env("PIP_SIZE", "0.01"))
                            profit_pips = (
                                (cur_price - entry_price) / pip_size
                                if position_side == "long"
                                else (entry_price - cur_price) / pip_size
                            )
                        else:
                            cur_price = float(
                                tick_data["prices"][0]["bids"][0]["price"]
                            )
                            pip_size = float(env_loader.get_env("PIP_SIZE", "0.01"))
                            profit_pips = 0.0

                        if (
                            secs_since_entry is not None
                            and secs_since_entry < MIN_HOLD_SECONDS
                        ):
                            log.info(
                                f"Hold time {secs_since_entry:.1f}s < {MIN_HOLD_SECONDS}s → skip exit call"
                            )
                            pass_exit = False
                        else:
                            pass_exit = pass_exit_filter(indicators, position_side)

                        if pass_exit:
                            log.info(
                                "Filter OK → Processing periodic exit decision with AI."
                            )
                            self.last_ai_call = datetime.now()
                            log.debug(f"Market condition (review): {market_cond}")
                            exit_ctx = build_exit_context(
                                has_position,
                                tick_data,
                                indicators,
                                indicators_m1=self.indicators_M1,
                            )
                            try:
                                ai_dec = evaluate_exit_ai(exit_ctx)
                            except Exception as exc:
                                log.warning(f"exit AI evaluation failed: {exc}")
                                ai_dec = None
                            if ai_dec and ai_dec.action == "SCALE":
                                pip_size = float(env_loader.get_env("PIP_SIZE", "0.01"))
                                entry_price = float(
                                    has_position[position_side].get("averagePrice", 0.0)
                                )
                                cur_price = (
                                    float(tick_data["prices"][0]["bids"][0]["price"])
                                    if position_side == "long"
                                    else float(
                                        tick_data["prices"][0]["asks"][0]["price"]
                                    )
                                )
                                diff_pips = (
                                    (cur_price - entry_price) / pip_size
                                    if position_side == "long"
                                    else (entry_price - cur_price) / pip_size
                                )
                                atr_val = (
                                    indicators["atr"].iloc[-1]
                                    if hasattr(indicators.get("atr"), "iloc")
                                    else indicators.get("atr", [0])[-1]
                                )
                                allow_scale = True
                                if (
                                    SCALE_MAX_POS > 0
                                    and self.scale_count >= SCALE_MAX_POS
                                ):
                                    log.info(
                                        "Scale limit reached → ignoring SCALE signal"
                                    )
                                    allow_scale = False
                                if (
                                    allow_scale
                                    and SCALE_TRIGGER_ATR > 0
                                    and diff_pips
                                    < (atr_val / pip_size) * SCALE_TRIGGER_ATR
                                ):
                                    log.info(
                                        f"Scale trigger {diff_pips:.1f} < {(atr_val / pip_size) * SCALE_TRIGGER_ATR:.1f} pips"
                                    )
                                    allow_scale = False
                                if allow_scale:
                                    try:
                                        risk_pct = float(
                                            env_loader.get_env("ENTRY_RISK_PCT", "0.01")
                                        )
                                        pip_val = float(
                                            env_loader.get_env("PIP_VALUE_JPY", "100")
                                        )
                                        base_lot = calc_lot_size(
                                            self.account_balance,
                                            risk_pct,
                                            float(
                                                env_loader.get_env("INIT_SL_PIPS", "20")
                                            ),
                                            pip_val,
                                            risk_engine=self.risk_mgr,
                                        )
                                        lot_sz = min(SCALE_LOT_SIZE, base_lot)
                                        order_mgr.enter_trade(
                                            side=position_side,
                                            lot_size=lot_sz,
                                            market_data=tick_data,
                                            strategy_params={
                                                "instrument": DEFAULT_PAIR,
                                                "mode": "market",
                                            },
                                        )
                                        log.info(
                                            f"Scaled into position ({position_side}) by {SCALE_LOT_SIZE} lots"
                                        )
                                        self.scale_count += 1
                                        has_position = check_current_position(
                                            DEFAULT_PAIR
                                        )
                                    except Exception as exc:
                                        log.warning(f"Failed to scale position: {exc}")
                                    exit_executed = False
                                else:
                                    exit_executed = process_exit(
                                        indicators,
                                        tick_data,
                                        market_cond,
                                        higher_tf,
                                        indicators_m1=self.indicators_M1,
                                        patterns=PATTERN_NAMES,
                                        pattern_names=self.patterns_by_tf,
                                    )
                            else:
                                exit_executed = process_exit(
                                    indicators,
                                    tick_data,
                                    market_cond,
                                    higher_tf,
                                    indicators_m1=self.indicators_M1,
                                    patterns=PATTERN_NAMES,
                                    pattern_names=self.patterns_by_tf,
                                )
                            if exit_executed:
                                self.last_close_ts = datetime.now(timezone.utc)
                                log.info("Position closed based on AI recommendation.")
                                send_line_message(
                                    f"【EXIT】{DEFAULT_PAIR} {cur_price} で決済しました。PL={profit_pips * pip_size:.2f}"
                                )
                                self._record_strategy_result(profit_pips)
                                self.scale_count = 0
                                info(
                                    "exit",
                                    pair=DEFAULT_PAIR,
                                    reason="AI",
                                    price=cur_price,
                                    pnl=profit_pips * pip_size,
                                )
                            else:
                                log.info("AI decision was HOLD → No exit executed.")
                        else:
                            log.info("Filter blocked → AI exit decision skipped.")

                    # AIによるエントリー/エグジット判断
                    if not has_position:
                        self.tp_extended = False
                        self.tp_reduced = False
                        self.max_profit_pips = 0.0
                        entry_params: dict[str, Any] = {}
                        # 1) Entry cooldown check
                        if (
                            self.last_close_ts
                            and (
                                datetime.now(timezone.utc) - self.last_close_ts
                            ).total_seconds()
                            < self.entry_cooldown_sec
                        ):
                            log.info(
                                f"Entry cooldown active ({(datetime.now(timezone.utc) - self.last_close_ts).total_seconds():.1f}s < {self.entry_cooldown_sec}s). Skipping entry."
                            )
                            self.last_run = now
                            update_oanda_trades()
                            time.sleep(self.interval_seconds)
                            timer.stop()
                            continue
                        # ── Entry side ───────────────────────────────
                        current_price = float(
                            tick_data["prices"][0]["bids"][0]["price"]
                        )
                        self.last_ai_call = datetime.now()  # record AI call time *before* the call

                        climax_side = detect_climax_reversal(candles_m5, indicators)
                        if climax_side and not has_position:
                            log.info(
                                f"Climax reversal detected → {climax_side} entry"
                            )
                            params = {
                                "instrument": DEFAULT_PAIR,
                                "side": climax_side,
                                "tp_pips": float(
                                    env_loader.get_env("CLIMAX_TP_PIPS", "7")
                                ),
                                "sl_pips": float(
                                    env_loader.get_env("CLIMAX_SL_PIPS", "10")
                                ),
                                "mode": "market",
                                "market_cond": market_cond,
                            }
                            risk_pct = float(
                                env_loader.get_env("ENTRY_RISK_PCT", "0.01")
                            )
                            pip_val = float(
                                env_loader.get_env("PIP_VALUE_JPY", "100")
                            )
                            lot = calc_lot_size(
                                self.account_balance,
                                risk_pct,
                                float(params["sl_pips"]),
                                pip_val,
                                risk_engine=self.risk_mgr,
                            )
                            order_mgr.enter_trade(
                                side=climax_side,
                                lot_size=lot if lot > 0 else 0.0,
                                market_data=tick_data,
                                strategy_params=params,
                            )
                            self.last_run = now
                            update_oanda_trades()
                            time.sleep(self.interval_seconds)
                            timer.stop()
                            continue

                            # AI を呼び出す前のフィルター処理は廃止
                            # フィルター通過後は必ず AI 判定を実行する

                            if (
                                not has_position
                                and market_cond.get("market_condition") == "break"
                            ):
                                try:
                                    direction = market_cond.get("range_break")
                                    follow = follow_breakout(
                                        candles_m5, indicators, direction
                                    )
                                    log.info(f"follow_breakout result: {follow}")
                                except Exception as exc:
                                    log.warning(f"follow_breakout failed: {exc}")

                            margin_used = get_margin_used()
                            log.info(f"marginUsed={margin_used}")
                            if margin_used is None:
                                log.warning("Failed to obtain marginUsed")
                            elif (
                                MARGIN_WARNING_THRESHOLD > 0
                                and margin_used > MARGIN_WARNING_THRESHOLD
                            ):
                                log.warning(
                                    f"marginUsed {margin_used} exceeds threshold {MARGIN_WARNING_THRESHOLD}"
                                )

                            # --- SL hit cooldown check ----------------------
                            # SL 直後のクールダウンによるスキップは行わない

                            try:
                                plan_check = get_trade_plan(
                                    tick_data,
                                    {"M5": indicators},
                                    {"M1": candles_m1, "M5": candles_m5},
                                    patterns=PATTERN_NAMES,
                                    detected_patterns=self.patterns_by_tf,
                                    trade_mode=self.trade_mode,
                                    mode_reason=self.mode_reason,
                                )
                                side = (
                                    plan_check.get("entry", {})
                                    .get("side", "no")
                                    .lower()
                                )
                            except Exception as exc:
                                log.warning(f"get_trade_plan failed for check: {exc}")
                                side = "no"

                            # 直前の SL 側と同方向でもエントリーを継続

                            # 連続高値安値によるエントリーブロックを廃止

                            tp_ratio = None
                            is_counter = counter_trend_block(
                                side,
                                indicators,
                                self.indicators_M15,
                                self.indicators_H1,
                            )
                            if is_counter:
                                log.info("Counter-trend detected → TP reduced")
                                tp_ratio = float(
                                    env_loader.get_env("COUNTER_TREND_TP_RATIO", "0.5")
                                )

                            entry_params = {"tp_ratio": tp_ratio} if tp_ratio else None

                            metrics = {}
                            metrics["atr"] = atr_pips
                            try:
                                metrics["adx"] = float(
                                    self.indicators_M5.get("adx").iloc[-1]
                                    if hasattr(self.indicators_M5.get("adx"), "iloc")
                                    else self.indicators_M5.get("adx", [0])[-1]
                                )
                            except Exception:
                                metrics["adx"] = 0.0
                            try:
                                metrics["ma_angle_m1"] = float(
                                    self.indicators_M1.get("ema_slope").iloc[-1]
                                    if hasattr(self.indicators_M1.get("ema_slope"), "iloc")
                                    else self.indicators_M1.get("ema_slope", [0])[-1]
                                )
                            except Exception:
                                metrics["ma_angle_m1"] = 0.0
                            try:
                                metrics["ma_angle_m5"] = float(
                                    self.indicators_M5.get("ema_slope").iloc[-1]
                                    if hasattr(self.indicators_M5.get("ema_slope"), "iloc")
                                    else self.indicators_M5.get("ema_slope", [0])[-1]
                                )
                            except Exception:
                                metrics["ma_angle_m5"] = 0.0
                            try:
                                width = (
                                    self.indicators_M5["bb_upper"].iloc[-1]
                                    - self.indicators_M5["bb_lower"].iloc[-1]
                                )
                                metrics["bb_atr_ratio"] = (
                                    float(width) / pip_size / atr_pips if atr_pips else 0.0
                                )
                            except Exception:
                                metrics["bb_atr_ratio"] = 0.0

                            regime = regime_hint or self.classifier.classify(metrics)
                            tp_pips, sl_pips = calc_tp_sl(regime, atr_pips)
                            if entry_params is None:
                                entry_params = {}
                            entry_params.update(
                                {"tp_pips": tp_pips, "sl_pips": sl_pips, "regime": regime}
                            )

                            if not ENTRY_USE_AI:
                                res = tech_run_cycle()
                                if res:
                                    price = float(tick_data["prices"][0]["bids"][0]["price"])
                                    send_line_message(
                                        f"【ENTRY】{DEFAULT_PAIR} {price} でエントリーしました。"
                                    )
                                    info(
                                        "entry",
                                        pair=DEFAULT_PAIR,
                                        side=res.get("side"),
                                        price=price,
                                        lot=1.0,
                                        regime=res.get("mode"),
                                    )
                                self.last_run = now
                                update_oanda_trades()
                                time.sleep(self.interval_seconds)
                                timer.stop()
                                continue

                            if self.use_vote_arch:
                                pip_size = float(env_loader.get_env("PIP_SIZE", "0.01"))
                                bb_width = None
                                try:
                                    bb_width = (
                                        (self.indicators_M5["bb_upper"].iloc[-1] - self.indicators_M5["bb_lower"].iloc[-1])
                                        / pip_size
                                    )
                                except Exception:
                                    bb_width = 0.0
                                metrics = MarketMetrics(
                                    adx_m5=float(
                                        self.indicators_M5.get("adx").iloc[-1]
                                        if hasattr(self.indicators_M5.get("adx"), "iloc")
                                        else self.indicators_M5.get("adx", [0])[-1]
                                    ),
                                    ema_fast=float(
                                        self.indicators_M5.get("ema_fast").iloc[-1]
                                        if hasattr(self.indicators_M5.get("ema_fast"), "iloc")
                                        else self.indicators_M5.get("ema_fast", [0])[-1]
                                    ),
                                    ema_slow=float(
                                        self.indicators_M5.get("ema_slow").iloc[-1]
                                        if hasattr(self.indicators_M5.get("ema_slow"), "iloc")
                                        else self.indicators_M5.get("ema_slow", [0])[-1]
                                    ),
                                    bb_width_m5=float(bb_width),
                                )
                                atr_val = float(
                                    self.indicators_M5.get("atr").iloc[-1]
                                    if hasattr(self.indicators_M5.get("atr"), "iloc")
                                    else self.indicators_M5.get("atr", [0])[-1]
                                )
                                snapshot = MarketSnapshot(
                                    atr=atr_val,
                                    news_score=float(market_cond.get("news_score", 0.0)),
                                    oi_bias=float(market_cond.get("oi_bias", 0.0)),
                                )
                                spread = float(tick_data["prices"][0]["asks"][0]["price"]) - float(
                                    tick_data["prices"][0]["bids"][0]["price"]
                                )
                                if self.use_vote_pipeline:
                                    log.info("Using vote pipeline for entry")
                                    res = vote_run_cycle(
                                        indicators,
                                        metrics,
                                        snapshot,
                                        self.plan_buffer,
                                        pair=DEFAULT_PAIR,
                                        timeframe="M5",
                                        spread=spread,
                                        atr=atr_val,
                                    )
                                    if not res or not res.plan:
                                        log.info("Pipeline declined entry → skipping")
                                        self.last_run = now
                                        update_oanda_trades()
                                        time.sleep(self.interval_seconds)
                                        timer.stop()
                                        continue
                                    plan = res.plan
                                    side = plan.side
                                    lot = plan.lot
                                else:
                                    log.info("Using technical pipeline for entry")
                                    tech_run_cycle()
                                    self.last_run = now
                                    update_oanda_trades()
                                    time.sleep(self.interval_seconds)
                                    timer.stop()
                                    continue
                                params = {
                                    "instrument": DEFAULT_PAIR,
                                    "side": side,
                                    "tp_pips": plan.tp,
                                    "sl_pips": plan.sl,
                                    "mode": "market",
                                    "market_cond": market_cond,
                                }
                                order_mgr.enter_trade(
                                    side=side,
                                    lot_size=lot if lot > 0 else 0.0,
                                    market_data=tick_data,
                                    strategy_params=params,
                                )
                                price = float(tick_data["prices"][0]["bids"][0]["price"])
                                send_line_message(
                                    f"【ENTRY】{DEFAULT_PAIR} {price} でエントリーしました。"
                                )
                                info(
                                    "entry",
                                    pair=DEFAULT_PAIR,
                                    side=side,
                                    price=price,
                                    lot=lot,
                                    regime=res.mode,
                                )
                                self.scale_count = 0
                                self.last_entry_context = self.current_context
                                self.last_entry_strategy = self.current_strategy_name
                                set_last_entry_info(self.last_entry_context, self.last_entry_strategy)
                                self.last_run = now
                                update_oanda_trades()
                                time.sleep(self.interval_seconds)
                                timer.stop()
                                continue
                            else:
                                side = None
                                result = process_entry(
                                    indicators,
                                    candles_m5,
                                    tick_data,
                                    market_cond,
                                    entry_params,
                                    higher_tf=higher_tf,
                                    patterns=PATTERN_NAMES,
                                    candles_dict={"M1": candles_m1, "M5": candles_m5},
                                    pattern_names=self.patterns_by_tf,
                                    tf_align=align,
                                    indicators_multi={
                                        "M1": self.indicators_M1 or {},
                                        "M5": self.indicators_M5 or {},
                                        "H1": self.indicators_H1 or {},
                                    },
                                    risk_engine=self.risk_mgr,
                                )
                            # process_entry 結果に関わらず必ず進める
                            # Send LINE notification on entry
                            price = float(tick_data["prices"][0]["bids"][0]["price"])
                            send_line_message(
                                f"【ENTRY】{DEFAULT_PAIR} {price} でエントリーしました。"
                            )
                            info(
                                "entry",
                                pair=DEFAULT_PAIR,
                                side=side,
                                price=price,
                                lot=float(env_loader.get_env("TRADE_LOT_SIZE", "1.0")),
                                regime=self.trade_mode,
                            )
                            self.scale_count = 0
                            self.last_entry_context = self.current_context
                            self.last_entry_strategy = self.current_strategy_name
                            set_last_entry_info(self.last_entry_context, self.last_entry_strategy)
                        else:

                            log.info("Filter blocked → AI entry decision skipped.")
                            log.info("Filter NG → forcing entry after AI.")
                            side = None
                            result = process_entry(
                                indicators,
                                candles_m5,
                                tick_data,
                                market_cond,
                                entry_params,
                                higher_tf=higher_tf,
                                patterns=PATTERN_NAMES,
                                candles_dict={"M1": candles_m1, "M5": candles_m5},
                                pattern_names=self.patterns_by_tf,
                                tf_align=align,
                                indicators_multi={
                                    "M1": self.indicators_M1 or {},
                                    "M5": self.indicators_M5 or {},
                                    "H1": self.indicators_H1 or {},
                                },
                                risk_engine=self.risk_mgr,
                            )
                            price = float(tick_data["prices"][0]["bids"][0]["price"])
                            send_line_message(
                                f"【ENTRY】{DEFAULT_PAIR} {price} でエントリーしました。"
                            )
                            info(
                                "entry",
                                pair=DEFAULT_PAIR,
                                side=side,
                                price=price,
                                lot=float(env_loader.get_env("TRADE_LOT_SIZE", "1.0")),
                                regime=self.trade_mode,
                            )
                            self.scale_count = 0
                            self.last_entry_context = self.current_context
                            self.last_entry_strategy = self.current_strategy_name
                            set_last_entry_info(self.last_entry_context, self.last_entry_strategy)
                            self.last_position_review_ts = None
                    # (removed: periodic exit check block)
                # Update OANDA trade history every second
                self.last_run = now

                update_oanda_trades()
                metrics_publisher.publish(
                    "job_loop_success",
                    1,
                    {"mode": self.trade_mode or "unknown"},
                )
                time.sleep(self.interval_seconds)
                timer.stop()
                loops += 1
                if max_loops is not None and loops >= max_loops:
                    self._stop = True

            except Exception as e:
                log.error(f"Error occurred during job execution: {e}", exc_info=True)
                self.safety.record_error()
                metrics_publisher.publish("job_error", 1)
                time.sleep(self.interval_seconds)

    def stop(self) -> None:
        """Signal the runner loop to exit."""
        self._stop = True


"""Compatibility wrapper for job runner."""
from piphawk_ai.runner.core import main

if __name__ == "__main__":
    main()
