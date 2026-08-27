"""YouTube visual deep-dive utilities.

영상에서 뽑은 화면/슬라이드와 생성된 튜토리얼의 사진 제안을
하나의 markdown-backed study item으로 저장/조회하는 서비스입니다.
외부 도구(yt-dlp/ffmpeg)는 선택적으로 사용하고, 핵심 저장/파싱 로직은
테스트 가능한 순수 Python으로 유지합니다.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import secrets
import signal
import shutil
import subprocess
import tempfile
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping
from urllib.parse import parse_qs, urlparse

try:  # Linux/macOS 배포에서는 프로세스 간 사용자 잠금도 함께 건다.
    import fcntl
except ImportError:  # pragma: no cover - Windows 개발 환경용 폴백
    fcntl = None

YOUTUBE_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")
FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n?(.*)$", re.DOTALL)
VISUAL_MARKER_RE = re.compile(r"^\[(사진|스크린샷)\s*(\d+)\]\s*:\s*(.+?)\s*$")
SHOWINFO_TIME_RE = re.compile(r"pts_time:([0-9]+(?:\.[0-9]+)?)")
SAFE_MEDIA_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,199}$")
SAFE_MEDIA_SUFFIXES = frozenset({".jpg", ".jpeg", ".png", ".webp"})

DEFAULT_MAX_DOWNLOAD_BYTES = 512 * 1024 * 1024
DEFAULT_MAX_VIDEO_DURATION_SECONDS = 2 * 60 * 60
DEFAULT_MAX_PROCESSING_SECONDS = 10 * 60
DEFAULT_MAX_SLIDES = 24
DEFAULT_MAX_MEDIA_FILE_BYTES = 16 * 1024 * 1024
DEFAULT_MAX_ARTIFACT_BYTES = 64 * 1024 * 1024
DEFAULT_MAX_OWNER_BYTES = 512 * 1024 * 1024
DEFAULT_MAX_OWNER_ITEMS = 100

_ACTIVE_OWNER_SCOPES: set[str] = set()
_ACTIVE_OWNER_SCOPES_LOCK = threading.Lock()
_STORAGE_MUTATION_LOCK = threading.Lock()


class VideoDeepDiveBusyError(RuntimeError):
    """같은 사용자의 영상 추출이 이미 실행 중임."""


class VideoDeepDiveLimitError(RuntimeError):
    """영상 처리 또는 영구 저장 예산을 넘긴 요청."""

    def __init__(self, message: str, *, status_code: int = 413, code: str = "VIDEO_DEEPDIVE_LIMIT"):
        super().__init__(message)
        self.status_code = status_code
        self.code = code


class MonitoredDownloadError(RuntimeError):
    """실시간 감시 중 다운로드 프로세스를 중단한 내부 오류."""

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


def _positive_int(value: Any, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default


@dataclass(frozen=True)
class VideoDeepDiveLimits:
    """영상 추출 한 건과 사용자 저장소에 적용하는 자원 예산."""

    max_download_bytes: int = DEFAULT_MAX_DOWNLOAD_BYTES
    max_video_duration_seconds: int = DEFAULT_MAX_VIDEO_DURATION_SECONDS
    max_processing_seconds: int = DEFAULT_MAX_PROCESSING_SECONDS
    max_slides: int = DEFAULT_MAX_SLIDES
    max_media_file_bytes: int = DEFAULT_MAX_MEDIA_FILE_BYTES
    max_artifact_bytes: int = DEFAULT_MAX_ARTIFACT_BYTES
    max_owner_bytes: int = DEFAULT_MAX_OWNER_BYTES
    max_owner_items: int = DEFAULT_MAX_OWNER_ITEMS

    @classmethod
    def from_config(cls, config: Mapping[str, Any] | None = None) -> "VideoDeepDiveLimits":
        values = config or {}

        def configured(name: str, default: int) -> int:
            return _positive_int(values.get(name, os.environ.get(name)), default)

        return cls(
            max_download_bytes=configured("VIDEO_DEEPDIVE_MAX_DOWNLOAD_BYTES", DEFAULT_MAX_DOWNLOAD_BYTES),
            max_video_duration_seconds=configured(
                "VIDEO_DEEPDIVE_MAX_DURATION_SECONDS", DEFAULT_MAX_VIDEO_DURATION_SECONDS
            ),
            max_processing_seconds=configured(
                "VIDEO_DEEPDIVE_MAX_PROCESSING_SECONDS", DEFAULT_MAX_PROCESSING_SECONDS
            ),
            max_slides=configured("VIDEO_DEEPDIVE_MAX_SLIDES", DEFAULT_MAX_SLIDES),
            max_media_file_bytes=configured(
                "VIDEO_DEEPDIVE_MAX_MEDIA_FILE_BYTES", DEFAULT_MAX_MEDIA_FILE_BYTES
            ),
            max_artifact_bytes=configured(
                "VIDEO_DEEPDIVE_MAX_ARTIFACT_BYTES", DEFAULT_MAX_ARTIFACT_BYTES
            ),
            max_owner_bytes=configured("VIDEO_DEEPDIVE_MAX_OWNER_BYTES", DEFAULT_MAX_OWNER_BYTES),
            max_owner_items=configured("VIDEO_DEEPDIVE_MAX_OWNER_ITEMS", DEFAULT_MAX_OWNER_ITEMS),
        )


@dataclass
class VideoSlide:
    """A visual slide/frame attached to a video deep-dive."""

    idx: int
    t: float
    title: str = ""
    note: str = ""
    img: str = ""
    suggestion: str = ""
    source: str = "auto"
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        data = {
            "idx": int(self.idx),
            "t": float(self.t),
            "mmss": seconds_to_mmss(self.t),
            "title": self.title or f"화면 {self.idx}",
            "note": self.note or "",
            "img": self.img or "",
            "suggestion": self.suggestion or "",
            "source": self.source or "auto",
        }
        data.update(self.extra)
        return data


def seconds_to_hhmmss(seconds: float | int | str | None) -> str:
    """Return HH:MM:SS for a seconds value, falling back to 0."""
    try:
        total = max(0, int(float(seconds or 0)))
    except (TypeError, ValueError):
        total = 0
    h, rem = divmod(total, 3600)
    m, s = divmod(rem, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def seconds_to_mmss(seconds: float | int | str | None) -> str:
    """Return MM:SS for slide display, or HH:MM:SS for long videos."""
    hhmmss = seconds_to_hhmmss(seconds)
    return hhmmss[3:] if hhmmss.startswith("00:") else hhmmss


def normalize_youtube_id(value: str) -> str:
    """Extract and validate an 11-character YouTube video id from an id or URL."""
    raw = (value or "").strip()
    if YOUTUBE_ID_RE.match(raw):
        return raw

    parsed = urlparse(raw)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("유효한 YouTube 영상 ID가 아닙니다.")
    host = (parsed.hostname or "").lower()
    path = parsed.path.strip("/")

    candidate = ""
    if host in {"youtu.be", "www.youtu.be"}:
        candidate = path.split("/", 1)[0]
    elif host == "youtube.com" or host.endswith(".youtube.com"):
        if path.startswith("shorts/") or path.startswith("embed/"):
            candidate = path.split("/", 1)[1].split("/", 1)[0]
        else:
            candidate = parse_qs(parsed.query).get("v", [""])[0]

    if YOUTUBE_ID_RE.match(candidate):
        return candidate
    raise ValueError("유효한 YouTube 영상 ID가 아닙니다.")


def extract_visual_suggestions(content: str) -> list[dict[str, Any]]:
    """Extract `[사진 N]: ...` / `[스크린샷 N]: ...` markers from generated content.

    The closest previous markdown heading is kept as `section` so the frontend can
    show where that image belongs in the tutorial/course.
    """
    suggestions: list[dict[str, Any]] = []
    current_section = ""
    for line in (content or "").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        heading = re.match(r"^#{1,6}\s+(.+?)\s*$", stripped)
        if heading:
            current_section = heading.group(1).strip()
            continue
        marker = VISUAL_MARKER_RE.match(stripped)
        if marker:
            label_kind, number, description = marker.groups()
            idx = int(number)
            suggestions.append(
                {
                    "idx": idx,
                    "kind": "screenshot" if label_kind == "스크린샷" else "photo",
                    "label": f"{label_kind} {idx}",
                    "description": description.strip(),
                    "section": current_section,
                }
            )
    return suggestions


def transcript_segments_to_text(segments: list[dict[str, Any]] | None) -> str:
    """Format transcript segment dicts as `[HH:MM:SS] text` lines."""
    lines: list[str] = []
    for seg in segments or []:
        if not isinstance(seg, dict):
            continue
        text = str(seg.get("text", "")).strip()
        if not text:
            continue
        lines.append(f"[{seconds_to_hhmmss(seg.get('start', 0))}] {text}")
    return "\n".join(lines)


def select_candidate_times(times: list[float | int], max_slides: int = 24, min_gap: float = 12.0) -> list[float]:
    """Deduplicate scene timestamps by minimum time gap and cap the result."""
    selected: list[float] = []
    for raw in sorted(float(t) for t in times if float(t) >= 0):
        if selected and raw - selected[-1] < min_gap:
            continue
        selected.append(round(raw, 2))
        if len(selected) >= max(1, int(max_slides)):
            break
    return selected


def split_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    match = FRONTMATTER_RE.match(text or "")
    if not match:
        return {}, text or ""
    raw_meta, body = match.groups()
    try:
        meta = json.loads(raw_meta)
    except json.JSONDecodeError:
        meta = {}
    if body.startswith("## Transcript\n"):
        body = body[len("## Transcript\n") :]
    return meta, body.strip()


def dump_frontmatter(meta: dict[str, Any], body: str) -> str:
    return "---\n" + json.dumps(meta, ensure_ascii=False, indent=2) + "\n---\n## Transcript\n" + (body or "").strip() + "\n"


class VideoDeepDiveLibrary:
    """Markdown + media storage for video study deep-dives."""

    def __init__(
        self,
        root: str | os.PathLike[str] | None = None,
        *,
        owner_id: str | None = None,
        limits: VideoDeepDiveLimits | None = None,
    ):
        self.base_root = Path(
            root or os.environ.get("VIDEO_DEEPDIVE_DIR", "data/video_deepdives")
        ).expanduser().resolve()
        self.base_root.mkdir(parents=True, exist_ok=True)
        self.owner_scope = (
            hashlib.sha256(str(owner_id).encode("utf-8")).hexdigest()
            if owner_id is not None
            else None
        )
        self.root = (
            (self.base_root / "_owners" / self.owner_scope).resolve()
            if self.owner_scope
            else self.base_root
        )
        if self.root != self.base_root and self.base_root not in self.root.parents:
            raise ValueError("허용되지 않은 deep-dive 사용자 경로입니다.")
        self.root.mkdir(parents=True, exist_ok=True)
        (self.root / "_media").mkdir(parents=True, exist_ok=True)
        self.limits = limits or VideoDeepDiveLimits.from_config()

        if self.owner_scope:
            marker = self.root / ".owner-scope"
            if marker.exists() and marker.read_text(encoding="ascii").strip() != self.owner_scope:
                raise RuntimeError("deep-dive 사용자 저장소 소유권 표식이 일치하지 않습니다.")
            if not marker.exists():
                marker.write_text(self.owner_scope, encoding="ascii")

    def _safe_id(self, video_id: str) -> str:
        return normalize_youtube_id(video_id)

    def item_path(self, video_id: str) -> Path:
        safe_id = self._safe_id(video_id)
        path = (self.root / f"{safe_id}.md").resolve()
        if self.root not in path.parents and path != self.root:
            raise ValueError("허용되지 않은 deep-dive 경로입니다.")
        return path

    def media_dir(self, video_id: str, *, create: bool = True) -> Path:
        safe_id = self._safe_id(video_id)
        path = (self.root / "_media" / safe_id).resolve()
        if self.root not in path.parents:
            raise ValueError("허용되지 않은 media 경로입니다.")
        if create:
            path.mkdir(parents=True, exist_ok=True)
        return path

    def media_url(self, video_id: str, filename: str) -> str:
        safe_id = self._safe_id(video_id)
        clean_name = self._safe_media_name(filename)
        return f"/api/video-deepdives/{safe_id}/media/{clean_name}"

    def _safe_media_name(self, filename: str) -> str:
        raw = str(filename or "")
        if (
            Path(raw).name != raw
            or not SAFE_MEDIA_NAME_RE.fullmatch(raw)
            or Path(raw).suffix.lower() not in SAFE_MEDIA_SUFFIXES
        ):
            raise ValueError("허용되지 않은 deep-dive 미디어 파일명입니다.")
        return raw

    def _verify_owner(self, meta: Mapping[str, Any]) -> None:
        stored_scope = meta.get("_owner_scope")
        if self.owner_scope:
            if stored_scope != self.owner_scope:
                # 존재 여부 자체를 다른 사용자에게 알리지 않는다.
                raise FileNotFoundError("deep-dive 항목을 찾을 수 없습니다.")
        elif stored_scope:
            raise FileNotFoundError("deep-dive 항목을 찾을 수 없습니다.")

    @staticmethod
    def _public_meta(meta: Mapping[str, Any]) -> dict[str, Any]:
        return {key: value for key, value in meta.items() if key != "_owner_scope"}

    def _read_item(self, video_id: str) -> tuple[dict[str, Any], str]:
        path = self.item_path(video_id)
        if not path.exists() or path.is_symlink():
            raise FileNotFoundError("deep-dive 항목을 찾을 수 없습니다.")
        meta, body = split_frontmatter(path.read_text(encoding="utf-8"))
        if not meta:
            raise FileNotFoundError("deep-dive 항목을 찾을 수 없습니다.")
        self._verify_owner(meta)
        return meta, body

    def _referenced_media_names(self, video_id: str, meta: Mapping[str, Any]) -> set[str]:
        safe_id = self._safe_id(video_id)
        expected_prefix = f"/api/video-deepdives/{safe_id}/media/"
        names: set[str] = set()
        for slide in meta.get("slides") or []:
            if not isinstance(slide, dict):
                continue
            raw_url = str(slide.get("img") or "")
            parsed_path = urlparse(raw_url).path
            if not parsed_path.startswith(expected_prefix):
                continue
            filename = parsed_path[len(expected_prefix) :]
            if "/" in filename:
                continue
            try:
                names.add(self._safe_media_name(filename))
            except ValueError:
                continue
        return names

    def media_path(self, video_id: str, filename: str, *, require_referenced: bool = True) -> Path:
        safe_id = self._safe_id(video_id)
        clean_name = self._safe_media_name(filename)
        meta, _ = self._read_item(safe_id)
        if require_referenced and clean_name not in self._referenced_media_names(safe_id, meta):
            raise FileNotFoundError("미디어 파일을 찾을 수 없습니다.")
        media_root = self.media_dir(safe_id, create=False)
        candidate = media_root / clean_name
        if candidate.is_symlink():
            raise FileNotFoundError("미디어 파일을 찾을 수 없습니다.")
        resolved = candidate.resolve()
        if media_root != resolved.parent or not resolved.exists() or not resolved.is_file():
            raise FileNotFoundError("미디어 파일을 찾을 수 없습니다.")
        return resolved

    def _storage_bytes(self) -> int:
        total = 0
        for path in self.root.rglob("*"):
            if path.is_symlink() or not path.is_file() or path.name == ".owner-scope":
                continue
            try:
                total += path.stat().st_size
            except OSError:
                continue
        return total

    def _artifact_storage_bytes(self, video_id: str) -> int:
        total = 0
        item = self.item_path(video_id)
        if item.exists() and item.is_file() and not item.is_symlink():
            total += item.stat().st_size
        media = self.media_dir(video_id, create=False)
        if media.exists() and media.is_dir() and not media.is_symlink():
            for path in media.iterdir():
                if path.is_file() and not path.is_symlink():
                    total += path.stat().st_size
        return total

    def assert_can_create(self, video_id: str) -> None:
        path = self.item_path(video_id)
        if not path.exists() and len(list(self.root.glob("*.md"))) >= self.limits.max_owner_items:
            raise VideoDeepDiveLimitError("사용자별 deep-dive 항목 수 상한을 초과했습니다.")

    @staticmethod
    def _atomic_write(path: Path, payload: str) -> None:
        pending = path.with_name(f".{path.name}.{secrets.token_hex(8)}.tmp")
        try:
            with pending.open("x", encoding="utf-8") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(pending, path)
        finally:
            try:
                pending.unlink(missing_ok=True)
            except OSError:
                pass

    @contextmanager
    def _storage_mutation_slot(self):
        """용량 검사와 원자 교체를 프로세스/워커 간 직렬화한다."""
        lock_fd: int | None = None
        with _STORAGE_MUTATION_LOCK:
            try:
                lock_dir = self.base_root / "_locks"
                lock_dir.mkdir(parents=True, exist_ok=True)
                scope = self.owner_scope or "legacy-anonymous"
                lock_fd = os.open(
                    lock_dir / f"{scope}.storage.lock", os.O_CREAT | os.O_RDWR, 0o600
                )
                if fcntl is not None:
                    fcntl.flock(lock_fd, fcntl.LOCK_EX)
                yield
            finally:
                if lock_fd is not None:
                    if fcntl is not None:
                        try:
                            fcntl.flock(lock_fd, fcntl.LOCK_UN)
                        except OSError:
                            pass
                    os.close(lock_fd)

    def _commit_item(
        self,
        *,
        video_id: str,
        meta: dict[str, Any],
        body: str,
        media_files: Iterable[str | os.PathLike[str]] | None = None,
    ) -> dict[str, Any]:
        with self._storage_mutation_slot():
            return self._commit_item_locked(
                video_id=video_id,
                meta=meta,
                body=body,
                media_files=media_files,
            )

    def _commit_item_locked(
        self,
        *,
        video_id: str,
        meta: dict[str, Any],
        body: str,
        media_files: Iterable[str | os.PathLike[str]] | None = None,
    ) -> dict[str, Any]:
        safe_id = self._safe_id(video_id)
        self.assert_can_create(safe_id)
        if len(meta.get("slides") or []) > self.limits.max_slides:
            raise VideoDeepDiveLimitError(
                f"deep-dive 화면은 최대 {self.limits.max_slides}개까지 저장할 수 있습니다."
            )

        stored_meta = dict(meta)
        if self.owner_scope:
            stored_meta["_owner_scope"] = self.owner_scope
        else:
            stored_meta.pop("_owner_scope", None)
        payload = dump_frontmatter(stored_meta, body)
        payload_bytes = len(payload.encode("utf-8"))

        sources: list[tuple[Path, str, int]] = []
        for raw_source in media_files or []:
            source = Path(raw_source)
            if source.is_symlink() or not source.exists() or not source.is_file():
                raise VideoDeepDiveLimitError("유효하지 않은 deep-dive 미디어 산출물입니다.")
            name = self._safe_media_name(source.name)
            size = source.stat().st_size
            if size > self.limits.max_media_file_bytes:
                raise VideoDeepDiveLimitError("deep-dive 미디어 파일 크기 상한을 초과했습니다.")
            sources.append((source, name, size))

        referenced = self._referenced_media_names(safe_id, stored_meta)
        staged_names = {name for _, name, _ in sources}
        preserved_bytes = 0
        existing_media_root = self.media_dir(safe_id, create=False)
        if existing_media_root.exists() and not existing_media_root.is_symlink():
            for name in referenced - staged_names:
                path = existing_media_root / name
                if path.exists() and path.is_file() and not path.is_symlink():
                    preserved_bytes += path.stat().st_size

        artifact_bytes = payload_bytes + preserved_bytes + sum(size for _, _, size in sources)
        if artifact_bytes > self.limits.max_artifact_bytes:
            raise VideoDeepDiveLimitError("deep-dive 영구 산출물 크기 상한을 초과했습니다.")

        current_total = self._storage_bytes()
        replaced_bytes = self._artifact_storage_bytes(safe_id)
        if current_total - replaced_bytes + artifact_bytes > self.limits.max_owner_bytes:
            raise VideoDeepDiveLimitError("사용자별 deep-dive 저장 용량 상한을 초과했습니다.")

        media_root = self.media_dir(safe_id)
        installed: list[Path] = []
        try:
            for source, name, _ in sources:
                target = media_root / name
                if target.exists() or target.is_symlink():
                    raise VideoDeepDiveLimitError("deep-dive 미디어 파일명이 충돌했습니다.", status_code=409)
                pending = media_root / f".{name}.{secrets.token_hex(8)}.tmp"
                try:
                    shutil.copyfile(source, pending)
                    os.replace(pending, target)
                finally:
                    pending.unlink(missing_ok=True)
                installed.append(target)

            self._atomic_write(self.item_path(safe_id), payload)
        except Exception:
            for path in installed:
                path.unlink(missing_ok=True)
            raise

        for path in media_root.iterdir():
            if path.name in referenced or path.is_symlink() or not path.is_file():
                continue
            try:
                path.unlink()
            except OSError:
                pass
        return self._public_meta(stored_meta)

    def write_item(
        self,
        *,
        video_id: str,
        title: str,
        source_url: str,
        transcript: str = "",
        slides: list[VideoSlide | dict[str, Any]] | None = None,
        visual_suggestions: list[dict[str, Any]] | None = None,
        tags: list[str] | None = None,
        media_files: Iterable[str | os.PathLike[str]] | None = None,
    ) -> dict[str, Any]:
        safe_id = self._safe_id(video_id)
        normalized_slides = [s.to_dict() if isinstance(s, VideoSlide) else dict(s) for s in (slides or [])]
        meta = {
            "id": safe_id,
            "title": (title or "YouTube Deep Dive").strip(),
            "youtube_id": safe_id,
            "source_url": source_url or f"https://www.youtube.com/watch?v={safe_id}",
            "created": date.today().isoformat(),
            "slide_count": len(normalized_slides),
            "slides": normalized_slides,
            "visual_suggestions": visual_suggestions or [],
            "tags": tags or [],
        }
        return self._commit_item(
            video_id=safe_id,
            meta=meta,
            body=transcript,
            media_files=media_files,
        )

    def list_items(self) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        for path in sorted(self.root.glob("*.md")):
            if path.is_symlink():
                continue
            meta, body = split_frontmatter(path.read_text(encoding="utf-8"))
            if not meta:
                continue
            try:
                self._verify_owner(meta)
            except FileNotFoundError:
                continue
            items.append({**self._public_meta(meta), "slug": path.stem, "preview": body[:180]})
        return items

    def get_item(self, video_id: str) -> dict[str, Any]:
        meta, body = self._read_item(video_id)
        return {"slug": self._safe_id(video_id), "meta": self._public_meta(meta), "body": body}

    def update_slide_notes(self, video_id: str, slides: list[dict[str, Any]]) -> dict[str, Any]:
        meta, body = self._read_item(video_id)
        meta = dict(meta)
        meta["slides"] = slides
        meta["slide_count"] = len(slides)
        return self._commit_item(video_id=video_id, meta=meta, body=body)

    @contextmanager
    def extraction_slot(self):
        """사용자별 동시 추출을 한 프로세스/여러 워커 모두에서 하나로 제한."""
        scope = self.owner_scope or "legacy-anonymous"
        with _ACTIVE_OWNER_SCOPES_LOCK:
            if scope in _ACTIVE_OWNER_SCOPES:
                raise VideoDeepDiveBusyError("이 사용자의 영상 추출이 이미 진행 중입니다.")
            _ACTIVE_OWNER_SCOPES.add(scope)

        lock_fd: int | None = None
        try:
            lock_dir = self.base_root / "_locks"
            lock_dir.mkdir(parents=True, exist_ok=True)
            lock_fd = os.open(lock_dir / f"{scope}.lock", os.O_CREAT | os.O_RDWR, 0o600)
            if fcntl is not None:
                try:
                    fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except BlockingIOError as exc:
                    raise VideoDeepDiveBusyError(
                        "이 사용자의 영상 추출이 이미 진행 중입니다."
                    ) from exc
            yield
        finally:
            if lock_fd is not None:
                if fcntl is not None:
                    try:
                        fcntl.flock(lock_fd, fcntl.LOCK_UN)
                    except OSError:
                        pass
                os.close(lock_fd)
            with _ACTIVE_OWNER_SCOPES_LOCK:
                _ACTIVE_OWNER_SCOPES.discard(scope)


def require_tool(name: str) -> str:
    path = shutil.which(name)
    if not path:
        raise RuntimeError(f"{name} 실행 파일을 찾을 수 없습니다.")
    return path


def _bounded_timeout(timeout: int | float, deadline: float | None) -> int:
    bounded = max(1, int(math.ceil(float(timeout))))
    if deadline is None:
        return bounded
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise VideoDeepDiveLimitError(
            "영상 전체 처리 제한 시간을 초과했습니다.",
            status_code=504,
            code="VIDEO_DEEPDIVE_TIMEOUT",
        )
    return max(1, min(bounded, int(math.ceil(remaining))))


def run_command(
    args: list[str],
    *,
    timeout: int = 120,
    cwd: str | os.PathLike[str] | None = None,
    deadline: float | None = None,
) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            args,
            cwd=cwd,
            timeout=_bounded_timeout(timeout, deadline),
            check=True,
            text=True,
            capture_output=True,
        )
    except subprocess.TimeoutExpired as exc:
        raise VideoDeepDiveLimitError(
            "영상 전체 처리 제한 시간을 초과했습니다.",
            status_code=504,
            code="VIDEO_DEEPDIVE_TIMEOUT",
        ) from exc
    except subprocess.CalledProcessError as exc:
        raise RuntimeError("영상 처리 도구 실행에 실패했습니다.") from exc


def _matching_download_paths(root: Path, prefix: str) -> list[Path]:
    """yt-dlp가 만든 최종/part/분리 스트림 파일만 반환한다."""
    try:
        entries = list(root.iterdir())
    except FileNotFoundError:
        return []
    return [path for path in entries if path.name.startswith(prefix)]


def _download_bytes(root: Path, prefix: str) -> int:
    total = 0
    for path in _matching_download_paths(root, prefix):
        if path.is_symlink() or not path.is_file():
            continue
        try:
            total += path.stat().st_size
        except OSError:
            continue
    return total


def _cleanup_download_paths(root: Path, prefix: str) -> None:
    for path in _matching_download_paths(root, prefix):
        if path.is_dir() and not path.is_symlink():
            continue
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass


def _terminate_process_group(
    process: subprocess.Popen,
    *,
    grace_seconds: float = 0.35,
) -> None:
    """부모와 yt-dlp가 띄운 ffmpeg를 TERM→유예→KILL 순서로 종료."""
    if os.name == "posix":
        group_exists = True
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            group_exists = False
        except OSError:
            try:
                process.terminate()
            except OSError:
                pass

        if group_exists:
            stop_at = time.monotonic() + max(0.05, grace_seconds)
            while time.monotonic() < stop_at:
                process.poll()
                time.sleep(0.02)

            # 부모가 먼저 끝나도 같은 그룹의 ffmpeg가 남아 있을 수 있으므로
            # 그룹 전체에 KILL을 한 번 더 보낸다.
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except (ProcessLookupError, OSError):
                pass
    else:  # Windows: 새 프로세스 그룹 + terminate/kill 안전 폴백
        if process.poll() is not None:
            return
        ctrl_break = getattr(signal, "CTRL_BREAK_EVENT", None)
        if ctrl_break is not None:
            try:
                process.send_signal(ctrl_break)
            except OSError:
                pass
        if process.poll() is None:
            try:
                process.terminate()
            except OSError:
                pass
        try:
            process.wait(timeout=max(0.05, grace_seconds))
        except subprocess.TimeoutExpired:
            try:
                process.kill()
            except OSError:
                pass

    try:
        process.wait(timeout=1)
    except (subprocess.TimeoutExpired, OSError):
        try:
            process.kill()
        except OSError:
            pass


def run_monitored_download(
    args: list[str],
    *,
    watch_root: str | os.PathLike[str],
    watch_prefix: str,
    max_bytes: int,
    timeout: int | float,
    deadline: float | None = None,
    cwd: str | os.PathLike[str] | None = None,
    poll_interval: float = 0.05,
) -> subprocess.CompletedProcess[str]:
    """다운로드 중 파일 총량/시간을 감시하고 전체 프로세스 그룹을 정리.

    stdout/stderr는 파이프 대신 DEVNULL로 보내므로 진행 로그가 파이프 버퍼를
    채워 부모와 자식이 서로 기다리는 교착 상태가 생기지 않는다.
    """
    root = Path(watch_root).expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    if not watch_prefix or Path(watch_prefix).name != watch_prefix:
        raise ValueError("유효하지 않은 다운로드 감시 접두사입니다.")
    if max_bytes <= 0:
        raise ValueError("다운로드 바이트 상한은 양수여야 합니다.")

    now = time.monotonic()
    expires_at = now + max(0.001, float(timeout))
    if deadline is not None:
        expires_at = min(expires_at, float(deadline))
    if expires_at <= now:
        _cleanup_download_paths(root, watch_prefix)
        raise MonitoredDownloadError("timeout")

    popen_kwargs: dict[str, Any] = {
        "cwd": cwd,
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
    }
    if os.name == "posix":
        popen_kwargs["start_new_session"] = True
    else:
        creation_flag = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        if creation_flag:
            popen_kwargs["creationflags"] = creation_flag

    process: subprocess.Popen | None = None
    try:
        try:
            process = subprocess.Popen(args, **popen_kwargs)
        except OSError as exc:
            raise MonitoredDownloadError("missing_executable") from exc

        while True:
            return_code = process.poll()
            if _download_bytes(root, watch_prefix) > max_bytes:
                raise MonitoredDownloadError("size")
            if time.monotonic() >= expires_at:
                raise MonitoredDownloadError("timeout")
            if return_code is not None:
                if _download_bytes(root, watch_prefix) > max_bytes:
                    raise MonitoredDownloadError("size")
                if return_code != 0:
                    raise MonitoredDownloadError("process")
                return subprocess.CompletedProcess(args, return_code, stdout="", stderr="")
            time.sleep(max(0.01, min(float(poll_interval), 0.25)))
    except BaseException:
        if process is not None:
            _terminate_process_group(process)
        _cleanup_download_paths(root, watch_prefix)
        raise


def detect_scene_times(
    video_path: str | os.PathLike[str],
    *,
    threshold: float = 0.30,
    timeout: int = 180,
    deadline: float | None = None,
) -> list[float]:
    """Use ffmpeg scene detection and parse candidate timestamps."""
    ffmpeg = require_tool("ffmpeg")
    expr = f"select='gt(scene,{float(threshold):.3f})',showinfo"
    proc = run_command(
        [ffmpeg, "-hide_banner", "-i", str(video_path), "-vf", expr, "-f", "null", "-"],
        timeout=timeout,
        deadline=deadline,
    )
    return [float(m.group(1)) for m in SHOWINFO_TIME_RE.finditer(proc.stderr or "")]


def extract_slide_images(
    *,
    video_id: str,
    video_path: str | os.PathLike[str],
    times: list[float],
    library: VideoDeepDiveLibrary,
    width: int = 1280,
    timeout_per_frame: int = 30,
    output_dir: str | os.PathLike[str] | None = None,
    limits: VideoDeepDiveLimits | None = None,
    deadline: float | None = None,
) -> list[VideoSlide]:
    """Extract selected frames into the deep-dive media folder."""
    ffmpeg = require_tool("ffmpeg")
    safe_id = normalize_youtube_id(video_id)
    effective_limits = limits or library.limits
    out_dir = Path(output_dir) if output_dir is not None else library.media_dir(safe_id)
    out_dir.mkdir(parents=True, exist_ok=True)
    slides: list[VideoSlide] = []
    created: list[Path] = []
    total_bytes = 0
    extraction_id = secrets.token_hex(6)
    try:
        for idx, t in enumerate(times[: effective_limits.max_slides], 1):
            filename = f"{safe_id}-{extraction_id}-slide-{idx:02d}.jpg"
            out_path = out_dir / filename
            run_command(
                [
                    ffmpeg,
                    "-hide_banner",
                    "-y",
                    "-ss",
                    f"{float(t):.2f}",
                    "-i",
                    str(video_path),
                    "-frames:v",
                    "1",
                    "-vf",
                    f"scale={min(max(int(width), 320), 1920)}:-1",
                    "-q:v",
                    "3",
                    str(out_path),
                ],
                timeout=timeout_per_frame,
                deadline=deadline,
            )
            if not out_path.exists() or out_path.is_symlink():
                raise RuntimeError("추출된 화면 파일을 찾을 수 없습니다.")
            created.append(out_path)
            size = out_path.stat().st_size
            total_bytes += size
            if size > effective_limits.max_media_file_bytes:
                raise VideoDeepDiveLimitError("deep-dive 미디어 파일 크기 상한을 초과했습니다.")
            if total_bytes > effective_limits.max_artifact_bytes:
                raise VideoDeepDiveLimitError("deep-dive 영구 산출물 크기 상한을 초과했습니다.")
            slides.append(
                VideoSlide(
                    idx=idx,
                    t=float(t),
                    title=f"화면 {idx}",
                    img=library.media_url(safe_id, filename),
                    source="ffmpeg-scene",
                )
            )
    except Exception:
        for path in created:
            path.unlink(missing_ok=True)
        raise
    return slides


def download_youtube_video(
    url_or_id: str,
    scratch_dir: str | os.PathLike[str],
    *,
    timeout: int = 600,
    max_download_bytes: int = DEFAULT_MAX_DOWNLOAD_BYTES,
    max_duration_seconds: int = DEFAULT_MAX_VIDEO_DURATION_SECONDS,
    deadline: float | None = None,
    on_cost_start: Callable[[], None] | None = None,
) -> tuple[str, Path, str]:
    """Download a ≤720p mp4 and return (video_id, path, title). Requires yt-dlp."""
    ytdlp = require_tool("yt-dlp")
    video_id = normalize_youtube_id(url_or_id)
    url = f"https://www.youtube.com/watch?v={video_id}"
    scratch = Path(scratch_dir)
    scratch.mkdir(parents=True, exist_ok=True)
    if on_cost_start is not None:
        on_cost_start()
    metadata_proc = run_command(
        [
            ytdlp,
            "--no-playlist",
            "--skip-download",
            "--dump-single-json",
            url,
        ],
        timeout=min(timeout, 60),
        deadline=deadline,
    )
    try:
        info = json.loads(metadata_proc.stdout or "{}")
        duration = float(info.get("duration") or 0)
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise VideoDeepDiveLimitError(
            "영상 길이를 확인할 수 없어 안전하게 추출을 중단했습니다.", status_code=422
        ) from exc
    if duration <= 0 or duration > max_duration_seconds:
        raise VideoDeepDiveLimitError(
            f"영상 길이는 최대 {max_duration_seconds // 60}분까지 허용됩니다.", status_code=422
        )

    output_tpl = str(scratch / "video.%(ext)s")
    download_args = [
        ytdlp,
        "--no-playlist",
        "--no-progress",
        "--max-filesize",
        str(max_download_bytes),
        "--match-filter",
        f"duration <= {max_duration_seconds}",
        "-f",
        "bv*[height<=720][ext=mp4]+ba[ext=m4a]/b[height<=720][ext=mp4]/best[height<=720]",
        "--merge-output-format",
        "mp4",
        "-o",
        output_tpl,
        url,
    ]
    try:
        # 메타데이터 조회 후 임대가 유실될 수 있으므로 실제 영상
        # 다운로드 프로세스를 시작하기 직전에 소유권을 다시 확인한다.
        if on_cost_start is not None:
            on_cost_start()
        run_monitored_download(
            download_args,
            watch_root=scratch,
            watch_prefix="video",
            max_bytes=max_download_bytes,
            timeout=timeout,
            deadline=deadline,
        )
    except MonitoredDownloadError as exc:
        if exc.reason == "size":
            raise VideoDeepDiveLimitError("다운로드 영상 크기 상한을 초과했습니다.") from exc
        if exc.reason == "timeout":
            raise VideoDeepDiveLimitError(
                "영상 전체 처리 제한 시간을 초과했습니다.",
                status_code=504,
                code="VIDEO_DEEPDIVE_TIMEOUT",
            ) from exc
        raise RuntimeError("영상 다운로드에 실패했습니다.") from exc
    video_path = scratch / "video.mp4"
    if not video_path.exists():
        candidates = sorted(
            path
            for path in scratch.glob("video.*")
            if path.suffix.lower() in {".mp4", ".mkv", ".webm", ".mov"}
            and path.is_file()
            and not path.is_symlink()
        )
        if not candidates:
            _cleanup_download_paths(scratch, "video")
            raise RuntimeError("다운로드된 영상 파일을 찾을 수 없습니다.")
        video_path = candidates[0]
    if video_path.is_symlink() or video_path.stat().st_size > max_download_bytes:
        _cleanup_download_paths(scratch, "video")
        raise VideoDeepDiveLimitError("다운로드 영상 크기 상한을 초과했습니다.")
    title = str(info.get("title") or "YouTube 영상")
    return video_id, video_path, title


def build_visual_deepdive_from_video(
    *,
    url_or_id: str,
    transcript: str = "",
    title: str = "",
    content: str = "",
    library: VideoDeepDiveLibrary | None = None,
    max_slides: int = 18,
    scene_threshold: float = 0.30,
    min_gap: float = 12.0,
    limits: VideoDeepDiveLimits | None = None,
    on_cost_start: Callable[[], None] | None = None,
) -> dict[str, Any]:
    """Download a YouTube video, extract representative screens, and persist an item."""
    lib = library or VideoDeepDiveLibrary()
    effective_limits = limits or lib.limits
    lib.assert_can_create(normalize_youtube_id(url_or_id))
    deadline = time.monotonic() + effective_limits.max_processing_seconds
    with tempfile.TemporaryDirectory(prefix="insight-deepdive-") as td:
        video_id, video_path, downloaded_title = download_youtube_video(
            url_or_id,
            td,
            timeout=effective_limits.max_processing_seconds,
            max_download_bytes=effective_limits.max_download_bytes,
            max_duration_seconds=effective_limits.max_video_duration_seconds,
            deadline=deadline,
            on_cost_start=on_cost_start,
        )
        times = select_candidate_times(
            detect_scene_times(
                video_path,
                threshold=min(max(float(scene_threshold), 0.05), 0.95),
                deadline=deadline,
            ),
            max_slides=min(max(1, int(max_slides)), effective_limits.max_slides),
            min_gap=min(max(float(min_gap), 1.0), 600.0),
        )
        frame_dir = Path(td) / "frames"
        slides = extract_slide_images(
            video_id=video_id,
            video_path=video_path,
            times=times,
            library=lib,
            output_dir=frame_dir,
            limits=effective_limits,
            deadline=deadline,
        )
        _bounded_timeout(1, deadline)
        meta = lib.write_item(
            video_id=video_id,
            title=title or downloaded_title,
            source_url=f"https://www.youtube.com/watch?v={video_id}",
            transcript=transcript,
            slides=slides,
            visual_suggestions=extract_visual_suggestions(content),
            tags=["youtube", "visual-deepdive"],
            media_files=sorted(frame_dir.glob("*")) if frame_dir.exists() else [],
        )
        return {"meta": meta, "slides": [s.to_dict() for s in slides]}
