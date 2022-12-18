"""Module for holding simple functions"""
import base64
import copy
import json
import logging
import logging.config
import math
import re
from decimal import Decimal

from PyQt5 import QtCore, QtGui

from report_tool.utils.constants import (
    get_comments_file,
    get_config_file,
    get_credentials_file,
    get_export_dir,
    get_root_project_dir,
    get_screenshots_dir,
)
from report_tool.utils.json_utils import RoundTripDecoder, RoundTripEncoder

RE_CONVERT = re.compile(r"^(.*)converted")

# init loggers
logger_debug = logging.getLogger("ReportTool_debug.IGAPI")
logger_info = logging.getLogger("ReportTool_info.IGAPI")


def create_graph_args(title="", x_label="", y_label="", *args, **kwargs):

    """
    Create html string for classEquityChart.EquityChart initialization

    :param title: string for graph title
    :param x_label: string for graph x_label
    :param y_label: string for graph y_label

    Return a dict
    """

    title = (
        '<span style="color: rgb(95,95,95) ;'
        'font-size : 14pt;">' + title + "</span style>"
    )

    x_label = '<span style = "font-size : 12pt">' + x_label + " </span style>"
    y_label = '<span style = "font-size : 12pt">' + y_label + "</span style>"

    graph_options = {"title": title, "labels": {"bottom": x_label, "left": y_label}}

    return graph_options


def format_market_name(market_name, *args, **kwargs):

    """
    Format market names received to a cleaner one as market
    can be e.g DAX au comptant (converted at xxx) It is use
    to have the same market name as the conversion rate changes

    :param market_name: string, raw name received from IG
    """

    try:
        match = RE_CONVERT.match(market_name)  # looks for conversion infos
        return match.group(1)  # name without conversion infos
    except AttributeError:
        return market_name


def read_ig_config(*args, **kwargs):
    """Read ig_config.json file"""
    return json.loads((get_root_project_dir() / "ig_config.json").read_text())


def read_credentials(*args, **kwargs):

    """Reads credentials files"""

    credentials_path = get_credentials_file()
    empty_account = {"pwd": "", "api_key": "", "type": "Live", "proxies": {"https": ""}}

    saved_accounts = {}

    with credentials_path.open("r") as f:
        try:
            saved_accounts = json.load(f, cls=RoundTripDecoder)

            for key in saved_accounts.keys():

                # decode pwd and api key
                decoded_pwd = base64.b64decode(saved_accounts[key]["pwd"]).decode()
                decoded_key = base64.b64decode(saved_accounts[key]["api_key"]).decode()

                saved_accounts[key]["api_key"] = decoded_key
                saved_accounts[key]["pwd"] = decoded_pwd

            if saved_accounts == {}:
                saved_accounts[""] = empty_account

        # log error and returns empty account
        except Exception as e:
            msg = "No users save"
            logger_debug.log(logging.ERROR, msg)
            saved_accounts[""] = empty_account

    return saved_accounts


def write_credentials(credentials):

    """
    Write credentials

    :param credentials: dict with all users saved
    """

    credentials_path = get_credentials_file()

    with credentials_path.open("w") as f:
        for key in credentials.keys():

            # encode pwd and api key
            encoded_pwd = base64.b64encode(credentials[key]["pwd"].encode()).decode()
            encoded_key = base64.b64encode(
                credentials[key]["api_key"].encode()
            ).decode()

            credentials[key]["api_key"] = encoded_key
            credentials[key]["pwd"] = encoded_pwd

        # write dict (default or not)
        json.dump(credentials, f, cls=RoundTripEncoder, indent=4)


def read_comment(*args, **kwargs):

    """Reads comments files"""

    comment_path = get_comments_file()

    with comment_path.open("r") as f:
        try:
            saved_comments = json.load(f, cls=RoundTripDecoder)

        # log error and returns empty dict
        except Exception as e:
            msg = "No comments saved for this user"
            logger_debug.log(logging.ERROR, msg)
            saved_comments = {}

    return saved_comments


def write_comments(comments):

    """
    Write credentials

    :param coments: dict of comments to saved
    """

    comment_path = get_comments_file()

    with comment_path.open("w") as f:
        json.dump(comments, f, cls=RoundTripEncoder)  # write dict (default or not)


