"""Health endpoint payload helpers."""

from __future__ import annotations


def detect_runtime_environment(flask_env: str | None, *, debug: bool) -> str:
    """Map Flask runtime flags to the public health environment value."""
    if flask_env == "development" or debug:
        return "development"
    return "production"


def get_process_memory_usage_mb() -> float | None:
    """Return process memory usage in megabytes when available."""
    try:
        import resource

        return round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1)
    except ImportError:
        return _get_windows_memory_usage_mb()
    except Exception:
        return None


def _get_windows_memory_usage_mb() -> float | None:
    try:
        import ctypes
        import ctypes.wintypes

        class PROCESS_MEMORY_COUNTERS(ctypes.Structure):
            _fields_ = [
                ("cb", ctypes.wintypes.DWORD),
                ("PageFaultCount", ctypes.wintypes.DWORD),
                ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t),
                ("PeakPagefileUsage", ctypes.c_size_t),
            ]

        pmc = PROCESS_MEMORY_COUNTERS()
        pmc.cb = ctypes.sizeof(pmc)
        handle = ctypes.windll.kernel32.GetCurrentProcess()
        if ctypes.windll.psapi.GetProcessMemoryInfo(handle, ctypes.byref(pmc), pmc.cb):
            return round(pmc.WorkingSetSize / (1024 * 1024), 1)
    except Exception:
        return None
    return None


def build_health_payload(
    *,
    environment: str,
    request_count: int,
    error_count: int,
    error_rate: float,
    memory_usage_mb: float | None,
) -> dict:
    """Build the JSON-serializable `/health` response body."""
    return {
        "status": "healthy",
        "environment": environment,
        "api_version": "v2.0",
        "request_count": request_count,
        "error_count": error_count,
        "error_rate": error_rate,
        "memory_usage_mb": memory_usage_mb,
    }
