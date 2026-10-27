"""Offline regressions for transport verification failures found by Muzakere."""

import contextlib
import importlib.util
import io
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock


spec = importlib.util.spec_from_file_location(
    "check_transports", Path(__file__).with_name("check-transports.py"),
)
transport = importlib.util.module_from_spec(spec)
spec.loader.exec_module(transport)


class TemporaryWork(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix="muzakere-regression-")
        self.addCleanup(temporary.cleanup)
        self.work = Path(temporary.name)


class HeaderTests(TemporaryWork):
    def header(self, extra=(), omit=(), values=None, newline="\n"):
        fields = {
            "workdir": str(self.work), "sandbox": "read-only",
            "approval": "never", "session id": "original-session",
        }
        fields.update(values or {})
        lines = [f"{key}: {value}" for key, value in fields.items() if key not in omit]
        return newline.join([*lines, *extra, "user", "prompt content"])

    def test_valid_header_and_crlf(self):
        for newline in ("\n", "\r\n"):
            with self.subTest(newline=repr(newline)):
                self.assertEqual(
                    transport.parse_codex_header(self.header(newline=newline), self.work),
                    "original-session",
                )

    def test_sanitized_real_codex_header(self):
        fixture = Path(__file__).parent / "fixtures" / "codex-0.164.header.txt"
        header = fixture.read_text().replace("<WORKDIR>", str(self.work))
        self.assertEqual(transport.parse_codex_header(header, self.work), "captured-session")

    def test_conflicting_sandbox_fields_are_rejected_in_both_orders(self):
        for first, second in (("workspace-write", "read-only"), ("read-only", "workspace-write")):
            with self.subTest(first=first):
                header = self.header(values={"sandbox": first}, extra=[f"sandbox: {second}"])
                with self.assertRaisesRegex(RuntimeError, "duplicate.*sandbox"):
                    transport.parse_codex_header(header, self.work)

    def test_duplicate_fields_are_rejected_even_when_identical(self):
        for name, value in (("workdir", self.work), ("sandbox", "read-only"),
                            ("approval", "never"), ("session id", "original-session")):
            with self.subTest(field=name):
                with self.assertRaisesRegex(RuntimeError, "duplicate"):
                    transport.parse_codex_header(self.header(extra=[f"{name}: {value}"]), self.work)

    def test_missing_and_empty_fields_are_rejected(self):
        for name in ("workdir", "sandbox", "approval", "session id"):
            for header in (self.header(omit=[name]), self.header(values={name: ""})):
                with self.subTest(field=name, header=header):
                    with self.assertRaisesRegex(RuntimeError, "missing or empty"):
                        transport.parse_codex_header(header, self.work)

    def test_unsafe_values_are_rejected(self):
        for values in ({"sandbox": "workspace-write"}, {"approval": "on-request"},
                       {"workdir": str(self.work / "other")}):
            with self.subTest(values=values):
                with self.assertRaisesRegex(RuntimeError, "did not confirm"):
                    transport.parse_codex_header(self.header(values=values), self.work)

    def test_prompt_fields_cannot_replace_missing_header_fields(self):
        header = self.header(omit=["sandbox"]) + "\nsandbox: read-only\n"
        with self.assertRaisesRegex(RuntimeError, "missing or empty"):
            transport.parse_codex_header(header, self.work)

    def test_missing_boundary_is_rejected(self):
        header = self.header().split("\nuser\n")[0]
        with self.assertRaisesRegex(RuntimeError, "boundary"):
            transport.parse_codex_header(header, self.work)


