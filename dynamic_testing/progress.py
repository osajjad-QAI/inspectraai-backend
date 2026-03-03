import threading
from datetime import datetime


_progress_lock = threading.Lock()
MAX_RECENT_ERRORS = 20

_progress_state = {
    "status": "idle",
    "current_agent": None,
    "message": "Waiting",
    "updated_at": None,
    "current_error": None,
    "last_error": None,
    "error_count": 0,
    "recent_errors": [],
    "all_errors": [],
}


def set_progress(
    status: str = None,
    current_agent: str = None,
    message: str = None,
    error_details: dict = None,
    append_error: bool = True,
) -> None:
    with _progress_lock:
        if status is not None:
            _progress_state["status"] = status
        if current_agent is not None:
            _progress_state["current_agent"] = current_agent
        if message is not None:
            _progress_state["message"] = message
        if error_details is not None:
            _progress_state["current_error"] = error_details
            _progress_state["last_error"] = error_details
            if append_error:
                _progress_state["error_count"] += 1
                _progress_state["recent_errors"].append(error_details)
                _progress_state["all_errors"].append(error_details)
                if len(_progress_state["recent_errors"]) > MAX_RECENT_ERRORS:
                    overflow = len(_progress_state["recent_errors"]) - MAX_RECENT_ERRORS
                    del _progress_state["recent_errors"][0:overflow]
        _progress_state["updated_at"] = datetime.utcnow().isoformat() + "Z"


def get_progress() -> dict:
    with _progress_lock:
        return dict(_progress_state)
