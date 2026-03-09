"""
비디오 API 서비스 — 비디오 메타데이터 API 인터페이스 (시뮬레이션)
"""

import json
import time
import uuid
from dataclasses import dataclass, field

VALID_OPERATIONS = ("get_info", "get_transcript", "get_chapters")


@dataclass
class VideoAPIRequest:
    """비디오 API 요청"""
    request_id: str
    video_id: str
    operation: str  # get_info / get_transcript / get_chapters
    params: dict


@dataclass
class VideoAPIResponse:
    """비디오 API 응답"""
    request_id: str
    status: str  # success / error / not_found
    data: dict
    processing_time_ms: float


def process_request(request: VideoAPIRequest) -> VideoAPIResponse:
    """요청 처리 (시뮬레이션)"""
    start = time.time()

    # 유효성 검증
    errors = validate_request(request)
    if errors:
        elapsed = (time.time() - start) * 1000
        return VideoAPIResponse(
            request_id=request.request_id,
            status="error",
            data={"errors": errors},
            processing_time_ms=round(elapsed, 2),
        )

    # 시뮬레이션 데이터 생성
    if request.operation == "get_info":
        data = {
            "video_id": request.video_id,
            "title": f"Video {request.video_id}",
            "duration_seconds": 600,
            "channel": "Demo Channel",
            "view_count": 10000,
        }
    elif request.operation == "get_transcript":
        data = {
            "video_id": request.video_id,
            "language": request.params.get("language", "ko"),
            "segments": [
                {"start": 0.0, "end": 5.0, "text": "안녕하세요"},
                {"start": 5.0, "end": 10.0, "text": "이 영상에서는..."},
            ],
        }
    elif request.operation == "get_chapters":
        data = {
            "video_id": request.video_id,
            "chapters": [
                {"title": "소개", "start_seconds": 0},
                {"title": "본론", "start_seconds": 60},
                {"title": "결론", "start_seconds": 300},
            ],
        }
    else:
        data = {}

    elapsed = (time.time() - start) * 1000
    return VideoAPIResponse(
        request_id=request.request_id,
        status="success",
        data=data,
        processing_time_ms=round(elapsed, 2),
    )


def validate_request(request: VideoAPIRequest) -> list:
    """요청 검증"""
    errors = []

    if not request.video_id.strip():
        errors.append("video_id가 비어있습니다")

    if request.operation not in VALID_OPERATIONS:
        errors.append(f"유효하지 않은 operation: {request.operation}. 허용: {VALID_OPERATIONS}")

    return errors


def format_response(response: VideoAPIResponse, fmt: str = "json") -> str:
    """응답 포맷팅 (json/xml 시뮬레이션)"""
    if fmt == "json":
        return json.dumps({
            "request_id": response.request_id,
            "status": response.status,
            "data": response.data,
            "processing_time_ms": response.processing_time_ms,
        }, ensure_ascii=False, indent=2)

    elif fmt == "xml":
        lines = ['<?xml version="1.0" encoding="UTF-8"?>']
        lines.append("<response>")
        lines.append(f"  <request_id>{response.request_id}</request_id>")
        lines.append(f"  <status>{response.status}</status>")
        lines.append(f"  <processing_time_ms>{response.processing_time_ms}</processing_time_ms>")
        lines.append("  <data>")
        for k, v in response.data.items():
            lines.append(f"    <{k}>{v}</{k}>")
        lines.append("  </data>")
        lines.append("</response>")
        return "\n".join(lines)

    else:
        raise ValueError(f"지원하지 않는 포맷: {fmt}. 허용: json, xml")
