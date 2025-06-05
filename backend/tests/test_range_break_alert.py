import importlib
import sys
import types
import unittest

fastapi_stub = types.ModuleType("fastapi")
fastapi_stub.HTTPException = Exception
sys.modules["fastapi"] = fastapi_stub
linebot_stub = types.ModuleType("linebot")
linebot_models = types.ModuleType("linebot.models")
linebot_stub.LineBotApi = lambda *a, **k: None
linebot_models.TextSendMessage = lambda text: None
sys.modules["linebot"] = linebot_stub
sys.modules["linebot.models"] = linebot_models

import backend.utils.notification as notif


class TestRangeBreakAlert(unittest.TestCase):
    def setUp(self):
        self.sent = []
        self._orig = notif.send_line_message
        importlib.reload(notif)
        notif.send_line_message = lambda text, token=None, user_id=None: self.sent.append(text)

    def tearDown(self):
        notif.send_line_message = self._orig
        sys.modules.pop("fastapi", None)
        sys.modules.pop("linebot", None)
        sys.modules.pop("linebot.models", None)

    def test_alert_message_contains_direction(self):
        notif.send_range_break_alert("up")
        self.assertEqual(len(self.sent), 1)
        self.assertIn("⚡️Range Break!", self.sent[0])
        self.assertIn("up", self.sent[0])


if __name__ == "__main__":
    unittest.main()
