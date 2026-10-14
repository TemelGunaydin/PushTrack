#!/usr/bin/env python3
"""Real PTY acceptance tests. Run: uv run --no-project --with pyte scripts/test_tui.py"""
import codecs
import fcntl
import json
import os
from pathlib import Path
import pty
import select
import signal
import struct
import subprocess
import sys
import tempfile
import termios
import time

import pyte

BINARY = Path(sys.argv[1] if len(sys.argv) > 1 else "target/debug/pushtrack").resolve()
EVIDENCE = Path(tempfile.mkdtemp(prefix="pushtrack-tui-evidence-"))
print(f"Fresh PTY screen evidence: {EVIDENCE}", flush=True)


def git(path, *args):
    return subprocess.run(
        ["git", "-c", "core.hooksPath=/dev/null", "-c", "commit.gpgsign=false",
         "-c", "user.name=TUI Tests", "-c", "user.email=test@example.invalid", *args],
        cwd=path, check=True, capture_output=True,
    )


class Session:
    def __init__(self, args, env, columns=140, rows=36):
        self.master, self.slave = pty.openpty()
        self.original = termios.tcgetattr(self.slave)
        fcntl.ioctl(self.slave, termios.TIOCSWINSZ, struct.pack("HHHH", rows, columns, 0, 0))
        self.screen = pyte.Screen(columns, rows)
        self.stream = pyte.Stream(self.screen)
        self.decoder = codecs.getincrementaldecoder("utf-8")("replace")
        self.raw = b""
        self.process = subprocess.Popen(
            [str(BINARY), *map(str, args)], stdin=self.slave, stdout=self.slave,
            stderr=self.slave, env=env, start_new_session=True,
        )

    @property
    def text(self):
        return "\n".join(self.screen.display)

    def pump(self, timeout=0.1):
        if select.select([self.master], [], [], timeout)[0]:
            chunk = os.read(self.master, 65536)
            self.raw += chunk
            if b"\x1b[6n" in chunk:
                os.write(self.master, b"\x1b[1;1R")
            self.stream.feed(self.decoder.decode(chunk))

    def wait(self, predicate, timeout=8):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            self.pump()
            if predicate(self.text):
                return
            if self.process.poll() is not None:
                raise AssertionError(f"Exited {self.process.returncode}\n{self.text}")
        raise AssertionError(f"Timed out\n{self.text}")

    def drain_frame(self):
        # A wait predicate may match midway through a multi-write ANSI frame.
        deadline = time.monotonic() + .2
        while time.monotonic() < deadline:
            self.pump(min(.02, max(0, deadline-time.monotonic())))

    def keys(self, keys):
        os.write(self.master, keys)

    def resize(self, columns, rows):
        self.screen.resize(lines=rows, columns=columns)
        fcntl.ioctl(self.slave, termios.TIOCSWINSZ, struct.pack("HHHH", rows, columns, 0, 0))
        os.kill(self.process.pid, signal.SIGWINCH)

    def finish(self, expected, key=b"q", sig=None):
        if sig is not None:
            os.kill(self.process.pid, sig)
        else:
            self.keys(key)
        deadline = time.monotonic() + 4
        while self.process.poll() is None and time.monotonic() < deadline:
            self.pump()
        assert self.process.wait(timeout=1) == expected, self.text
        self.pump()
        assert b"\x1b[?1049h" in self.raw, "Alternate screen not entered"
        assert b"\x1b[?1049l" in self.raw, "Alternate screen not restored"
        assert b"\x1b[?25h" in self.raw, "Cursor not restored"
        assert termios.tcgetattr(self.slave) == self.original, "Raw mode/echo not restored"

    def close(self):
        if self.process.poll() is None:
            # Give owned worker groups a chance to terminate even on failed assertions.
            self.process.send_signal(signal.SIGTERM)
            deadline = time.monotonic() + 6
            while self.process.poll() is None and time.monotonic() < deadline:
                self.pump()
            if self.process.poll() is None:
                self.process.kill()
            self.process.wait()
        os.close(self.master)
        os.close(self.slave)


