import unittest

from tests.support import workspace_temp_dir
from yue_core.app import YueCore
from yue_core.config import Settings, load_settings
from yue_core.contracts import DesktopPresence
from yue_core.errors import ConfigurationError


class DesktopConfigTests(unittest.TestCase):
    def test_desktop_settings_load(self):
        with workspace_temp_dir() as temp:
            path = temp / "config.toml"
            path.write_text(
                """
[desktop]
hotkey = "Alt+Y"
window_anchor = "bottom-left"
model_path = "avatars/yue.vrm"
click_opens_console = false
""".strip(),
                encoding="utf-8",
            )
            settings = load_settings(path, base_dir=temp)
        self.assertEqual(settings.desktop.hotkey, "Alt+Y")
        self.assertEqual(settings.desktop.window_anchor, "bottom-left")
        self.assertEqual(settings.desktop.model_path, "avatars/yue.vrm")
        self.assertFalse(settings.desktop.click_opens_console)

    def test_rejects_invalid_window_anchor(self):
        with workspace_temp_dir() as temp:
            path = temp / "config.toml"
            path.write_text(
                "[desktop]\nwindow_anchor = \"middle\"\n",
                encoding="utf-8",
            )
            with self.assertRaises(ConfigurationError):
                load_settings(path, base_dir=temp)


class DesktopSessionTests(unittest.IsolatedAsyncioTestCase):
    async def test_attach_and_toggle_console(self):
        with workspace_temp_dir() as temp:
            settings = Settings()
            settings.core.data_dir = temp
            core = YueCore(settings)
            async with core:
                state = await core.desktop.attach("desktop-ui", metadata={"surface": "test"})
                self.assertEqual(state.attached_session_ids, ("desktop-ui",))
                state = await core.desktop.handle_command("avatar.click", source="test")
                self.assertTrue(state.console_open)
                state = await core.desktop.handle_command("avatar.sleep", source="test")
                self.assertEqual(state.presence, DesktopPresence.SLEEPING)
                state = await core.desktop.handle_command(
                    "presence.set",
                    value="thinking",
                    source="test",
                )
                self.assertEqual(state.presence, DesktopPresence.THINKING)
                state = await core.desktop.detach("desktop-ui")
                self.assertEqual(state.attached_session_ids, ())

    async def test_avatar_click_can_be_disabled(self):
        with workspace_temp_dir() as temp:
            settings = Settings()
            settings.core.data_dir = temp
            settings.desktop.click_opens_console = False
            core = YueCore(settings)
            async with core:
                state = await core.desktop.handle_command("avatar.click", source="test")
        self.assertFalse(state.console_open)


if __name__ == "__main__":
    unittest.main()
