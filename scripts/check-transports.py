#!/usr/bin/env python3
"""Opt-in live opening/continuation checks; uses the configured CLI accounts."""

import argparse
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import tempfile
import uuid


def run(command, cwd, timeout, prompt=None):
    with subprocess.Popen(
        command, cwd=cwd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, text=True, start_new_session=True,
    ) as process:
        try:
            stdout, stderr = process.communicate(prompt, timeout=timeout)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGKILL)
            process.communicate()
            raise RuntimeError(
                "timed out; check API networking and CLI session-storage access. "
                "Request launch access through the host approval mechanism; "
                "keep participant permissions read-only."
            ) from None
    if process.returncode:
        # Do not print raw event streams, credentials, or participant reasoning.
        if re.search(r"ENOTFOUND|Could not resolve|Connection error", stderr + stdout):
            reason = "API networking is unavailable"
        elif re.search(r"EPERM|EACCES|Permission denied|Operation not permitted", stderr + stdout):
            reason = "the host denied CLI runtime or session-storage access"
        else:
            reason = "check CLI authentication, model access, and supported flags"
        raise RuntimeError(f"command exited {process.returncode}: {reason}")
    return stdout, stderr


def version(binary, timeout):
    stdout, _ = run([binary, "--version"], Path.cwd(), timeout)
    return stdout.strip()


def executable(name, timeout):
    override = os.environ.get(f"MUZAKERE_{name.upper()}_BIN")
    candidates = [override] if override else [shutil.which(name)]
    if name == "codex" and not override:
        candidates += [
            os.environ.get("CODEX_APP_RUNTIME_CLI_PATH"),
            "/Applications/ChatGPT.app/Contents/Resources/codex-cli/bin/codex",
        ]
    available = []
    failures = []
    for candidate in dict.fromkeys(candidates):
        if not candidate:
            continue
        try:
            if not os.access(candidate, os.X_OK):
                if override:
                    raise RuntimeError("not executable")
                continue
            binary = str(Path(candidate).resolve())
            label = version(binary, timeout)
            match = re.search(r"(\d+)\.(\d+)\.(\d+)([^\s]*)", label)
            if not match:
                raise RuntimeError("unrecognized version output")
            suffix = match[4]
            order = tuple(map(int, match.group(1, 2, 3))) + (
                0 if suffix else 1,
                tuple(map(int, re.findall(r"\d+", suffix))),
            )
        except (OSError, RuntimeError, ValueError) as error:
            if override:
                raise RuntimeError(f"{name} override {candidate}: {error}") from None
            failures.append(f"{candidate}: {error}")
            continue
        available.append((order, binary, label))
    if not available:
        detail = "; ".join(failures) if failures else "none found"
        raise RuntimeError(f"no verified {name} executable found ({detail})")
    for failure in failures:
        print(f"SKIP {name} candidate {failure}", file=sys.stderr)
    _, binary, label = max(available)
    return binary, label


def claude(binary, work, prompt_file, session, timeout):
    command = [
        binary, "-p", "--permission-mode", "plan", "--permission-prompts", "none",
        "--output-format", "json", "--tools", "Read,Grep,Glob",
        "--strict-mcp-config", "--mcp-config", '{"mcpServers":{}}',
        "--settings", '{"disableAllHooks":true}',
    ]
    if session:
        command += ["--resume", session]
    command += [prompt_file.read_text()]
    stdout, _ = run(command, work, timeout)
    try:
        result = json.loads(stdout)
    except ValueError:
        raise RuntimeError("Claude returned invalid JSON") from None
    if result.get("is_error") is not False:
        raise RuntimeError("Claude returned an error result")
    return result.get("session_id"), result.get("result", "")


def parse_codex_header(stderr, work):
    sections = re.split(r"(?m)^user\r?$", stderr, maxsplit=1)
    if len(sections) != 2:
        raise RuntimeError("Codex returned no recognizable run-header boundary")
    fields = {}
    for line in sections[0].splitlines():
        match = re.fullmatch(r"(workdir|sandbox|approval|session id):[ \t]*(.*)", line)
        if match:
            name, value = match.groups()
            if name in fields:
                raise RuntimeError(f"Codex returned duplicate header field: {name}")
            fields[name] = value.strip()
    required = {"workdir", "sandbox", "approval", "session id"}
    if fields.keys() != required or not all(fields.values()):
        raise RuntimeError("Codex returned missing or empty run-header fields")
    if (fields["sandbox"] != "read-only" or fields["approval"] != "never"
            or Path(fields["workdir"]).resolve() != work.resolve()):
        raise RuntimeError("Codex did not confirm read-only access, approvals, and workdir")
    return fields["session id"]


def codex(binary, work, prompt_file, session, timeout):
    output = work / "reply.txt"
    output.unlink(missing_ok=True)
    command = [
        binary, "-c", 'sandbox_mode="read-only"', "--ask-for-approval", "never",
        "exec", "--cd", str(work),
    ]
    command += ["resume", session] if session else ["--sandbox", "read-only"]
    command += ["--skip-git-repo-check", "-o", str(output), "-"]
    _, stderr = run(command, work, timeout, prompt_file.read_text())
    returned = parse_codex_header(stderr, work)
    return returned, output.read_text() if output.exists() else ""


def check(name, timeout):
    binary, label = executable(name, timeout)
    with tempfile.TemporaryDirectory(prefix=f"muzakere-{name}-") as directory:
        work = Path(directory)
        marker = f"fixture-{uuid.uuid4()}"
        (work / "fixture.txt").write_text(marker + "\n")
        prompts = [
            "Read-only transport check. Read fixture.txt independently using a file-reading "
            "tool, remember its marker, and reply exactly READY followed by the marker. "
            "Do not modify files, write a plan, or call another agent.",
            "Read-only continuation check. Without re-reading files, recall the marker "
            "from the previous turn. Reply exactly READY followed by that marker. "
            "Do not modify files or call another agent.",
        ]
        session = None
        for phase, prompt in zip(("open", "resume"), prompts):
            if session:
                (work / "fixture.txt").write_text(f"decoy-{uuid.uuid4()}\n")
                (work / "reply.txt").unlink(missing_ok=True)
            prompt_file = work / f"{phase}.txt"
            prompt_file.write_text(prompt)
            transport = {"claude": claude, "codex": codex}[name]
            returned, reply = transport(binary, work, prompt_file, session, timeout)
            if not isinstance(returned, str) or not returned.strip():
                raise RuntimeError(f"{phase}: missing session handle")
            if session and returned != session:
                raise RuntimeError("resume: the CLI replaced the original session")
            if reply.strip() != f"READY {marker}":
                raise RuntimeError(f"{phase}: fixture read or retained session context failed")
            session = returned
            print(f"PASS {name} {phase} ({label})", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("participant", nargs="?", choices=("all", "claude", "codex"), default="all")
    parser.add_argument("--timeout", type=float, default=120, help="seconds per command (default: 120)")
    args = parser.parse_args()
    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    failed = False
    for name in ("claude", "codex") if args.participant == "all" else (args.participant,):
        try:
            check(name, args.timeout)
        except (RuntimeError, OSError) as error:
            print(f"FAIL {name}: {error}", file=sys.stderr, flush=True)
            failed = True
    return int(failed)


if __name__ == "__main__":
    sys.exit(main())
