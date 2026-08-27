"""Export 도구 자동 래핑 — services/export/ 서비스를 Tool로 등록"""
from __future__ import annotations

import importlib
import inspect
import json
import logging
import os
import pkgutil

from agent.registry import TOOL_EXECUTION_ERROR_MESSAGE, registry
from agent.tools._auto_register import build_parameters_schema
from services.usage.usage_lock import UsageLockUnavailable

logger = logging.getLogger(__name__)

_SERVICE_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "services", "export")
_SKIP_MODULES = set()
_TRUSTED_CONTEXT_PARAMETERS = frozenset({"api_key", "on_cost_start"})


def _register_tools():
    count = 0
    for _, module_name, _ in pkgutil.iter_modules([_SERVICE_DIR]):
        if module_name.startswith("_") or module_name in _SKIP_MODULES:
            continue
        try:
            mod = importlib.import_module(f"services.export.{module_name}")
            for name, fn in inspect.getmembers(mod, inspect.isfunction):
                if name.startswith("_") or fn.__module__ != mod.__name__:
                    continue
                doc = (fn.__doc__ or "").strip().split("\n")[0][:200] or module_name
                sig = inspect.signature(fn)
                params = _build_schema(fn)
                pnames = [p for p in sig.parameters if p not in ("self", "cls", "kwargs", "args")]
                accepts_cost_callback = "on_cost_start" in pnames
                accepts_google_docs_key = "api_key" in pnames

                def make_handler(
                    func,
                    pn,
                    accepts_on_cost_start,
                    accepts_server_google_docs_key,
                ):
                    def handler(args, **kw):
                        call_args = {
                            key: args[key]
                            for key in pn
                            if key not in _TRUSTED_CONTEXT_PARAMETERS and key in args
                        }
                        if accepts_server_google_docs_key:
                            api_key = os.getenv("GOOGLE_DOCS_API_KEY", "").strip()
                            if api_key:
                                call_args["api_key"] = api_key
                        on_cost_start = kw.get("on_cost_start")
                        if accepts_on_cost_start and callable(on_cost_start):
                            call_args["on_cost_start"] = on_cost_start
                        try:
                            r = func(**call_args)
                            return r if isinstance(r, str) else json.dumps(r, ensure_ascii=False, default=str)
                        except UsageLockUnavailable:
                            raise
                        except Exception:
                            return json.dumps(
                                {"error": TOOL_EXECUTION_ERROR_MESSAGE},
                                ensure_ascii=False,
                            )
                    return handler

                registry.register(
                    name=name,
                    toolset="export",
                    description=doc,
                    parameters=params,
                    handler=make_handler(
                        fn,
                        pnames,
                        accepts_cost_callback,
                        accepts_google_docs_key,
                    ),
                )
                count += 1
                break  # 모듈당 첫 번째 공개 함수만 등록
        except Exception as e:
            logger.debug("[export] skip: %s — %s", module_name, e)
    logger.info("[Export] tools registered: %d", count)


def _build_schema(function_or_signature):
    return build_parameters_schema(
        function_or_signature,
        excluded_parameters=_TRUSTED_CONTEXT_PARAMETERS,
    )


_register_tools()
