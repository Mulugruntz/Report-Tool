import json
from datetime import datetime, date, time
from decimal import Decimal
import logging
from typing import Any, TypedDict, Mapping, TypeVar

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
        return super().default(obj)


InputT = TypeVar("InputT", bound=Mapping[str, Any])


class RoundTripDecoder(json.JSONDecoder):
    def __init__(self, *args, **kwargs):
        json.JSONDecoder.__init__(self, object_hook=self.object_hook, *args, **kwargs)

    @staticmethod
    def object_hook(obj: InputT) -> InputT | datetime | date | time | Decimal:
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
