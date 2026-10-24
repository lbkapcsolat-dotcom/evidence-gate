import tempfile
import unittest
from dataclasses import replace
from datetime import datetime, timezone, timedelta
from pathlib import Path

from remote_fetch_request_ledger import (
    AppendOnlyRequestLedger, ConnectorFailure, ConnectorFailureKind,
    ConnectorSuccess, ExpectedObject, FetchReceipt, FailClosedNoPayloadError,
    LedgerCorruptError, resolve_fail_closed, sha256_bytes
)

NOW = datetime(2026, 9, 29, 19, 0, tzinfo=timezone.utc)
DIRECT = b"direct-cache-v1"
FALLBACK = b"full-package-v1"

def exp(route, drive_id, name, payload):
    return ExpectedObject(route, drive_id, name, len(payload), sha256_bytes(payload))

D = exp("DIRECT", "drive-direct-1", "direct.bin", DIRECT)
F = exp("FULL_PACKAGE", "drive-package-1", "package.zip", FALLBACK)

def rec(e, rid, age=timedelta(0), success=True):
    return FetchReceipt(rid, e.route_key, e.drive_id, e.object_name, e.file_size_bytes,
                        e.raw_sha256, (NOW-age).isoformat(), success)

def ok(e, payload, rid):
    return ConnectorSuccess(rec(e, rid), payload)

def run(direct, fallback, ledger):
    return resolve_fail_closed(lambda: direct, lambda: fallback, D, F, ledger, NOW)


class RequestLedgerGate(unittest.TestCase):
    def new_ledger(self, td):
        return AppendOnlyRequestLedger(Path(td) / "ledger.jsonl")

    def test_restart_replay_rejected_and_unique_fallback_allowed(self):
        with tempfile.TemporaryDirectory() as td:
            first = ok(D, DIRECT, "req-restart")
            self.assertEqual(run(first, ConnectorFailure(ConnectorFailureKind.UNKNOWN), self.new_ledger(td)).route_key, "DIRECT")
            restarted = self.new_ledger(td)
            out = run(first, ok(F, FALLBACK, "req-fallback"), restarted)
            self.assertEqual(out.route_key, "FULL_PACKAGE")

    def test_cross_route_request_id_replay_fail_closed(self):
        with tempfile.TemporaryDirectory() as td:
            ledger = self.new_ledger(td)
            run(ok(D, DIRECT, "shared-id"), ConnectorFailure(ConnectorFailureKind.UNKNOWN), ledger)
            fb = ConnectorSuccess(replace(rec(F, "shared-id"), request_id="shared-id"), FALLBACK)
            with self.assertRaises(FailClosedNoPayloadError):
                run(ConnectorFailure(ConnectorFailureKind.MISSING_OBJECT), fb, self.new_ledger(td))

    def test_corrupt_ledger_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "ledger.jsonl"
            p.write_text('{"broken":true}\n', encoding="utf-8")
            with self.assertRaises(LedgerCorruptError):
                AppendOnlyRequestLedger(p)

    def test_untyped_connector_result_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(FailClosedNoPayloadError):
                resolve_fail_closed(lambda: {"success": True}, lambda: {"success": True}, D, F, self.new_ledger(td), NOW)


class MutationReplay(unittest.TestCase):
    def test_mutation_kill_15_of_15(self):
        cases = []
        cases += [
            ("M01", replace(D, drive_id="wrong"), D, DIRECT, "expected"),
            ("M02", replace(F, drive_id="wrong"), F, FALLBACK, "fallback_expected"),
            ("M03", replace(D, file_size_bytes=D.file_size_bytes+1), D, DIRECT, "expected"),
            ("M04", replace(D, raw_sha256="0"*64), D, DIRECT, "expected"),
            ("M05", replace(F, file_size_bytes=F.file_size_bytes+1), F, FALLBACK, "fallback_expected"),
            ("M06", replace(F, raw_sha256="0"*64), F, FALLBACK, "fallback_expected"),
            ("M07", D, D, DIRECT+b"x", "payload"),
            ("M08", D, D, b"X"*len(DIRECT), "payload"),
            ("M09", replace(D, object_name="wrong-member"), D, DIRECT, "expected"),
            ("M10", replace(D, object_name="wrong-file"), D, DIRECT, "expected"),
        ]
        bad_receipts = [
            ("M11", replace(rec(D, "m11"), drive_id="")),
            ("M12", replace(rec(D, "m12"), success=False)),
            ("M13", replace(rec(D, "m13"), drive_id="wrong")),
            ("M14", replace(rec(D, "m14"), file_size_bytes=D.file_size_bytes+1)),
            ("M15", replace(rec(D, "m15"), raw_sha256="f"*64)),
        ]
        killed = 0
        for mid, mutated, baseline, payload, kind in cases:
            with self.subTest(mid=mid), tempfile.TemporaryDirectory() as td:
                ledger = AppendOnlyRequestLedger(Path(td)/"l.jsonl")
                try:
                    if kind == "fallback_expected":
                        resolve_fail_closed(lambda: ConnectorFailure(ConnectorFailureKind.MISSING_OBJECT),
                            lambda: ok(F, FALLBACK, mid+"fb"), D, mutated, ledger, NOW)
                    elif kind == "payload":
                        resolve_fail_closed(lambda: ConnectorSuccess(rec(D, mid), payload),
                            lambda: ConnectorFailure(ConnectorFailureKind.MISSING_OBJECT), D, F, ledger, NOW)
                    else:
                        resolve_fail_closed(lambda: ok(D, DIRECT, mid),
                            lambda: ConnectorFailure(ConnectorFailureKind.MISSING_OBJECT), mutated, F, ledger, NOW)
                except FailClosedNoPayloadError:
                    killed += 1
        for mid, bad in bad_receipts:
            with self.subTest(mid=mid), tempfile.TemporaryDirectory() as td:
                try:
                    resolve_fail_closed(lambda: ConnectorSuccess(bad, DIRECT),
                        lambda: ConnectorFailure(ConnectorFailureKind.MISSING_OBJECT),
                        D, F, AppendOnlyRequestLedger(Path(td)/"l.jsonl"), NOW)
                except FailClosedNoPayloadError:
                    killed += 1
        self.assertEqual(killed, 15)


