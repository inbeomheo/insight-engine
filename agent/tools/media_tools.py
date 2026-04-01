"""Media 도구 자동 래핑"""
import importlib
import inspect
import json
import logging
import os
import pkgutil
from agent.registry import registry

logger = logging.getLogger(__name__)
_SERVICE_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "services", "media")

def _register_tools():
    count = 0
    for _, module_name, _ in pkgutil.iter_modules([_SERVICE_DIR]):
        if module_name.startswith("_"):
            continue
        # Skip already-wrapped modules
        if module_name in _SKIP_MODULES:
            continue
        try:
            mod = importlib.import_module(f"services.media.{module_name}")
            for name, fn in inspect.getmembers(mod, inspect.isfunction):
                if name.startswith("_") or fn.__module__ != mod.__name__:
                    continue
                doc = (fn.__doc__ or "").strip().split("\n")[0][:200] or f"{module_name}"
                sig = inspect.signature(fn)
                params = _build_params_schema(sig)
                param_names = list(sig.parameters.keys())

                def make_handler(func, pnames):
                    def handler(args, **kwargs):
                        call_args = {k: args.get(k) for k in pnames if k in args}
                        try:
                            result = func(**call_args)
                            return result if isinstance(result, str) else json.dumps(result, ensure_ascii=False, default=str)
                        except Exception as e:
                            return json.dumps({"error": str(e)}, ensure_ascii=False)
                    return handler

                registry.register(
                    name=name, toolset="media", description=doc,
                    parameters=params, handler=make_handler(fn, param_names),
                )
                count += 1
                break
        except Exception as e:
            logger.debug("media 모듈 스킵: %s — %s", module_name, e)
    logger.info("Media 도구 자동 등록: %d개", count)

def _build_params_schema(sig):
    props = {}
    required = []
    for pname, param in sig.parameters.items():
        if pname in ("self", "cls", "kwargs", "args"):
            continue
        ann = param.annotation
        ptype = "string"
        if ann == int: ptype = "integer"
        elif ann == float: ptype = "number"
        elif ann == bool: ptype = "boolean"
        props[pname] = {"type": ptype}
        if param.default is inspect.Parameter.empty:
            required.append(pname)
    if not props:
        props = {"content": {"type": "string", "description": "입력 텍스트"}}
        required = ["content"]
    return {"type": "object", "properties": props, "required": required}

_SKIP_MODULES = set()
_register_tools()
