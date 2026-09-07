"""Shared helpers for service-function auto registration."""
from __future__ import annotations

import inspect
import types
from collections import abc as collections_abc
from typing import Annotated, Any, Literal, Union, get_args, get_origin, get_type_hints


_SKIPPED_PARAMETERS = frozenset({"self", "cls", "args", "kwargs"})
_PRIMITIVE_SCHEMAS = {
    str: {"type": "string"},
    int: {"type": "integer"},
    float: {"type": "number"},
    bool: {"type": "boolean"},
}
_ARRAY_ORIGINS = {
    list,
    set,
    frozenset,
    collections_abc.Sequence,
    collections_abc.Set,
}
_OBJECT_ORIGINS = {
    dict,
    collections_abc.Mapping,
    collections_abc.MutableMapping,
}
_UNION_ORIGINS = {Union}
if hasattr(types, "UnionType"):
    _UNION_ORIGINS.add(types.UnionType)


def _split_annotation_arguments(value: str) -> list[str]:
    """Split generic or union arguments without evaluating annotation text."""
    arguments: list[str] = []
    start = 0
    depth = 0
    for index, character in enumerate(value):
        if character == "[":
            depth += 1
        elif character == "]":
            depth -= 1
        elif character in {",", "|"} and depth == 0:
            arguments.append(value[start:index].strip())
            start = index + 1
    arguments.append(value[start:].strip())
    return [argument for argument in arguments if argument]


def _string_annotation_to_schema(annotation: str) -> dict[str, Any]:
    """Resolve common postponed annotations without executing their text."""
    normalized = annotation.strip().replace("typing.", "")
    primitive_types = {
        "str": "string",
        "int": "integer",
        "float": "number",
        "bool": "boolean",
        "None": "null",
        "NoneType": "null",
    }
    if normalized in primitive_types:
        return {"type": primitive_types[normalized]}

    union_arguments = _split_annotation_arguments(normalized)
    if len(union_arguments) > 1 and "|" in normalized:
        non_null = [
            argument
            for argument in union_arguments
            if argument not in {"None", "NoneType"}
        ]
        if len(non_null) == 1:
            return _string_annotation_to_schema(non_null[0])
        return {
            "anyOf": [
                _string_annotation_to_schema(argument)
                for argument in union_arguments
            ]
        }

    if "[" in normalized and normalized.endswith("]"):
        container, raw_arguments = normalized.split("[", 1)
        arguments = _split_annotation_arguments(raw_arguments[:-1])
        if container == "Optional" and arguments:
            return _string_annotation_to_schema(arguments[0])
        if container in {"Union"} and arguments:
            non_null = [arg for arg in arguments if arg not in {"None", "NoneType"}]
            if len(non_null) == 1:
                return _string_annotation_to_schema(non_null[0])
            return {
                "anyOf": [_string_annotation_to_schema(arg) for arg in arguments]
            }
        if container in {"list", "List", "set", "Set", "Sequence"}:
            item_schema = (
                _string_annotation_to_schema(arguments[0]) if arguments else {}
            )
            return {"type": "array", "items": item_schema}
        if container in {"dict", "Dict", "Mapping", "MutableMapping"}:
            schema: dict[str, Any] = {"type": "object"}
            if len(arguments) == 2:
                schema["additionalProperties"] = _string_annotation_to_schema(
                    arguments[1]
                )
            return schema

    if normalized in {"list", "List", "set", "Set", "Sequence"}:
        return {"type": "array", "items": {}}
    if normalized in {"dict", "Dict", "Mapping", "MutableMapping"}:
        return {"type": "object"}
    return {"type": "string"}


def _literal_schema(values: tuple[Any, ...]) -> dict[str, Any]:
    """Build the narrowest JSON Schema possible for ``Literal`` values."""
    value_types = {type(value) for value in values}
    if len(value_types) == 1 and next(iter(value_types)) in _PRIMITIVE_SCHEMAS:
        schema = dict(_PRIMITIVE_SCHEMAS[next(iter(value_types))])
        schema["enum"] = list(values)
        return schema
    return {"enum": list(values)}


