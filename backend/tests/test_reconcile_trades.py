import os
import sqlite3
import tempfile
import importlib
import unittest

class TestReconcileTrades(unittest.TestCase):
    def setUp(self):
        # 一時DBファイルを用意
        self.tmp = tempfile.NamedTemporaryFile(delete=False)
        self.tmp.close()
        os.environ['TRADES_DB_PATH'] = self.tmp.name

        # モジュールを再読み込みして環境変数を反映
        import backend.logs.log_manager as lm
        import backend.logs.reconcile_trades as rt
        importlib.reload(lm)
        importlib.reload(rt)
        self.lm = lm
        self.rt = rt

        # スキーマを作成
        lm.init_db()
        conn = lm.get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO trades (instrument, entry_time, entry_price, units) VALUES (?,?,?,?)",
            ("EUR_USD", "2024-01-01T00:00:00Z", 1.0, 1000),
        )
        cur.execute(
            """
            INSERT INTO oanda_trades (trade_id, instrument, open_time, close_time, open_price, close_price, units, realized_pl, state)
            VALUES (?,?,?,?,?,?,?,?,?)
            """,
            (
                10,
                "EUR_USD",
                "2024-01-01T00:00:00Z",
                "2024-01-01T01:00:00Z",
                1.0,
                1.1,
                1000,
                1.5,
                "CLOSED",
            ),
        )
        conn.commit()
        conn.close()

    def tearDown(self):
        os.unlink(self.tmp.name)
        os.environ.pop('TRADES_DB_PATH', None)

    def test_reconcile_updates_trade(self):
        # 処理を実行
        self.rt.reconcile_trades()

        # 更新内容を検証
        conn = self.lm.get_db_connection()
        row = conn.execute(
            "SELECT profit_loss, exit_time, exit_price FROM trades WHERE trade_id = 1"
        ).fetchone()
        conn.close()
        self.assertAlmostEqual(row[0], 1.5)
        self.assertEqual(row[1], "2024-01-01T01:00:00Z")
        self.assertAlmostEqual(row[2], 1.1)

if __name__ == "__main__":
    unittest.main()
