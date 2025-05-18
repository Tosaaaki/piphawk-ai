from fastapi import FastAPI, HTTPException
from backend.utils import env_loader
import sqlite3
import os
from apscheduler.schedulers.background import BackgroundScheduler
from linebot import LineBotApi
from linebot.models import TextSendMessage
from datetime import datetime, timedelta
from fastapi import APIRouter
from pydantic import BaseModel

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# --- CORS ---
# Allow requests from any origin (frontend dev & Cloud Run UI).
# Adjust `allow_origins` to a specific list when moving to production.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


DATABASE_PATH = env_loader.get_env("TRADES_DB_PATH", "/app/trades.db")
LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")

# Initialize and start the background scheduler
scheduler = BackgroundScheduler()
scheduler.start()

LINE_CHANNEL_TOKEN = os.getenv("LINE_CHANNEL_TOKEN", "")
LINE_USER_ID = os.getenv("LINE_USER_ID", "")

line_api = LineBotApi(LINE_CHANNEL_TOKEN)

def send_line_message(text: str):
    if not LINE_CHANNEL_TOKEN or not LINE_USER_ID:
        raise HTTPException(status_code=500, detail="LINE API token or user ID not configured")
    line_api.push_message(
        to=LINE_USER_ID,
        messages=[TextSendMessage(text=text)]
    )


@app.get("/logs/errors")
def get_error_logs():
    try:
        with open(os.path.join(LOG_DIR, "errors.log"), "r") as file:
            errors = file.read().splitlines()
        # Return the latest 50 lines (or all if fewer)
        return {"errors": errors[-50:]}
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Error log file not found")



# In-memory settings store
current_settings = {
    "ai_cooldown_flat": int(env_loader.get_env("AI_COOLDOWN_SEC_FLAT", "60")),
    "ai_cooldown_open": int(env_loader.get_env("AI_COOLDOWN_SEC_OPEN", "30")),
    "review_sec": int(env_loader.get_env("POSITION_REVIEW_SEC", "60")),
}

class NotificationSettings(BaseModel):
    enabled: bool
    token: str

# In-memory notification settings
notification_settings = {"enabled": False, "token": LINE_CHANNEL_TOKEN}


@app.get("/strategy/backtest")
def backtest(start_date: str, end_date: str, strategy: str = "ema_cross", capital: float = 10000.0, risk_pct: float = 1.0):
    """
    Placeholder for backtest endpoint.
    Returns a dummy equity curve and summary.
    """
    equity_curve = [
        {"date": start_date, "equity": capital},
        {"date": end_date, "equity": capital + 1000.0}
    ]
    summary = {
        "trades": 0,
        "total_pl": 0.0,
        "win_rate": 0.0,
        "max_dd": 0.0,
        "sharpe": 0.0
    }
    return {"equity_curve": equity_curve, "summary": summary}

@app.get("/strategy/analyze")
def analyze(start_date: str | None = None, end_date: str | None = None, group_by: str = "month"):
    """
    Placeholder for analyze endpoint.
    Returns dummy grouped performance and overall summary.
    """
    by_group = [
        {"group": "2025-01", "trades": 0, "pl": 0.0},
        {"group": "2025-02", "trades": 0, "pl": 0.0}
    ]
    overall = {
        "trades": 0,
        "total_pl": 0.0,
        "win_rate": 0.0
    }
    return {f"by_{group_by}": by_group, "overall": overall}

def send_hourly_summary():
    end = datetime.utcnow()
    start = end - timedelta(hours=1)
    conn = sqlite3.connect(DATABASE_PATH)
    cur = conn.cursor()
    cur.execute("""
        SELECT
          COUNT(*),
          SUM(CASE WHEN realized_pl > 0 THEN 1 ELSE 0 END),
          SUM(CASE WHEN realized_pl <= 0 THEN 1 ELSE 0 END),
          SUM(realized_pl)
        FROM oanda_trades
        WHERE close_time BETWEEN ? AND ?
    """, (start.isoformat(), end.isoformat()))
    total, wins, losses, total_pl = cur.fetchone()
    conn.close()
    win_rate = round((wins or 0) / (total or 1) * 100, 2)
    msg = (
        f"【１時間サマリー】\n"
        f"総取引数: {total}\n"
        f"勝ち: {wins} / 負け: {losses} (勝率 {win_rate}%)\n"
        f"損益合計: {total_pl:.2f}"
    )
    send_line_message(msg)

# Schedule the job to run every hour at minute 0

# Schedule the job to run every hour at minute 0
scheduler.add_job(send_hourly_summary, 'cron', minute=0)

# Test endpoint: Get trade summary for the last hour (no notification)
@app.get("/trades/summary")
def get_trade_summary():
    """
    Returns a summary of trades in the past hour for testing purposes.
    """
    end = datetime.utcnow()
    start = end - timedelta(hours=1)
    conn = sqlite3.connect(DATABASE_PATH)
    cur = conn.cursor()
    cur.execute("""
        SELECT
          COUNT(*),
          SUM(CASE WHEN realized_pl > 0 THEN 1 ELSE 0 END),
          SUM(CASE WHEN realized_pl <= 0 THEN 1 ELSE 0 END),
          SUM(realized_pl)
        FROM oanda_trades
        WHERE close_time BETWEEN ? AND ?
    """, (start.isoformat(), end.isoformat()))
    total, wins, losses, total_pl = cur.fetchone()
    conn.close()
    win_rate = round((wins or 0) / (total or 1) * 100, 2)
    return {
        "start": start.isoformat(),
        "end": end.isoformat(),
        "summary": {
            "total_trades": total or 0,
            "wins": wins or 0,
            "losses": losses or 0,
            "win_rate": win_rate,
            "total_pl": total_pl or 0
        }
    }


# ------------------------------------------------------------------
#  UI‑friendly settings endpoints (alias for /notifications/settings)
# ------------------------------------------------------------------
@app.get("/settings")
def ui_get_settings():
    return notification_settings

@app.post("/settings")
def ui_update_settings(settings: NotificationSettings):
    notification_settings.update(settings.dict())
    return {"status": "ok", "settings": notification_settings}

notifications_router = APIRouter(prefix="/notifications")

@notifications_router.get("/settings")
def get_notification_settings():
    return notification_settings

@notifications_router.post("/settings")
def update_notification_settings(settings: NotificationSettings):
    notification_settings.update(settings.dict())
    return {"status": "ok", "settings": notification_settings}

@notifications_router.post("/send")
def send_test_notification():
    send_line_message("This is a test LINE notification.")
    return {"status": "sent"}

app.include_router(notifications_router)