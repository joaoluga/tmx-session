from __future__ import annotations

import tomllib
from pathlib import Path
from typing import cast


def read_toml(path: Path) -> dict[str, object]:
    with path.open("rb") as f:
        return cast(dict[str, object], tomllib.load(f))


def as_dict(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ValueError("expected a table")
    return cast(dict[str, object], value)


def as_list(value: object) -> list[object]:
    if not isinstance(value, list):
        raise ValueError("expected an array")
    return cast(list[object], value)


def opt_str(data: dict[str, object], key: str) -> str | None:
    value = data.get(key)
    if value is not None and not isinstance(value, str):
        raise ValueError(f"'{key}' must be a string")
    return value


def req_str(data: dict[str, object], key: str) -> str:
    value = opt_str(data, key)
    if value is None:
        raise ValueError(f"missing '{key}'")
    return value


def opt_int(data: dict[str, object], key: str) -> int | None:
    value = data.get(key)
    # tomllib decodes TOML booleans as bool, a subclass of int — reject them.
    if value is not None and (isinstance(value, bool) or not isinstance(value, int)):
        raise ValueError(f"'{key}' must be an integer")
    return value


def toml_str(key: str, value: str) -> str:
    """Render `key = "value"` as a TOML basic string (zero-dep, our schema only).

    Our profiles only ever hold strings, so a basic-string escaper is all the
    emitting we need — no `tomli-w` dependency. Covers the escapes TOML requires
    inside a basic string.
    """
    escaped = (
        value.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\n", "\\n")
        .replace("\t", "\\t")
        .replace("\r", "\\r")
    )
    return f'{key} = "{escaped}"'
