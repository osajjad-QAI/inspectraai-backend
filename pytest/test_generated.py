import io
import pytest
from fastapi.testclient import TestClient

# Import the FastAPI app defined in the provided module
from main import fastapi_app


@pytest.fixture
def client():
    """Test client for the FastAPI application."""
    return TestClient(fastapi_app)


def test_get_skip_folders(monkeypatch, client):
    """The endpoint should return the SKIP_FOLDERS list in lower‑case."""
    # Mock the SKIP_FOLDERS constant used in the route
    monkeypatch.setattr("scan_config.SKIP_FOLDERS", ["__pycache__", "venv"])
    response = client.get("/skip-folders")
    assert response.status_code == 200
    json_data = response.json()
    assert "skip_folders" in json_data
    # The returned list must be lower‑cased
    assert json_data["skip_folders"] == ["__pycache__", "venv"]


def test_analyze_success(monkeypatch, client):
    """A valid .py file should be processed and the mocked workflow result returned."""
    # Mock the LangGraph workflow invocation
    mock_result = {"final_report": "All good", "fixed_code": "print('fixed')"}
    monkeypatch.setattr("static_backend.app.invoke", lambda payload: mock_result)

    # Ensure the file‑skip logic does not filter the test file
    monkeypatch.setattr("scan_config.should_skip_file", lambda _: False)

    files = {
        "files": ("example.py", io.BytesIO(b"print('hello')"), "text/x-python")
    }
    response = client.post("/analyze", files=files)
    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    assert len(data["results"]) == 1
    result = data["results"][0]
    assert result["filename"] == "example.py"
    assert result["report"] == "All good"
    assert result["fixed_code"] == "print('fixed')"
    assert data["skipped"] == 0


def test_analyze_non_python_file(monkeypatch, client):
    """Files that do not end with .py should be ignored."""
    monkeypatch.setattr("scan_config.should_skip_file", lambda _: False)
    files = {
        "files": ("readme.txt", io.BytesIO(b"just text"), "text/plain")
    }
    response = client.post("/analyze", files=files)
    # No .py files → 400 error as per the endpoint implementation
    assert response.status_code == 400
    assert response.json()["detail"] == "No .py files found in the uploaded payload"


def test_analyze_skipped_file(monkeypatch, client):
    """Files whose path matches a skipped folder should be counted but not processed."""
    # Mock the skip‑check to return True for the given filename
    monkeypatch.setattr("scan_config.should_skip_file", lambda name: "skipme" in name.lower())
    files = {
        "files": ("skipme/example.py", io.BytesIO(b"print('x')"), "text/x-python")
    }
    response = client.post("/analyze", files=files)
    # No processed results, but skipped count should be reported
    assert response.status_code == 400
    assert response.json()["detail"] == "No .py files found in the uploaded payload"


def test_analyze_all_keys_exhausted(monkeypatch, client):
    """When the workflow raises AllKeysExhaustedError the endpoint should return a warning."""
    # Mock the exception class
    class DummyError(Exception):
        pass

    monkeypatch.setattr("groq_key_manager.AllKeysExhaustedError", DummyError)
    # Mock the workflow to raise the error on invoke
    def raise_error(_):
        raise DummyError("keys exhausted")
    monkeypatch.setattr("static_backend.app.invoke", raise_error)

    monkeypatch.setattr("scan_config.should_skip_file", lambda _: False)

    files = {
        "files": ("example.py", io.BytesIO(b"print('test')"), "text/x-python")
    }
    response = client.post("/analyze", files=files)
    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    assert len(data["results"]) == 1
    result = data["results"][0]
    assert "All available Groq API keys have been rate‑limited" in result["report"]
    assert result["fixed_code"] == ""