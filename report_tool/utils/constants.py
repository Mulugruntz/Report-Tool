"""A module for constants."""

from pathlib import Path


def get_root_project_dir() -> Path:
    """Get the root project path.

    Go one directory up, until the root project is found (name is "Report-Tool").
    """
    current_dir = Path(__file__).parent
    while current_dir.name != "Report-Tool":
        current_dir = current_dir.parent
        if current_dir.name == "":
            raise FileNotFoundError("Root project directory not found.")
    return current_dir


def get_logs_dir() -> Path:
    """Get the logs directory."""
    return get_root_project_dir() / "Logs"
