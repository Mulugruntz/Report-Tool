"""Utils for dealing with FileSystem."""

from pathlib import Path

from report_tool.utils.constants import get_icons_dir


def get_icon_path(icon_name: str, *, ext: str = "png") -> Path:
    """Get the path of an icon."""
    return get_icons_dir() / f"{icon_name}.{ext}"
