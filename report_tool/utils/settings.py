"""Module for settings."""

import json
from decimal import Decimal
from pathlib import Path
from typing import Any

from pydantic import BaseModel, BaseSettings, Field, validator
from pydantic.env_settings import SettingsSourceCallable
from PyQt5.QtCore import QByteArray

from report_tool.utils.constants import (
    get_config_file,
    get_export_dir,
    get_screenshots_dir,
)
from report_tool.utils.json_utils import RoundTripDecoder


def json_config_settings_source(settings: BaseSettings) -> dict[str, Any]:
    """
    A simple settings source that loads variables from a JSON file
    at the project's root.

    Here we happen to choose to use the `env_file_encoding` from Config
    when reading `config.json`
    """
    encoding = settings.__config__.env_file_encoding
    return json.loads(get_config_file().read_text(encoding), cls=RoundTripDecoder)


class WhatToShow(BaseModel):
    """Details about the ``what_to_show`` field."""

    state_infos: str = Field(default="Only for screenshot")
    state_size: str = Field(default="Only for screenshot")
    state_details: int = Field(default=0)
    state_dates: int = Field(default=0)
    high: int = Field(default=2)
    depth: int = Field(default=2)
    maxdd: int = Field(default=2)


class Settings(BaseSettings):
    """Settings."""

    ec_size: int = 3
    ec_style: str = "Solid"
    ec_color: str = "#000000"
    dd_size: int = 11
    maxdd_style: str = "o"
    maxdd_color: str = "#ff0000"
    high_style: str = "o"
    high_color: str = "#00ff00"
    depth_style: str = "o"
    depth_color: str = "#ffaa00"
    profit_color: str = "#32CD32"
    flat_color: str = "#000000"
    loss_color: str = "#E62309"
    currency_symbol: str = "\u20ac"
    what_to_print: str = "All window"
    result_in: str = "Points"
    last_usr: str = ""
    dir_out: Path = Field(default_factory=get_screenshots_dir)
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

    class Config:
        env_file_encoding = "utf-8"

        @classmethod
        def customise_sources(
            cls,
            init_settings: SettingsSourceCallable,
            env_settings: SettingsSourceCallable,
            file_secret_settings: SettingsSourceCallable,
        ) -> tuple[SettingsSourceCallable, ...]:
            return (
                init_settings,
                json_config_settings_source,
                # env_settings,
                # file_secret_settings,
            )

    @validator("gui_state", pre=True)
    def gui_state_to_qbytearray(cls, v: str) -> QByteArray:
        """Transform the gui_state into a QByteArray."""
        return QByteArray.fromBase64(v.encode())


if __name__ == "__main__":
    print(Settings().dict())
