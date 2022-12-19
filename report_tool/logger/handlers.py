"""
Module with class for custom logger
Could be used by many of IG API related app
"""

import logging.handlers
import re
from datetime import time
from pathlib import Path
from typing import Literal

from report_tool.utils.constants import get_logs_dir

RE_FILENAME = re.compile(r"(\w)*(-)")


class ReportToolFileHandler(logging.handlers.TimedRotatingFileHandler):
    """Custom TimedRotatingFileHandler.

    This class is used to create a custom TimedRotatingFileHandler that
    prepends the filename with the log directory.
    """

    def __init__(
        self,
        filename: str | Path,
        when: Literal[
            "S", "M", "H", "D", "midnight", "W0", "W1", "W2", "W3", "W4", "W5", "W6"
        ] = "H",
        interval: int = 1,
        backupCount: int = 0,
        encoding: str | None = None,
        delay: bool = False,
        utc: bool = False,
        atTime: time | None = None,
        errors: str | None = None,
    ) -> None:
        """Prepend the filename with the log directory."""
        filepath = Path(filename)
        if not filepath.is_absolute():
            filepath = get_logs_dir() / filepath
        super().__init__(
            filepath,
            when=when,
            interval=interval,
            backupCount=backupCount,
            encoding=encoding,
            delay=delay,
            utc=utc,
            atTime=atTime,
            errors=errors,
        )
