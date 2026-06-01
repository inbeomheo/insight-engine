from __future__ import annotations

import os
import sys

from chatmock.cli import main

# ChatMock 1.36 does not advertise GPT-5.5 yet; expose it locally for QA.
try:
    from chatmock import model_registry as _registry
    if not any(spec.public_id == "gpt-5.5" for spec in _registry._MODEL_SPECS):
        _registry._MODEL_SPECS = (
            _registry.ModelSpec(
                public_id="gpt-5.5",
                upstream_id="gpt-5.5",
                aliases=("gpt5.5", "gpt-5.5-latest"),
                allowed_efforts=_registry.DEFAULT_REASONING_EFFORTS,
                variant_efforts=("high", "medium", "low", "minimal"),
            ),
        ) + _registry._MODEL_SPECS
except Exception:
    pass

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

os.environ.setdefault("PYTHONIOENCODING", "utf-8")
os.environ.setdefault("CHATGPT_LOCAL_DEBUG_MODEL", "gpt-5.5")

sys.argv = [
    "chatmock",
    "serve",
    "--host",
    os.getenv("CHATMOCK_HOST", "127.0.0.1"),
    "--port",
    os.getenv("CHATMOCK_PORT", "8000"),
    "--debug-model",
    os.getenv("CHATMOCK_DEBUG_MODEL", "gpt-5.5"),
]

if os.getenv("CHATMOCK_VERBOSE", "").lower() in {"1", "true", "yes", "on"}:
    sys.argv.append("--verbose")

main()
