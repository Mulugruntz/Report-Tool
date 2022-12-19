import csv
import re
from dataclasses import astuple
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Final, Iterable, Literal, TypeVar, cast, overload

from PyQt5.QtWidgets import QTableWidget

from report_tool.exports.formats import (
    AccountInfo,
    DataToExport,
    ExportableSummary,
    ExportableTransaction,
    Transaction,
)
from report_tool.utils.constants import get_export_dir
from report_tool.utils.settings import read_config

RE_TEXT_BETWEEN_TAGS: Final[re.Pattern[str]] = re.compile(r">(.*?)<")

T = TypeVar("T")


class NothingToExport(Exception):
    """Raised when there is nothing to export."""


def make_comment_transactions(
    transactions: Iterable[ExportableTransaction],
) -> str:
    dates: list[date] = sorted(
        datetime.strptime(t.date, "%d/%m/%y").date() for t in transactions
    )
    return f"#Transactions from {dates[0]} to {dates[-1]}"


class ExportToExcel:
    """An exported to save to a file in an Excel format."""

    def __init__(self, data: DataToExport) -> None:
        """Initialize the exporter.

        Args:
            data: The data to export.
        """
        self._data_to_export: DataToExport = data
        self.config: dict = read_config()

    @staticmethod
    @overload
    def clean_value(value: str) -> str:
        ...

    @staticmethod
    @overload
    def clean_value(value: T) -> T:
        ...

    @staticmethod
    def clean_value(value: str | T) -> str | T:
        """Clean value. Remove html tags in strings.

        Args:
            value: value to clean.

        Returns:
            Cleaned value.
        """

        if isinstance(value, str):
            if (groups := RE_TEXT_BETWEEN_TAGS.search(value)) is not None:
                return groups.group(1)
        return value

    def _get_filename(
        self,
        what_to_export: Literal["all", "transactions", "summary"],
        account_info: AccountInfo,
    ) -> str:
        """Return filename to export to."""
        acc_name: str = account_info["Account name: "].lower()
        acc_type: str = account_info["Account type: "].lower()

        if what_to_export == "summary":
            return f"report_tool_{acc_type}_{acc_name}_{what_to_export}_summary.txt"

        # constructs a header with date range
        dates: list[date] = self.get_transaction_dates(
            self._data_to_export["transactions"].values()
        )

        if not dates:
            raise NothingToExport("No transactions to export")

        # construct fixed file name
        return f"report tool_{acc_type}_{acc_name}_{what_to_export}_from {dates[0]:%Y-%m-%d} to {dates[-1]:%Y-%m-%d}.txt"

    def export(self, widget_pos: QTableWidget) -> None:
        """Export data to file."""
        config = self.config
        what_to_export: Literal["all", "transactions", "summary"] = config[
            "what_to_export"
        ].lower()

        try:
            filename: str = self._get_filename(
                what_to_export, self._data_to_export["current_acc"]
            )
            filepath: Path = get_export_dir() / filename
        except NothingToExport as exc:
            print(exc)
            return

        start_capital = self._data_to_export["start_capital"]

        if what_to_export in ["all", "transactions"]:
            transactions: list[
                ExportableTransaction
            ] = self._get_exportable_transactions(widget_pos)
            self.write_comment_transactions(filepath, transactions=transactions)
            self.write_transactions(filepath, transactions, sep=config["separator"])

        if what_to_export in ["all", "summary"]:
            summary = self._get_exportable_summary()
            self.write_comment_summary(
                filepath, start_capital=start_capital, config=config
            )
            self.write_summary(filepath, summary, sep=config["separator"])

    def _get_exportable_transactions(
        self, widget_pos: QTableWidget
    ) -> list[ExportableTransaction]:
        """Get exportable transactions from widget."""
        nb_row: int = widget_pos.rowCount()
        nb_col: int = widget_pos.columnCount()

        return [
            ExportableTransaction(
                *[
                    cell.text()
                    for j in range(nb_col)
                    if (cell := widget_pos.item(i, j)) is not None
                ]
            )
            for i in range(nb_row)
        ]

    def _get_exportable_summary(self) -> list[ExportableSummary]:
        """Get exportable summary from internal data.

        Returns:
            An exportable summary.
        """
        return [
            ExportableSummary(key=key, value=self.clean_value(cast(str, value)))
            for key, value in self._data_to_export["summary"].items()
        ]

    @staticmethod
    def get_transaction_dates(
        transactions: Iterable[Transaction],
    ) -> list[date]:
        """Get the dates of transactions.

        Args:
            transactions: Transactions to get dates from.

        Returns:
            A list of dates.
        """
        return sorted(
            datetime.strptime(t["date"], "%d/%m/%y").date() for t in transactions
        )

    @staticmethod
    def make_comment_summary(
        *,
        is_aggregated: bool,
        currency_symbol: str,
        is_included: bool,
        result_type: str,
        start_capital: Decimal,
        is_auto_capital: bool,
    ) -> str:
        """Make a comment for the summary."""
        return (
            f"#Summary calculated in {result_type.lower()}"
            f" | interest {'' if is_included else 'not '}included"
            f" | positions {'' if is_aggregated else 'not '}aggregated"
            f" | capital initial = {start_capital}{currency_symbol}"
            f"{'(auto)' if is_auto_capital else '(manual)'}"
        )

    def write_comment_transactions(
        self, filename: Path, *, transactions: list[ExportableTransaction]
    ) -> None:
        """Write a comment with the date range of transactions."""
        # constructs a header with options
        comment = make_comment_transactions(transactions)
        with filename.open("a", encoding="utf-8") as f:
            f.write(comment + "\n")

    @staticmethod
    def write_transactions(
        filename: Path,
        transactions: list[ExportableTransaction],
        *,
        sep: str = ";",
    ) -> None:
        """Write transactions to a file."""
        with filename.open("a") as fp:
            # create csv writer
            writer = csv.writer(fp, delimiter=sep, lineterminator="\n")
            # write header
            writer.writerow(
                [
                    "Date",
                    "Market",
                    "Direction",
                    "Open Size",
                    "Open",
                    "Close",
                    "Points",
                    "Points/lot",
                    "Profit/Loss",
                ]
            )
            # write transactions
            writer.writerows(astuple(t) for t in transactions)

    def write_comment_summary(
        self, filename: Path, *, start_capital: Decimal, config: dict
    ) -> None:
        """Write a comment about the summary."""
        comment = self.make_comment_summary(
            is_aggregated=config["aggregate"] == 2,
            currency_symbol=config["currency_symbol"],
            is_included=config["include"],
            result_type=config["result_in"],
            start_capital=start_capital,
            is_auto_capital=config["auto_calculate"] == 2,
        )
        with filename.open("a", encoding="utf-8") as f:
            f.write(comment + "\n")

    @staticmethod
    def write_summary(
        filename: Path, summary: list[ExportableSummary], *, sep: str = ";"
    ) -> None:
        """Write summary to file"""
        with filename.open("a") as fp:
            # create csv writer
            writer = csv.writer(fp, delimiter=sep, lineterminator="\n")
            # write summary
            writer.writerows(astuple(s) for s in summary)