def annotation_to_schema(annotation: Any) -> dict[str, Any]:
    """Convert a resolved Python annotation to a JSON Schema fragment.

    Unknown application-specific classes retain the legacy string fallback. An
    unparameterized collection is still advertised as a collection, with an
    unconstrained item/value schema instead of inventing a member type.
    """
    if annotation is inspect.Parameter.empty or annotation is Any:
        return {"type": "string"}
    if isinstance(annotation, str):
        return _string_annotation_to_schema(annotation)
    if annotation in _PRIMITIVE_SCHEMAS:
        return dict(_PRIMITIVE_SCHEMAS[annotation])
    if annotation is type(None):
        return {"type": "null"}

    origin = get_origin(annotation)
    args = get_args(annotation)

    if origin is Annotated:
        return annotation_to_schema(args[0])
    if origin is Literal:
        return _literal_schema(args)

    if origin in _UNION_ORIGINS:
        non_null_args = tuple(arg for arg in args if arg is not type(None))
        if len(non_null_args) == 1:
            # Optional values are represented by omission in tool arguments;
            # keep the useful concrete type for provider compatibility.
            return annotation_to_schema(non_null_args[0])
        return {"anyOf": [annotation_to_schema(arg) for arg in args]}

    if annotation in _ARRAY_ORIGINS or origin in _ARRAY_ORIGINS:
        item_annotation = args[0] if args else Any
        item_schema = {} if item_annotation is Any else annotation_to_schema(item_annotation)
        return {"type": "array", "items": item_schema}

    if annotation is tuple or origin is tuple:
        if not args:
            return {"type": "array", "items": {}}
        if len(args) == 2 and args[1] is Ellipsis:
            return {"type": "array", "items": annotation_to_schema(args[0])}
        return {
            "type": "array",
            "prefixItems": [annotation_to_schema(arg) for arg in args],
            "minItems": len(args),
            "maxItems": len(args),
        }

    if annotation in _OBJECT_ORIGINS or origin in _OBJECT_ORIGINS:
        schema: dict[str, Any] = {"type": "object"}
        if len(args) == 2:
            value_annotation = args[1]
            schema["additionalProperties"] = (
                {} if value_annotation is Any else annotation_to_schema(value_annotation)
            )
        return schema

    return {"type": "string"}


def build_parameters_schema(
    function_or_signature: Any,
    *,
    default_content_description: str | None = None,
    excluded_parameters: collections_abc.Iterable[str] = (),
) -> dict[str, Any]:
    """Build an object parameter schema from a function or signature.

    Passing the function is preferred because ``get_type_hints`` resolves
    postponed annotations. Signature support remains for compatibility with
    callers that already evaluated their annotations. ``excluded_parameters``
    removes trusted context values from the model-visible schema.
    """
    if isinstance(function_or_signature, inspect.Signature):
        signature = function_or_signature
        type_hints: dict[str, Any] = {}
    else:
        signature = inspect.signature(function_or_signature)
        try:
            type_hints = get_type_hints(function_or_signature, include_extras=True)
        except (NameError, TypeError):
            type_hints = {}

    excluded = frozenset(excluded_parameters)
    properties: dict[str, Any] = {}
    required: list[str] = []
    function_parameter_seen = False
    for parameter_name, parameter in signature.parameters.items():
        if parameter_name in _SKIPPED_PARAMETERS:
            continue
        function_parameter_seen = True
        if parameter_name in excluded:
            continue
        annotation = type_hints.get(parameter_name, parameter.annotation)
        properties[parameter_name] = annotation_to_schema(annotation)
        if parameter.default is inspect.Parameter.empty:
            required.append(parameter_name)

    if not properties and not function_parameter_seen:
        # Preserve the legacy content fallback for truly argument-less functions,
        # but do not invent a model argument when every real parameter is hidden
        # because it comes from trusted dispatch context.
        content_schema: dict[str, Any] = {"type": "string"}
        if default_content_description is not None:
            content_schema["description"] = default_content_description
        properties = {"content": content_schema}
        required = ["content"]

    return {
        "type": "object",
        "properties": properties,
        "required": required,
    }
