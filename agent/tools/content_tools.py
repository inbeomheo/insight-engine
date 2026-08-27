"""Content 도구 자동 래핑"""
import importlib
import inspect
import json
import logging
import os
import pkgutil
from dataclasses import asdict, is_dataclass

from agent.registry import TOOL_EXECUTION_ERROR_MESSAGE, registry
from agent.tools._auto_register import build_parameters_schema
from services.usage.usage_lock import UsageLockUnavailable

logger = logging.getLogger(__name__)
_SERVICE_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "services", "content")
_USER_SCOPE_PARAMETERS = frozenset({"owner_id", "user_id"})
_TRUSTED_CONTEXT_PARAMETERS = _USER_SCOPE_PARAMETERS | frozenset({
    "model",
    "on_cost_start",
})
_AUTHENTICATION_REQUIRED_ERROR = "[인증 실패] 사용자 데이터 도구는 인증이 필요합니다."


def _register_tools():
    count = 0
    for _, module_name, _ in pkgutil.iter_modules([_SERVICE_DIR]):
        if module_name.startswith("_"):
            continue
        # Skip already-wrapped modules
        if module_name in _SKIP_MODULES:
            continue
        try:
            mod = importlib.import_module(f"services.content.{module_name}")
            for name, fn in inspect.getmembers(mod, inspect.isfunction):
                if name.startswith("_") or fn.__module__ != mod.__name__:
                    continue
                if name in _SKIP_FUNCTIONS.get(module_name, set()):
                    continue
                doc = (fn.__doc__ or "").strip().split("\n")[0][:200] or f"{module_name}"
                sig = inspect.signature(fn)
                params = _build_params_schema(fn)
                param_names = list(sig.parameters.keys())
                user_scope_parameters = tuple(
                    parameter_name
                    for parameter_name in param_names
                    if parameter_name in _USER_SCOPE_PARAMETERS
                )
                accepts_cost_callback = "on_cost_start" in param_names

                def make_handler(
                    func,
                    pnames,
                    scope_parameters,
                    accepts_on_cost_start,
                ):
                    def handler(args, **kwargs):
                        call_args = {
                            key: args.get(key)
                            for key in pnames
                            if key not in _TRUSTED_CONTEXT_PARAMETERS and key in args
                        }
                        if scope_parameters:
                            authenticated_user_id = kwargs.get("user_id")
                            if (
                                not isinstance(authenticated_user_id, str)
                                or not authenticated_user_id.strip()
                            ):
                                return json.dumps(
                                    {"error": _AUTHENTICATION_REQUIRED_ERROR},
                                    ensure_ascii=False,
                                )
                            # Ownership is established by authenticated dispatch
                            # context. Any model-supplied owner/user identifier is
                            # deliberately ignored, even for direct crafted calls.
                            for parameter_name in scope_parameters:
                                call_args[parameter_name] = authenticated_user_id.strip()
                        on_cost_start = kwargs.get("on_cost_start")
                        if accepts_on_cost_start and callable(on_cost_start):
                            call_args["on_cost_start"] = on_cost_start
                        try:
                            result = func(**call_args)
                            if is_dataclass(result):
                                result = asdict(result)
                            return (
                                result
                                if isinstance(result, str)
                                else json.dumps(result, ensure_ascii=False, default=str)
                            )
                        except UsageLockUnavailable:
                            raise
                        except Exception:
                            return json.dumps(
                                {"error": TOOL_EXECUTION_ERROR_MESSAGE},
                                ensure_ascii=False,
                            )
                    return handler

                registry.register(
                    name=name, toolset="content", description=doc,
                    parameters=params,
                    handler=make_handler(
                        fn,
                        param_names,
                        user_scope_parameters,
                        accepts_cost_callback,
                    ),
                )
                count += 1
                break
        except Exception as exc:
            logger.debug(
                "content 모듈 스킵: %s (type=%s)",
                module_name,
                type(exc).__name__,
            )
    logger.info("Content 도구 자동 등록: %d개", count)


def _build_params_schema(function_or_signature):
    return build_parameters_schema(
        function_or_signature,
        default_content_description="입력 텍스트",
        excluded_parameters=_TRUSTED_CONTEXT_PARAMETERS,
    )


_SKIP_MODULES = {"multi_source_collector"}
# 자동 JSON handler가 애플리케이션 dataclass 입력을 복원하지 못하는 함수는
# 노출하지 않는다. quiz 모듈에서는 그 다음 공개 함수인 generate_quiz가 등록돼
# 문자열/숫자 JSON 인자만으로 완전한 퀴즈 결과를 반환한다.
_SKIP_FUNCTIONS = {"quiz_generator_service": {"calculate_results"}}
_register_tools()
