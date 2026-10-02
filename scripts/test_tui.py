#!/usr/bin/env python3
"""Real PTY acceptance tests. Run: uv run --no-project --with pyte scripts/test_tui.py"""
import codecs
import fcntl
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
    env = dict(os.environ, XDG_CONFIG_HOME=str(root / "config"), TERM="xterm-256color")
    env.pop("NO_COLOR", None)
    env.pop("GIT_SSH_COMMAND", None)
    env.pop("GIT_SSH", None)

    session = Session([projects, "--watch"], env)
    try:
        session.wait(lambda text: "Last scan" in text and "atlas-api" in text)
        assert b"\x1b[38;2;" in session.raw, "Expected true-color theme"
        Path("/tmp/pushtrack-tui-wide.txt").write_text(session.text)
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
        Path("/tmp/pushtrack-tui-narrow.txt").write_text(session.text)
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
    print("PASS: alternate screen, arrows, paging, stable selection, resize, detail scrolling, refresh, q, terminal restoration")

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