class ExecutableTests(TemporaryWork):
    def stub(self, name, body):
        path = self.work / name
        path.write_text("#!/bin/sh\n" + body + "\n")
        path.chmod(0o700)
        return str(path)

    def discovery(self, first, second, override=None):
        environment = {"CODEX_APP_RUNTIME_CLI_PATH": second}
        if override:
            environment["MUZAKERE_CODEX_BIN"] = override
        stack = contextlib.ExitStack()
        stack.enter_context(mock.patch.dict(os.environ, environment, clear=True))
        stack.enter_context(mock.patch.object(transport.shutil, "which", return_value=first))
        stack.enter_context(mock.patch.object(
            transport.os, "access", side_effect=lambda path, mode: path in (first, second),
        ))
        return stack

    def test_failing_version_candidate_falls_back(self):
        broken = self.stub("broken", "exit 9")
        working = self.stub("working", "echo codex-cli 9.9.9")
        errors = io.StringIO()
        with self.discovery(broken, working), contextlib.redirect_stderr(errors):
            binary, label = transport.executable("codex", 5)
        self.assertEqual(binary, str(Path(working).resolve()))
        self.assertEqual(label, "codex-cli 9.9.9")
        self.assertIn("exited 9", errors.getvalue())

    def test_unreadable_timed_out_and_unparseable_candidates_fall_back(self):
        broken, working = str(self.work / "broken"), str(self.work / "working")
        for failure in (
            OSError("unreadable"), RuntimeError("timed out"), "unknown build",
            UnicodeDecodeError("utf-8", b"\xff", 0, 1, "invalid start byte"),
            ValueError("invalid version number"),
        ):
            with self.subTest(failure=str(failure)), self.discovery(broken, working):
                with mock.patch.object(transport, "version", side_effect=[failure, "codex-cli 9.9.9"]):
                    with contextlib.redirect_stderr(io.StringIO()):
                        binary, _ = transport.executable("codex", 5)
                self.assertEqual(binary, str(Path(working).resolve()))

    def test_invalid_byte_output_does_not_block_a_working_candidate(self):
        broken = self.stub("invalid-output", r"printf '\377'")
        working = self.stub("working", "echo codex-cli 9.9.9")
        with self.discovery(broken, working), contextlib.redirect_stderr(io.StringIO()):
            binary, label = transport.executable("codex", 5)
        self.assertEqual(binary, str(Path(working).resolve()))
        self.assertEqual(label, "codex-cli 9.9.9")

    def test_newest_healthy_candidate_wins_in_either_order(self):
        pairs = (
            ("1.0.0", "2.0.0"),
            ("2.0.0-alpha.10", "2.0.0"),
            ("2.0.0-alpha.9", "2.0.0-alpha.10"),
        )
        for older, newer in pairs:
            for first_version, second_version in ((older, newer), (newer, older)):
                with self.subTest(first=first_version, second=second_version):
                    first = self.stub("first", f"echo codex-cli {first_version}")
                    second = self.stub("second", f"echo codex-cli {second_version}")
                    with self.discovery(first, second):
                        _, label = transport.executable("codex", 5)
                    self.assertEqual(label, f"codex-cli {newer}")

    def test_explicit_override_never_silently_falls_back(self):
        broken = self.stub("broken", "exit 9")
        working = self.stub("working", "echo codex-cli 9.9.9")
        with self.discovery(broken, working, override=broken):
            with mock.patch.object(transport, "version", wraps=transport.version) as version:
                with self.assertRaisesRegex(RuntimeError, "override.*exited 9"):
                    transport.executable("codex", 5)
                self.assertEqual(version.call_count, 1)

    def test_missing_override_is_reported(self):
        with self.discovery("unused", "unused", override=str(self.work / "missing")):
            with self.assertRaisesRegex(RuntimeError, "override.*not executable"):
                transport.executable("codex", 5)

    def test_all_failed_candidates_retain_diagnostics(self):
        first, second = self.stub("first", "exit 9"), self.stub("second", "exit 7")
        with self.discovery(first, second):
            with self.assertRaisesRegex(RuntimeError, "exited 9.*exited 7"):
                transport.executable("codex", 5)


class RecallTests(unittest.TestCase):
    def exercise(self, remember, replace_session=False):
        original = None

        def participant(binary, work, prompt_file, session, timeout):
            nonlocal original
            fixture = (work / "fixture.txt").read_text().strip()
            if session is None:
                original = fixture
                (work / "reply.txt").write_text(f"READY {original}")
            else:
                self.assertNotEqual(fixture, original)
                self.assertFalse((work / "reply.txt").exists())
                for path in work.iterdir():
                    if path.is_file():
                        self.assertNotIn(original, path.read_text())
            marker = original if remember else fixture
            returned = "replacement-session" if session and replace_session else "original-session"
            return returned, f"READY {marker}"

        with mock.patch.object(transport, "executable", return_value=("stub", "stub 1.0.0")):
            with mock.patch.object(transport, "claude", side_effect=participant):
                with contextlib.redirect_stdout(io.StringIO()):
                    transport.check("claude", 5)

    def test_retained_context_passes_after_fixture_replacement_and_output_removal(self):
        self.exercise(remember=True)

    def test_memoryless_fixture_reader_cannot_pass_resume(self):
        with self.assertRaisesRegex(RuntimeError, "resume: fixture read or retained session context failed"):
            self.exercise(remember=False)

    def test_replacement_session_is_rejected_even_with_correct_marker(self):
        with self.assertRaisesRegex(RuntimeError, "replaced the original session"):
            self.exercise(remember=True, replace_session=True)


if __name__ == "__main__":
    unittest.main()
