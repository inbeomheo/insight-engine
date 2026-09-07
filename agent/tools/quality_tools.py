"""Quality 도구 자동 래핑"""
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
_SERVICE_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "services", "quality")
_HIDDEN_PARAMETERS = frozenset({"model", "on_cost_start"})
_PREFERRED_FUNCTIONS = {"quality_service": "evaluate_quality"}

def _register_tools():
    count = 0
    for _, module_name, _ in pkgutil.iter_modules([_SERVICE_DIR]):
        if module_name.startswith("_"):
            continue
        # Skip already-wrapped modules
        if module_name in _SKIP_MODULES:
            continue
        try:
            mod = importlib.import_module(f"services.quality.{module_name}")
            for name, fn in inspect.getmembers(mod, inspect.isfunction):
                if name.startswith("_") or fn.__module__ != mod.__name__:
                    continue
                preferred_name = _PREFERRED_FUNCTIONS.get(module_name)
                if preferred_name is not None and name != preferred_name:
                    continue
                doc = (fn.__doc__ or "").strip().split("\n")[0][:200] or f"{module_name}"
                sig = inspect.signature(fn)
                params = _build_params_schema(fn)
                param_names = list(sig.parameters.keys())
                accepts_cost_callback = "on_cost_start" in param_names

                def make_handler(func, pnames, accepts_on_cost_start):
                    def handler(args, **kwargs):
                        call_args = {
                            key: args.get(key)
                            for key in pnames
                            if key not in _HIDDEN_PARAMETERS and key in args
                        }
                        on_cost_start = kwargs.get("on_cost_start")
                        if accepts_on_cost_start and callable(on_cost_start):
                            call_args["on_cost_start"] = on_cost_start
                        try:
                            result = func(**call_args)
                            return result if isinstance(result, str) else json.dumps(result, ensure_ascii=False, default=str)
                        except UsageLockUnavailable:
                            raise
                        except Exception:
                            return json.dumps(
                                {"error": TOOL_EXECUTION_ERROR_MESSAGE},
                                ensure_ascii=False,
                            )
                    return handler

                registry.register(
                    name=name, toolset="quality", description=doc,
                    parameters=params,
                    handler=make_handler(
                        fn,
                        param_names,
                        accepts_cost_callback,
                    ),
                )
                count += 1
                break
        except Exception as e:
            logger.debug("quality 모듈 스킵: %s — %s", module_name, e)
    logger.info("Quality 도구 자동 등록: %d개", count)

def _build_params_schema(function_or_signature):
    return build_parameters_schema(
        function_or_signature,
        default_content_description="입력 텍스트",
        excluded_parameters=_HIDDEN_PARAMETERS,
    )

_SKIP_MODULES = set()
_register_tools()
