"""Small, read-only ``.env`` loader for local development.

The application only needs to read simple ``KEY=value`` pairs. Keeping that
surface local avoids mutation helpers such as ``set_key`` and ``unset_key``;
this module never rewrites the source file. Production deployments should
inject variables through their runtime instead of relying on a checkout file.
"""
from __future__ import annotations

import os
import re
from pathlib import Path


_ENV_KEY = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _parse_value(raw_value: str) -> str:
    value = raw_value.strip()
    if not value:
        return ""

    if value[0] in {"'", '"'}:
        quote = value[0]
        if len(value) < 2 or value[-1] != quote:
            raise ValueError("unterminated quoted .env value")
        inner = value[1:-1]
        if quote == "'":
            return inner
        # Support common local escapes without shell expansion or command
        # substitution.
        replacements = {
            r"\n": "\n",
            r"\r": "\r",
            r"\t": "\t",
            r'\"': '"',
            r"\\": "\\",
        }
        for escaped, replacement in replacements.items():
            inner = inner.replace(escaped, replacement)
        return inner

    # An inline comment begins only after whitespace. This preserves URL
    # fragments and secret values that legitimately contain ``#``.
    comment = re.search(r"\s+#", value)
    if comment:
        value = value[:comment.start()].rstrip()
    return value


def load_env_file(path: str | os.PathLike[str] = ".env", *, override: bool = False) -> bool:
    """Load a simple UTF-8 env file without ever modifying it.

    Invalid lines are ignored so a local typo does not prevent application
    startup. Existing process variables win unless ``override`` is requested.
    """
    env_path = Path(path)
    try:
        if not env_path.is_file():
            return False
        text = env_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return False

    loaded = False
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip()
        if "=" not in line:
            continue
        key, raw_value = line.split("=", 1)
        key = key.strip()
        if not _ENV_KEY.fullmatch(key):
            continue
        try:
            value = _parse_value(raw_value)
        except ValueError:
            continue
        if override or key not in os.environ:
            os.environ[key] = value
            loaded = True
    return loaded
