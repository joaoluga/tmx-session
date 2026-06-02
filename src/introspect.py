from __future__ import annotations

import os

from layout import detect_split
from model import Pane, Profile, Window
from tmux import Tmux
from util import SHELLS, collapse_home


def profile_from_session(tmux: Tmux, session: str) -> Profile:
    """Introspect a live session into a Profile — the reverse of `create`.

    Single-pane windows collapse to a plain window (dir + optional command). A
    multi-pane window becomes a `split` with per-pane `size` percentages when its
    panes form a single row/column; otherwise it keeps the exact tmux layout
    string. The first pane carries no dir of its own — the window's dir is its
    dir, which mirrors how `build` treats the first pane.
    """
    # The pane running `tmx` reports its own process (python3) as the current
    # command; tmux exports that pane's id as $TMUX_PANE, so we skip it rather
    # than baking the `tmx` invocation itself into the saved profile.
    own_pane = os.environ.get("TMUX_PANE")

    windows: list[Window] = []
    on_attach: str | None = None
    for win in tmux.list_windows(session):
        if win.active:
            on_attach = win.name
        infos = tmux.list_panes(f"{session}:{win.idx}")
        cells = [
            (
                collapse_home(p.path),
                None if (p.command in SHELLS or p.pane_id == own_pane) else p.command,
            )
            for p in infos
        ]
        if len(cells) <= 1:
            pdir, pcmd = cells[0] if cells else ("~", None)
            windows.append(Window(name=win.name, dir=pdir, command=pcmd))
            continue

        detected = detect_split(infos, win.width, win.height)
        sizes = detected[1] if detected else None
        windows.append(
            Window(
                name=win.name,
                dir=cells[0][0],
                layout=None if detected else win.layout,
                split=detected[0] if detected else None,
                panes=[
                    Pane(
                        command=cmd,
                        dir=None if i == 0 else pdir,
                        size=sizes[i] if sizes else None,
                    )
                    for i, (pdir, cmd) in enumerate(cells)
                ],
            )
        )
    return Profile(session=session, windows=windows, on_attach=on_attach)


def window_cells(window: Window) -> list[Pane]:
    """A window's panes as a flat list — a command-style window is one pane."""
    if window.panes:
        return window.panes
    return [Pane(command=window.command, dir=window.dir)]


def merge_command(live: str | None, old: str | None) -> str | None:
    """Reconcile a pane command, defending the profile against weaker live data.

    Two traps, both from tmux's blind spots:
    - an idle pane reports only its shell, so `live` is None — keep the profile's.
    - tmux reports just the program *name* (no args); if that's the same program
      the profile already spells out (`sleep` vs `sleep 999`), keep the fuller
      profile command. Only a genuinely different program replaces it.
    """
    if live is None:
        return old
    if old is None:
        return live
    first = old.split()[0] if old.split() else ""
    return old if live == os.path.basename(first) else live


def merge_pane(live: Pane, old: Pane | None) -> Pane:
    """Live pane wins, but fall back to the profile where live tells us nothing."""
    if old is None:
        return live
    return Pane(
        command=merge_command(live.command, old.command),
        dir=live.dir if live.dir is not None else old.dir,
        size=live.size if live.size is not None else old.size,
    )


def merge_window(old: Window, live: Window) -> Window:
    """Take the live window's structure, back-filling commands from the profile."""
    old_cells = window_cells(old)
    if live.panes:
        merged = [
            merge_pane(lp, old_cells[i] if i < len(old_cells) else None)
            for i, lp in enumerate(live.panes)
        ]
        return Window(
            name=live.name, dir=live.dir or old.dir,
            layout=live.layout, split=live.split, panes=merged,
        )
    cell = merge_pane(Pane(command=live.command, dir=live.dir), old_cells[0] if old_cells else None)
    return Window(name=live.name, dir=cell.dir or old.dir, command=cell.command)


def merge_profile(old: Profile, live: Profile) -> Profile:
    """Update windows present in both, append windows only in the live session.

    Non-destructive: windows you've closed stay in the profile (sync adds and
    updates, never deletes). Profile-level `root`/`on_attach` are preserved —
    they're launch preferences the live session can't reconstruct.
    """
    live_by_name = {w.name: w for w in live.windows}
    old_names = {w.name for w in old.windows}
    windows = [
        merge_window(w, live_by_name[w.name]) if w.name in live_by_name else w
        for w in old.windows
    ]
    windows += [w for w in live.windows if w.name not in old_names]
    return Profile(
        session=old.session,
        windows=windows,
        root=old.root,
        on_attach=old.on_attach or live.on_attach,
    )
