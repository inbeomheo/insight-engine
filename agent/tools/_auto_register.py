"""서비스 모듈의 공개 함수를 에이전트 도구로 등록하는 공통 헬퍼."""
from __future__ import annotations

import importlib
import inspect
import json
import logging
import pkgutil
from collections.abc import Iterable
from types import ModuleType
from typing import Any, Callable, Dict, List

from agent.registry import ToolRegistry, registry


_SKIPPED_PARAMETER_NAMES = {"self", "cls", "args", "kwargs"}
_TYPE_MAP = {
    str: "string",
    int: "integer",
    float: "number",
    bool: "boolean",
    list: "array",
    dict: "object",
}


def _resolve_json_type(annotation: Any) -> str:
    """Python 타입 어노테이션을 기본 JSON Schema 타입으로 변환합니다."""
    if annotation in _TYPE_MAP:
        return _TYPE_MAP[annotation]

    origin = getattr(annotation, "__origin__", None)
    if origin in _TYPE_MAP:
        return _TYPE_MAP[origin]

    annotation_text = str(annotation).lower()
    if "list" in annotation_text or "sequence" in annotation_text:
        return "array"
    if "dict" in annotation_text or "mapping" in annotation_text:
        return "object"
    if annotation_text in {"int", "<class 'int'>"}:
        return "integer"
    if annotation_text in {"float", "<class 'float'>"}:
        return "number"
    if annotation_text in {"bool", "<class 'bool'>"}:
        return "boolean"
    return "string"


def build_params_schema(
    signature: inspect.Signature,
    *,
    default_content_description: str | None = None,
) -> Dict[str, Any]:
    """함수 시그니처를 OpenAI 호환 JSON Schema로 변환합니다."""
    properties: Dict[str, Any] = {}
    required: List[str] = []

    for name, parameter in signature.parameters.items():
        if name in _SKIPPED_PARAMETER_NAMES or parameter.kind in {
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        }:
            continue

        json_type = _resolve_json_type(parameter.annotation)
        property_schema: Dict[str, Any] = {"type": json_type}
        if json_type == "array":
            property_schema["items"] = {"type": "string"}
        properties[name] = property_schema
        if parameter.default is inspect.Parameter.empty:
            required.append(name)

    if not properties:
        content_schema: Dict[str, Any] = {"type": "string"}
        if default_content_description:
            content_schema["description"] = default_content_description
        properties = {"content": content_schema}
        required = ["content"]

    return {"type": "object", "properties": properties, "required": required}


def find_main_function(module: ModuleType) -> Callable[..., Any] | None:
    """모듈에서 직접 정의된 첫 번째 공개 함수를 찾습니다."""
    for name, function in inspect.getmembers(module, inspect.isfunction):
        if not name.startswith("_") and function.__module__ == module.__name__:
            return function
    return None


def make_handler(
    function: Callable[..., Any],
    parameter_names: Iterable[str],
    *,
    logger: logging.Logger,
    toolset: str,
) -> Callable[..., str]:
    """레지스트리 호출 규약에 맞는 안전한 동기 핸들러를 생성합니다."""
    names = tuple(parameter_names)

    def handler(args: dict, **_kwargs: Any) -> str:
        call_args = {name: args[name] for name in names if name in args}
        try:
            result = function(**call_args)
            if isinstance(result, str):
                return result
            return json.dumps(result, ensure_ascii=False, default=str)
        except Exception as error:
            logger.warning(
                "%s 도구 실행 실패: %s — %s",
                toolset,
                function.__name__,
                error,
            )
            return json.dumps({"error": str(error)}, ensure_ascii=False)

    return handler


def _callable_parameter_names(signature: inspect.Signature) -> list[str]:
    return [
        name
        for name, parameter in signature.parameters.items()
        if name not in _SKIPPED_PARAMETER_NAMES
        and parameter.kind not in {
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        }
    ]


def _register_module_tool(
    service_package: str,
    module_name: str,
    toolset: str,
    *,
    fallback_description_suffix: str,
    default_content_description: str | None,
    target_registry: ToolRegistry,
    logger: logging.Logger,
) -> bool:
    try:
        module = importlib.import_module(f"{service_package}.{module_name}")
    except Exception as error:
        logger.debug("%s 모듈 import 스킵: %s — %s", toolset, module_name, error)
        return False

    function = find_main_function(module)
    if function is None:
        logger.debug("%s 모듈에 공개 함수 없음: %s", toolset, module_name)
        return False

    signature = inspect.signature(function)
    description = (function.__doc__ or "").strip().split("\n")[0][:200]
    if not description:
        description = f"{module_name}{fallback_description_suffix}"

    target_registry.register(
        name=function.__name__,
        toolset=toolset,
        description=description,
        parameters=build_params_schema(
            signature,
            default_content_description=default_content_description,
        ),
        handler=make_handler(
            function,
            _callable_parameter_names(signature),
            logger=logger,
            toolset=toolset,
        ),
    )
    return True


def register_service_tools(
    service_package: str,
    toolset: str,
    *,
    skip_modules: Iterable[str] = (),
    fallback_description_suffix: str = "",
    default_content_description: str | None = None,
    target_registry: ToolRegistry = registry,
    logger: logging.Logger | None = None,
) -> int:
    """서비스 패키지의 각 모듈에서 첫 번째 공개 함수를 도구로 등록합니다."""
    log = logger or logging.getLogger(__name__)
    skipped_modules = set(skip_modules)

    try:
        package = importlib.import_module(service_package)
    except Exception as error:
        log.warning("%s 서비스 패키지 로드 실패: %s", toolset, error)
        return 0

    package_paths = list(getattr(package, "__path__", []))
    if not package_paths:
        log.warning("%s 서비스 패키지 경로 없음: %s", toolset, service_package)
        return 0

    registered = 0
    skipped = 0
    for _, module_name, is_package in pkgutil.iter_modules(package_paths):
        if module_name.startswith("_") or module_name in skipped_modules or is_package:
            skipped += 1
            continue

        if _register_module_tool(
            service_package,
            module_name,
            toolset,
            fallback_description_suffix=fallback_description_suffix,
            default_content_description=default_content_description,
            target_registry=target_registry,
            logger=log,
        ):
            registered += 1
        else:
            skipped += 1

    log.info("%s 도구 자동 등록: %d개 (스킵: %d개)", toolset, registered, skipped)
    return registered
