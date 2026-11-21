"""Deployment behavior: public bind, assigned port, and safe invocation."""
import importlib.util
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("start_render", ROOT / "scripts" / "start_render.py")
start_render = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(start_render)


class RenderLaunchTests(unittest.TestCase):
    def test_render_assigned_port_and_public_bind(self):
        command = start_render.build_command({"PORT": "18325"})
        self.assertEqual(command[:4], [sys.executable, "-m", "streamlit", "run"])
        self.assertIn(str(ROOT / "app.py"), command)
        self.assertIn("--server.port=18325", command)
        self.assertIn("--server.address=0.0.0.0", command)
        self.assertIn("--server.enableCORS=true", command)
        self.assertIn("--server.enableXsrfProtection=true", command)
        self.assertIn("--server.fileWatcherType=none", command)

    def test_default_port_is_render_default(self):
        self.assertIn("--server.port=10000", start_render.build_command({}))

    def test_invalid_port_stops_before_start(self):
        for port in ("", "nope", "0", "65536", "10000 --server.enableCORS=false"):
            with self.subTest(port=port), self.assertRaises(ValueError):
                start_render.build_command({"PORT": port})

    def test_launch_replaces_process_without_shell_or_secrets(self):
        with patch.dict("os.environ", {"PORT": "10505", "NYAYA_API_KEY": "synthetic-private-key"}), patch.object(start_render.os, "chdir") as chdir, patch.object(start_render.os, "execv") as execute:
            start_render.main()
            chdir.assert_called_once_with(ROOT)
            executable, command = execute.call_args.args
            self.assertEqual(executable, sys.executable)
            self.assertIn("--server.port=10505", command)
            self.assertNotIn("synthetic-private-key", " ".join(command))


if __name__ == "__main__":
    unittest.main()
