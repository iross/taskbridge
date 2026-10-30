"""Real fzf, driven through a pseudo-terminal, honours the backlog link picker keys."""

import fcntl
import os
import pty
import select
import shlex
import shutil
import struct
import termios
import time

import pytest

from taskbridge.main import fzf_args

pytestmark = pytest.mark.skipif(shutil.which("fzf") is None, reason="fzf not installed")

ESC, ENTER = "\x1b", "\r"
LINES = ["alpha", "xray", "kilo"]


def _drain(fd: int, seconds: float) -> None:
    deadline = time.monotonic() + seconds
    while (left := deadline - time.monotonic()) > 0:
        ready, _, _ = select.select([fd], [], [], left)
        if ready:
            try:
                os.read(fd, 65536)
            except OSError:
                return


def drive(tmp_path, args: list[str], keys: list[str]) -> tuple[int, list[str]]:
    """Run fzf on LINES in a 40x120 pty, type `keys`; return (exit code, chosen lines)."""
    source, chosen = tmp_path / "in.txt", tmp_path / "out.txt"
    source.write_text("\n".join(LINES) + "\n")
    command = f"{shlex.join(args)} < {shlex.quote(str(source))} > {shlex.quote(str(chosen))}"
    pid, fd = pty.fork()
    if pid == 0:
        os.execvp("sh", ["sh", "-c", command])
    fcntl.ioctl(fd, termios.TIOCSWINSZ, struct.pack("HHHH", 40, 120, 0, 0))
    _drain(fd, 0.8)
    for key in keys:
        os.write(fd, key.encode())
        _drain(fd, 0.4)
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        done, status = os.waitpid(pid, os.WNOHANG)
        if done:
            os.close(fd)
            return os.waitstatus_to_exitcode(status), chosen.read_text().splitlines()
        _drain(fd, 0.1)
    os.kill(pid, 9)
    pytest.fail(f"fzf still running after keys {keys!r}")


@pytest.fixture
def multi():
    return fzf_args(prompt="> ", multi=True, browse_keys=True)


@pytest.fixture
def single():
    return fzf_args(prompt="> ", browse_keys=True)


def test_j_moves_and_x_marks_several(tmp_path, multi):
    assert drive(tmp_path, multi, ["j", "x", "j", "x", ENTER]) == (0, ["xray", "kilo"])


def test_x_unmarks_and_k_moves_up(tmp_path, multi):
    keys = ["x", "j", "x", "k", "x", ENTER]
    assert drive(tmp_path, multi, keys) == (0, ["xray"])


def test_enter_without_marks_takes_current(tmp_path, multi):
    assert drive(tmp_path, multi, ["j", "j", "k", ENTER]) == (0, ["xray"])


def test_slash_searches_and_keys_are_typed_while_searching(tmp_path, multi):
    assert drive(tmp_path, multi, ["/", "x", ENTER]) == (0, ["xray"])
    assert drive(tmp_path, multi, ["/", "k", "i", ENTER]) == (0, ["kilo"])


def test_esc_while_searching_returns_to_browsing_keeping_filter(tmp_path, multi):
    exit_code, chosen = drive(tmp_path, multi, ["/", "k", "i", ESC, "x", ENTER])
    assert (exit_code, chosen) == (0, ["kilo"])


def test_esc_while_browsing_cancels(tmp_path, multi):
    exit_code, chosen = drive(tmp_path, multi, ["j", "x", ESC])
    assert exit_code != 0
    assert chosen == []


def test_single_picker_ignores_x(tmp_path, single):
    assert drive(tmp_path, single, ["x", "j", ENTER]) == (0, ["xray"])
