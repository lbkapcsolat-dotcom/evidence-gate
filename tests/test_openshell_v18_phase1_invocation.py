"""Regression guards for the OpenShell V1.8 Phase 1 consumer invocation.

Offline tests only. No gateway, secrets, Docker or GitHub Actions execution.
"""
from pathlib import Path
import os
import subprocess
import tempfile
import unittest

WORKFLOW = Path(__file__).resolve().parents[1] / ".github/workflows/ess-openshell-live-v1.yml"
CALL = 'python3 "$WORKDIR/v1_8_consumer.py"'
CHECK = 'test -s "$WORKDIR/v1_8-phase1-replay.json"'


class V18Phase1InvocationTests(unittest.TestCase):
    def test_consumer_called_once_between_heredoc_and_fresh_event(self):
        text = WORKFLOW.read_text()
        anchor = 'cat >"$WORKDIR/v1_8_consumer.py" <<\'PY\''
        start = text.index(anchor)
        end = text.index('# Capture current fresh-host UID set before the new event.', start)
        region = text[start:end]
        self.assertEqual(region.count(CALL), 1)
        self.assertLess(region.index("\n          PY\n"), region.index(CALL))
        self.assertLess(region.index(CALL), region.index(CHECK))

    def test_empty_or_missing_phase1_fails_closed(self):
        for mode in ("missing", "empty"):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as d:
                p = Path(d) / "v1_8-phase1-replay.json"
                if mode == "empty":
                    p.touch()
                result = subprocess.run(["bash", "-c", 'test -s "$WORKDIR/v1_8-phase1-replay.json"'],
                                        env={**os.environ, "WORKDIR": d}, capture_output=True)
                self.assertNotEqual(result.returncode, 0)

    def test_nonempty_phase1_passes_file_guard(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "v1_8-phase1-replay.json").write_text('{"pinned_event_count":4}')
            result = subprocess.run(["bash", "-c", 'test -s "$WORKDIR/v1_8-phase1-replay.json"'],
                                    env={**os.environ, "WORKDIR": d}, capture_output=True)
            self.assertEqual(result.returncode, 0)


    def test_phase2_fail_closed_after_receipt_write(self):
        text = WORKFLOW.read_text()
        start = text.index("body['receipt_sha256']=sh(body)", text.index("V1_8_NEW_EVENT_COUNT_HOLD"))
        end = text.index("\n          PY", start)
        region = text[start:end]
        self.assertIn("raise SystemExit('V1_8_PHASE2_HOLD:'+missing)", region)
        self.assertLess(region.index("v1_8-final-receipt.json"), region.index("raise SystemExit('V1_8_PHASE2_HOLD:'+missing)"))

    def test_producer_artifact_retention_is_30_days(self):
        text = WORKFLOW.read_text()
        start = text.index("- name: Persist V1.8 producer bundle as immutable run artifact")
        end = text.index("- name: Emit raw readback bundle to job log", start)
        region = text[start:end]
        self.assertIn("retention-days: 30", region)
        self.assertIn("overwrite: false", region)
        self.assertIn("if-no-files-found: error", region)


    def test_phase2_registry_commit_only_after_hold_gate(self):
        text = WORKFLOW.read_text()
        start = text.index("new_distinct={", text.index("current_before=set("))
        end = text.index("\n          PY", start)
        region = text[start:end]
        hold = region.index("raise SystemExit('V1_8_PHASE2_HOLD:'+missing)")
        commit = region.index("existing[uid]=receipt")
        write = region.index("registry_path.write_text(")
        self.assertLess(hold, commit)
        self.assertLess(commit, write)
        self.assertNotIn("if not already: existing[uid]=receipt", region)


if __name__ == "__main__":
    unittest.main()
