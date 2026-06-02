from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import NoReturn

__version__ = "0.1.0"

PROFILE_DIR = Path(
    os.environ.get("TMX_PROFILE_DIR", Path.home() / ".config" / "tmux" / "profiles")
)

# Foreground commands we treat as "just a shell" — i.e. no command worth saving.
# tmux reports `pane_current_command` as the shell for an idle pane, which is
# noise in a generated profile (the same wall tmuxp's `freeze` hits).
SHELLS = frozenset({"bash", "zsh", "sh", "fish", "dash", "ksh", "tcsh", "csh"})


def die(msg: str, code: int = 1) -> NoReturn:
    print(msg, file=sys.stderr)
    sys.exit(code)


def expand(path: str | None, fallback: str = "~") -> str:
    return os.path.expanduser(path if path else fallback)


def collapse_home(path: str) -> str:
    """Rewrite an absolute path under $HOME back to `~` so profiles stay portable."""
    home = str(Path.home())
    if path == home:
        return "~"
    if path.startswith(home + os.sep):
        return "~" + path[len(home):]
    return path
