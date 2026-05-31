# tmx — Tmux Session Manager

[![Version](https://img.shields.io/github/v/tag/joaoluga/tmx-session?label=version&sort=semver&color=blue)](https://github.com/joaoluga/tmx-session/tags)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![tmux](https://img.shields.io/badge/tmux-required-1BB91F?logo=tmux&logoColor=white)](https://github.com/tmux/tmux)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

A lightweight, dependency-free Python CLI that builds tmux sessions from TOML profiles. Describe your windows, panes, and commands once, then launch a full working environment with a single command.

- **No dependencies** — just Python 3 and tmux.
- **Declarative** — sessions are plain TOML, easy to version and share.
- **Idempotent** — re-running attaches to an existing session instead of
  duplicating it.

## Requirements

| Dependency                           | Version    | Notes                                                                                                    |
| ------------------------------------ | ---------- | -------------------------------------------------------------------------------------------------------- |
| [Python](https://www.python.org/)    | 3.11+      | Standard library only — **no pip packages** to install. Uses `tomllib` (added in 3.11) to read profiles. |
| [tmux](https://github.com/tmux/tmux) | any recent | The `tmux` binary must be on your `PATH`.                                                                |

The commands inside your profiles (e.g. `nvim`, `git`, `lazygit`) are yours to provide — `tmx` just launches whatever you put in them.

## Install

```bash
git clone https://github.com/joaoluga/tmx-session.git
cd tmx-session
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
cp profiles/*.toml ~/.config/tmux/profiles/
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

Profiles are TOML files read from `~/.config/tmux/profiles/`. Set the `TMX_PROFILE_DIR` environment variable to read them from somewhere else:

```bash
TMX_PROFILE_DIR=~/dotfiles/tmux/profiles tmx dev
```

A complete, runnable example ships in [`profiles/example.toml`](profiles/example.toml) — copy it and adapt it to your own tools.

### Schema

```toml
session = "name"
root = "~/default/dir"          # optional (default: ~)
on_attach = "window-to-focus"   # optional (default: first window)

[[windows]]
name = "editor"
dir = "~/override/dir"          # optional (inherits root)
command = "nvim"

[[windows]]
name = "git"
layout = "even-horizontal"
  [[windows.panes]]             # first pane = the window itself
  [[windows.panes]]
  command = "lazygit"
```

| Field                       | Required | Description                                                                                  |
| --------------------------- | -------- | -------------------------------------------------------------------------------------------- |
| `session`                   | yes      | Tmux session name                                                                            |
| `root`                      | no       | Default working directory (default: `~`)                                                     |
| `on_attach`                 | no       | Window to focus after creation (default: first window)                                       |
| `windows`                   | yes      | List of windows (at least one)                                                               |
| `windows[].name`            | yes      | Window name                                                                                  |
| `windows[].dir`             | no       | Working directory (inherits `root`)                                                          |
| `windows[].command`         | no       | Command to run (omit for a plain shell)                                                      |
| `windows[].panes`           | no       | Split into panes (takes precedence over `command`)                                           |
| `windows[].panes[].command` | no       | Pane command (omit for a plain shell)                                                        |
| `windows[].panes[].dir`     | no       | Pane directory (inherits the window's dir)                                                   |
| `windows[].layout`          | no       | Tmux layout: `even-horizontal`, `even-vertical`, `main-horizontal`, `main-vertical`, `tiled` |

**Notes**

- The first pane of a `panes` window is the window itself; its directory is the window's `dir`/`root` (a `dir` set on the first pane is ignored).
- If a window defines both `panes` and `command`, `panes` wins.

## Adding a profile

Drop a new TOML file into your profile directory and run it:

```bash
cat > ~/.config/tmux/profiles/work.toml << 'EOF'
session = "work"
root = "~/code/work"

[[windows]]
name = "code"
command = "nvim"

[[windows]]
name = "shell"
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
│   └── example.toml    # example profile
├── README.md
└── LICENSE
```

## Tips & integration

### Synergy with tmux-resurrect / continuum

`tmx` and [tmux-resurrect](https://github.com/tmux-plugins/tmux-resurrect) / [tmux-continuum](https://github.com/tmux-plugins/tmux-continuum) solve **different halves** of the same problem, and pair naturally:

- **`tmx` is the declarative layout** — _what a session should look like from scratch_: which windows, panes, working directories, and startup commands. It's version-controlled TOML you can share and reproduce on any machine.
- **resurrect / continuum is the runtime state** — _what was actually running last time_: the live processes, pane contents, and cursor positions, which continuum autosaves on an interval and restores when the tmux server starts.

A typical workflow:

1. Define your sessions once as profiles and launch them with `tmx dev`.
2. Work normally — continuum keeps autosaving in the background.
3. After a reboot, continuum restores the sessions automatically; running `tmx dev` again just **reattaches** (it's idempotent), so the same command works whether the session is brand new or being resumed.

In short: `tmx` gives you a clean, repeatable starting point; resurrect/continuum preserve the state you build up on top of it.

### Auto-launch on login

Start a profile automatically from your compositor or login shell, e.g. Hyprland:

```ini
exec-once = env -u TMUX kitty ~/.local/bin/tmx dev
```

## Roadmap

Ideas for future versions — the project is intentionally small, so these stay optional and opt-in:

- [ ] **Generate a profile from a running session** — introspect a live tmux session that doesn't have a profile yet and write out the matching TOML (e.g. `tmx --save dev`), so ad-hoc sessions can be captured without hand-writing a profile.
- [ ] **Sync session changes back into a profile** — when you add a window, pane, or command during a session and want to keep it, update the existing profile to match on demand, instead of editing the file by hand.

## License

[MIT](LICENSE)
