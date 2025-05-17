from fastapi import FastAPI
from backend.utils import env_loader

import sqlite3
from fastapi import HTTPException
from pydantic import BaseModel

app = FastAPI()

DATABASE_PATH = env_loader.get_env("TRADES_DB_PATH", "/app/trades.db")

@app.get("/status")
def status():
    return {"status": "ok"}

@app.get("/dashboard")
def get_dashboard():
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        cur = conn.cursor()
        cur.execute("SELECT id, time, type, tradeID, price, reason, pl FROM trades ORDER BY time DESC LIMIT 10")
        rows = cur.fetchall()
        trades = [
            {"id": r[0], "time": r[1], "type": r[2], "tradeID": r[3], "price": r[4], "reason": r[5], "pl": r[6]}
            for r in rows
        ]
        cur.execute("""
            SELECT
              SUM(CASE WHEN pl > 0 THEN 1 ELSE 0 END),
              SUM(CASE WHEN pl <= 0 THEN 1 ELSE 0 END)
            FROM trades
        """)
        wins, losses = cur.fetchone()
        total = (wins or 0) + (losses or 0)
        win_rate = round((wins or 0) / total * 100, 2) if total > 0 else None
        performance = {"wins": wins or 0, "losses": losses or 0, "win_rate": win_rate}
        return {"trades": trades, "performance": performance}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()

class Settings(BaseModel):
    ai_cooldown_flat: int
    ai_cooldown_open: int
    review_sec: int

# In-memory settings store
current_settings = {
    "ai_cooldown_flat": int(env_loader.get_env("AI_COOLDOWN_SEC_FLAT", "60")),
    "ai_cooldown_open": int(env_loader.get_env("AI_COOLDOWN_SEC_OPEN", "30")),
    "review_sec": int(env_loader.get_env("POSITION_REVIEW_SEC", "60")),
}

@app.get("/settings")
def get_settings():
    return current_settings

@app.post("/settings")
def update_settings(settings: Settings):
    current_settings.update(settings.dict())
    return {"status": "ok", "settings": current_settings}

@app.post("/control/{action}")
def control_job(action: str):
    if action not in {"start", "stop", "restart"}:
        raise HTTPException(status_code=400, detail="Invalid action")
    # TODO: integrate with JobRunner control mechanism
    return {"status": "ok", "action": action}