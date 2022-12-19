"""Module for settings."""

from datetime import date, datetime, time
from decimal import Decimal
from enum import StrEnum
from json import JSONDecodeError
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field, validator
from PyQt5.QtCore import QByteArray

from report_tool.utils.constants import (
    get_config_file,
    get_export_dir,
    get_screenshots_dir,
)

DATE_FORMAT = "%Y-%m-%d"
TIME_FORMAT = "%H:%M:%S.%f"
DATETIME_FORMAT = f"{DATE_FORMAT} {TIME_FORMAT}"

Symbol = Literal["x", "d", "o", "t", "+", "s"]


class ScreenshotVisibility(StrEnum):
    """Enum for screenshot visibility."""

    ALWAYS = "always"
    NEVER = "never"
    ONLY_FOR_SCREENSHOT = "Only for screenshot"


class ScreenshotPrintOptions(StrEnum):
    """Enum for screenshot print options."""

    ALL_WINDOW = "All window"
    SUMMARY = "Summary"
    TRANSACTIONS = "Transactions"
    GRAPH = "Graph"


class WhatToShow(BaseModel):
    """Details about the ``what_to_show`` field."""

    state_infos: ScreenshotVisibility = Field(
        default=ScreenshotVisibility.ONLY_FOR_SCREENSHOT,
        description="Hide sensitive infos",
    )
    state_size: ScreenshotVisibility = Field(
        default=ScreenshotVisibility.ONLY_FOR_SCREENSHOT, description="Hide lot size"
    )
    state_details: int = Field(default=0)
    state_dates: int = Field(default=0)
    high: int = Field(default=2)
    depth: int = Field(default=2)
    maxdd: int = Field(default=2)


class Settings(BaseModel):
    """Settings."""

    # ------------------ Chart options ------------------
    ec_size: int = Field(3, description="Thickness")
    ec_style: str = Field("Solid", description="Style")
    ec_color: str = Field("#000000", description="Color")

    # --------------  Scatter plot options --------------
    dd_size: int = Field(11, description="Symbol size")

    # Sub: Max drawdown options
    maxdd_style: str = Field("o", description="Max drawdown symbol")
    maxdd_color: str = Field("#ff0000", description="Max drawdown color")

    # Sub: New high options
    high_style: Symbol = Field("o", description="New high symbol")
    high_color: str = Field("#00ff00", description="New high color")

    # Sub: Drawdowns options
    depth_style: Symbol = Field("o", description="Drawdowns symbol")
    depth_color: str = Field("#ffaa00", description="Drawdowns color")

    # ------------------ Transactions options ------------------
    profit_color: str = Field("#32CD32", description="Profit color")
    flat_color: str = Field("#000000", description="Flat color")
    loss_color: str = Field("#E62309", description="Loss color")

    currency_symbol: str = "\u20ac"
    what_to_print: ScreenshotPrintOptions = Field(
        default=ScreenshotPrintOptions.ALL_WINDOW, description="Print"
    )
    result_in: str = "Points"
    last_usr: str = ""
    dir_out: Path = Field(default_factory=get_screenshots_dir)

    # ------------------ Screenshot options ------------------
    shortcut: str = "Enter shortcut"

    start_capital: Decimal = Decimal(0)
    auto_calculate: int = 2
    what_to_show: WhatToShow = Field(default_factory=WhatToShow)
    include: int = 2
    all: int = 2
    auto_connect: int = 0
    aggregate: int = 0
    gui_state: QByteArray = QByteArray(b"")
    gui_size: tuple[int, int] = (800, 600)
    gui_pos: tuple[int, int] = (0, 0)
    dir_export: Path = Field(default_factory=get_export_dir)
    what_to_export: str = "All"
    separator: str = ";"

    @validator("gui_state", pre=True)
    def gui_state_to_qbytearray(cls, v: str | QByteArray) -> QByteArray:
        """Transform the gui_state into a QByteArray."""
        if isinstance(v, str):
            return QByteArray.fromBase64(v.encode())
        return v

    class Config:
        """Config."""

        arbitrary_types_allowed = True
        json_encoders = {
            Path: lambda v: str(v),
            Decimal: lambda v: str(v),
            QByteArray: lambda v: v.toBase64().data().decode(),
            datetime: lambda v: v.strftime(DATETIME_FORMAT),
            date: lambda v: v.strftime(DATE_FORMAT),
            time: lambda v: v.strftime(TIME_FORMAT),
            ScreenshotVisibility: lambda v: v.value,
            ScreenshotPrintOptions: lambda v: v.value,
        }
        json_decoders = {
            datetime: lambda v: datetime.strptime(v, DATETIME_FORMAT),
            date: lambda v: datetime.strptime(v, DATE_FORMAT).date(),
            time: lambda v: datetime.strptime(v, TIME_FORMAT).time(),
            QByteArray: lambda v: QByteArray.fromBase64(v.encode()),
        }


def read_config() -> dict[str, Any]:
    """Read the config file."""
    try:
        return Settings.parse_file(get_config_file()).dict()
    except (JSONDecodeError, FileNotFoundError):
        return Settings().dict()


def write_config(config: dict[str, Any]) -> None:
    """Write the config file."""
    json_str = Settings(**config).json(indent=4)
    get_config_file().write_text(json_str)


if __name__ == "__main__":
    # print(Settings().dict())
    config = read_config()
    print(config)
    config["ec_size"] = 3
    write_config(config)
    config = read_config()
    print(config)
