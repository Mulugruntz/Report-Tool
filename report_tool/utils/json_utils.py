import json
import logging
from datetime import date, datetime, time
from decimal import Decimal
from pathlib import Path, PosixPath
from typing import Any, Callable, Mapping, TypedDict, TypeVar

from PyQt5.QtCore import QByteArray

DATE_FORMAT = "%Y-%m-%d"
TIME_FORMAT = "%H:%M:%S.%f"
DATETIME_FORMAT = f"{DATE_FORMAT} {TIME_FORMAT}"


logger = logging.getLogger(__name__)


class EncodedValue(TypedDict):
    """A value that can be encoded in JSON."""

    _type: str
    value: str


class RoundTripEncoder(json.JSONEncoder):
    def default(self, obj: Any) -> EncodedValue:
        if isinstance(obj, PosixPath):
            return {
                "_type": "path",
                "value": str(obj),
            }
        if isinstance(obj, datetime):
            return {
                "_type": "datetime.datetime",
                "value": obj.strftime(DATETIME_FORMAT),
            }
        if isinstance(obj, date):
            return {
                "_type": "datetime.date",
                "value": obj.strftime(DATE_FORMAT),
            }
        if isinstance(obj, time):
            return {
                "_type": "datetime.time",
                "value": obj.strftime(TIME_FORMAT),
            }
        if isinstance(obj, Decimal):
            return {
                "_type": "decimal.Decimal",
                "value": str(obj),
            }
        if isinstance(obj, QByteArray):
            return {
                "_type": "PyQt5.QtCore.QByteArray",
                "value": obj.toBase64().data().decode(),
            }
        raise TypeError(
            f"Object of type {obj.__class__.__name__} " f"is not JSON serializable"
        )


InputT = TypeVar("InputT", bound=Mapping[str, Any])


class RoundTripDecoder(json.JSONDecoder):
    def __init__(
        self,
        *,
        object_hook: Callable[[dict[str, Any]], Any | None] | None = None,
        parse_float: Callable[[str], Any | None] | None = None,
        parse_int: Callable[[str], Any | None] | None = None,
        parse_constant: Callable[[str], Any | None] | None = None,
        strict: bool = True,
        object_pairs_hook: Callable[[list[tuple[str, Any]]], Any | None] | None = None,
    ) -> None:
        if object_hook is None:
            object_hook = self.object_hook
        super().__init__(
            object_hook=object_hook,
            parse_float=parse_float,
            parse_int=parse_int,
            parse_constant=parse_constant,
            strict=strict,
            object_pairs_hook=object_pairs_hook,
        )

    @staticmethod
    def object_hook(
        obj: InputT,
    ) -> InputT | datetime | date | time | Decimal | Path | None:
        if "_type" not in obj:
            return obj
        type_ = obj["_type"]
        if type_ == "datetime.datetime":
            return datetime.strptime(obj["value"], DATETIME_FORMAT)
        if type_ == "datetime.date":
            return datetime.strptime(obj["value"], DATE_FORMAT).date()
        if type_ == "datetime.time":
            return datetime.strptime(obj["value"], TIME_FORMAT).time()
        if type_ == "decimal.Decimal":
            return Decimal(obj["value"])
        if type_ == "path":
            return Path(obj["value"])
        if type_ == "PyQt5.QtCore.QByteArray":
            return QByteArray.fromBase64(obj["value"].encode())
        logger.warning(f"Unknown type for Json Decoded: {type_}.")
        return obj


if __name__ == "__main__":
    data = {
        "name": "Report O'Toole",
        "dt": datetime.now(),
        "d": datetime.now().date(),
        "t": datetime.now().time(),
        "value": Decimal("42.23"),
    }
    json_str = json.dumps(data, cls=RoundTripEncoder, indent=2)
    print(json_str)
    data_out = json.loads(json_str, cls=RoundTripDecoder)
    assert data == data_out
    print("Success")
