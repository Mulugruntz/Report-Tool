import json
import datetime
from decimal import Decimal
import logging

DATE_FORMAT = "%Y-%m-%d"
TIME_FORMAT = "%H:%M:%S.%f"
DATETIME_FORMAT = f"{DATE_FORMAT} {TIME_FORMAT}"


logger = logging.getLogger(__name__)


class RoundTripEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime.datetime):
            return {
                "_type": "datetime.datetime",
                "value": obj.strftime(DATETIME_FORMAT),
            }
        if isinstance(obj, datetime.date):
            return {
                "_type": "datetime.date",
                "value": obj.strftime(DATE_FORMAT),
            }
        if isinstance(obj, datetime.time):
            return {
                "_type": "datetime.time",
                "value": obj.strftime(TIME_FORMAT),
            }
        if isinstance(obj, Decimal):
            return {
                "_type": "decimal.Decimal",
                "value": str(obj),
            }
        return super(RoundTripEncoder, self).default(obj)


class RoundTripDecoder(json.JSONDecoder):
    def __init__(self, *args, **kwargs):
        json.JSONDecoder.__init__(self, object_hook=self.object_hook, *args, **kwargs)

    def object_hook(self, obj):
        if "_type" not in obj:
            return obj
        type = obj["_type"]
        if type == "datetime.datetime":
            return datetime.datetime.strptime(obj["value"], DATETIME_FORMAT)
        if type == "datetime.date":
            return datetime.datetime.strptime(obj["value"], DATE_FORMAT).date()
        if type == "datetime.time":
            return datetime.datetime.strptime(obj["value"], TIME_FORMAT).time()
        if type == "decimal.Decimal":
            return Decimal(obj["value"])
        logger.warning(f"Unknown type for Json Decoded: {type}.")
        return obj


if __name__ == "__main__":
    data = {
        "name": "Report O'Toole",
        "dt": datetime.datetime.now(),
        "d": datetime.datetime.now().date(),
        "t": datetime.datetime.now().time(),
        "value": Decimal("42.23"),
    }
    json_str = json.dumps(data, cls=RoundTripEncoder, indent=2)
    print(json_str)
    data_out = json.loads(json_str, cls=RoundTripDecoder)
    assert data == data_out
    print("Success")
