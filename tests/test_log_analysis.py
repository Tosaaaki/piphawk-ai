import importlib
import os
import unittest
from pathlib import Path


class TestLogAnalysis(unittest.TestCase):
    def setUp(self):
        self.db_path = Path("test_log.db")
        os.environ["TRADES_DB_PATH"] = str(self.db_path)
        import backend.logs.log_manager as lm
        importlib.reload(lm)
        lm.init_db()
        self.lm = lm
        import analysis.log_analysis as la
        importlib.reload(la)
        self.la = la

    def tearDown(self):
        if self.db_path.exists():
            self.db_path.unlink()

    def test_label_win_rate(self):
        trade_id = self.lm.log_trade(
            instrument="EUR_USD",
            entry_time="2024-01-01T00:00:00",
            entry_price=1.0,
            units=1,
            ai_reason="test",
        )
        self.lm.add_trade_label(trade_id, "mode=trend")
        conn = self.lm.get_db_connection()
        conn.execute("UPDATE trades SET profit_loss = 1 WHERE trade_id=?", (trade_id,))
        conn.commit()
        stats = self.la.label_win_rates()
        self.assertAlmostEqual(stats.get("mode=trend"), 1.0)

if __name__ == "__main__":
    unittest.main()
