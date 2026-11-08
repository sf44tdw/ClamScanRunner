#!/usr/bin/env python3
"""Exercise the built RPM's scriptlets without modifying the host."""

import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest


RPM = os.environ["CLAMSCANRUNNER_RPM"]
SCRIPTS = subprocess.check_output(["rpm", "-qp", "--scripts", RPM], text=True)


def scriptlet(name):
    match = re.search(
        rf"(?ms)^{name} scriptlet \(using /bin/sh\):\n(.*?)(?=^\w+ scriptlet \(using /bin/sh\):\n|\Z)",
        SCRIPTS,
    )
    if not match:
        raise AssertionError(f"Missing RPM scriptlet: {name}")
    return match.group(1)


class ScriptletTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.bin = self.root / "bin"
        self.bin.mkdir()
        self.etc = self.root / "etc"
        (self.etc / "cron.d").mkdir(parents=True)
        self.local_bin = self.root / "local-bin"
        self.local_bin.mkdir()
        self.conf = self.etc / "freshclam.conf"
        self.conf.write_text("Example\n#NotifyClamd /path/to/clamd.conf\n")
        self.trace = self.root / "trace"
        for command in ("systemctl", "getenforce", "semanage", "freshclam"):
            stub = self.bin / command
            output = 'echo "$SELINUX_STATUS"' if command == "getenforce" else ":"
            stub.write_text(
                "#!/bin/sh\n"
                f'echo "{command} $*" >> "$TRACE"\n'
                f'[ "$FAIL_COMMAND" != "{command}" ] || exit 1\n'
                f"{output}\n"
            )
            stub.chmod(0o755)
        self.env = {
            **os.environ,
            "PATH": f"{self.bin}:{os.environ['PATH']}",
            "TRACE": str(self.trace),
            "FAIL_COMMAND": "",
            "SELINUX_STATUS": "Enforcing",
        }

    def run_scriptlet(self, name, argument):
        script = scriptlet(name)
        script = script.replace(
            "old_cron=/etc/cron.d/", f"old_cron={self.etc}/cron.d/"
        ).replace(
            "old_helper=/usr/local/bin/", f"old_helper={self.local_bin}/"
        ).replace("/etc/freshclam.conf", str(self.conf))
        return subprocess.run(
            ["/bin/sh", "-s", "--", str(argument)],
            input=script,
            text=True,
            capture_output=True,
            env=self.env,
            check=True,
        )

    def calls(self):
        return self.trace.read_text().splitlines() if self.trace.exists() else []

    def test_initial_install_and_legacy_migration(self):
        cron = self.etc / "cron.d/remove_clamscan_runner_lockfile"
        cron.write_text(
            "SHELL=/bin/bash\n"
            "@reboot root sleep 60 && /usr/local/bin/"
            "remove_clamscan_runner_lockfile clamscanrunner\n"
        )
        helper = self.local_bin / "remove_clamscan_runner_lockfile"
        helper.write_text("ps_llist\n")
        result = self.run_scriptlet("postinstall", 1)
        self.assertEqual(result.stderr, "")
        self.assertFalse(cron.exists())
        self.assertTrue(helper.exists())
        self.assertEqual(
            self.conf.read_text(),
            "#Example\nNotifyClamd /etc/clamd.d/scan.conf\n",
        )
        self.assertEqual(len(list(self.etc.glob("freshclam.conf.*.bak"))), 1)
        self.assertIn("freshclam ", self.calls())
        self.assertIn("semanage boolean -m --on antivirus_can_scan_system", self.calls())
        self.assertIn("systemctl enable clamscanrunner-lock-cleanup.service", self.calls())
        self.assertIn("systemctl enable --now crond.service", self.calls())

    def test_upgrade_preserves_configuration_and_service_state(self):
        self.run_scriptlet("postinstall", 2)
        self.run_scriptlet("preuninstall", 1)
        self.assertEqual(self.conf.read_text(), "Example\n#NotifyClamd /path/to/clamd.conf\n")
        self.assertEqual(self.calls(), [])
        self.run_scriptlet("postuninstall", 1)
        self.assertEqual(self.calls(), ["systemctl daemon-reload"])

    def test_removal_stops_only_cleanup_service(self):
        self.run_scriptlet("preuninstall", 0)
        self.run_scriptlet("postuninstall", 0)
        self.assertEqual(
            self.calls(),
            ["systemctl disable clamscanrunner-lock-cleanup.service",
             "systemctl daemon-reload"],
        )

    def test_modified_legacy_job_is_preserved_and_warned(self):
        cron = self.etc / "cron.d/remove_clamscan_runner_lockfile"
        cron.write_text(
            "SHELL=/bin/bash\n"
            "@reboot root sleep 60 && /usr/local/bin/"
            "remove_clamscan_runner_lockfile clamscanrunner\n"
            "custom job\n"
        )
        result = self.run_scriptlet("postinstall", 1)
        self.assertTrue(cron.exists())
        self.assertIn("WARNING: Review", result.stderr)

    def test_failures_are_reported(self):
        self.env["FAIL_COMMAND"] = "freshclam"
        result = self.run_scriptlet("postinstall", 1)
        self.assertIn("WARNING: Initial freshclam update failed", result.stderr)
        self.assertIn("systemctl enable --now crond.service", self.calls())

    def test_service_failures_are_reported(self):
        self.env["FAIL_COMMAND"] = "systemctl"
        result = self.run_scriptlet("postinstall", 1)
        self.assertIn("WARNING: Could not enable lock cleanup", result.stderr)
        self.assertIn("WARNING: Could not enable/start crond.service", result.stderr)

    def test_missing_freshclam_config_is_reported(self):
        self.conf.unlink()
        result = self.run_scriptlet("postinstall", 1)
        self.assertIn("WARNING: Could not back up", result.stderr)
        self.assertNotIn("freshclam ", self.calls())

    def test_selinux_disabled(self):
        self.env["SELINUX_STATUS"] = "Disabled"
        self.run_scriptlet("postinstall", 1)
        self.assertFalse(any(call.startswith("semanage ") for call in self.calls()))


if __name__ == "__main__":
    unittest.main()