class FailureReplay(unittest.TestCase):
    def test_failure_cases_10_of_10(self):
        cases = [
            ("F01", ConnectorFailureKind.TIMEOUT, True),
            ("F02", ConnectorFailureKind.PERMISSION_DENIED, True),
            ("F03", ConnectorFailureKind.PARTIAL_DOWNLOAD, True),
            ("F04", ConnectorFailureKind.STALE_CACHE, True),
            ("F05", ConnectorFailureKind.MISSING_OBJECT, True),
            ("F06", ConnectorFailureKind.PARTIAL_DOWNLOAD, False),
            ("F07", ConnectorFailureKind.TIMEOUT, False),
            ("F08", None, None),
            ("F09", ConnectorFailureKind.MISSING_OBJECT, True),
            ("F10", "success_false", True),
        ]
        passed = 0
        for cid, kind, fb_valid in cases:
            with self.subTest(cid=cid), tempfile.TemporaryDirectory() as td:
                ledger = AppendOnlyRequestLedger(Path(td)/"l.jsonl")
                direct = ok(D, DIRECT, cid+"d") if kind is None else (
                    ConnectorSuccess(replace(rec(D, cid+"d"), success=False), DIRECT)
                    if kind == "success_false" else ConnectorFailure(kind)
                )
                fallback = ok(F, FALLBACK, cid+"f") if fb_valid else (
                    ConnectorFailure(ConnectorFailureKind.UNKNOWN) if fb_valid is None
                    else ConnectorSuccess(rec(F, cid+"f"), FALLBACK+b"bad")
                )
                try:
                    result = run(direct, fallback, ledger)
                    self.assertEqual(result.route_key, "DIRECT" if cid == "F08" else "FULL_PACKAGE")
                    passed += 1
                except FailClosedNoPayloadError:
                    if cid in {"F06","F07"}:
                        passed += 1
        self.assertEqual(passed, 10)


class ReceiptRouteGuards(unittest.TestCase):
    def test_receipt_route_guards_8_of_8(self):
        guards = [
            ("G01", replace(rec(D,"g01"), fetched_at=(NOW-timedelta(hours=1)).isoformat())),
            ("G02", replace(rec(D,"g02"), route_key="WRONG")),
            ("G03", replace(rec(D,"g03"), object_name="wrong.bin")),
            ("G04", replace(rec(D,"g04"), drive_id="wrong")),
            ("G05", replace(rec(D,"g05"), fetched_at=(NOW+timedelta(minutes=5)).isoformat())),
            ("G06", replace(rec(D,"g06"), file_size_bytes=D.file_size_bytes+1)),
            ("G07", replace(rec(D,"g07"), raw_sha256="f"*64)),
            ("G08", replace(rec(D,"g08"), success=False)),
        ]
        passed = 0
        for gid, bad in guards:
            with self.subTest(gid=gid), tempfile.TemporaryDirectory() as td:
                result = run(ConnectorSuccess(bad, DIRECT), ok(F, FALLBACK, gid+"fb"),
                             AppendOnlyRequestLedger(Path(td)/"l.jsonl"))
                self.assertEqual(result.route_key, "FULL_PACKAGE")
                passed += 1
        self.assertEqual(passed, 8)


if __name__ == "__main__":
    unittest.main()
