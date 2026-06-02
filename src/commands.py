from __future__ import annotations

import difflib
import sys
import tomllib
from pathlib import Path

from introspect import merge_profile, profile_from_session
from model import Profile
from tmux import Tmux
from tomlio import read_toml
from util import PROFILE_DIR, die, expand


def load_profile(name: str) -> Profile:
    path = PROFILE_DIR / f"{name}.toml"
    if not path.exists():
        die(f"Profile not found: {path}")
    try:
        return Profile.from_dict(read_toml(path))
    except tomllib.TOMLDecodeError as e:
        die(f"Invalid TOML in {path}: {e}")
    except ValueError as e:
        die(f"Profile '{name}': {e}")


def save_session(tmux: Tmux, name: str, output: str | None = None) -> None:
    if not tmux.has_session(name):
        die(f"No such session: {name}")
    profile = profile_from_session(tmux, name)
    toml = profile.to_toml()

    # `-o -` prints to stdout — the escape hatch when the profiles dir is
    # read-only (e.g. deployed by home-manager), so you can redirect it into a
    # source repo instead.
    if output == "-":
        _ = sys.stdout.write(toml)
        return

    path = Path(expand(output)) if output else PROFILE_DIR / f"{name}.toml"
    if path.is_dir():
        path = path / f"{name}.toml"
    if path.exists():
        die(f"Profile already exists: {path} (refusing to overwrite)")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        _ = path.write_text(toml)
    except OSError as e:
        die(
            f"Could not write {path}: {e.strerror}\n"
            + f"The profiles dir may be read-only — try `tmx --save {name} -o -` "
            + "to print to stdout, or `-o <path>` to pick a destination."
        )
    print(f"Saved session '{name}' -> {path} ({len(profile.windows)} window(s)).")


def sync_session(tmux: Tmux, name: str, output: str | None = None) -> None:
    if not tmux.has_session(name):
        die(f"No such session: {name}")
    path = PROFILE_DIR / f"{name}.toml"
    if not path.exists():
        die(f"No profile to sync: {path} (use `tmx --save {name}` to create one)")
    try:
        old = Profile.from_dict(read_toml(path))
    except tomllib.TOMLDecodeError as e:
        die(f"Invalid TOML in {path}: {e}")
    except ValueError as e:
        die(f"Profile '{name}': {e}")

    merged = merge_profile(old, profile_from_session(tmux, name))
    if merged == old:
        print(f"Profile '{name}' already matches the session — nothing to sync.")
        return
    new_toml = merged.to_toml()

    if output == "-":
        _ = sys.stdout.write(new_toml)
        return

    # Diff the *semantic* TOML (old profile re-emitted vs merged) so the preview
    # shows real structural changes, not the comment stripping that any rewrite
    # incurs — tomllib can't preserve comments.
    _ = sys.stdout.writelines(difflib.unified_diff(
        old.to_toml().splitlines(keepends=True),
        new_toml.splitlines(keepends=True),
        fromfile=f"{name}.toml", tofile=f"{name}.toml (synced)",
    ))

    dest = Path(expand(output)) if output else path
    if dest.is_dir():
        dest = dest / f"{name}.toml"
    try:
        if dest == path:  # in-place: keep a backup, since comments are dropped
            _ = path.with_suffix(".toml.bak").write_text(path.read_text())
        dest.parent.mkdir(parents=True, exist_ok=True)
        _ = dest.write_text(new_toml)
    except OSError as e:
        die(
            f"Could not write {dest}: {e.strerror}\n"
            + f"The profiles dir may be read-only — try `tmx --sync {name} -o -` "
            + "to print to stdout, or `-o <path>` to pick a destination."
        )

    old_by_name = {w.name: w for w in old.windows}
    added = sum(1 for w in merged.windows if w.name not in old_by_name)
    updated = sum(
        1 for w in merged.windows
        if w.name in old_by_name and w != old_by_name[w.name]
    )
    summary = f"Synced session '{name}' -> {dest} ({added} added, {updated} updated)."
    if dest == path:
        summary += f" Backup: {path.with_suffix('.toml.bak')} (comments not preserved)."
    print(summary)


def list_profiles(tmux: Tmux) -> None:
    if not PROFILE_DIR.exists():
        die(f"No profiles directory: {PROFILE_DIR}")
    paths = sorted(PROFILE_DIR.glob("*.toml"))
    if not paths:
        print("No profiles found.")
        return
    for p in paths:
        try:
            profile = Profile.from_dict(read_toml(p))
        except (tomllib.TOMLDecodeError, ValueError) as e:
            print(f"  {p.stem:16s}  <invalid: {e}>")
            continue
        active = " (active)" if tmux.has_session(profile.session) else ""
        n_win = len(profile.windows)
        print(f"  {p.stem:16s}  {n_win} window(s)  session: {profile.session}{active}")


def kill_profiles(tmux: Tmux, names: list[str]) -> None:
    for name in names:
        session = load_profile(name).session
        if tmux.has_session(session):
            tmux.kill_session(session)
            print(f"Session '{session}' killed.")
        else:
            print(f"Session '{session}' not running.")


def launch_profiles(tmux: Tmux, names: list[str], force_reload: bool = False) -> None:
    created: list[str] = []
    for name in names:
        profile = load_profile(name)
        if force_reload:
            tmux.kill_session_quiet(profile.session)
        profile.create(tmux)
        created.append(profile.session)

    # Attach once, to the first requested session. Creating every session up
    # front (rather than attaching after each) is what lets `tmx a b c` work
    # from outside tmux, where `attach` takes over the terminal.
    if created:
        tmux.attach(created[0])
