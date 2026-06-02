from __future__ import annotations

import os
import subprocess
from typing import NamedTuple


class WindowInfo(NamedTuple):
    idx: str
    name: str
    layout: str
    active: bool
    width: int
    height: int


class PaneInfo(NamedTuple):
    path: str
    command: str
    left: int
    top: int
    width: int
    height: int
    pane_id: str


class Tmux:
    """Thin wrapper around the `tmux` command — the only I/O boundary."""

    def _run(self, *args: str) -> None:
        _ = subprocess.run(["tmux", *args], check=True)

    def _ok(self, *args: str) -> bool:
        return subprocess.run(["tmux", *args], capture_output=True).returncode == 0

    def has_session(self, name: str) -> bool:
        return self._ok("has-session", "-t", name)

    def new_session(self, name: str, window: str, cwd: str) -> None:
        self._run("new-session", "-d", "-s", name, "-n", window, "-c", cwd)

    def new_window(self, session: str, name: str, cwd: str) -> None:
        self._run("new-window", "-t", session, "-n", name, "-c", cwd)

    def split_window(self, target: str, cwd: str) -> None:
        self._run("split-window", "-t", target, "-c", cwd)

    def send_keys(self, target: str, keys: str) -> None:
        self._run("send-keys", "-t", target, keys, "Enter")

    def select_layout(self, target: str, layout: str) -> None:
        self._run("select-layout", "-t", target, layout)

    def select_window(self, target: str) -> None:
        self._run("select-window", "-t", target)

    def kill_session(self, name: str) -> None:
        self._run("kill-session", "-t", name)

    def kill_session_quiet(self, name: str) -> None:
        _ = self._ok("kill-session", "-t", name)

    def attach(self, name: str) -> None:
        # `switch-client` from inside tmux, `attach` otherwise (the latter takes
        # over the terminal, which is why callers create every session first).
        if os.environ.get("TMUX"):
            self._run("switch-client", "-t", name)
        else:
            self._run("attach", "-t", name)

    def _capture(self, *args: str) -> str:
        return subprocess.run(
            ["tmux", *args], capture_output=True, text=True, check=True
        ).stdout

    def list_windows(self, session: str) -> list[WindowInfo]:
        """One WindowInfo per window, in index order."""
        fmt = "\t".join((
            "#{window_index}", "#{window_name}", "#{window_layout}",
            "#{window_active}", "#{window_width}", "#{window_height}",
        ))
        rows: list[WindowInfo] = []
        for line in self._capture("list-windows", "-t", session, "-F", fmt).splitlines():
            index, name, layout, active, width, height = line.split("\t")
            rows.append(WindowInfo(
                index, name, layout, active == "1", int(width), int(height)
            ))
        return rows

    def list_panes(self, target: str) -> list[PaneInfo]:
        """One PaneInfo per pane, in pane-index order."""
        fmt = "\t".join((
            "#{pane_current_path}", "#{pane_current_command}",
            "#{pane_left}", "#{pane_top}", "#{pane_width}", "#{pane_height}",
            "#{pane_id}",
        ))
        rows: list[PaneInfo] = []
        for line in self._capture("list-panes", "-t", target, "-F", fmt).splitlines():
            path, command, left, top, width, height, pane_id = line.split("\t")
            rows.append(PaneInfo(
                path, command, int(left), int(top), int(width), int(height), pane_id
            ))
        return rows

    def window_size(self, target: str) -> tuple[int, int]:
        out = self._capture("display", "-p", "-t", target, "#{window_width}\t#{window_height}")
        width, height = out.strip().split("\t")
        return int(width), int(height)

    def pane_ids(self, target: str) -> list[str]:
        """Pane ids (`%N`) for the window, in pane-index order."""
        return self._capture("list-panes", "-t", target, "-F", "#{pane_id}").split()
