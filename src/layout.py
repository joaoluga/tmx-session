from __future__ import annotations

from tmux import PaneInfo


def layout_checksum(body: str) -> str:
    csum = 0
    for ch in body:
        csum = ((csum >> 1) + ((csum & 1) << 15)) & 0xFFFF
        csum = (csum + ord(ch)) & 0xFFFF
    return f"{csum:04x}"


def distribute(sizes: list[int], total: int) -> list[int]:
    """Split `total` cells across panes by percentage, exact to the last cell.

    Rounding remainder lands on the final pane so the parts always sum to
    `total`; every pane keeps at least one cell.
    """
    weight = sum(sizes) or 1
    dims = [max(1, round(size / weight * total)) for size in sizes]
    dims[-1] += total - sum(dims)
    return dims


def build_layout_string(
    split: str, sizes: list[int], width: int, height: int, pane_ids: list[str]
) -> str:
    """Render a tmux layout string for a single-axis split at the given sizes.

    `split` is "horizontal" (panes side by side, `{...}`) or "vertical" (panes
    stacked, `[...]`). One cell per pane divider is reserved along the split
    axis, mirroring how tmux lays panes out.
    """
    horizontal = split == "horizontal"
    span = (width if horizontal else height) - (len(pane_ids) - 1)
    dims = distribute(sizes, span)

    cells: list[str] = []
    offset = 0
    for dim, pane_id in zip(dims, pane_ids):
        if horizontal:
            cells.append(f"{dim}x{height},{offset},0,{pane_id.lstrip('%')}")
        else:
            cells.append(f"{width}x{dim},0,{offset},{pane_id.lstrip('%')}")
        offset += dim + 1

    open_, close = ("{", "}") if horizontal else ("[", "]")
    body = f"{width}x{height},0,0{open_}{','.join(cells)}{close}"
    return f"{layout_checksum(body)},{body}"


def percentages(dims: list[int]) -> list[int]:
    """Cell sizes -> integer percentages that sum to exactly 100."""
    total = sum(dims) or 1
    pct = [round(dim / total * 100) for dim in dims]
    pct[-1] += 100 - sum(pct)
    return pct


def detect_split(panes: list[PaneInfo], width: int, height: int) -> tuple[str, list[int]] | None:
    """Classify a window's panes as a single-axis split, or None if nested.

    A clean left/right or top/bottom row of panes becomes a ("horizontal" |
    "vertical", percentages) pair we can store as readable sizes. Anything that
    doesn't reduce to one axis (nested grids, main-pane layouts) returns None,
    and the caller keeps the exact tmux layout string instead.
    """
    if len(panes) < 2:
        return None
    if all(p.top == 0 and p.height == height for p in panes):
        return "horizontal", percentages([p.width for p in panes])
    if all(p.left == 0 and p.width == width for p in panes):
        return "vertical", percentages([p.height for p in panes])
    return None
