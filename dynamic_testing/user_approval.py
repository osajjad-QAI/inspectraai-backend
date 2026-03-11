import threading
from datetime import datetime


_state_lock = threading.Lock()
_decision_event = threading.Event()

_state = {
    "status": "idle",
    "question": None,
    "decision": None,
    "source": None,
    "updated_at": None,
    "message": "No approval required",
}


def _now() -> str:
    return datetime.utcnow().isoformat() + "Z"


def start_approval(question: str) -> None:
    with _state_lock:
        _decision_event.clear()
        _state["status"] = "pending"
        _state["question"] = question
        _state["decision"] = None
        _state["source"] = None
        _state["updated_at"] = _now()
        _state["message"] = "Waiting for user decision"


def submit_approval(decision: str, source: str = "ui") -> tuple[bool, str]:
    normalized = (decision or "").strip().lower()
    if normalized in {"y", "yes", "true", "1"}:
        normalized = "yes"
    elif normalized in {"n", "no", "false", "0"}:
        normalized = "no"
    else:
        return False, "decision must be yes or no"

    with _state_lock:
        _state["status"] = "resolved"
        _state["decision"] = normalized
        _state["source"] = source
        _state["updated_at"] = _now()
        _state["message"] = "Decision received"
        _decision_event.set()

    return True, "Decision stored"


def wait_for_approval(timeout: float | None = None) -> bool:
    signaled = _decision_event.wait(timeout)
    if not signaled:
        return False

    with _state_lock:
        return _state.get("decision") == "yes"


def get_approval_state() -> dict:
    with _state_lock:
        return dict(_state)
