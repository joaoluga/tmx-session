# tmx — Tmux Session Manager

[![Version](https://img.shields.io/github/v/tag/joaoluga/tmx?label=version&sort=semver&color=blue)](https://github.com/joaoluga/tmx/tags)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![tmux](https://img.shields.io/badge/tmux-required-1BB91F?logo=tmux&logoColor=white)](https://github.com/tmux/tmux)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

A lightweight, dependency-free Python CLI that builds tmux sessions from JSON profiles. Describe your windows, panes, and commands once, then launch a full working environment with a single command.

- **No dependencies** — just Python 3 and tmux.
- **Declarative** — sessions are plain JSON, easy to version and share.
- **Idempotent** — re-running attaches to an existing session instead of
  duplicating it.

## Requirements

| Dependency | Version | Notes |
| ---------- | ------- | ----- |
| [Python](https://www.python.org/) | 3.10+ | Standard library only — **no pip packages** to install. Uses `dataclass(slots=True)`, which requires 3.10. |
| [tmux](https://github.com/tmux/tmux) | any recent | The `tmux` binary must be on your `PATH`. |

The commands inside your profiles (e.g. `nvim`, `git`, `lazygit`) are yours to provide — `tmx` just launches whatever you put in them.

## Install

```bash
git clone https://github.com/joaoluga/tmx.git
cd tmx
```

### With make

```bash
make install            # install the `tmx` script to ~/.local/bin
make install-profiles   # copy the example profile to ~/.config/tmux/profiles
make install-all        # do both
```

Override the locations if you like:

```bash
make install PREFIX=/usr/local                  # -> /usr/local/bin/tmx
make install-profiles PROFILE_DIR=~/my/profiles
```

Make sure the chosen bin directory is on your `PATH`. `make help` lists every target, and `make uninstall` removes the script (your profiles are left untouched).

### Manual

```bash
install -Dm755 tmx ~/.local/bin/tmx
mkdir -p ~/.config/tmux/profiles
cp profiles/*.json ~/.config/tmux/profiles/
```

## Usage

```bash
tmx dev               # create + attach to the "dev" session
tmx dev music         # launch multiple profiles, attach to the first
tmx -fr dev           # force-reload: kill the session, then recreate it
tmx -l                # list available profiles
tmx -k dev            # kill a running session
tmx -h                # help
```

- If a session already exists, `tmx` **attaches** to it instead of recreating.
- When run from **inside** tmux, it uses `switch-client` instead of `attach`.
- Launching several profiles creates them all up front and attaches to the
  first one; the rest keep running in the background.

## Profiles

Profiles are JSON files read from `~/.config/tmux/profiles/`. Set the `TMX_PROFILE_DIR` environment variable to read them from somewhere else:

```bash
TMX_PROFILE_DIR=~/dotfiles/tmux/profiles tmx dev
```

A complete, runnable example ships in [`profiles/example.json`](profiles/example.json) — copy it and adapt it to your own tools.

### Schema

```json
{
  "session": "name",
  "root": "~/default/dir",
  "on_attach": "window-to-focus",
  "windows": [
    {
      "name": "editor",
      "dir": "~/override/dir",
      "command": "nvim"
    },
    {
      "name": "git",
      "panes": [{ "command": null }, { "command": "lazygit" }],
      "layout": "even-horizontal"
    }
  ]
}
```

| Field                       | Required | Description                                                                                  |
| --------------------------- | -------- | -------------------------------------------------------------------------------------------- |
| `session`                   | yes      | Tmux session name                                                                            |
| `root`                      | no       | Default working directory (default: `~`)                                                     |
| `on_attach`                 | no       | Window to focus after creation (default: first window)                                       |
| `windows`                   | yes      | List of windows (at least one)                                                               |
| `windows[].name`            | yes      | Window name                                                                                  |
| `windows[].dir`             | no       | Working directory (inherits `root`)                                                          |
| `windows[].command`         | no       | Command to run (`null` / omitted = plain shell)                                              |
| `windows[].panes`           | no       | Split into panes (takes precedence over `command`)                                           |
| `windows[].panes[].command` | no       | Pane command (`null` = plain shell)                                                          |
| `windows[].panes[].dir`     | no       | Pane directory (inherits the window's dir)                                                   |
| `windows[].layout`          | no       | Tmux layout: `even-horizontal`, `even-vertical`, `main-horizontal`, `main-vertical`, `tiled` |

**Notes**

- The first pane of a `panes` window is the window itself; its directory is the window's `dir`/`root` (a `dir` set on the first pane is ignored).
- If a window defines both `panes` and `command`, `panes` wins.

## Adding a profile

Drop a new JSON file into your profile directory and run it:

```bash
cat > ~/.config/tmux/profiles/work.json << 'EOF'
{
  "session": "work",
  "root": "~/code/work",
  "windows": [
    { "name": "code", "command": "nvim" },
    { "name": "shell" }
  ]
}
EOF

tmx work
```

If you manage your dotfiles separately, keep the source profiles in your dotfiles repo and either symlink them into `~/.config/tmux/profiles/` or point `TMX_PROFILE_DIR` at them.

## Project layout

```
tmx-session/
├── tmx                 # the session manager (Python 3, no deps)
├── Makefile            # install / uninstall targets
├── profiles/
│   └── example.json    # example profile
├── README.md
└── LICENSE
```

## Tips & integration

- **tmux-resurrect / continuum**: `tmx` creates sessions explicitly while continuum auto-saves/restores on tmux start — they complement each other.
- **Auto-launch on login** (e.g. Hyprland): `exec-once = kitty tmx dev`.

## License

[MIT](LICENSE)
