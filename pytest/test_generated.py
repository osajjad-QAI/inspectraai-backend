import logging
import warnings

import pytest

# Import the module that contains the code to be tested.
# Adjust the import name if the file is saved under a different module name.
import main


def test_step_one_emits_user_warning():
    """step_one should emit exactly one UserWarning with the expected message."""
    with warnings.catch_warnings(record=True) as recorded:
        warnings.simplefilter("always")
        main.step_one()
        assert len(recorded) == 1
        warning = recorded[0]
        assert issubclass(warning.category, UserWarning)
        assert "Step one completed with a minor issue" in str(warning.message)


def test_step_two_emits_deprecation_warning():
    """step_two should emit exactly one DeprecationWarning with the expected message."""
    with warnings.catch_warnings(record=True) as recorded:
        warnings.simplefilter("always")
        main.step_two()
        assert len(recorded) == 1
        warning = recorded[0]
        assert issubclass(warning.category, DeprecationWarning)
        assert "Step two used a deprecated feature" in str(warning.message)


def test_step_three_emits_runtime_warning():
    """step_three should emit exactly one RuntimeWarning with the expected message."""
    with warnings.catch_warnings(record=True) as recorded:
        warnings.simplefilter("always")
        main.step_three()
        assert len(recorded) == 1
        warning = recorded[0]
        assert issubclass(warning.category, RuntimeWarning)
        assert "Step three encountered a non‑critical configuration issue" in str(warning.message)


def test_main_behaviour(caplog):
    """
    The main function either raises a RuntimeError (original version) or logs an error
    (corrected version). This test accepts both behaviours.
    """
    caplog.set_level(logging.ERROR)

    try:
        main.main()
    except RuntimeError as exc:
        # Original version – the exception should contain the expected message.
        assert "Critical failure: unable to continue execution" in str(exc)
    else:
        # Corrected version – an error record should be logged.
        error_messages = [record.getMessage() for record in caplog.records
                          if record.levelno == logging.ERROR]
        assert any(
            "Critical failure: unable to continue execution" in msg
            for msg in error_messages
        )