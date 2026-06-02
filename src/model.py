from __future__ import annotations

from dataclasses import dataclass, field

from layout import build_layout_string
from tmux import Tmux
from tomlio import as_dict, as_list, opt_int, opt_str, req_str, toml_str
from util import expand


@dataclass(frozen=True, slots=True)
class Pane:
    command: str | None = None
    dir: str | None = None
    size: int | None = None  # percent of the window along the split axis

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> Pane:
        return cls(
            command=opt_str(data, "command"),
            dir=opt_str(data, "dir"),
            size=opt_int(data, "size"),
        )

    def to_toml_lines(self) -> list[str]:
        lines = ["[[windows.panes]]"]
        if self.command is not None:
            lines.append(toml_str("command", self.command))
        if self.dir is not None:
            lines.append(toml_str("dir", self.dir))
        if self.size is not None:
            lines.append(f"size = {self.size}")
        return lines


@dataclass(frozen=True, slots=True)
class Window:
    name: str
    dir: str | None = None
    command: str | None = None
    layout: str | None = None
    split: str | None = None  # "horizontal" | "vertical" — panes sized by percent
    panes: list[Pane] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> Window:
        panes_value = data.get("panes")
        panes = (
            [] if panes_value is None
            else [Pane.from_dict(as_dict(p)) for p in as_list(panes_value)]
        )
        split = opt_str(data, "split")
        if split is not None and split not in ("horizontal", "vertical"):
            raise ValueError("'split' must be 'horizontal' or 'vertical'")
        return cls(
            name=req_str(data, "name"),
            dir=opt_str(data, "dir"),
            command=opt_str(data, "command"),
            layout=opt_str(data, "layout"),
            split=split,
            panes=panes,
        )

    def to_toml_lines(self) -> list[str]:
        lines = ["[[windows]]", toml_str("name", self.name)]
        if self.dir is not None:
            lines.append(toml_str("dir", self.dir))
        if self.command is not None:
            lines.append(toml_str("command", self.command))
        if self.layout is not None:
            lines.append(toml_str("layout", self.layout))
        if self.split is not None:
            lines.append(toml_str("split", self.split))
        for pane in self.panes:
            lines.append("")
            lines.extend(pane.to_toml_lines())
        return lines

    def apply_layout(self, tmux: Tmux, target: str) -> None:
        """Arrange the panes: generated string for `split`, else a raw `layout`.

        `split` wins when both are set — it's the precise, percentage-driven
        path; `layout` is the fallback for named presets or captured strings.
        """
        if self.split:
            width, height = tmux.window_size(target)
            ids = tmux.pane_ids(target)
            # Even split unless every pane states a size.
            even = max(1, round(100 / len(ids)))
            sizes = [p.size if p.size is not None else even for p in self.panes]
            tmux.select_layout(
                target, build_layout_string(self.split, sizes, width, height, ids)
            )
        elif self.layout:
            tmux.select_layout(target, self.layout)

    def build(self, tmux: Tmux, session: str, root: str) -> None:
        """Populate this window (assumes it already exists) via `tmux`."""
        target = f"{session}:{self.name}"

        if self.panes:
            # The first pane is the window itself; its dir is the window's dir.
            first, *rest = self.panes
            if first.command:
                tmux.send_keys(target, first.command)
            for pane in rest:
                tmux.split_window(target, expand(pane.dir, self.dir or root))
                if pane.command:
                    tmux.send_keys(target, pane.command)
            self.apply_layout(tmux, target)
        elif self.command:
            tmux.send_keys(target, self.command)


@dataclass(frozen=True, slots=True)
class Profile:
    session: str
    windows: list[Window]
    root: str = "~"
    on_attach: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> Profile:
        session = req_str(data, "session")
        windows_value = data.get("windows")
        if not windows_value:
            raise ValueError("no windows defined")
        return cls(
            session=session,
            windows=[Window.from_dict(as_dict(w)) for w in as_list(windows_value)],
            root=opt_str(data, "root") or "~",
            on_attach=opt_str(data, "on_attach"),
        )

    def to_toml(self) -> str:
        lines = [toml_str("session", self.session), toml_str("root", self.root)]
        if self.on_attach is not None:
            lines.append(toml_str("on_attach", self.on_attach))
        for window in self.windows:
            lines.append("")
            lines.extend(window.to_toml_lines())
        return "\n".join(lines) + "\n"

    def create(self, tmux: Tmux) -> None:
        """Create the session. No-op if it already exists."""
        if tmux.has_session(self.session):
            print(f"Session '{self.session}' already exists.")
            return

        first, *rest = self.windows
        tmux.new_session(self.session, first.name, expand(first.dir, self.root))
        first.build(tmux, self.session, self.root)

        for win in rest:
            tmux.new_window(self.session, win.name, expand(win.dir, self.root))
            win.build(tmux, self.session, self.root)

        focus = self.on_attach or first.name
        tmux.select_window(f"{self.session}:{focus}")
        print(f"Session '{self.session}' created ({len(self.windows)} windows).")
