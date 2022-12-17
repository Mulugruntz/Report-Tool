"""
Module with class for custom logger
Could be used by many of IG API related app
"""

import re

import logging.handlers
from pathlib import Path

from report_tool.utils.constants import get_logs_dir

try:
    import codecs
except ImportError:
    codecs = None

RE_FILENAME = re.compile(r"(\w)*(-)")


class ReportToolFileHandler(logging.handlers.TimedRotatingFileHandler):
    """
    Custom TimedRotatingFileHandler, as the name of log created
    in base class in not convenient(an extension is appended to
    the base file name). Subclass getFilesToDelete as we change
    of log file. Looks complicated for a simple goal
    """

    def __init__(self, filename: str | Path, *args, **kwargs):
        """Prepend the filename with the log directory."""
        filepath = Path(filename)
        if not filepath.is_absolute():
            filepath = get_logs_dir() / filepath
        super().__init__(filepath, *args, **kwargs)
