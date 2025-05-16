import sqlite3
from datetime import datetime, timedelta
import os
import dotenv
import json
import shutil
from backend.utils.openai_client import ask_openai
from backend.logs.log_manager import log_param_change

import logging
logger = logging.getLogger(__name__)

DB_PATH = "backend/logs/trades.db"
SETTINGS_PATH = "backend/config/settings.env"
# SQLite table that stores every environment‐parameter change suggested/applied by the strategy optimizer
PARAM_CHANGE_DB_TABLE = "param_changes"
def load_env_settings():
    """
    .envファイルから戦略パラメータを読み込む
    """
    dotenv.load_dotenv(SETTINGS_PATH, override=True)
    settings = {
        "RSI_PERIOD": int(os.getenv("RSI_PERIOD", 14)),
        "EMA_PERIOD": int(os.getenv("EMA_PERIOD", 20)),
        "ATR_PERIOD": int(os.getenv("ATR_PERIOD", 14)),
        "BOLLINGER_WINDOW": int(os.getenv("BOLLINGER_WINDOW", 20)),
        "BOLLINGER_STD": float(os.getenv("BOLLINGER_STD", 2.0)),
        "RSI_ENTRY_LOWER": int(os.getenv("RSI_ENTRY_LOWER", 30)),
        "RSI_ENTRY_UPPER": int(os.getenv("RSI_ENTRY_UPPER", 70)),
        "ATR_ENTRY_THRESHOLD": float(os.getenv("ATR_ENTRY_THRESHOLD", 0.05)),
        "EMA_DIFF_THRESHOLD": float(os.getenv("EMA_DIFF_THRESHOLD", 0.1)),
        "BB_POSITION_THRESHOLD": float(os.getenv("BB_POSITION_THRESHOLD", 0.9)),
    }
    return settings

def ensure_param_change_table():
    """Create the param_changes table if it does not exist."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(f"""
            CREATE TABLE IF NOT EXISTS {PARAM_CHANGE_DB_TABLE} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                param_key TEXT,
                old_value TEXT,
                new_value TEXT
            )
        """)

def backup_settings():
    """Create a timestamped backup of the current settings.env file."""
    ts = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    backup_path = f"{SETTINGS_PATH}.{ts}.bak"
    shutil.copy2(SETTINGS_PATH, backup_path)
    return backup_path

def apply_param_changes(changes: dict):
    """Write suggested param changes into settings.env and log them."""
    # Backup first
    backup_settings()
    # Read current lines
    with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
        lines = f.readlines()

    updated_lines = []
    seen_keys = set()
    for line in lines:
        if "=" not in line:
            updated_lines.append(line)
            continue
        key, _ = line.split("=", 1)
        key = key.strip()
        if key in changes:
            updated_lines.append(f"{key}={changes[key]}\n")
            seen_keys.add(key)
            # Log parameter change
            log_param_change(key, os.getenv(key, ""), str(changes[key]), ai_reason="strategy_optimizer")
        else:
            updated_lines.append(line)

    # Add any new keys that weren't previously present
    for k, v in changes.items():
        if k not in seen_keys:
            updated_lines.append(f"{k}={v}\n")
            log_param_change(k, "", str(v), ai_reason="strategy_optimizer")

    with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
        f.writelines(updated_lines)

def suggest_parameter_adjustments(settings, summary_text: str):
    summary_text = summary_text or "No recent performance data."
    """Ask OpenAI for JSON suggestions and apply them."""
    ensure_param_change_table()
    prompt = (
        "You are a trading-strategy tuning assistant.\n" 
        "Current environment parameters (key=value) are:\n" +
        "\n".join([f"{k}={v}" for k, v in settings.items()]) + "\n\n" +
        "Here is the latest performance summary:\n" +
        summary_text + "\n\n" +
        "Respond ONLY with a JSON object whose keys are the parameter names to change and values are the new values. " +
        "Do not wrap the JSON in markdown fences or add commentary."
    )
    response = ask_openai(prompt)
    logger.info(f"Strategy optimizer AI response: {response}")
    try:
        changes = json.loads(response)
        if isinstance(changes, dict) and changes:
            print("[戦略分析AI] 提案されたパラメータ変更: ", changes)
            apply_param_changes(changes)
            print("[戦略分析AI] settings.env を更新しました。次サイクルから有効になります。")
        else:
            print("[戦略分析AI] 有効な変更提案はありません。")
    except json.JSONDecodeError:
        print("[戦略分析AI] OpenAI からの応答を JSON として解析できませんでした。応答:\n", response)

def fetch_recent_trades(hours=1):
    since = datetime.utcnow() - timedelta(hours=hours)
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT entry_time, exit_time, profit_loss FROM trades
            WHERE exit_time IS NOT NULL AND entry_time >= ?
        """, (since.isoformat(),))
        return cursor.fetchall()

def fetch_ai_decisions(hours=1):
    since = datetime.utcnow() - timedelta(hours=hours)
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT timestamp, decision_type, instrument FROM ai_decisions
            WHERE timestamp >= ?
        """, (since.isoformat(),))
        return cursor.fetchall()

def analyze_performance(trades):
    if not trades:
        print("No trades found.")
        return

    total = len(trades)
    wins = [p for _, _, p in trades if p and p > 0]
    losses = [p for _, _, p in trades if p and p <= 0]
    avg_win = sum(wins) / len(wins) if wins else 0
    avg_loss = sum(losses) / len(losses) if losses else 0
    win_rate = len(wins) / total * 100 if total else 0
    net = sum(p for _, _, p in trades if p is not None)

    print(f"[戦略分析AIレポート] {datetime.utcnow().isoformat()} UTC")
    print(f"トレード数: {total}")
    print(f"勝率: {win_rate:.2f}%")
    print(f"平均利益: {avg_win:.2f}pips")
    print(f"平均損失: {avg_loss:.2f}pips")
    print(f"純利益: {net:.2f}pips")
    return f"勝率:{win_rate:.2f}% 純利益:{net:.2f}pips 平均利益:{avg_win:.2f} 平均損失:{avg_loss:.2f}"

def main():
    trades = fetch_recent_trades(hours=1)
    decisions = fetch_ai_decisions(hours=1)
    perf_summary = analyze_performance(trades)
    print(f"AI判断回数: {len(decisions)}")

    # パラメータ表示
    settings = load_env_settings()
    print("\n[現在の戦略パラメータ]")
    for k, v in settings.items():
        print(f"{k}: {v}")

    # OpenAI による自動最適化提案
    performance_summary = perf_summary  # returned string
    suggest_parameter_adjustments(settings, performance_summary)

if __name__ == "__main__":
    main()