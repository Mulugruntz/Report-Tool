from dataclasses import dataclass
from decimal import Decimal
from typing import TypedDict


@dataclass(frozen=True, slots=True)
class ExportableTransaction:
    """A transaction that can be exported to a file."""

    date: str
    market: str
    direction: str
    open_size: str
    open: str
    close: str
    points: str
    points_lot: str
    profit_loss: str


@dataclass(frozen=True, slots=True)
class ExportableSummary:
    """A summary that can be exported to a file."""

    key: str
    value: str


class Transaction(TypedDict):
    """Transaction type."""

    type: str
    date: str
    market_name: str
    direction: str
    open_size: Decimal
    open_level: Decimal
    final_level: Decimal
    points: Decimal
    points_lot: Decimal
    pnl: Decimal
    growth: str


Summary = TypedDict(
    "Summary",
    {
        "Points won": str,
        "Trades won": str,
        "Points lost": str,
        "Trades lost": str,
        "Total points": str,
        "Trades flat": str,
        "Total trades": str,
        "Avg trade": str,
        "Profit Factor": str,
        "Avg win": str,
        "Capital growth": str,
        "Avg loss": str,
        "Max drawdown": str,
        "Avg drawdown": str,
        "Consec. wins": str,
        "Consec. losses": str,
        "Interests": str,
        "Fees": str,
        "Cash in/out": str,
        "Transfers": str,
    },
    total=False,
)
AccountInfo = TypedDict(
    "AccountInfo",
    {
        "Account ID: ": str,
        "Account type: ": str,
        "Account name: ": str,
        "Cash available: ": str,
        "Account balance: ": str,
        "Profit/loss: ": str,
        "currency_ISO": str,
        "preferred": bool,
    },
    total=False,
)


class DataToExport(TypedDict, total=False):
    """Data to export."""

    transactions: dict[str, Transaction]
    summary: Summary
    start_capital: Decimal
    current_acc: AccountInfo
