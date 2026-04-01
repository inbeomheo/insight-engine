"""RAG 도구 자동 래핑 — services/rag/ 서비스를 Tool로 등록"""
from __future__ import annotations

import importlib
import inspect
import json
import logging
import os
import pkgutil

from agent.registry import registry

logger = logging.getLogger(__name__)

_SERVICE_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "services", "rag")
_SKIP_MODULES = set()


def _register_tools():
    count = 0
    for _, module_name, _ in pkgutil.iter_modules([_SERVICE_DIR]):
        if module_name.startswith("_") or module_name in _SKIP_MODULES:
            continue
        try:
            mod = importlib.import_module(f"services.rag.{module_name}")
            for name, fn in inspect.getmembers(mod, inspect.isfunction):
                if name.startswith("_") or fn.__module__ != mod.__name__:
                    continue
                doc = (fn.__doc__ or "").strip().split("\n")[0][:200] or module_name
                sig = inspect.signature(fn)
                params = _build_schema(sig)
                pnames = [p for p in sig.parameters if p not in ("self", "cls", "kwargs", "args")]

                def make_handler(func, pn):
                    def handler(args, **kw):
                        try:
                            r = func(**{k: args[k] for k in pn if k in args})
                            return r if isinstance(r, str) else json.dumps(r, ensure_ascii=False, default=str)
                        except Exception as e:
                            return json.dumps({"error": str(e)}, ensure_ascii=False)
                    return handler

                registry.register(
                    name=name,
                    toolset="rag",
                    description=doc,
                    parameters=params,
                    handler=make_handler(fn, pnames),
                )
                count += 1
                break  # 모듈당 첫 번째 공개 함수만 등록
        except Exception as e:
            logger.debug("[rag] skip: %s — %s", module_name, e)
    logger.info("[RAG] tools registered: %d", count)


def _build_schema(sig):
    props, req = {}, []
    for pname, param in sig.parameters.items():
        if pname in ("self", "cls", "kwargs", "args"):
            continue
        ann = param.annotation
        t = "string"
        if ann == int:
            t = "integer"
        elif ann == float:
            t = "number"
        elif ann == bool:
            t = "boolean"
        props[pname] = {"type": t}
        if param.default is inspect.Parameter.empty:
            req.append(pname)
    if not props:
        props = {"content": {"type": "string"}}
        req = ["content"]
    return {"type": "object", "properties": props, "required": req}


_register_tools()
