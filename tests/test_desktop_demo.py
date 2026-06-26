import unittest

from tests.support import workspace_temp_dir
from yue_core.config import Settings
from yue_core.desktop_demo import run_desktop_headless_smoke_test, start_desktop_runtime


class DesktopDemoTests(unittest.TestCase):
    def test_headless_smoke_test(self):
        with workspace_temp_dir() as temp:
            settings = Settings()
            settings.core.data_dir = temp
            payload = run_desktop_headless_smoke_test(settings)
        self.assertEqual(payload["reply"], "Echo: hello from desktop demo")
        self.assertFalse(payload["state_before"]["console_open"])
        self.assertTrue(payload["state_after_toggle"]["console_open"])
        self.assertIsNotNone(payload["conversation_id"])

    def test_runtime_controller_updates_state(self):
        with workspace_temp_dir() as temp:
            settings = Settings()
            settings.core.data_dir = temp
            runtime = start_desktop_runtime(settings)
            try:
                runtime.call(runtime.controller.set_expression("happy"))
                runtime.call(runtime.controller.set_presence("listening"))
                snapshot = runtime.controller.state.to_dict()
            finally:
                runtime.shutdown()
        self.assertEqual(snapshot["expression"], "happy")
        self.assertEqual(snapshot["presence"], "listening")


if __name__ == "__main__":
    unittest.main()
