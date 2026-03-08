import subprocess
import threading
import sys
import os
import time
import re
from datetime import datetime
from core.llm import send_to_llm   # 👈 NEW
from dynamic_testing.progress import set_progress

WATCH_EXTENSIONS = (".py",)
IGNORE_DIRS = {".inspectra", "__pycache__", ".venv", "venv","pytest"}


def get_files_snapshot(base_dir):
    snapshot = {}
    for root, dirs, files in os.walk(base_dir):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]

        for file in files:
            if file.endswith(WATCH_EXTENSIONS):
                path = os.path.join(root, file)
                snapshot[path] = os.path.getmtime(path)
    return snapshot


def has_changed(old, new):
    return old != new


# def send_batch_to_llm(lines, source="stdout"):
#     """
#     Send a list of log lines as a single batch to LLM.
#     """
#     if not lines:
#         return

#     combined = "".join(lines).rstrip()
#     send_to_llm(combined, source)

EVENT_START_MARKERS = [
    "Traceback (most recent call last):",
    "Warning:",
    "DeprecationWarning:"
]


def _stream_reader(stream, log_file, prefix="", primary_source="stdout"):
    """
    Reads lines from a stream and batches them into single events.
    Sends to LLM with primary and secondary source.
    """
    buffer = []
    secondary_source = "normal"  # default

    def flush_event():
        if buffer:
            event_text = "".join(buffer)
            if secondary_source in ["error", "warning"]:
                error_details = _parse_error_event(buffer, f"{primary_source} / {secondary_source}")
                set_progress(
                    status="running",
                    current_agent="runner",
                    message="Captured runtime log",
                    error_details=error_details,
                )

            llm_response = send_to_llm(event_text, f"{primary_source} / {secondary_source}")
            print("LLM Solution: ", llm_response)
            buffer.clear()

    for line in iter(stream.readline, ""):
        if not line:
            break

        formatted = f"{prefix}{line}"

        # Terminal
        sys.stdout.write(formatted)
        sys.stdout.flush()

        # Runtime log file
        log_file.write(formatted)
        log_file.flush()

        # Determine secondary source based on content
        if "Traceback (most recent call last):" in line:
            flush_event()  # flush previous
            secondary_source = "error"
        elif "warning" in line.lower() or "DeprecationWarning" in line.lower():
            flush_event()
            secondary_source = "warning"
        else:
            # normal lines keep secondary_source as normal unless in middle of event
            if secondary_source not in ["error", "warning"]:
                secondary_source = "normal"

        buffer.append(formatted)

        # If line is blank, consider event ended
        if line.strip() == "":
            flush_event()
            secondary_source = "normal"

    # Flush remaining lines
    flush_event()
    stream.close()


def _parse_error_event(lines, source_label):
    """
    Extract a best-effort error/warning location and snippet from log lines.
    """
    detail = {
        "source": source_label,
        "file": None,
        "line": None,
        "function": None,
        "exception": None,
        "message": None,
        "snippet": None,
        "raw": "".join(lines).strip(),
    }

    traceback_file_re = re.compile(r'File "([^"]+)", line (\d+), in (.+)')
    warning_re = re.compile(r'^(?:\[ERR\]\s*)?(.+?):(\d+):\s*([A-Za-z]+Warning):\s*(.*)')
    exception_re = re.compile(r'^(?:\[ERR\]\s*)?([A-Za-z_][\w\.]*):\s*(.*)')

    last_trace_match = None
    for idx, line in enumerate(lines):
        match = traceback_file_re.search(line)
        if match:
            last_trace_match = (match, idx)

    if last_trace_match:
        match, idx = last_trace_match
        detail["file"] = match.group(1)
        detail["line"] = int(match.group(2))
        detail["function"] = match.group(3)
        if idx + 1 < len(lines):
            detail["snippet"] = lines[idx + 1].strip()
    else:
        for idx, line in enumerate(lines):
            match = warning_re.search(line)
            if match:
                detail["file"] = match.group(1)
                detail["line"] = int(match.group(2))
                detail["exception"] = match.group(3)
                detail["message"] = match.group(4)
                if idx + 1 < len(lines):
                    detail["snippet"] = lines[idx + 1].strip()
                break

    for line in reversed(lines):
        match = exception_re.search(line.strip())
        if match:
            detail["exception"] = match.group(1)
            detail["message"] = match.group(2)
            break

    if detail["snippet"] is None:
        for line in reversed(lines):
            if line.strip():
                detail["snippet"] = line.strip()
                break

    return detail


def build_env_command(command: str, env_type: str, env_name: str) -> str:
    """
    Returns a shell command that activates the environment
    and then runs the actual command.
    """
    is_windows = os.name == "nt"

    if env_type == "conda":
        if is_windows:
            # conda activate only works inside cmd.exe
            return f'cmd.exe /c "conda activate {env_name} && {command}"'
        else:
            # conda needs shell hook
            return (
                f'bash -c "source $(conda info --base)/etc/profile.d/conda.sh '
                f'&& conda activate {env_name} && {command}"'
            )

    elif env_type == "venv":
        if is_windows:
            activate = os.path.join(env_name, "Scripts", "activate.bat")
            return f'cmd.exe /c "{activate} && {command}"'
        else:
            activate = os.path.join(env_name, "bin", "activate.bat")
            return f'bash -c "source {activate} && {command}"'

    else:
        raise ValueError("env_type must be 'conda' or 'venv'")
    

def run_with_watch(
    command: str,
    env_type: str,
    env_name: str,
    workdir: str,
    poll_interval: float = 1.0
):
    if not workdir:
        raise ValueError("workdir is required")

    log_dir = os.path.join(".inspectra", "logs")
    os.makedirs(log_dir, exist_ok=True)

    wrapped_command = build_env_command(command, env_type, env_name)
    print("Wrapped command: ", wrapped_command)

    print("👀 Watching for file changes...")
    print(f"🐍 Environment: {env_type} → {env_name}")
    print("🔁 Auto-restart enabled\n")

    last_snapshot = get_files_snapshot(workdir)

    while True:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_path = os.path.join(log_dir, f"run_{timestamp}.txt")

        print(f"\n🚀 Starting: {command}")
        print(f"📄 Log: {log_path}")

        process_exited_msg_printed = False

        with open(log_path, "w", encoding="utf-8") as log_file:
            process = subprocess.Popen(
                wrapped_command,
                shell=True,
                cwd=workdir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )

            t_out = threading.Thread(
                target=_stream_reader,
                args=(process.stdout, log_file, "", "stdout")
            )
            t_err = threading.Thread(
                target=_stream_reader,
                args=(process.stderr, log_file, "[ERR] ", "stderr")
            )

            print(process.stderr)

            t_out.start()
            t_err.start()

            while True:
                time.sleep(poll_interval)

                new_snapshot = get_files_snapshot(workdir)

                if has_changed(last_snapshot, new_snapshot):
                    print("\n🔄 File change detected — restarting...")
                    process.terminate()
                    break

                if process.poll() is not None:
                    if not process_exited_msg_printed:
                        print("\n🛑 Process exited. Waiting for changes...")
                        process_exited_msg_printed = True

            t_out.join()
            t_err.join()

        last_snapshot = get_files_snapshot(workdir)
        time.sleep(0.5)  # debounce
