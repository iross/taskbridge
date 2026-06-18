"""Shared fixtures for unit tests."""

import pytest


@pytest.fixture(autouse=True)
def no_focus_session(mocker):
    """Prevent tests from opening Raycast Focus."""
    mocker.patch("taskbridge.main.start_focus_session")
