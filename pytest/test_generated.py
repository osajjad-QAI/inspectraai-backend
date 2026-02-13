import builtins
import sys
import warnings

import pytest

# Import the modules that contain the functions we need to test.
import warnings_demo
import main


def test_warnings_demo_main_raises_runtime_error_and_emits_warnings():
    """The demo should emit three warnings and then raise RuntimeError."""
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")  # capture all warnings

        with pytest.raises(RuntimeError) as exc_info:
            warnings_demo.main()

        # Verify the exception message is exactly as defined.
        assert "Critical failure: unable to continue execution" in str(exc_info.value)

        # Verify we got exactly three warnings with the expected categories.
        assert len(caught) == 3
        categories = {w.category for w in caught}
        assert categories == {UserWarning, DeprecationWarning, RuntimeWarning}

        # Optional: check the warning messages themselves.
        messages = {str(w.message) for w in caught}
        expected_messages = {
            "Step one completed with a minor issue",
            "Step two used a deprecated feature",
            "Step three encountered a non‑critical configuration issue",
        }
        assert messages == expected_messages


def test_run_query_success(monkeypatch, capsys):
    """When build_graph and invoke succeed, the final output should be printed."""

    class DummyGraph:
        def invoke(self, payload):
            # payload is irrelevant for the test – just return a dict with the key.
            return {"final_output": "42"}

    # Monkey‑patch the build_graph function used by main.run_query.
    monkeypatch.setattr(main, "build_graph", lambda: DummyGraph())

    # Run the function under test.
    main.run_query()

    # Capture stdout and verify the expected line.
    captured = capsys.readouterr()
    assert "FINAL RESULT: 42" in captured.out.strip()


def test_run_query_missing_key(monkeypatch, capsys):
    """If the result dict lacks 'final_output', the placeholder should be printed."""

    class DummyGraph:
        def invoke(self, payload):
            # Return a dict without the expected key.
            return {"some_other_key": "value"}

    monkeypatch.setattr(main, "build_graph", lambda: DummyGraph())

    main.run_query()

    captured = capsys.readouterr()
    # The fallback string "<missing>" is defined in main._print_final_result.
    assert "FINAL RESULT: <missing>" in captured.out.strip()


def test_run_query_graph_raises(monkeypatch, capsys):
    """If building the graph raises, the CLI should exit with code 1 and print an error."""

    # Make build_graph raise a generic exception.
    monkeypatch.setattr(main, "build_graph", lambda: (_ for _ in ()).throw(RuntimeError("boom")))

    # run_query should call sys.exit(1); capture the SystemExit.
    with pytest.raises(SystemExit) as exc_info:
        main.run_query()

    # Verify exit code.
    assert exc_info.value.code == 1

    # Verify that the error message was written to stderr.
    captured = capsys.readouterr()
    assert "Error while executing query: boom" in captured.err