with tempfile.TemporaryDirectory(prefix="pushtrack-tui-") as temporary:
    root = Path(temporary).resolve()
    projects = root / "projects"
    projects.mkdir()
    paths = [projects / name for name in ["atlas-api", "beacon-web", *[f"project-{i:02}" for i in range(2, 35)]]]
    for path in paths:
        git(root, "init", "--initial-branch=main", str(path))
    (paths[0] / "initial.txt").write_text("initial\n")
    git(paths[0], "add", ".")
    git(paths[0], "commit", "-m", "initial")
    remote = root / "remote.git"
    git(root, "init", "--bare", "--initial-branch=main", str(remote))
    git(paths[0], "remote", "add", "origin", str(remote))
    git(paths[0], "push", "-u", "origin", "main")
    git(paths[1], "remote", "add", "origin", str(remote))
    git(paths[1], "fetch", "origin")
    git(paths[1], "checkout", "-B", "main", "origin/main")
    (paths[1] / "pending.txt").write_text("not pushed\n")
    git(paths[1], "add", ".")
    git(paths[1], "commit", "-m", "pending")
    env = dict(os.environ, XDG_CONFIG_HOME=str(root / "config"), XDG_CACHE_HOME=str(root / "model-cache"), TERM="xterm-256color")
    env.pop("NO_COLOR", None)
    env.pop("GIT_SSH_COMMAND", None)
    env.pop("GIT_SSH", None)

    session = Session([projects, "--watch"], env)
    try:
        session.wait(lambda text: "Last scan" in text and "atlas-api" in text)
        assert b"\x1b[38;2;" in session.raw, "Expected true-color theme"
        (EVIDENCE / "wide.txt").write_text(session.text)
        # Branch history stays synchronized, but the working tree is dirty.
        (paths[0] / "initial.txt").write_text("modified, not committed\n")
        (paths[0] / "staged.txt").write_text("staged, not committed\n")
        git(paths[0], "add", "staged.txt")
        (paths[0] / "untracked.txt").write_text("not staged\n")
        session.keys(b"r")
        session.wait(lambda text: "3 uncommitted" in text and "In sync" in text and "Last scan" in text)
        session.keys(b"\x1b[B")
        session.wait(lambda text: "2 / 35" in text and "1 to push" in text)
        session.keys(b"\x1b[F")
        session.wait(lambda text: "35 / 35" in text and "project-34" in text)
        session.keys(b"\x1b[5~")
        session.wait(lambda text: "35 / 35" not in text)
        session.keys(b"\x1b[H")
        session.wait(lambda text: "1 / 35" in text)
        session.resize(80, 24)
        session.wait(lambda text: "DETAILS" in text and "q quit" in text and "atlas-api" in text)
        time.sleep(0.2)
        session.pump()
        (EVIDENCE / "narrow.txt").write_text(session.text)
        assert "3 uncommitted" in session.text
        session.resize(60, 18)
        session.wait(lambda text: "3 uncommitted" in text and "In sync" in text)
        session.resize(80, 24)
        session.wait(lambda text: "DETAILS" in text and "q quit" in text)
        session.keys(b"\x1b[F")
        session.wait(lambda text: "35 / 35" in text)
        (paths[-1] / "first.txt").write_text("new commit\n")
        git(paths[-1], "add", ".")
        git(paths[-1], "commit", "-m", "first")
        session.keys(b"r")
        session.wait(lambda text: "No upstream" in text and "35 / 35" in text)
        session.keys(b"\t\x1b[F")
        session.wait(lambda text: "Local refs can be stale" in text)
        session.finish(0)
        assert session.raw.count(b"\x1b[?1049h") == 1
    finally:
        session.close()
    print("PASS: dirty-but-synchronized worktree is visible at wide, narrow, and minimum sizes; navigation, refresh, q, terminal restoration")

    for key, sig, expected in [(b"\x03", None, 130), (None, signal.SIGTERM, 143), (None, signal.SIGINT, 130)]:
        session = Session([paths[0], "--watch", "--color", "never"], env, 80, 24)
        try:
            session.wait(lambda text: "Last scan" in text)
            assert b"\x1b[38;2;" not in session.raw and b"\x1b[48;2;" not in session.raw
            session.finish(expected, key=key, sig=sig)
        finally:
            session.close()
    print("PASS: monochrome mode and Ctrl+C/SIGINT/SIGTERM restore terminal state")

    helper = root / "slow-ssh.sh"
    pidfile = root / "ssh.pid"
    helper.write_text(f'echo $$ > "{pidfile}"\nexec sleep 30\n')
    git(paths[0], "config", "core.sshCommand", f"sh '{helper}'")
    git(paths[0], "remote", "set-url", "origin", "ssh://127.0.0.1:1/repo")
    env["GIT_SSH_VARIANT"] = "ssh"
    session = Session([projects, "--fetch", "--watch"], env)
    helper_pid = None
    try:
        session.wait(lambda text: pidfile.exists() and "atlas-api" in text)
        helper_pid = int(pidfile.read_text())
        session.keys(b"\x1b[F")
        session.wait(lambda text: "35 / 35" in text and "project-34" in text, timeout=2)
        session.finish(0)
        time.sleep(0.1)
        try:
            os.kill(helper_pid, 0)
        except ProcessLookupError:
            helper_pid = None
        assert helper_pid is None, "SSH helper survived quit"
    finally:
        session.close()
        if helper_pid is not None:
            try:
                os.kill(helper_pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
    print("PASS: navigation and quit stay responsive during blocked fetch; transport helper is terminated")

    # Actual dashboard flow with fake Python transport; no model inference in this suite.
    repo = root / "draft-repo"
    git(root, "init", "--initial-branch=main", str(repo))
    (repo / "constant.py").write_bytes(b"TIMEOUT = 10\n")
    git(repo, "add", "constant.py")
    (repo / "private-untracked.txt").write_text("SYNTHETIC_UNTRACKED_NOT_SELECTED\n")
    index_before = (repo / ".git/index").read_bytes()
    model = root / "model.gguf"
    server = root / "llama-server"
    model.write_bytes(b"fake fixture")
    server.write_text("#!/bin/sh\nprintf 'version: 0.6.0-dev (build 11429, commit d81235049)\\n'\n")
    server.chmod(0o700)
    captured = root / "received.diff"
    embedded = root / "embedded-local_subject.py"
    fake = root / "fake-python"
    fake.write_text(f'#!/bin/sh\ncp "$5" "{embedded}"\ncat > "{captured}"\nprintf "Add timeout constant\\n"\n')
    fake.chmod(0o700)
    args = [repo, "--watch", "--ai-model", model, "--ai-server", server, "--ai-python", fake]
    session = Session(args, env, 80, 24)
    try:
        session.wait(lambda text: "Last scan" in text)
        assert not captured.exists(), "Model ran during initial scan"
        session.keys(b"m")
        session.wait(lambda text: "Add timeout constant" in text and "English subject" in text)
        assert "Staged changes only" in session.text and "Unstaged/untracked" in session.text
        assert "Review wording" not in session.text
        scope = next((y, row.index("Staged changes only")) for y, row in enumerate(session.screen.display) if "Staged changes only" in row)
        secondary = session.screen.buffer[scope[0]][scope[1]]
        assert secondary.fg == '8192a4' and not secondary.bold, "Scope competes with the primary title"
        brand = next((y, row.index("PUSHTRACK")) for y, row in enumerate(session.screen.display) if "PUSHTRACK" in row)
        background = session.screen.buffer[brand[0]][brand[1]]
        assert background.fg == '8192a4' and not background.bold and not background.reverse, "Modal background retained active status/selection colors"
        (EVIDENCE / 'draft-editing.txt').write_text(session.text)
        assert b"+TIMEOUT = 10" in captured.read_bytes()
        assert b"SYNTHETIC_UNTRACKED" not in captured.read_bytes()
        export = Path(tempfile.mkdtemp(prefix="pushtrack-draft-native-input-"))
        (export / "diff.patch").write_bytes(captured.read_bytes())
        (export / "local_subject.py").write_bytes(embedded.read_bytes())
        session.keys(b"\x15Add configured timeout\r")
        session.wait(lambda text: "Reviewed subject" in text and "Add configured timeout" in text)
        assert (repo / ".git/index").read_bytes() == index_before
        assert (repo / "constant.py").read_bytes() == b"TIMEOUT = 10\n"
        session.keys(b"\x1b")
        session.wait(lambda text: "LOCAL COMMIT DRAFT" not in text)
        session.keys(b"m")
        session.wait(lambda text: "English subject" in text and "Add timeout constant" in text)
        (repo / "constant.py").write_bytes(b"TIMEOUT = 11\n")
        git(repo, "add", "constant.py")
        session.keys(b"\r")
        session.wait(lambda text: "Draft unavailable" in text and "changed" in text)
        rows = session.screen.display
        excluded_y = next(y for y, row in enumerate(rows) if 'Unstaged/untracked excluded.' in row)
        error_y, error_x = next((y, row.index('Draft unavailable')) for y, row in enumerate(rows) if 'Draft unavailable' in row)
        assert error_y > excluded_y + 1, 'Error box touches header'
        assert session.screen.buffer[error_y][error_x].fg == 'dce4ed', 'Error title is not readable'
        (EVIDENCE / 'draft-error-spacing.txt').write_text(session.text)
        assert "Add timeout constant" not in session.text, "Stale subject remained visible"
        session.keys(b"\x1b")
        session.wait(lambda text: "LOCAL COMMIT DRAFT" not in text)
        session.finish(0)
    finally:
        session.close()
    print(f"PASS: on-demand staged-only editable draft, Enter recheck, stale-index refusal, no Git writes; native-input export: {export}")

    # A larger context cannot start until the user explicitly confirms it.
    report = dict(diff_bytes=len(captured.read_bytes()), diff_tokens=2000,
                  prompt_tokens=6000, output_tokens=192, context=4096, suggested_context=8192)
    expanded = root / "expanded-context"
    fake.write_text(f'''#!/bin/sh
cat >/dev/null
last=''
for arg; do last="$arg"; done
if [ "$last" = '4096' ]; then
 printf '%s\\n' '{json.dumps(report)}'
 exit 2
fi
printf '%s' "$last" > "{expanded}"
printf 'Add timeout constant\\n'
''')
    session = Session(args, env, 80, 24)
    try:
        session.wait(lambda text: "Last scan" in text)
        session.keys(b"m")
        session.wait(lambda text: "Complete-input capacity" in text and "Required context: 8192" in text and "Prompt 6000" in text and "Enter approve larger context" in text)
        assert not expanded.exists(), "Large context started without confirmation"
        session.keys(b"\x1b")
        session.wait(lambda text: "LOCAL COMMIT DRAFT" not in text and "Required context: 8192" not in text and "Complete-input capacity" not in text)
        assert not expanded.exists(), "Esc incorrectly confirmed large context"
        session.keys(b"m")
        session.wait(lambda text: "Complete-input capacity" in text and "Required context: 8192" in text and "Prompt 6000" in text and "Enter approve larger context" in text)
        session.keys(b"\r")
        session.wait(lambda text: "English subject" in text and "Add timeout constant" in text)
        assert expanded.read_text() == "8192"
        session.keys(b"\x1b")
        session.wait(lambda text: "LOCAL COMMIT DRAFT" not in text)
        session.finish(0)
    finally:
        session.close()
    print("PASS: full prompt capacity, no automatic context expansion, explicit Enter confirmation and Esc refusal")

    # A labeled timeout is surfaced after explicit expansion, without retry or Git writes.
    calls = root / 'timeout-calls'
    fake.write_text(f'''#!/bin/sh
cat >/dev/null
last=''
for arg; do last="$arg"; done
printf '%s\\n' "$last" >> "{calls}"
if [ "$last" = '4096' ]; then
 printf '%s\\n' '{json.dumps(report)}'
 exit 2
fi
printf '%s\\n' 'Local draft error: Local CPU /completion request timed out (HTTP budget 175.0s; context 8192; total job limit 300s); no draft accepted' >&2
exit 1
''')
    before_timeout_index = (repo / '.git/index').read_bytes()
    session = Session(args, env, 80, 24)
    try:
        session.wait(lambda text: 'Last scan' in text)
        session.keys(b'm')
        session.wait(lambda text: 'Required context: 8192' in text and 'Enter approve larger context' in text)
        assert calls.read_text().splitlines() == ['4096']
        session.keys(b'\r')
        session.wait(lambda text: 'Draft unavailable' in text and '/completion' in text and '300s' in text)
        assert 'context 8192' in session.text and '175.0s' in session.text
        (EVIDENCE / 'expanded-timeout.txt').write_text(session.text)
        session.pump(.2)
        assert calls.read_text().splitlines() == ['4096', '8192'], 'Unexpected automatic retry'
        assert (repo / '.git/index').read_bytes() == before_timeout_index
        session.keys(b'\x1b')
        session.wait(lambda text: 'LOCAL COMMIT DRAFT' not in text)
        session.finish(0)
    finally:
        session.close()
    print('PASS: expanded-context endpoint/budget timeout is visible; no automatic retry or Git writes')

    # The outer owned process group must stop the connector and model descendant on Esc/quit.
    child_pid = root / "model-child.pid"
    fake.write_text(f'#!/bin/sh\ncat >/dev/null\nsleep 60 &\necho $! > "{child_pid}"\nwait\n')
    session = Session(args, env, 80, 24)
    try:
        session.wait(lambda text: "Last scan" in text)
        session.keys(b"m")
        session.wait(lambda text: child_pid.exists() and "Preparing CPU draft" in text)
        pid = int(child_pid.read_text())
        session.keys(b"\x1b")
        session.wait(lambda text: "LOCAL COMMIT DRAFT" not in text, timeout=2)
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            pass
        else:
            raise AssertionError("Model descendant survived cancellation")
        session.finish(0)
    finally:
        session.close()
    print("PASS: Esc cancellation kills owned model descendant and restores responsive dashboard")

    curl_bin = root / "curl-bin"
    curl_bin.mkdir()
    curl_pid = root / "curl-child.pid"
    (curl_bin / "curl").write_text(f'''#!/bin/sh
out=''
while [ $# -gt 0 ]; do
 if [ "$1" = '--output' ]; then out="$2"; shift 2; else shift; fi
done
dd if=/dev/zero bs=1048576 count=1 2>/dev/null >> "$out"
sleep 60 &
echo $! > "{curl_pid}"
wait
''')
    (curl_bin / "curl").chmod(0o700)
    model_env = dict(env, PATH=str(curl_bin) + os.pathsep + env.get("PATH", ""))
    session = Session(args, model_env, 80, 24)
    try:
        session.wait(lambda text: "Last scan" in text)
        session.keys(b"a")
        session.wait(lambda text: "AI MODEL LIBRARY" in text and "Apache-2.0" in text and "GitHub Release" in text)
        session.drain_frame()
        rows=session.screen.display
        primary_y=next(y for y,row in enumerate(rows) if 'AI MODEL LIBRARY' in row)
        source_y=next(y for y,row in enumerate(rows) if 'GitHub Release · source stays local' in row)
        browse_y=next(y for y,row in enumerate(rows) if 'Select a model/source.' in row)
        choice_y,choice_x=next((y,row.index('Existing file · pinned Qwen3.5')) for y,row in enumerate(rows) if 'Existing file · pinned Qwen3.5' in row)
        assert choice_y>primary_y+1 and browse_y>source_y+1, 'Model modal sections are crowded'
        selected=session.screen.buffer[choice_y][choice_x]
        assert selected.fg=='dce4ed' and selected.bg=='1b313c', 'Choice needs a distinct selected style'
        brand_y,brand_x=next((y,row.index('PUSHTRACK')) for y,row in enumerate(rows) if 'PUSHTRACK' in row)
        assert session.screen.buffer[brand_y][brand_x].fg=='8192a4', 'Model modal must dim project dashboard'
        (EVIDENCE/'models-browse.txt').write_text(session.text)
        assert not (root / "model-cache").exists(), "Opening library triggered an install"
        session.keys(b"\x1b[A")
        session.keys(b"d")
        session.wait(lambda text: "Download 2.74GB from GitHub?" in text and 'Enter/D confirm' in text)
        session.drain_frame()
        assert '~7.5GB free disk required' in session.text and 'No model/code executes.' in session.text
        assert not curl_pid.exists(), 'Network action started before confirmation'
        (EVIDENCE/'models-confirm.txt').write_text(session.text)
        session.keys(b"\r")
        session.wait(lambda text: "Downloading" in text and "0.2%" in text and curl_pid.exists())
        session.drain_frame()
        (EVIDENCE/'models-progress.txt').write_text(session.text)
        pid = int(curl_pid.read_text())
        session.keys(b"\x1b")
        session.wait(lambda text: "AI MODEL LIBRARY" not in text)
        partials = list((root / "model-cache").rglob("*.partial"))
        assert len(partials) == 1 and partials[0].stat().st_size == 1048576
        assert not list((root / "model-cache").rglob(".download.lock"))
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            pass
        else:
            raise AssertionError("Download descendant survived Esc cancellation")
        session.finish(0)
    finally:
        session.close()
    print("PASS: model/source selection, explicit download confirmation, real byte progress using fake transport, Esc cleanup/partial retention; no automatic model network action")
