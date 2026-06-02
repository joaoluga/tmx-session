from __future__ import annotations

import argparse

from commands import (
    kill_profiles,
    launch_profiles,
    list_profiles,
    save_session,
    sync_session,
)
from tmux import Tmux
from util import __version__, die


class Args(argparse.Namespace):
    # Defaults are placeholders; argparse populates these at parse time.
    profiles: list[str] = []
    list: bool = False
    kill: bool = False
    save: bool = False
    sync: bool = False
    force_reload: bool = False
    output: str | None = None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tmx",
        description="Create tmux sessions from TOML profiles.",
        epilog="Profiles are read from $TMX_PROFILE_DIR (default: ~/.config/tmux/profiles).",
    )
    _ = parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )
    _ = parser.add_argument(
        "profiles", nargs="*", metavar="PROFILE", help="profile name(s) to launch"
    )
    mode = parser.add_mutually_exclusive_group()
    _ = mode.add_argument(
        "-l", "--list", action="store_true", help="list available profiles"
    )
    _ = mode.add_argument(
        "-k", "--kill", action="store_true", help="kill the session(s) instead"
    )
    _ = mode.add_argument(
        "-s", "--save", action="store_true",
        help="save a running session as a new profile",
    )
    _ = mode.add_argument(
        "-u", "--sync", action="store_true",
        help="sync a running session back into its existing profile",
    )
    _ = parser.add_argument(
        "-o", "--output", metavar="PATH", default=None,
        help="with --save/--sync: write to PATH (a file or directory), or '-' "
             + "for stdout (default: $TMX_PROFILE_DIR/<session>.toml)",
    )
    _ = mode.add_argument(
        "-fr", "--force-reload", action="store_true",
        help="kill the session(s) first, then recreate",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv, namespace=Args())
    tmux = Tmux()

    if args.list:
        list_profiles(tmux)
    elif args.save:
        if len(args.profiles) != 1:
            die("tmx --save requires exactly one session name")
        save_session(tmux, args.profiles[0], args.output)
    elif args.sync:
        if len(args.profiles) != 1:
            die("tmx --sync requires exactly one session name")
        sync_session(tmux, args.profiles[0], args.output)
    elif args.kill:
        if not args.profiles:
            die("tmx -k requires at least one profile")
        kill_profiles(tmux, args.profiles)
    else:
        if not args.profiles:
            die("No profiles specified (try `tmx --list` or `tmx --help`).")
        launch_profiles(tmux, args.profiles, force_reload=args.force_reload)