def read_config() -> dict:

    """
    Simple function to read config file and manages moslty
    common errors. In case of errors returns a default dict
    I may used QSettings instead of custom config file
    """
    # TODO: call read_config less often!

    default_dict = {
        "ec_size": 3,
        "ec_style": "Solid",
        "ec_color": "#000000",
        "dd_size": 11,
        "maxdd_style": "o",
        "maxdd_color": "#ff0000",
        "high_style": "o",
        "high_color": "#00ff00",
        "depth_style": "o",
        "depth_color": "#ffaa00",
        "profit_color": "#32CD32",
        "flat_color": "#000000",
        "loss_color": "#E62309",
        "currency_symbol": "\u20ac",
        "what_to_print": "All window",
        "result_in": "Points",
        "last_usr": "",
        "dir_out": get_screenshots_dir(),
        "shortcut": "Enter shorcut",
        "start_capital": 0,
        "auto_calculate": 2,
        "what_to_show": {
            "state_infos": "Only for screenshot",
            "state_size": "Only for screenshot",
            "state_details": 0,
            "state_dates": 0,
            "high": 2,
            "depth": 2,
            "maxdd": 2,
        },
        "include": 2,
        "all": 2,
        "auto_connect": 0,
        "agregate": 0,
        "gui_state": QtCore.QByteArray(b""),
        "gui_size": (800, 600),
        "gui_pos": (0, 0),
        "dir_export": get_export_dir(),
        "what_to_export": "All",
        "separator": ";",
    }

    config = {}
    config_path = get_config_file()

    with config_path.open("r") as f:

        try:
            data_read = json.load(f, cls=RoundTripDecoder)

            for key in default_dict.keys():

                if key == "start_capital":

                    start_capital = data_read["start_capital"]

                    # no capital set
                    if start_capital == "":
                        start_capital = 0
                    else:
                        start_capital = Decimal(data_read["start_capital"])

                    config["start_capital"] = start_capital

                # no dir for screenchots saved
                elif key == "dir_out":

                    dir_out = data_read["dir_out"]

                    if dir_out == "":
                        dir_out = default_dict["dir_out"]
                    else:
                        dir_out = data_read["dir_out"]

                    config["dir_out"] = dir_out

                elif key == "dir_export":

                    dir_export = data_read["dir_export"]

                    if dir_export == "":
                        dir_export = default_dict["dir_export"]
                    else:
                        dir_export = data_read["dir_export"]

                    config["dir_export"] = dir_export
                elif key == "gui_state":
                    config["gui_state"] = QtCore.QByteArray.fromBase64(
                        data_read["gui_state"].encode()
                    )
                else:
                    config[key] = data_read[key]

        except Exception as e:
            msg = "Error while loading configuration, use default one"
            logger_debug.log(logging.ERROR, msg)

            for key in default_dict:
                config[key] = default_dict[key]
            write_config(config)

    return config


def write_config(config):

    """
    Write config file

    :param: config: dict of config to save
    """

    config_file = get_config_file()
    out_config = copy.deepcopy(config)
    out_config["gui_state"] = out_config["gui_state"].toBase64().data().decode()
    with config_file.open("w") as f:
        # write dict (default or not)
        json.dump(out_config, f, cls=RoundTripEncoder, indent=4)


def create_dates_list(state_dates, dates_string, key, start_capital):

    """
    Create a dict used to update x_axis values and string.

    :param state_dates: boolean, show or not dates on axis
    :param dates_string: list of dates plotted
    :param key: string, type of graph
    :param start_capital: float
    """

    # keys are idx of trade and values are date string
    if state_dates == 2:
        xaxis_dict = dict(enumerate(dates_string))

    # keys and values are idx of trades
    else:
        xaxis_dict = {i: i for i in range(len(dates_string))}

    if key == "Growth" and start_capital == 0.0:
        xaxis_dict = {}  # don"t set string if no data

    return xaxis_dict


