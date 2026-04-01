"""Analysis 도구 자동 래핑 — services/analysis/ 분석 서비스를 자동 등록

메타 등록 패턴:
1. services/analysis/ 디렉토리의 모든 Python 모듈을 스캔
2. 각 모듈의 첫 번째 공개 함수(_ 미시작)를 도구로 등록
3. 함수 시그니처에서 JSON Schema를 자동 빌드
4. docstring 첫 줄을 도구 설명으로 사용
"""
from __future__ import annotations

import importlib
import inspect
import json
import logging
import os
import pkgutil
from typing import Any, Dict, List

from agent.registry import registry

logger = logging.getLogger(__name__)

_ANALYSIS_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..", "services", "analysis"
)

# 대부분의 분석 함수가 content: str을 받으므로 기본 스키마
_DEFAULT_PARAMS: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "content": {"type": "string", "description": "분석할 텍스트 콘텐츠"},
    },
    "required": ["content"],
}

# Python 타입 어노테이션 → JSON Schema 타입 매핑
_TYPE_MAP = {
    str: "string",
    int: "integer",
    float: "number",
    bool: "boolean",
    list: "array",
    dict: "object",
}


def _resolve_json_type(annotation: Any) -> str:
    """타입 어노테이션을 JSON Schema 타입 문자열로 변환합니다."""
    if annotation in _TYPE_MAP:
        return _TYPE_MAP[annotation]

    # typing.List, typing.Dict 등 제네릭 타입 처리
    origin = getattr(annotation, "__origin__", None)
    if origin is list:
        return "array"
    if origin is dict:
        return "object"

    # 문자열 표현 폴백 (typing.Optional 등)
    ann_str = str(annotation)
    if "List" in ann_str:
        return "array"
    if "Dict" in ann_str:
        return "object"

    return "string"


def _build_params_schema(sig: inspect.Signature) -> Dict[str, Any]:
    """함수 시그니처에서 JSON Schema를 빌드합니다."""
    props: Dict[str, Any] = {}
    required: List[str] = []

    for pname, param in sig.parameters.items():
        if pname in ("self", "cls", "kwargs", "args"):
            continue

        annotation = param.annotation
        if annotation is inspect.Parameter.empty:
            ptype = "string"
        else:
            ptype = _resolve_json_type(annotation)

        props[pname] = {"type": ptype}

        # 기본값이 없으면 required
        if param.default is inspect.Parameter.empty:
            required.append(pname)

    if not props:
        return _DEFAULT_PARAMS

    return {"type": "object", "properties": props, "required": required}


def _find_main_function(mod: Any) -> Any | None:
    """모듈에서 첫 번째 공개 함수를 찾습니다.

    조건: _ 미시작, 해당 모듈에서 정의된 함수 (re-export 제외).
    """
    for name, fn in inspect.getmembers(mod, inspect.isfunction):
        if name.startswith("_"):
            continue
        if fn.__module__ != mod.__name__:
            continue
        return fn
    return None


def _make_handler(func, param_names: List[str]):
    """도구 핸들러 클로저를 생성합니다.

    클로저 변수 캡처 문제를 피하기 위해 팩토리 함수 사용.
    """
    def handler(args: dict, **kwargs) -> str:
        call_args = {k: args.get(k) for k in param_names if k in args}
        try:
            result = func(**call_args)
            if isinstance(result, str):
                return result
            return json.dumps(result, ensure_ascii=False, default=str)
        except Exception as e:
            logger.warning("analysis 도구 실행 실패: %s — %s", func.__name__, e)
            return json.dumps({"error": str(e)}, ensure_ascii=False)
    return handler


def _register_analysis_tools() -> int:
    """services/analysis/ 모듈을 스캔하여 도구로 자동 등록합니다.

    Returns:
        등록된 도구 수
    """
    if not os.path.isdir(_ANALYSIS_DIR):
        logger.warning("analysis 디렉토리 없음: %s", _ANALYSIS_DIR)
        return 0

    count = 0
    skipped = 0

    for _, module_name, is_pkg in pkgutil.iter_modules([_ANALYSIS_DIR]):
        # __init__, _private, 하위 패키지 스킵
        if module_name.startswith("_") or is_pkg:
            continue

        try:
            mod = importlib.import_module(f"services.analysis.{module_name}")
        except Exception as e:
            logger.debug("analysis 모듈 import 스킵: %s — %s", module_name, e)
            skipped += 1
            continue

        fn = _find_main_function(mod)
        if fn is None:
            logger.debug("analysis 모듈에 공개 함수 없음: %s", module_name)
            skipped += 1
            continue

        # 도구 이름: 함수 이름 그대로 사용
        tool_name = fn.__name__

        # 설명: docstring 첫 줄 (없으면 모듈명 기반 기본값)
        doc = (fn.__doc__ or "").strip().split("\n")[0][:200]
        if not doc:
            doc = f"{module_name} 분석"

        # 파라미터 스키마
        sig = inspect.signature(fn)
        params = _build_params_schema(sig)

        # 핸들러 클로저
        param_names = [
            p for p in sig.parameters
            if p not in ("self", "cls", "kwargs", "args")
        ]

        registry.register(
            name=tool_name,
            toolset="analysis",
            description=doc,
            parameters=params,
            handler=_make_handler(fn, param_names),
        )
        count += 1

    logger.info(
        "Analysis 도구 자동 등록: %d개 (스킵: %d개)", count, skipped
    )
    return count


# import 시 자동 실행
_register_analysis_tools()
