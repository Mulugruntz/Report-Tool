"""A module for constants."""

from functools import lru_cache
from pathlib import Path
from typing import Final, TypedDict


class Proxies(TypedDict):
    """Proxies for an account."""

    https: str


class Account(TypedDict):
    """Account, as stored in the credentials file."""

    pwd: str
    api_key: str
    type: str
    proxies: Proxies


APPLICATION_TITLE: Final[str] = "Report Tool"
EMPTY_ACCOUNT: Final[Account] = {
    "pwd": "",
    "api_key": "",
    "type": "Live",
    "proxies": {"https": ""},
}


@lru_cache()
def get_root_project_dir() -> Path:
    """Get the root project path.

    Go one directory up, until the root project is found (name is "Report-Tool").
    """
    current_dir = Path(__file__).parent
    while current_dir.name not in ["Report-Tool", APPLICATION_TITLE]:
        current_dir = current_dir.parent
        if current_dir.name == "":
            raise FileNotFoundError("Root project directory not found.")
    return current_dir


@lru_cache()
def get_logs_dir() -> Path:
    """Get the logs directory."""
    return get_root_project_dir() / "Logs"


@lru_cache()
def get_icons_dir() -> Path:
    """Get the icons directory."""
    return get_root_project_dir() / "icons"


@lru_cache()
def get_credentials_file() -> Path:
    """Get the credentials file."""
    return get_root_project_dir() / "credentials.json"


@lru_cache()
def get_comments_file() -> Path:
    """Get the comments file."""
    return get_root_project_dir() / "comments.json"


@lru_cache()
def get_screenshots_dir() -> Path:
    """Get the screenshots directory."""
    return get_root_project_dir() / "Screenshots"


@lru_cache()
def get_export_dir() -> Path:
    """Get the export directory."""
    return get_root_project_dir() / "Export"


@lru_cache()
def get_config_file() -> Path:
    """Get the config file."""
    return get_root_project_dir() / "config.json"
