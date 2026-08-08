import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pybo import create_app
from scripts import monitor_friendary


class HealthEndpointTests(unittest.TestCase):
    def test_health_endpoint_checks_database(self):
        app = create_app()
        app.config.update(TESTING=True)
        response = app.test_client().get("/healthz")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {"status": "ok"})


class MonitorStateTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.state_file = Path(self.temp_dir.name) / "state.json"
        self.state_patcher = patch.object(monitor_friendary, "STATE_FILE", self.state_file)
        self.state_patcher.start()
        self.addCleanup(self.state_patcher.stop)

    def test_alerts_once_after_threshold_and_again_on_recovery(self):
        notifications = []
        with (
            patch.object(monitor_friendary, "FAILURE_THRESHOLD", 3),
            patch.object(monitor_friendary, "system_problems", return_value=[]),
            patch.object(monitor_friendary, "consume_incident_events", return_value=[]),
            patch.object(monitor_friendary, "notify", side_effect=lambda subject, detail: notifications.append(subject)),
        ):
            for _ in range(4):
                with patch.object(monitor_friendary, "probe", return_value=(False, "HTTP 503")):
                    self.assertEqual(monitor_friendary.main(), 1)
            self.assertEqual(len(notifications), 1)
            with patch.object(monitor_friendary, "probe", return_value=(True, "HTTP 200, database OK")):
                self.assertEqual(monitor_friendary.main(), 0)

        self.assertEqual(len(notifications), 2)
        self.assertIn("복구", notifications[1])
        state = json.loads(self.state_file.read_text(encoding="utf-8"))
        self.assertEqual(state["failures"], 0)
        self.assertFalse(state["alerted"])


if __name__ == "__main__":
    unittest.main()