def create_icons():

    """
    Function to create icons set in combobox of options windows.
    Icons correspond to avalaible style for curves and scatter plot.
    Symbols available for sctter plot can be found in
    ScatterPlotItem.py file in the pyqtgraph folder.
    """

    style_list = [
        QtCore.Qt.SolidLine,
        QtCore.Qt.DashLine,
        QtCore.Qt.DotLine,
        QtCore.Qt.DashDotLine,
        QtCore.Qt.DashDotDotLine,
    ]  # list with avalaible QtStyle

    style_name_list = ["Solid", "Dash", "Dot", "Dash Dot", "Dash Dot Dot"]

    # init dict to hold icons
    ec_icons = {}
    dd_pixmap = {}
    color = QtGui.QColor(36, 36, 36)

    # create line with available style
    for count, style in enumerate(style_list):
        pixmap = QtGui.QPixmap(100, 14)
        pixmap.fill(QtCore.Qt.transparent)

        painter = QtGui.QPainter(pixmap)
        pen = QtGui.QPen()
        name = style_name_list[count]
        pen.setColor(color)  # configure pen
        pen.setWidth(3)
        pen.setStyle(style)  # set style

        painter.setPen(pen)
        painter.drawLine(2, 7, 98, 7)  # draw line
        painter.end()
        ec_icons[name] = QtGui.QIcon(pixmap)  # add it to dict

    # configure default brush for symbol
    brush = QtGui.QBrush(color, QtCore.Qt.SolidPattern)

    # configure default pen
    pen = QtGui.QPen()
    pen.setColor(color)
    pen.setWidth(1)
    pen.setStyle(QtCore.Qt.SolidLine)

    # create a square symbol
    pixmap = QtGui.QPixmap(100, 14)
    pixmap.fill(QtCore.Qt.transparent)

    painter = QtGui.QPainter(pixmap)
    painter.setPen(pen)
    painter.setBrush(brush)
    painter.fillRect(0, 0, 14, 14, brush)
    painter.end()

    dd_pixmap["s"] = QtGui.QIcon(pixmap)

    # create a rotated square symbol
    pixmap = QtGui.QPixmap(100, 14)
    pixmap.fill(QtCore.Qt.transparent)

    painter = QtGui.QPainter(pixmap)
    painter.setRenderHint(QtGui.QPainter.Antialiasing)
    painter.rotate(45)
    painter.translate(math.sqrt((14**2) / 2) / 2, -math.sqrt((14**2) / 2) / 2)
    painter.setPen(pen)
    painter.setBrush(brush)
    painter.fillRect(
        QtCore.QRectF(0, 0, math.sqrt((14**2) / 2), math.sqrt((14**2) / 2)), brush
    )
    painter.resetTransform()
    painter.end()

    dd_pixmap["d"] = QtGui.QIcon(pixmap)

    # create a circle symbol
    pixmap = QtGui.QPixmap(100, 14)
    pixmap.fill(QtCore.Qt.transparent)

    painter = QtGui.QPainter(pixmap)
    painter.setRenderHint(QtGui.QPainter.Antialiasing)
    painter.setPen(pen)
    painter.setBrush(brush)
    painter.drawEllipse(QtCore.QRectF(0.5, 0.5, 13, 13))
    painter.end()

    dd_pixmap["o"] = QtGui.QIcon(pixmap)

    # create a triangulare symbol
    pixmap = QtGui.QPixmap(100, 14)
    pixmap.fill(QtCore.Qt.transparent)

    painter = QtGui.QPainter(pixmap)
    painter.setRenderHint(QtGui.QPainter.Antialiasing)
    painter.setPen(pen)
    painter.setBrush(brush)
    triangle_points = [
        QtCore.QPointF(0.5, 0.5),
        QtCore.QPointF(13.5, 0.5),
        QtCore.QPointF(7, 13.5),
    ]
    painter.drawPolygon(QtGui.QPolygonF(triangle_points))
    painter.end()

    dd_pixmap["t"] = QtGui.QIcon(pixmap)

    pen.setWidth(2)  # change pen width for cross symbols

    # create a cross symbol
    pixmap = QtGui.QPixmap(100, 14)
    pixmap.fill(QtCore.Qt.transparent)

    painter = QtGui.QPainter(pixmap)
    painter.setRenderHint(QtGui.QPainter.Antialiasing)
    painter.setPen(pen)
    painter.setBrush(brush)
    painter.drawLines([QtCore.QLineF(1, 7, 13, 7), QtCore.QLineF(7, 13, 7, 1)])
    painter.end()

    dd_pixmap["+"] = QtGui.QIcon(pixmap)

    # create a rotated cross symbol
    pixmap = QtGui.QPixmap(100, 14)
    pixmap.fill(QtCore.Qt.transparent)

    painter = QtGui.QPainter(pixmap)
    painter.setRenderHint(QtGui.QPainter.Antialiasing)
    painter.setPen(pen)
    painter.setBrush(brush)
    painter.drawLines([QtCore.QLineF(2, 2, 12, 12), QtCore.QLineF(2, 12, 12, 2)])
    painter.end()

    dd_pixmap["x"] = QtGui.QIcon(pixmap)

    return (ec_icons, dd_pixmap)


def create_status_icons(color):

    """
    Create a circle icons for status bar

    :param color: string, color can be red or green depending of status
    """

    brush = QtGui.QBrush(color, QtCore.Qt.SolidPattern)

    # configure default pen
    pen = QtGui.QPen()
    pen.setColor(color)
    pen.setWidth(1)
    pen.setStyle(QtCore.Qt.SolidLine)

    # create a circle symbol
    pixmap = QtGui.QPixmap(100, 14)
    pixmap.fill(QtCore.Qt.transparent)

    painter = QtGui.QPainter(pixmap)
    painter.setRenderHint(QtGui.QPainter.Antialiasing)
    painter.setPen(pen)
    painter.setBrush(brush)
    painter.drawEllipse(QtCore.QRectF(0.5, 0.5, 13, 13))
    painter.end()

    circle = pixmap

    return circle
