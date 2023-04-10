import datetime
import json
import logging
import os
import queue as queue
import re
import traceback
import warnings
from collections import OrderedDict
from copy import deepcopy
from decimal import Decimal

import numpy as np
import pyqtgraph as pg
from PyQt5 import QtCore, QtGui, QtWidgets

from report_tool.calculate.trades import TradesResults
from report_tool.communications.ig_lightstreamer import (
    MODE_DISTINCT,
    MODE_MERGE,
    LsClient,
    Table,
)
from report_tool.communications.ig_rest_api import IGAPI, APIError
from report_tool.exports.excel import ExportToExcel
from report_tool.qt.dialog_box import (
    AboutWindow,
    ConnectWindow,
    ExportWindow,
    FilterWindow,
    OptionsWindow,
)
from report_tool.qt.equity_chart import EquityChart
from report_tool.qt.functions import (
    create_dates_list,
    create_graph_args,
    create_status_icons,
    read_credentials,
    read_ig_config,
)
from report_tool.qt.ls_event import LsEvent
from report_tool.qt.thread import TransactionThread, UpdateCommentsThread
from report_tool.qt.widgets import CustomDockWidget, CustomLabel, CustomLineEdit
from report_tool.utils.fs_utils import get_icon_path
from report_tool.utils.settings import read_config, write_config

RE_TEXT_BETWEEN_TAGS = re.compile(r">(.*?)<")
RE_FLOAT = re.compile(r"[+-]? *(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?")
RE_BEFORE_SLASH_HYPHEN = re.compile(r"(.*?[A-z])[-/]")
RE_SPACE_START = re.compile(r"(.*?[A-z])\s")
RE_SPACE_START_COLON_END = re.compile(r"(\s.*?[A-z]): ")
RE_COLON_END = re.compile(r"(.*?[A-z]): ")
RE_UNDERSCORE_START = re.compile(r"_(.*)")


class ReportToolGUI(QtWidgets.QMainWindow):

    """Main class for ReportTool"""

    def __init__(self, title):
        """Init UI"""

        super(ReportToolGUI, self).__init__()

        self.data_exporter: ExportToExcel | None = None

        config = read_config()

        # load size and state of window
        state = config["gui_state"]

        size = config["gui_size"]
        size = QtCore.QSize(size[0], size[1])

        pos = config["gui_pos"]
        pos_point = QtCore.QPoint(pos[0], pos[1])

        self.create_menus()
        self.create_dock_options()
        self.create_dock_summary()
        self.create_dock_account()
        self.create_dock_details()
        self.create_central_widget()

        self.set_gui_enabled(False)  # disable interactions
        self.setMouseTracking(True)

        self.setWindowTitle(title)
        self.statusBar().showMessage("Not connected")
        self.setWindowIcon(QtGui.QIcon(str(get_icon_path("main"))))

        self.restoreState(state)
        self.resize(size)
        self.move(pos_point)

        # init loggers
        self.logger_debug = logging.getLogger("ReportTool_debug.IGAPI")
        self.logger_info = logging.getLogger("ReportTool_info.IGAPI")

        auto_connect = config["auto_connect"]

        if auto_connect == 2:
            self.connect_to_api(True)

    def create_menus(self):
        """
        Create menus
        -- One menu to connect/disconnect and switching
        between user accounts (sub-menu)
        -- One menu for options
        -- One menu for an about window
        """

        # create icons
        icon_disconnect = QtGui.QIcon(str(get_icon_path("disconnect")))
        icon_connect = QtGui.QIcon(str(get_icon_path("connect")))
        icon_infos = QtGui.QIcon(str(get_icon_path("info")))
        icon_options = QtGui.QIcon(str(get_icon_path("options")))
        icon_switch = QtGui.QIcon(str(get_icon_path("switch")))
        icon_refresh = QtGui.QPixmap(str(get_icon_path("refresh")))
        icon_screenshot = QtGui.QPixmap(str(get_icon_path("photo16")))
        icon_export = QtGui.QPixmap(str(get_icon_path("export")))

        # create menus
        self.menu_switch = QtWidgets.QMenu("Switch account")
        self.menu_connect = self.menuBar().addMenu("Connect")
        self.menu_options = self.menuBar().addMenu("&Options")
        self.menu_help = self.menuBar().addMenu("&Help")

        # create actions
        self.act_connect = QtWidgets.QAction(icon_connect, "Connect", self)
        self.act_connect.setStatusTip("Connect to API")
        self.act_connect.triggered.connect(self.connect_to_api)

        self.act_disconnect = QtWidgets.QAction(icon_disconnect, "Disconnect", self)
        self.act_disconnect.setStatusTip("Disconnect from API")
        self.act_disconnect.triggered.connect(self.disconnect_from_api)
        self.act_disconnect.setEnabled(False)

        self.act_about = QtWidgets.QAction(icon_infos, "About", self)
        self.act_about.triggered.connect(self.show_about)
        self.act_about.setEnabled(True)
        self.act_about.setCheckable(False)

        self.act_options = QtWidgets.QAction(icon_options, "Options", self)
        self.act_options.triggered.connect(self.show_options)
        self.act_options.setEnabled(False)
        self.act_options.setCheckable(False)

        #  action to be replaced by user accounts
        dummy_act = QtWidgets.QAction("Not connected", self)
        dummy_act.setEnabled(False)
        dummy_act.setCheckable(False)

        # configure connection menu
        self.menu_connect.addAction(self.act_connect)
        self.menu_switch.addAction(dummy_act)
        self.menu_connect.addMenu(self.menu_switch)
        self.menu_connect.addAction(self.act_disconnect)

        # configure menus
        self.menu_options.addAction(self.act_options)
        self.menu_help.addAction(self.act_about)
        self.menu_switch.setIcon(icon_switch)
        self.menu_switch.setEnabled(False)

        # create buttons to update results and take screenshot
        self.btn_screenshot = CustomLabel("lbl_screen")
        self.btn_refresh = CustomLabel("lbl_refresh")
        self.btn_export = CustomLabel("lbl_export")

        widget_corner = QtWidgets.QWidget()
        layout_corner = QtWidgets.QHBoxLayout()

        # configure refresh button
        self.btn_refresh.set_default_style("transparent", "#D7D9DB", "#5F6061")

        self.btn_refresh.setFixedSize(18, 18)
        self.btn_refresh.setPixmap(icon_refresh)
        self.btn_refresh.setStatusTip("Refresh transactions")

        # configure screenshot button
        self.btn_screenshot.set_default_style("transparent", "#D7D9DB", "#5F6061")

        self.btn_screenshot.setFixedSize(18, 18)
        self.btn_screenshot.setPixmap(icon_screenshot)
        self.btn_screenshot.setStatusTip("Take a screenshot")

        # configure export button
        self.btn_export.set_default_style("transparent", "#D7D9DB", "#5F6061")

        self.btn_export.setFixedSize(18, 18)
        self.btn_export.setPixmap(icon_export)
        self.btn_export.setStatusTip("No data to export")

        # connect signals
        self.btn_refresh.clicked_signal.connect(self.update_transactions)
        self.btn_screenshot.clicked_signal.connect(self.take_screenshot)
        self.btn_export.clicked_signal.connect(self.show_export)

        # add buttons to top right corner of window
        layout_corner.addWidget(self.btn_refresh)
        layout_corner.addWidget(self.btn_screenshot)
        layout_corner.addWidget(self.btn_export)
        widget_corner.setLayout(layout_corner)
        self.menuBar().setCornerWidget(widget_corner, QtCore.Qt.TopRightCorner)

        # create and configure a button to take screeenshot
        disconnected_color = QtGui.QColor("#F51616")
        icon_status = create_status_icons(disconnected_color)
        self.lbl_status = QtWidgets.QLabel()

        self.lbl_status.setFixedSize(18, 18)
        self.lbl_status.setPixmap(icon_status)
        self.statusBar().addPermanentWidget(self.lbl_status)

    def create_central_widget(self):
        """
        Creates a central tabbed widget (4 tabs).
        One tab contains a QTableWidget with all past positions.
        The three other ones contain 2 pyqtgraph plotWidget per tab.
        One plot widget is for equity curves and drawdown/depth/high
        plotted as scatter. The bottom plot is simplified with
        only equity curve and a linear region item that can be used
        navigate throught the top plot.
        """

        # create lists of columns headers for QTableWidget
        transaction_headers = [
            "Date ",
            "Market",
            "Direction",
            "Open Size",
            "Open",
            "Close",
            "Points",
            "Points/lot",
            "Profit/Loss",
        ]

        config = read_config()

        currency_symbol = config["currency_symbol"]

        # init and configure transaction QTableWidget
        self.widget_pos = QtWidgets.QTableWidget(1, len(transaction_headers))

        self.widget_pos.setObjectName("Transactions")
        self.widget_pos.setMinimumHeight(100)
        self.widget_pos.setHorizontalHeaderLabels(transaction_headers)

        self.widget_pos.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.widget_pos.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.widget_pos.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)

        # create equity graph
        pg.setConfigOption("background", (242, 242, 237))
        pg.setConfigOptions(antialias=True)

        points_args = create_graph_args(
            "Points over the period", "# of trades", "Points"
        )

        capital_args = create_graph_args(
            "Capital over the period", "# of trades", "Capital" + currency_symbol
        )

        growth_args = create_graph_args(
            "Capital growth over the period", "# of trades", "Capital growth (%)"
        )

        points_graph = EquityChart(**points_args)  # point graph

        currency_graph = EquityChart(**capital_args)  # currency graph

        growth_graph = EquityChart(**growth_args)  # growth graph

        self.graph_dict = OrderedDict([("Points", {}), ("Capital", {}), ("Growth", {})])

        # following lists whill be used to easily create central widget
        graph_list = [points_graph, currency_graph, growth_graph]

        # keys for nested dict. order matters to keep max dd visible
        scatter_list = ["high", "depth", "maxdd"]
        title_list = ["Points", "Capital", "Growth"]

        # get configuration of curves and scatter
        ec_color = config["ec_color"]
        ec_size = config["ec_size"]
        ec_style = config["ec_style"]

        scatter_color = [
            config["maxdd_color"],
            config["depth_color"],
            config["high_color"],
        ]

        scatter_style = [
            config["maxdd_style"],
            config["depth_style"],
            config["high_style"],
        ]

        scatter_size = config["dd_size"]

        # init and configure tab widget
        self.widget_tab = QtWidgets.QTabWidget()

        self.widget_tab.setMovable(True)
        self.widget_tab.addTab(self.widget_pos, "Transactions")

        zero_pen = pg.mkPen(color=(95, 95, 95), width=1, style=QtCore.Qt.SolidLine)

        for count, equity_plot in enumerate(graph_list):
            # create a simplified plotWidget
            overview_plot = EquityChart(title=None, x_label=None, y_label=None)

            tab_text = title_list[count]

            self.graph_dict[tab_text]["equity_plot"] = equity_plot
            self.graph_dict[tab_text]["overview_plot"] = overview_plot
            self.graph_dict[tab_text]["curve"] = OrderedDict()

            # splitter between the two plot widgets
            splitter = QtWidgets.QSplitter()
            splitter.setOrientation(QtCore.Qt.Vertical)
            splitter.setStyleSheet(
                "QSplitter:handle:vertical{height: 6px;\
                                                    background-color: white}"
            )

            # create curves
            equity_curve = equity_plot.plot_curve(ec_color, ec_size, ec_style)
            overview_curve = overview_plot.plot_curve(ec_color, ec_size, ec_style)
            region = overview_plot.linear_region  # region for bottom graph

            overview_plot.addItem(region)

            equity_plot.sigRangeChanged.connect(self.update_overview_graph)
            region.sigRegionChanged.connect(self.update_equity_graph)

            """
            build a nested dict with type of graph as main key
            equity_plot contains a equity curve and 3 scatter
            plot for drawdown value(max, depth, high). overview
            plot only contains an equity curve with same style
            """

            self.graph_dict[tab_text]["curve"]["equity_curve"] = equity_curve
            self.graph_dict[tab_text]["curve"]["overview_curve"] = overview_curve

            # init curves for dd, max dd and depth
            for idx, scatter_type in enumerate(scatter_list):
                scatter_plot = equity_plot.plot_scatter(
                    scatter_color[idx], scatter_style[idx], scatter_size
                )
                equity_plot.addItem(scatter_plot)
                self.graph_dict[tab_text]["curve"][scatter_type] = scatter_plot

            # configure top plot
            equity_plot.plotItem.showGrid(x=True, y=True, alpha=1)
            equity_plot.getAxis("bottom").setPen(zero_pen)
            equity_plot.getAxis("left").setPen(zero_pen)

            # configure bottom plot
            overview_plot.plotItem.showGrid(x=True, y=True, alpha=1)
            overview_plot.getAxis("bottom").setPen(zero_pen)
            overview_plot.getAxis("left").setPen(zero_pen)
            overview_plot.plotItem.hideAxis("left")

            # populate splitter
            splitter.addWidget(equity_plot)
            splitter.addWidget(overview_plot)

            # set plot sizes bottom graph height is 1/5 of the top one
            height = equity_plot.geometry().height()
            splitter.setSizes([height, height // 5])

            self.widget_tab.addTab(splitter, str(tab_text))

        self.setCentralWidget(self.widget_tab)  # set widget as central widget

    def create_dock_options(self):
        """
        Creates a dock widget with:
        -->QDateEdit to choose period of analyse,
        -->combobox to choose "units" of result (point, %, €...)
        -->line edit to manually enter start capital,
        -->checkbox to auto calculated or not capital,
        -->checkbox to aggregate or not positions,
        -->checkbox to include or not interest/fees,
        -->custom clickable label to set a filter
        """

        config = read_config()  # load config file

        icon_filter = QtGui.QPixmap(str(get_icon_path("filter")))

        capital = config["start_capital"]
        currency_symbol = config["currency_symbol"]
        auto_calculate = config["auto_calculate"]
        result_in = config["result_in"]
        include = config["include"]
        aggregate = config["aggregate"]

        # init widgets and layout for dates
        dock_options = QtWidgets.QDockWidget("Report options")
        widget_main = QtWidgets.QWidget()
        layout_dock = QtWidgets.QVBoxLayout()
        widget_date = QtWidgets.QGroupBox("Period of analyze")
        layout_date = QtWidgets.QGridLayout()

        LABEL_START_DATE = QtWidgets.QLabel("From: ")
        LABEL_END_DATE = QtWidgets.QLabel("To: ")
        self.start_date = QtWidgets.QDateEdit()
        self.end_date = QtWidgets.QDateEdit()

        today = datetime.datetime.now().strftime("%d/%m/%Y")

        # configure date widgets
        self.start_date.setMaximumWidth(100)
        self.start_date.setCalendarPopup(True)  # enable widget calendar popup
        self.start_date.setDisplayFormat("dd/MM/yyyy")  # set date format
        self.start_date.setDate(QtCore.QDate.fromString(today, "dd/MM/yyyy"))
        self.start_date.setMaximumDate(QtCore.QDate.fromString(today, "dd/MM/yyyy"))

        self.end_date.setMaximumWidth(100)
        self.end_date.setCalendarPopup(True)
        self.end_date.setDisplayFormat("dd/MM/yyyy")
        self.end_date.setDate(QtCore.QDate.fromString(today, "dd/MM/yyyy"))
        self.end_date.setMaximumDate(QtCore.QDate.fromString(today, "dd/MM/yyyy"))

        # set widget on layout
        layout_date.addWidget(LABEL_START_DATE, 0, 0, 1, 1)
        layout_date.addWidget(self.start_date, 0, 1, 1, 1)
        layout_date.addWidget(LABEL_END_DATE, 0, 2, 1, 1)
        layout_date.addWidget(self.end_date, 0, 3, 1, 1)

        # init widget for summary options
        widget_options = QtWidgets.QGroupBox("Summary options")
        layout_options = QtWidgets.QGridLayout()

        LABEL_CAPITAL = QtWidgets.QLabel("Initial capital: ")
        LABEL_AUTO = QtWidgets.QLabel("Auto-calculate: ")
        LABEL_OPTIONS = QtWidgets.QLabel("Show results in: ")
        LABEL_INCLUDE = QtWidgets.QLabel("Include interests/fees: ")
        LABEL_AGREGATE = QtWidgets.QLabel("Agregate positions: ")
        LABEL_FILTER = QtWidgets.QLabel("Set a filter: ")

        self.line_edit_capital = CustomLineEdit()
        self.btn_filter = CustomLabel("btn_filter")
        self.combobox_options = QtWidgets.QComboBox()
        self.checkbox_auto = QtWidgets.QCheckBox()
        self.checkbox_include = QtWidgets.QCheckBox()
        self.checkbox_aggregate = QtWidgets.QCheckBox()

        list_options = ["Points", "Points/lot", currency_symbol, "%"]
        option_idx = list_options.index(result_in)

        # confiure widgets
        self.line_edit_capital.blockSignals(True)
        self.line_edit_capital.setText(f"{capital:.2f} {currency_symbol}")
        self.line_edit_capital.blockSignals(False)
        self.line_edit_capital.setFixedWidth(120)

        self.combobox_options.addItems(list_options)
        self.combobox_options.setCurrentIndex(option_idx)
        self.combobox_options.setFixedWidth(120)

        self.checkbox_auto.setCheckState(auto_calculate)
        self.checkbox_include.setCheckState(include)
        self.checkbox_aggregate.setCheckState(aggregate)

        """
        create a mapper to identify sender when option
        is changed. Mapper send name of widget
        """

        self.options_mapper = QtCore.QSignalMapper()

        # set object name to identify checkbox
        self.checkbox_auto.setObjectName("auto_calculate")
        self.checkbox_include.setObjectName("include")
        self.checkbox_aggregate.setObjectName("aggregate")

        self.checkbox_auto.stateChanged.connect(self.options_mapper.map)
        self.options_mapper.setMapping(self.checkbox_auto, "auto_calculate")

        self.checkbox_aggregate.stateChanged.connect(self.options_mapper.map)
        self.options_mapper.setMapping(self.checkbox_aggregate, "aggregate")

        self.checkbox_include.stateChanged.connect(self.options_mapper.map)
        self.options_mapper.setMapping(self.checkbox_include, "include")

        self.combobox_options.currentIndexChanged.connect(self.options_mapper.map)
        self.options_mapper.setMapping(self.combobox_options, "result_in")
        self.options_mapper.mapped[str].connect(self.update_options)

        self.btn_filter.setPixmap(icon_filter)
        self.btn_filter.set_default_style("transparent", "transparent", "transparent")

        # add widgets on layout
        layout_options.addWidget(LABEL_OPTIONS, 0, 0, QtCore.Qt.AlignLeft)
        layout_options.addWidget(self.combobox_options, 0, 1, QtCore.Qt.AlignLeft)

        layout_options.addWidget(LABEL_CAPITAL, 1, 0, QtCore.Qt.AlignLeft)
        layout_options.addWidget(self.line_edit_capital, 1, 1, QtCore.Qt.AlignLeft)

        layout_options.addWidget(LABEL_AUTO, 2, 0, QtCore.Qt.AlignLeft)
        layout_options.addWidget(self.checkbox_auto, 2, 1, QtCore.Qt.AlignLeft)

        layout_options.addWidget(LABEL_INCLUDE, 3, 0, QtCore.Qt.AlignLeft)
        layout_options.addWidget(self.checkbox_include, 3, 1, QtCore.Qt.AlignLeft)

        layout_options.addWidget(LABEL_AGREGATE, 4, 0, QtCore.Qt.AlignLeft)
        layout_options.addWidget(self.checkbox_aggregate, 4, 1, QtCore.Qt.AlignLeft)

        layout_options.addWidget(LABEL_FILTER, 5, 0, QtCore.Qt.AlignLeft)
        layout_options.addWidget(self.btn_filter, 5, 1, QtCore.Qt.AlignLeft)

        # connect others signals
        self.start_date.dateChanged.connect(self.update_transactions)
        self.end_date.dateChanged.connect(self.update_transactions)

        self.line_edit_capital.textChanged.connect(self.update_capital)
        self.line_edit_capital.finish_signal.connect(self.update_options)

        self.btn_filter.clicked_signal.connect(self.show_filter)

        # set layout on widgets
        widget_date.setLayout(layout_date)
        widget_options.setLayout(layout_options)

        # configure main widget
        layout_dock.addWidget(widget_date)
        layout_dock.addWidget(widget_options)
        widget_main.setLayout(layout_dock)

        # configure dock widget
        dock_options.setObjectName("Report options")
        dock_options.setWidget(widget_main)
        dock_options.setFeatures(
            QtWidgets.QDockWidget.DockWidgetFloatable
            | QtWidgets.QDockWidget.DockWidgetMovable
        )

        self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, dock_options)

    def create_dock_summary(self):
        """Creates a QDockWidget with qlabel to show stat about trades."""

        # load config
        config = read_config()

        currency_symbol = config["currency_symbol"]
        result_in = config["result_in"]
        include = config["include"]
        aggregate = config["aggregate"]

        dock_summary = QtWidgets.QDockWidget("Summary")

        # creates a list of what is calculated to
        # easily create corresponding labels
        summary_headers = [
            "Points won",
            "Trades won",
            "Points lost",
            "Trades lost",
            "Total points",
            "Trades flat",
            "",
            "",  # for h_line see loop
            "Total trades",
            "Avg trade",
            "Profit Factor",
            "Avg win",
            "Capital growth",
            "Avg loss",
            "Max drawdown",
            "Avg drawdown",
            "Consec. wins",
            "Consec. losses",
            "",
            "",  # for h_line see loop
            "Interests",
            "Fees",
            "Cash in/out",
            "Transfers",
        ]

        widget_summary = QtWidgets.QWidget()
        layout_summary = QtWidgets.QGridLayout()

        """
        Loop over summary_headers to create and place
        Qlabels and to populate dict_summary_labels
        with header as keys and a QLabel as value.
        """

        self.dict_summary_labels = {}
        k = 0
        for count, header in enumerate(summary_headers):
            if header == "":  # add horizontal line
                h_line = QtWidgets.QFrame()
                h_line.setFrameShape(QtWidgets.QFrame.HLine)
                h_line.setStyleSheet("color:rgb(173,173,173);")
                layout_summary.addWidget(h_line, int(count / 2), 0, 1, 2)

            else:
                label = QtWidgets.QLabel(header + ": ")
                self.dict_summary_labels[header] = label

                if count % 2 == 0:
                    layout_summary.addWidget(
                        label, int(count / 2), 0, 1, 1, QtCore.Qt.AlignLeft
                    )
                else:
                    layout_summary.addWidget(
                        label, int(count / 2), 1, 1, 1, QtCore.Qt.AlignLeft
                    )
                k += 1

        widget_summary.setLayout(layout_summary)

        # configure dock widget
        dock_summary.setObjectName("Summary")
        dock_summary.setWidget(widget_summary)
        dock_summary.setFeatures(
            QtWidgets.QDockWidget.DockWidgetFloatable
            | QtWidgets.QDockWidget.DockWidgetMovable
        )

        self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, dock_summary)

    def create_dock_account(self):
        """
        Create a QDockWidget to display account
        informations (Balance, cash, profit...)
        """

        config = read_config()

        # init widgets
        dock_account = QtWidgets.QDockWidget("Account Informations")
        widget_account = QtWidgets.QWidget()
        layout_account = QtWidgets.QGridLayout()

        currency_symbol = config["currency_symbol"]  # temp currency symbol

        # init a dict to store QLabels
        self.dict_account_labels = OrderedDict()

        """
        list used to create static labels. Each string
        acts as key in self.dict_account_labels
        """

        list_account_labels = [
            "Account ID: ",
            "Account type: ",
            "Account name: ",
            "",
            "Cash available: ",
            "Account balance: ",
            "Profit/loss: ",
        ]

        """
        place labels on layout. An horizontal line
        is set between account info and cash infos
        """

        for count, static_text in enumerate(list_account_labels):
            # create and place horizontal line
            if count == 3:
                h_line = QtWidgets.QFrame()
                h_line.setFrameShape(QtWidgets.QFrame.HLine)
                h_line.setStyleSheet("color:rgb(173,173,173);")
                layout_account.addWidget(h_line, count, 0, 1, 2)

            else:
                lbl_static = QtWidgets.QLabel(static_text)
                lbl_variable = QtWidgets.QLabel()
                lbl_static.setText(static_text)

                if count > 3:  # labels displaying cash infos
                    lbl_variable.setText("xxxx" + currency_symbol)

                else:
                    lbl_variable.setText("xxxx")

                layout_account.addWidget(lbl_static, count, 0, 1, 1)
                # QtCore.Qt.AlignLeft)
                layout_account.addWidget(lbl_variable, count, 1, 1, 1)
                # QtCore.Qt.AlignRight)

                # store labels in dict
                self.dict_account_labels[static_text] = lbl_variable

        widget_account.setLayout(layout_account)

        # configure dockwidget
        dock_account.setWidget(widget_account)
        dock_account.setObjectName("dock_account")
        self.addDockWidget(QtCore.Qt.LeftDockWidgetArea, dock_account)

    def create_dock_details(self):
        """
        Create a dock that summarizes a clicked position
        Depending of state details can be shown or not
        Contains a QLineEdit and a QCheckBox to configure comments
        Others widgets are for display purpose only
        """

        config = read_config()  # load config file
        state_details = config["what_to_show"]["state_details"]

        """
        ordered dict with Label title as keys and values
        corresponding to keys in transactions dict as values
        """

        pos_details_headers = OrderedDict(
            [
                (" ", "market_name"),
                ("h_line", ""),
                ("Date", "date"),
                ("Trade", 1),
                ("Direction", "direction"),
                ("Size", "open_size"),
                ("Open", "open_level"),
                ("Close", "final_level"),
                ("Profit", "points,points_lot,pnl"),
                ("h_line_2", ""),
            ]
        )
        # init dock
        self.dock_pos_details = CustomDockWidget(self, pos_details_headers)

        self.text_edit_comment = self.dock_pos_details.text_edit_comment
        self.checkbox_showongraph = self.dock_pos_details.checkbox_showongraph

        self.text_edit_comment.textChanged.connect(self.write_comments)
        self.checkbox_showongraph.stateChanged.connect(self.write_comments)

        # show or not dock
        if state_details == 2:
            self.dock_pos_details.show()
        else:
            self.dock_pos_details.hide()

    def connect_to_api(self, auto_connect=True, *args, **kwargs):
        """
        Connect to API. If sender is the menu "Connect"
        show a dialog box to select/edit accounts.
        If connection is successful get user"s accounts
        , populate menu_switch with those accounts and update
        dock account. Finally connect to ls.

        :param auto_connect: boolean if true do not show a diagbox

        :kw param connect_dict: dict with data needed to make a request
                                See ConnectWindow
        """

        """
        try disconnect from lightstreamer. Avoid multiple
        subscription between demo and live account
        """

        try:
            self.ls_client.delete(self.balance_table)
            self.ls_client.delete(self.pos_table)
            self.ls_client.destroy()

        except AttributeError:
            pass

        """
        list is the same used to create static labels in
        create_dock_account (and self.dict_account_labels)
        here it used to created the keys of
        """

        list_account_labels = [
            "Account ID: ",
            "Account type: ",
            "Account name: ",
            "Cash available: ",
            "Account balance: ",
            "Profit/loss: ",
        ]

        credentials = read_credentials()
        config = read_config()
        ig_urls = read_ig_config()

        # auto connect do not show connect window
        if auto_connect == True:
            last_usr = config["last_usr"]
            acc_type = credentials[last_usr]["type"]
            pwd = credentials[last_usr]["pwd"]
            api_key = credentials[last_usr]["api_key"]
            proxies = credentials[last_usr]["proxies"]

            if acc_type == "Live":
                base_url = ig_urls["base_url"]["live"]
            elif acc_type == "Demo":
                base_url = ig_urls["base_url"]["demo"]

            connect_dict = {}

            payload = json.dumps({"identifier": last_usr, "password": pwd})

            headers = {
                "Content-Type": "application/json; charset=utf-8",
                "Accept": "application/json; charset=utf-8",
                "X-IG-API-KEY": api_key,
            }

            # build dict to connect to api
            connect_dict["base_url"] = base_url
            connect_dict["payload"] = payload
            connect_dict["headers"] = headers
            connect_dict["proxies"] = proxies

        # called by connect menu, show connect window
        elif self.sender().text() == "Connect":
            self.set_gui_enabled(False)  # disable interaction

            if self.dock_pos_details.isFloating() == False:
                pass

            elif self.dock_pos_details.isHidden() == False:
                self.dock_pos_details.hide()

            connect_diag = ConnectWindow(self)
            connect_dict = connect_diag._get_connect_dict()
            if not connect_dict:
                return

        # display and log a msg
        msg = "Connecting to API..."
        self.statusBar().showMessage(msg)
        self.logger_info.log(logging.INFO, msg)

        self.session = IGAPI(connect_dict)
        connect_reply = self.session.create_session()

        # request failed show error msg
        if type(connect_reply) == APIError:
            msg = connect_reply._get_error_msg()
            self.statusBar().showMessage(msg)
            return

        # connection successfull, get user"s accounts
        else:
            accounts_reply = self.session.get_user_accounts()

            # request failed show error msg
            if type(accounts_reply) == APIError:
                msg = accounts_reply._get_error_msg()
                self.statusBar().showMessage(msg)
                return

            # request successfull, update GUI
            else:
                self.user_accounts = accounts_reply
                for key in list(self.user_accounts.keys()):
                    if self.user_accounts[key]["preferred"] == True:
                        self.current_acc = self.user_accounts[key]

                        # update private attribute of self.session
                        cash_available = self.current_acc["Cash available: "]
                        self.session._set_cash_available(cash_available)

                        self.update_dock_account(self.current_acc)

                    else:
                        continue

                # display and log a msg
                msg = "Connected to API"
                self.logger_info.log(logging.INFO, msg)
                self.statusBar().showMessage(msg)

                self.update_menu_switch()

                ls_endpoint = self.session._get_ls_endpoint()
                self.connect_to_ls(ls_endpoint)

                # create threads to perform requests
                self.transaction_queue = queue.Queue()
                self.transaction_thread = TransactionThread(
                    self.session, self.transaction_queue, self.update_results
                )

                # thread for comments
                self.comments_queue = queue.Queue()
                self.comments_thread = UpdateCommentsThread(
                    self.comments_queue, self.update_comments
                )

                self.comments_thread.start()
                self.transaction_thread.start()

                # init dict that will hold results received
                self.local_transactions = OrderedDict()
                self.filtered_dict = OrderedDict()

                self.set_gui_enabled(True)  # enable interactions
                self.update_options(None)

    def connect_to_ls(self, ls_endpoint, *args, **kwargs):
        """
        Connect to LighStreamer. Suscribe to positions
        and balance table. See online doc for schema

        :param ls_endpoint: string private attribute of :any:`IGAPI`.
        """

        self.ls_client = LsClient(ls_endpoint + "/lightstreamer/")
        req_args = self.session._get_req_args()

        # get name of current account
        for action in self.menu_switch.actions():
            if action.isChecked() == True:
                action_name = action.text().replace("&", "")
                break
            else:
                continue

        for key in list(self.user_accounts.keys()):
            acc_name = self.user_accounts[key]["Account name: "]

            # get account id
            if action_name == acc_name:
                acc_id = self.user_accounts[key]["Account ID: "]
                break
            else:
                continue

        cst = req_args["headers"]["CST"]
        token = req_args["headers"]["X-SECURITY-TOKEN"]

        self.ls_client.create_session(
            username=acc_id, password="CST-" + cst + "|XST-" + token, adapter_set=""
        )

        # create a new subscription to account balance
        self.balance_table = Table(
            self.ls_client,
            mode=MODE_MERGE,
            item_ids="ACCOUNT:" + acc_id,
            schema="AVAILABLE_CASH DEPOSIT PNL",
        )

        # create a new subscription to positons
        self.pos_table = Table(
            self.ls_client,
            mode=MODE_DISTINCT,
            item_ids="TRADE:" + acc_id,
            schema="CONFIRMS",
        )

        # configure account event
        self.acc_update_sig = LsEvent()
        self.balance_table.on_update.listen(self.acc_update_sig.acc_update_event)
        self.acc_update_sig.acc_signal.connect(self.update_account)

        # configure positions event
        self.pos_update_sig = LsEvent()
        self.pos_table.on_update.listen(self.pos_update_sig.pos_update_event)
        self.pos_update_sig.pos_signal.connect(self.update_positions)

        # configure options changed signal
        self.diag_options = OptionsWindow(self)
        options_sig = self.diag_options.options_signal
        options_sig.connect(self.update_options)

        # configure status event
        status_sig = LsEvent()
        self.ls_client.on_state.listen(status_sig.on_state)
        status_sig.status_signal.connect(self.update_status)

        # update status infos
        connected_color = QtGui.QColor("#23A627")
        status_icon = create_status_icons(connected_color)
        self.lbl_status.setPixmap(status_icon)

    def switch_account(self):
        """Switch to account selected by user"""

        config = read_config()

        self.set_gui_enabled(False)  # disable interactions

        # disconnect from lightstreamer
        self.ls_client.delete(self.balance_table)
        self.ls_client.delete(self.pos_table)
        self.ls_client.destroy()

        # update status icons
        disconnected_color = QtGui.QColor("#F51616")
        status_icon = create_status_icons(disconnected_color)
        self.lbl_status.setPixmap(status_icon)

        # get the name of the account to connect to
        acc_name = self.menu_switch.sender().text()
        acc_name = acc_name.replace("&", "")  # remove ampersand Qt5 bug ??

        # display and log a msg
        msg = "Switching to account %s..." % acc_name
        self.logger_info.log(logging.INFO, msg)
        self.statusBar().showMessage(msg)

        for action in self.menu_switch.actions():
            action_name = action.text().replace("&", "")

            if action_name != acc_name:
                action.setChecked(False)  # uncheck other accounts
            else:
                action.setChecked(True)

        # search for the account ID to connect to
        for key in list(self.user_accounts.keys()):
            name = self.user_accounts[key]["Account name: "]

            if acc_name == name:
                acc_id = self.user_accounts[key]["Account ID: "]  # get account id
                break
            else:
                continue

        switch_body = json.dumps({"accountId": acc_id, "defaultAccount": ""})

        switch_reply = self.session.switch_account(acc_id, acc_name)

        # method returns a msg even if request is succesfull display it

        # request failed
        if type(switch_reply) == APIError:
            msg = switch_reply._get_error_msg()
            self.statusBar().showMessage(msg)
            return

        # request is successfull update GUI
        else:
            new_account = self.user_accounts[key]
            ls_endpoint = self.session._get_ls_endpoint()

            # update private attribute of self.session
            cash_available = new_account["Cash available: "]
            self.session._set_cash_available(cash_available)

            # update dock with new account and connect to ls
            self.update_dock_account(new_account)
            self.connect_to_ls(ls_endpoint)

            # log msg
            msg = "Connected to %s" % acc_name
            self.statusBar().showMessage(msg)
            self.logger_info.log(logging.INFO, msg)

            self.set_gui_enabled(True)  # enable interactions

            self.update_options(None)

            # update status infos
            connected_color = QtGui.QColor("#23A627")
            status_icon = create_status_icons(connected_color)
            self.lbl_status.setPixmap(status_icon)

    def update_menu_switch(self):
        """
        Populate the switch menu with name of
        each user"s account associated to a Qaction
        By default the preferred account is checked.
        """

        self.menu_switch.clear()  # clear previous menu

        # for each account add a new action
        for count, account in enumerate(self.user_accounts):
            acc_name = self.user_accounts[count]["Account name: "]
            preferred = self.user_accounts[count]["preferred"]

            if preferred == True:
                checked = True
            else:
                checked = False

            new_account = QtWidgets.QAction(acc_name, self)
            new_account.setCheckable(True)
            new_account.setChecked(checked)
            new_account.setStatusTip(f"Switch to {acc_name}")
            new_account.triggered.connect(self.switch_account)

            self.menu_switch.addAction(new_account)

    def update_dock_account(self, account_info):
        """
        Update dock_account with info of current account

        param: account_info: dict with info about the
                             current account. keys are the
                             same as list_accounts_labels
        """

        list_account_labels = [
            "Account ID: ",
            "Account name: ",
            "Account type: ",
            "Cash available: ",
            "Account balance: ",
            "Profit/loss: ",
        ]

        # update text of labels
        for count, label in enumerate(list_account_labels):
            lbl_to_update = self.dict_account_labels[label]
            acc_info = account_info[label]

            lbl_to_update.setText(acc_info)

    def update_options(self, sender):
        """
        Simple function to write options
        in config file. called when user changes
        options on options_widget.

        :param sender: string sent by function caller
        """

        config = read_config()  # read config file

        list_account_labels = [
            "Account ID: ",
            "Account name: ",
            "Account type: ",
            "Cash available: ",
            "Account balance: ",
            "Profit/loss: ",
        ]

        # get options set
        auto_calculate = self.checkbox_auto.checkState()
        result_in = self.combobox_options.currentText()
        include = self.checkbox_include.checkState()
        aggregate = self.checkbox_aggregate.checkState()

        currency_symbol = config["currency_symbol"]
        start_capital = config["start_capital"]
        state_infos = str(config["what_to_show"]["state_infos"])
        state_details = str(config["what_to_show"]["state_details"])

        # update dict config
        config["auto_calculate"] = auto_calculate
        config["result_in"] = result_in
        config["include"] = include
        config["aggregate"] = aggregate

        write_config(config)

        config = read_config()

        # get infos about dates

        start_date = self.start_date.date()
        end_date = self.end_date.date()

        date_range = f"""/{start_date.toString("dd-MM-yyyy")}/{end_date.toString("dd-MM-yyyy")}"""

        self.end_date.setMinimumDate(start_date)

        # update graph titles
        graph_title = f""" on {start_date.toString("dd/MM/yy")}"""
        if end_date != start_date:
            graph_title = f""" from {start_date.toString("dd/MM/yy")} to {end_date.toString("dd/MM/yy")}"""

        if result_in == "Points/lot":
            title = f">Points/lot{graph_title}<"
            y_label = ">Points/lot<"
        else:
            title = f">Points{graph_title}<"
            y_label = ">Points<"

        plot_widget = self.graph_dict["Points"]["equity_plot"]

        old_title = str(plot_widget.plotItem.titleLabel.text)
        old_y_label = str(plot_widget.plotItem.getAxis("left").labelText)

        new_title = RE_TEXT_BETWEEN_TAGS.sub(title, old_title)
        new_y_label = RE_TEXT_BETWEEN_TAGS.sub(y_label, old_y_label)

        plot_widget.plotItem.setTitle(new_title)
        plot_widget.plotItem.getAxis("left").labelText = new_y_label

        # hide account infos if user choose to
        if state_infos == "Always":
            for count, key in enumerate(self.dict_account_labels.keys()):
                label = self.dict_account_labels[key]
                old_text = label.text()  # retrieve account infos

                if key == "Account type: ":
                    connect_dict = self.session._get_connect_dict()
                    base_url = connect_dict["base_url"]

                    if "demo" in base_url:  # test url to show apropriate prefix
                        label.setText("Demo-xxxx")
                    else:
                        label.setText("Live-xxxx")

                elif currency_symbol in old_text:  # label contains currency infos
                    label.setText("xxxx" + currency_symbol)

                else:
                    label.setText("xxxx")
        else:
            # find the name of current account
            for action in self.menu_switch.actions():
                action_name = action.text().replace("&", "")

                if action.isChecked():
                    acc_name = action_name
                else:
                    continue

            # search for the account corresponding to acc_name
            for idx in list(self.user_accounts.keys()):
                name = self.user_accounts[idx]["Account name: "]

                if name == acc_name:
                    self.current_acc = self.user_accounts[idx]
                    self.update_dock_account(self.current_acc)
                    break
                else:
                    continue

        """
        Depending on sender send a new request to IG. If user changes
        the "units" of summary or changes options viaoptions window a
        local transactions is used. If userchanges one of the options
        checkboxes or if sender is another function, send an new request
        """

        if (
            sender == "aggregate"
            or sender == "auto_calculate"
            or sender == "include"
            or sender is None
        ):
            self.update_transactions()

        else:
            if config["all"] == 0:
                fill_args = {"modified_trans": self.filtered_dict}  # use filtered dict
            else:
                fill_args = {"modified_trans": self.local_transactions}

            fill_args["screenshot"] = False
            fill_args["sender"] = sender

            try:
                self.update_results({}, **fill_args)  # update infos with local dict

            except Exception:
                msg = "An error occured, see log file"
                self.statusBar().showMessage(msg)
                self.logger_debug.log(logging.ERROR, traceback.format_exc())

        if auto_calculate == 2:
            self.line_edit_capital.setEnabled(False)
        else:
            self.line_edit_capital.setEnabled(True)

    def update_capital(self):
        """
        Test the capital entered by the user.
        Set a empty string if it's not a float
        """

        config = read_config()

        currency_symbol = config["currency_symbol"]

        # test capital entered by user
        capital = self.line_edit_capital.text()

        match = RE_FLOAT.match(capital)
        float_capital = Decimal()

        # capital is Decimal
        if match is not None:
            float_capital = Decimal(match.group(0))

        text_capital = f"{float_capital}{currency_symbol}"
        self.line_edit_capital.setText(text_capital)
        self.line_edit_capital.setCursorPosition(len(str(float_capital)))
        config["start_capital"] = float_capital

        write_config(config)

    def update_account(self, myUpdateField):
        """
        Update Profit/Loss label on dock_account
        Call when lightstreamer sends an update

        :param myUpdateField: tuple of string
        """

        # unpack items sends by LS server
        balance, deposit, profit_loss = myUpdateField

        profit_loss = Decimal(profit_loss)

        config = read_config()
        label_pnl = self.dict_account_labels["Profit/loss: "]

        currency_symbol = config["currency_symbol"]
        state_infos = str(config["what_to_show"]["state_infos"])

        profit_color = config["profit_color"]
        flat_color = config["flat_color"]
        loss_color = config["loss_color"]

        # user does not want to show profit/loss
        if state_infos == "Always":
            return

        # set color according to config
        color = (
            profit_color
            if profit_loss > 0
            else flat_color
            if profit_loss == 0
            else loss_color
        )
        label_pnl.setText(
            f"""<font color={color}">{profit_loss}{currency_symbol}</font>"""
        )

    def update_positions(self, myUpdateField):
        """
        Called when lightstreamer sends
        notification about positions.

        :param myUpdateField: dict see online doc for content
        """

        try:
            if myUpdateField[0] is not None:
                pos_report = json.loads(myUpdateField[0])
                deal_status = pos_report["dealStatus"]
                reason = pos_report["reason"]

                # if position is fully or partially closed
                try:
                    pos_status = pos_report["affectedDeals"][0]["status"]

                    if pos_status == "FULLY_CLOSED" or pos_status == "PARTIALLY_CLOSED":
                        self.update_transactions()

                        # get user accounts to get cash available and update dock account
                        self.user_accounts = self.session.get_user_accounts()

                        # find the name of current account
                        for action in self.menu_switch.actions():
                            action_name = action.text().replace("&", "")

                            if action.isChecked():
                                acc_name = action_name
                            else:
                                continue

                        # search for the account corresponding to acc_name
                        for idx in list(self.user_accounts.keys()):
                            name = self.user_accounts[idx]["Account name: "]

                            if name == acc_name:
                                self.current_acc = self.user_accounts[idx]
                                self.update_dock_account(self.current_acc)
                                break
                            else:
                                continue

                    elif deal_status == "REJECTED":  # deal rejected
                        msg = deal_status + " " + reason
                        self.statusBar().showMessage(msg)
                        self.logger_debug.log(logging.ERROR, msg)

                except Exception as e:
                    msg = "An error occured, see log file"
                    self.statusBar().showMessage(msg)
                    self.logger_debug.log(logging.ERROR, traceback.format_exc())

        except Exception as e:
            msg = "An error occured, see log file"
            self.statusBar().showMessage(msg)
            self.logger_debug.log(logging.ERROR, traceback.format_exc())

    def update_status(self, state):
        """
        Update status bar label according to state received

        :param state: string
        """

        if state == "connected Lightstreamer session":
            connected_color = QtGui.QColor("#23A627")
            status_icon = create_status_icons(connected_color)
            self.lbl_status.setPixmap(status_icon)

        elif state == "disconnected from Lightstreamer":
            disconnected_color = QtGui.QColor("#F51616")
            status_icon = create_status_icons(disconnected_color)
            self.lbl_status.setPixmap(status_icon)

    def update_transactions(self):
        """
        Send a request for transactions. Calledwhen user changes dates
        or when optionsare changed (e.g: start capital changed)
        Infos and errors are log in classThread
        """

        config = read_config()

        result_in = self.combobox_options.currentText()

        start_date = self.start_date.date()
        end_date = self.end_date.date()

        date_range = f"""/{start_date.toString("dd-MM-yyyy")}/{end_date.toString("dd-MM-yyyy")}"""

        self.end_date.setMinimumDate(start_date)

        # update graph titles
        graph_title = f""" on {start_date.toString("dd/MM/yy")}"""
        if end_date != start_date:
            graph_title = f""" from {start_date.toString("dd/MM/yy")} to {end_date.toString("dd/MM/yy")}"""

        title_list = [
            "",
            f">Capital{graph_title}<",
            f">Capital growth{graph_title}<",
        ]

        if result_in == "Points/lot":
            title_list[0] = f">Points/lot{graph_title}<"
        else:
            title_list[0] = f">Points{graph_title}<"

        for count, key in enumerate(self.graph_dict.keys()):
            plot_widget = self.graph_dict[key]["equity_plot"]

            old_title = str(plot_widget.plotItem.titleLabel.text)
            new_title = RE_TEXT_BETWEEN_TAGS.sub(title_list[count], old_title)

            plot_widget.plotItem.setTitle(new_title)

        self.filtered_dict = OrderedDict()  # reset filtered dict
        config["all"] = 2  # reset filter

        write_config(config)

        self.statusBar().showMessage("Updating transactions...")

        self.transaction_queue.put(date_range)
        self.transaction_thread.start()

    def update_results(self, transactions, *args, **kwargs):
        """
        Update the GUI with results emit by transactions_thread
        or with a saved result dict if the users modifies options
        that don't need new request or when taking screenshot.
        pos_transaction_headers is a list with items same
        as the result dict used

        :param transactions: OrderedDict() with transactions

        :param kw modified_trans: OrderedDict() with modified
                                  transactions(e.g filtered)

        :param kw screenshot: boolean indicates when app is taking
                             screenshot

        :param kw sender: string, describing caller of the function
                         (widgets, other function)

        :param kw msg: string, msg to be displayed on statusBar
        """

        # an error occured while requests
        if type(transactions) == APIError:
            msg = transactions._get_error_msg()
            self.statusBar().showMessage(msg)
            return

        self.statusBar().showMessage("Updating transactions...")

        pos_transaction_headers = [
            "date",
            "market_name",
            "direction",
            "open_size",
            "open_level",
            "final_level",
            "points",
            "points_lot",
            "pnl",
            "growth",
        ]

        config = read_config()  # read options

        start_capital = config["start_capital"]
        currency_symbol = config["currency_symbol"]
        state_infos = str(config["what_to_show"]["state_infos"])
        state_size = str(config["what_to_show"]["state_size"])
        states_dd = config["what_to_show"]  # get what to show
        state_details = config["what_to_show"]["state_details"]
        all_state = config["all"]  # all markets or filter set

        ig_config = read_ig_config()

        """
        ig sends keywords to identify transactions type known
        keywords ares stored in ig_config.json
        if transaction type is unknown log it
        """

        kw_order = ig_config["keyword"]["ORDER"]
        kw_fees = ig_config["keyword"]["FEES"]
        kw_cashin = ig_config["keyword"]["CASH_IN"]
        kw_cashout = ig_config["keyword"]["CASH_OUT"]
        kw_transfer = ig_config["keyword"]["TRANSFER"]

        # Depending of caller use a local transactions or the one sent by thread
        try:
            transactions = kwargs["modified_trans"]
            screenshot = kwargs["screenshot"]
            sender = kwargs["sender"]
        except KeyError:
            self.local_transactions = transactions  # use dict sent by thread
            screenshot = False
            sender = "thread"

            if not transactions:  # manage when no trades done between period
                self.statusBar().showMessage("No transactions received")

        result_in = self.combobox_options.currentText()

        cash_available = Decimal(self.session._get_cash_available())

        summary = TradesResults()

        # calculate summary infos
        self.logger_info.log(logging.INFO, "Calculating summary...")

        try:
            dict_results = summary.calculate_result(
                transactions, start_capital, cash_available, screenshot
            )

        except Exception:
            msg = "An error occured: see log file"
            self.statusBar().showMessage(msg)
            self.logger_debug.log(logging.ERROR, traceback.format_exc())
            return

        self.logger_info.log(logging.INFO, "Done")

        start_capital = dict_results["start_capital"]
        summary_dict = dict_results["summary"]
        transactions = dict_results["transactions"]
        curves_dict = dict_results["curves_dict"]

        data_to_save = {
            "transactions": transactions,
            "summary": summary_dict,
            "start_capital": start_capital,
            "current_acc": self.current_acc,
        }

        # update data to export
        self.data_exporter = ExportToExcel(data_to_save)

        # hide capital info if user choose to
        if (
            state_infos == "Always"
            and result_in != currency_symbol
            or state_infos == "Only for screenshot"
            and screenshot == True
            and result_in != currency_symbol
        ):
            self.line_edit_capital.blockSignals(True)

            # hide initial capital
            self.line_edit_capital.setText(f"xxxx {currency_symbol}")

            # hide capital axe on graph
            self.graph_dict["Capital"]["equity_plot"].plotItem.hideAxis("left")

            self.line_edit_capital.blockSignals(False)

            # hide profit on dock pos details
            self.dock_pos_details.hide_profit_loss(currency_symbol)

        else:
            self.line_edit_capital.blockSignals(True)

            # show initial capital
            self.line_edit_capital.setText(f"{start_capital:.2f} {currency_symbol}")

            # show capital axe on graph
            self.graph_dict["Capital"]["equity_plot"].plotItem.showAxis("left")

            self.line_edit_capital.blockSignals(False)

            # show profit on dock pos details
            self.dock_pos_details.show_profit_loss()

        summary_headers = [
            "Points won",
            "Trades won",
            "Points lost",
            "Trades lost",
            "Total points",
            "Trades flat",
            "Total trades",
            "Avg trade",
            "Profit Factor",
            "Avg win",
            "Capital growth",
            "Avg loss",
            "Max drawdown",
            "Avg drawdown",
            "Consec. wins",
            "Consec. losses",
            "Interests",
            "Fees",
            "Cash in/out",
            "Transfers",
        ]  # same list as the one used to create dock

        # update summary labels
        for count, key in enumerate(summary_dict.keys()):
            label_text = self.dict_summary_labels[key].text()

            if count == 4:
                # get only 'points' if result in 'points/lot'
                try:
                    result_in = RE_BEFORE_SLASH_HYPHEN.search(result_in).group(1)
                except AttributeError:
                    pass

                static_text = RE_SPACE_START.search(label_text).group(0)
                static_text = f"{static_text}{result_in.lower()}: "

            elif count == 0 or count == 2:
                # get only "points" if result in "points/lot"
                try:
                    result_in = RE_BEFORE_SLASH_HYPHEN.search(result_in).group(1)
                except AttributeError:
                    pass

                static_text = RE_SPACE_START_COLON_END.search(label_text).group(0)
                static_text = f"{result_in}{static_text}"

            else:
                static_text = RE_COLON_END.search(label_text).group(0)

            text_to_set = f"{static_text}{summary_dict[key]}"
            self.dict_summary_labels[key].setText(text_to_set)

        # update transactions table
        for i in range(self.widget_pos.rowCount()):
            self.widget_pos.removeRow(0)  # remove all rows

        deal_id_plotted = []
        new_row = 0

        # iterate over deal_id from older to newer pos
        for count, deal_id in enumerate(transactions.keys()):
            transaction_type = transactions[deal_id]["type"]

            # skip dividend interest
            if config["include"] != 2 and transaction_type in kw_fees:
                continue

            elif transaction_type in ["CASHIN", "TRANSFER", "CASHOUT", "UNDEFINED"]:
                continue  # account transaction are never showed

            else:
                nb_row = self.widget_pos.rowCount()
                self.widget_pos.insertRow(nb_row)

                """
                fill transactions table. if screenshot is being
                taken ,hide lot size and/or pnl if user wants to
                """

                # add deal_id item at first column
                # item = QtWidgets.QTableWidgetItem()
                # item.setTextAlignment(QtCore.Qt.AlignCenter)
                # try:
                #     ig_deal_id = RE_UNDERSCORE_START.search(deal_id).groups()[0]
                # except Exception as e:
                #     ig_deal_id = deal_id

                # item.setText(ig_deal_id)
                # self.widget_pos.setItem(nb_row, 0, item)

                for idx, header in enumerate(pos_transaction_headers):
                    item = QtWidgets.QTableWidgetItem()
                    item.setTextAlignment(QtCore.Qt.AlignCenter)

                    if header == "pnl":
                        if (
                            state_infos == "Always"
                            and result_in != currency_symbol
                            or state_infos == "Only for screenshot"
                            and screenshot == True
                            and result_in != currency_symbol
                        ):
                            item.setText(f"-- {currency_symbol}")  # hide profit/loss
                        else:
                            item.setText(
                                f"{transactions[deal_id][header]}{currency_symbol}"
                            )  # show profit/loss

                    elif header == "open_size":
                        if (
                            state_size == "Always"
                            or state_size == "Only for screenshot"
                            and screenshot == True
                        ):  # screenshot is being taken
                            item.setText("-")  # hide lot size
                            self.dock_pos_details.hide_lot_size()
                        else:  # show lot_size
                            item.setText(f"{transactions[deal_id][header]}")

                    elif header == "growth":
                        continue  # don"t show growth in table

                    else:
                        item.setText(f"{transactions[deal_id][header]}")

                    profit_color = config["profit_color"]
                    flat_color = config["flat_color"]
                    loss_color = config["loss_color"]
                    pnl = transactions[deal_id]["pnl"]

                    # set line color according to profit/loss
                    color = (
                        loss_color
                        if pnl < 0
                        else profit_color
                        if pnl > 0
                        else flat_color
                    )
                    item.setForeground(QtGui.QColor(color))

                    self.widget_pos.setItem(nb_row, idx, item)

        """
        If user changes the "units" of summary or what to
        hide update or take a screenshot or change options
        for screenshot don't need to update data plotted,
        just the style eventually.
        """

        sender = str(sender)

        # list with options that don't require graph update
        list_sender = [
            "screenshot",
            "result_in",
            "what_to_print",
            "shortcut",
            "profit_color",
            "loss_color",
            "flat_color",
        ]

        today = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")

        if sender in list_sender:
            self.statusBar().showMessage("Last update: " + today)
            return

        elif sender == "state_infos" or sender == "state_size":
            """
            Sender concerns options on what to hide when taking
            screenshot, callupdate_trade_details to update pnl sring
            """

            if self.dock_pos_details.isHidden() == True and state_details == 2:
                self.dock_pos_details.show()

            for key in self.graph_dict.keys():
                equity_plot = self.graph_dict[key]["equity_plot"]

                vline_pos = len(transactions) // 2  # set a line pos

                # simulate a mouse click near the new pos
                vline_coord = equity_plot.plotItem.vb.mapViewToScene(
                    QtCore.QPointF(vline_pos, 0)
                ).toPoint()

                trade_args = {
                    "plot_widget": equity_plot,
                    "mouse_pos": vline_coord,
                    "vline_pos": vline_pos,
                    "screenshot": screenshot,
                }

                try:
                    self.update_trade_details(**trade_args)

                except Exception as e:
                    msg = "An error occured, see log file"
                    self.statusBar().showMessage(msg)
                    self.logger_debug.log(logging.ERROR, traceback.format_exc())

        elif "ec_" in sender:
            """
            Sender concerns options of equity curvestyle,
            call apropriate function with new style
            """

            for key in self.graph_dict.keys():
                ec_args = {
                    "ec_color": config["ec_color"],
                    "ec_style": config["ec_style"],
                    "ec_size": config["ec_size"],
                    "graph": key,
                }  # set curve style with user choice

                equity_plot = self.graph_dict[key]["equity_plot"]
                overview_plot = self.graph_dict[key]["overview_plot"]

                # select curve item
                equity_curve = self.graph_dict[key]["curve"]["equity_curve"]
                overview_curve = self.graph_dict[key]["curve"]["overview_curve"]

                equity_plot.update_curve_style(equity_curve, **ec_args)
                overview_plot.update_curve_style(overview_curve, **ec_args)

        elif "maxdd" in sender or "depth" in sender or "high" in sender:
            """
            Sender concerns scatter plot style. Call appropriate
            function with new style Update only concerned scatter.
            """

            # get scatter name as same as in config dict
            scatter_type = RE_UNDERSCORE_START.sub("", sender)

            # get state of scatter (show it or not)
            state_dd = states_dd[scatter_type]

            scatter_args = {}

            for key in self.graph_dict.keys():
                equity_plot = self.graph_dict[key]["equity_plot"]

                # get items to update
                equity_curve = self.graph_dict[key]["curve"]["equity_curve"]
                scatter_item = self.graph_dict[key]["curve"][scatter_type]

                # create list with keys corresponding to scatter to update
                keys_config = [
                    key_config
                    for key_config in config.keys()
                    if scatter_type in key_config
                ]

                scatter_args["dd_size"] = config["dd_size"]
                scatter_args["state"] = state_dd

                for option in keys_config:
                    scatter_args[option] = config[option]

                equity_plot.update_scatter_style(scatter_item, **scatter_args)

        elif sender == "dd_size":
            # Sender concerns symbol size.Need to update all scatter

            for key in self.graph_dict.keys():
                # select curve items
                equity_plot = self.graph_dict[key]["equity_plot"]
                equity_curve = self.graph_dict[key]["curve"]["equity_curve"]

                # loop over each scatter plotted
                for scatter_type in ["high", "depth", "maxdd"]:
                    scatter_args = {}

                    # get scatter plot to update
                    scatter_item = self.graph_dict[key]["curve"][scatter_type]

                    # get state of scatter (show it or not)
                    state_dd = states_dd[scatter_type]

                    # create list with keys corresponding to scatter to update
                    keys_config = [
                        key_config
                        for key_config in config.keys()
                        if scatter_type in key_config
                    ]

                    scatter_args["dd_size"] = config["dd_size"]
                    scatter_args["state"] = state_dd

                    for option in keys_config:
                        scatter_args[option] = config[option]

                    equity_plot.update_scatter_style(scatter_item, **scatter_args)

        else:
            """
            Sender directly concerns data plotted. need agraph update.
            Called when user changes start_capital,checkbox states
            in dockoptions, or when a new request has been sent.
            """

            graph_args = {
                "config": config,
                "transactions": transactions,
                "curves_dict": curves_dict,
                "start_capital": start_capital,
                "screenshot": screenshot,
            }

            try:
                self.update_graph(**graph_args)

            except Exception:
                msg = "An error occured: see log file"
                self.statusBar().showMessage(msg)
                self.logger_debug.log(logging.ERROR, traceback.format_exc())

        today = datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S")

        try:  # means func has been called by take_screeenshot
            msg = kwargs["msg"]
            self.statusBar().showMessage(msg)

        except KeyError:
            if self.widget_pos.rowCount() == 0:
                self.statusBar().showMessage("No transactions received")
                self.btn_export.setEnabled(False)
                self.btn_export.setStatusTip("No data to export")

            else:
                self.statusBar().showMessage("Last update: " + today)
                self.btn_export.setEnabled(True)
                self.btn_export.setStatusTip("Export data")

    def update_graph(self, *args, **kwargs):
        """Update equity curves and scatter plot for all graphs."""

        config = kwargs["config"]
        transactions = kwargs["transactions"]
        curves_dict = kwargs["curves_dict"]
        screenshot = kwargs["screenshot"]
        start_capital = kwargs["start_capital"]

        state_details = config["what_to_show"]["state_details"]
        state_dates = config["what_to_show"]["state_dates"]
        states_dd = config["what_to_show"]  # get what to show

        result_in = self.combobox_options.currentText()
        ig_config = read_ig_config()

        """
        ig sends keywords to identify transactions type known
        keywords ares stored in ig_config.json
        if transaction type is unknown log it
        """

        kw_order = ig_config["keyword"]["ORDER"]
        kw_fees = ig_config["keyword"]["FEES"]
        kw_cashin = ig_config["keyword"]["CASH_IN"]
        kw_cashout = ig_config["keyword"]["CASH_OUT"]
        kw_transfer = ig_config["keyword"]["TRANSFER"]

        """
        following listes are build to update classsEquityChart
        attributes. Used to know which deal_id/dates are plotted
        and update comments and date correctly.
        """

        # build a list with all transactions except accounts ones
        deal_id_plotted = [
            deal_id
            for deal_id in transactions.keys()
            if transactions[deal_id]["type"] != "CASHIN"
            and transactions[deal_id]["type"] != "CASHOUT"
            and transactions[deal_id]["type"] != "TRANSFER"
        ]

        # build a list with only trades
        trades_plotted = [
            deal_id
            for deal_id in transactions.keys()
            if transactions[deal_id]["type"] in kw_order
        ]

        # build a list with only dates when a trades occurs
        dates_plotted = [
            transactions[deal_id]["date"]
            for deal_id in transactions.keys()
            if transactions[deal_id]["type"] in kw_order
        ]

        # build a list with all dates except when accounts fund transfer
        dates_plotted_all = [
            transactions[deal_id]["date"]
            for deal_id in transactions.keys()
            if transactions[deal_id]["type"] != "CASHIN"
            and transactions[deal_id]["type"] != "CASHOUT"
            and transactions[deal_id]["type"] != "TRANSFER"
        ]

        if len(deal_id_plotted) != 0:
            deal_id_plotted.insert(0, "")
        if len(trades_plotted) != 0:
            trades_plotted.insert(0, "")
        if len(dates_plotted) != 0:
            dates_plotted.insert(0, dates_plotted[0])
        if len(dates_plotted_all) != 0:
            dates_plotted_all.insert(0, dates_plotted_all[0])

        # update chart
        for i, key in enumerate(self.graph_dict.keys()):
            # get the plot to update
            equity_plot = self.graph_dict[key]["equity_plot"]
            overview_plot = self.graph_dict[key]["overview_plot"]

            if key == "Points":  # points graph never show interest/dividend
                # update list of deal id plotte (attribute of the plot objects)
                overview_plot._set_deal_id_plotted(trades_plotted)
                equity_plot._set_deal_id_plotted(trades_plotted)
                deal_id_list = trades_plotted
                xaxis_dict = create_dates_list(
                    state_dates, dates_plotted, key, start_capital
                )

            else:
                if config["include"] == 2:  # plot interest/dividend
                    # update list of deal id plotted (attribute of the plot objects)
                    overview_plot._set_deal_id_plotted(deal_id_plotted)
                    equity_plot._set_deal_id_plotted(deal_id_plotted)
                    deal_id_list = deal_id_plotted
                    xaxis_dict = create_dates_list(
                        state_dates, dates_plotted_all, key, start_capital
                    )

                else:
                    overview_plot._set_deal_id_plotted(trades_plotted)
                    equity_plot._set_deal_id_plotted(trades_plotted)
                    deal_id_list = trades_plotted
                    xaxis_dict = create_dates_list(
                        state_dates, dates_plotted, key, start_capital
                    )

            # get the curve to update
            overview_curve = self.graph_dict[key]["curve"]["overview_curve"]
            equity_curve = self.graph_dict[key]["curve"]["equity_curve"]

            # update x axis values/string
            equity_plot.getAxis("bottom").update_axis(
                xaxis_dict, show_dates=state_dates
            )
            overview_plot.getAxis("bottom").update_axis(xaxis_dict)

            for scatter_type in curves_dict[key].keys():
                # Scatter type can be equity_curve dd, maxdd or depth
                if scatter_type == "equity_curve":
                    ec_args = {
                        "ec_color": config["ec_color"],
                        "ec_style": config["ec_style"],
                        "ec_size": config["ec_size"],
                        "graph": key,
                    }  # set curve style with user choice

                    equity_plot.update_curve(
                        equity_curve,
                        curves_dict[key]["equity_curve"],
                        list(xaxis_dict.keys()),
                        **ec_args,
                    )  # update equity curve

                    overview_plot.update_curve(
                        overview_curve,
                        curves_dict[key]["equity_curve"],
                        list(xaxis_dict.keys()),
                        **ec_args,
                    )  # update overview curve

                else:
                    scatter_args = {}

                    # get state of scatter (show it or not)
                    state_dd = states_dd[scatter_type]

                    if state_dd == 0:
                        scatter_item = self.graph_dict[key]["curve"][scatter_type]

                        # get data to diplay
                        xy_value = curves_dict[key][scatter_type]
                        scatter_args["clear"] = True
                        equity_plot.update_scatter(
                            scatter_item, np.array([]), np.array([]), **scatter_args
                        )

                    else:
                        # create list with keys corresponding to scatter to update
                        keys_config = [
                            key_config
                            for key_config in config.keys()
                            if scatter_type in key_config
                        ]

                        for option in keys_config:
                            scatter_args[option] = config[option]

                        scatter_args["dd_size"] = config["dd_size"]

                        scatter_item = self.graph_dict[key]["curve"][scatter_type]

                        # get data to diplay
                        xy_value = curves_dict[key][scatter_type]

                        equity_plot.update_scatter(
                            scatter_item, xy_value[0], xy_value[1], **scatter_args
                        )

            # When new data are plotted set vline_pos are the middle
            vline_pos = len(transactions) // 2

            # simulate a mouse click near the new pos
            vline_coord = equity_plot.plotItem.vb.mapViewToScene(
                QtCore.QPointF(vline_pos, 0)
            ).toPoint()

            trade_args = {
                "plot_widget": equity_plot,
                "mouse_pos": vline_coord,
                "vline_pos": vline_pos,
                "screenshot": screenshot,
                "deal_id_plotted": deal_id_list,
            }

            # update trade details
            try:
                self.update_trade_details(**trade_args)

            except Exception as e:
                msg = "An error occured, see log file"
                self.statusBar().showMessage(msg)
                self.logger_debug.log(logging.ERROR, traceback.format_exc())

            equity_plot.autoRange()
            overview_plot.autoRange()

            """
            When new data are plotted removeall items
            on graph and send newdeal_id_list to thread
            """

            if state_details == 2 and screenshot == False:
                equity_plot.remove_text_item("", all_comments=True)
                self.comments_queue.put(deal_id_list)

            elif screenshot == False:  # user don't want to show comments
                equity_plot.remove_text_item("", all_comments=True)

                self.dock_pos_details.hide()  # hide dock

    def update_comments(self, object_send):
        """
        Update comments on dock_pos_details
        and items on graph (arrow and text_item)

        :param object_send: dict or list
        """

        if type(object_send) == dict:
            """
            If object received is a dict means new data
            has been plotted. the dict contains all comment found
            for data plotted (keys are deal_id, values are comments)
            """

            for deal_id in object_send.keys():  # iterate over deal
                comment = object_send[deal_id]  # get comment
                comment_str = str(comment[0])
                comment[0] = comment_str

                for key in self.graph_dict.keys():  # update graph
                    equity_plot = self.graph_dict[key]["equity_plot"]
                    equity_curve = self.graph_dict[key]["curve"]["equity_curve"]
                    overview_plot = self.graph_dict[key]["overview_plot"]

                    equity_plot.add_text_item(equity_curve, comment, deal_id, key)

                    """
                    as the comments are shown an equity plot only
                    update the attribute of overview plot because
                    when the range is modify on that plot we need to
                    the items on the equity plot form the overview
                    plot to update the items. see class EquityChart
                    """

                    comments_items = equity_plot._get_comments_items()
                    overview_plot._set_comments_items(comments_items)

        elif type(object_send) == list:
            """
            If object received is a list thread has
            been sollicited for a particular deal_id.
            """

            comment = object_send
            comment_str = str(comment[0])
            comment[0] = comment_str

            # set comment found and state of checkbox
            self.text_edit_comment.setPlainText(comment[0])
            self.checkbox_showongraph.setCheckState(comment[1])

            for key in self.graph_dict.keys():
                equity_plot = self.graph_dict[key]["equity_plot"]
                equity_curve = self.graph_dict[key]["curve"]["equity_curve"]
                overview_plot = self.graph_dict[key]["overview_plot"]
                equity_plot.add_text_item(
                    equity_curve, comment, self.deal_id_clicked, key
                )

                """
                as the comments are shown an equity plot only
                update the attribute of overview plot because
                when the range is modify on that plot we need to
                the items on the equity plot form the overview
                plot to update the items. see class EquityChart
                """

                comments_items = equity_plot._get_comments_items()
                overview_plot._set_comments_items(comments_items)

    def update_overview_graph(self, plot, plot_range):
        """
        Called when range on equity_plot (graph on top)
        is changed. Update region on overview_plot
        (gaph on bottom) according to new x range
        Maybe merge it with update_equity_graph

        :param plot: pyqtgraph.PlotWidget
        :param plot_range: list of list contains range X Y of graph
        """

        active_tab = self.widget_tab.currentIndex()
        active_tab_name = str(self.widget_tab.tabText(active_tab)).replace("&", "")

        # get plot (points, capital or growth) selected
        try:
            overview_plot = self.graph_dict[active_tab_name]["overview_plot"]
            overview_curve = self.graph_dict[active_tab_name]["curve"]["overview_curve"]

            equity_plot = self.graph_dict[active_tab_name]["equity_plot"]
            equity_curve = self.graph_dict[active_tab_name]["curve"]["equity_curve"]

        except KeyError:  # when Transactions tab is selected
            overview_plot = self.graph_dict["Points"]["overview_plot"]
            overview_curve = self.graph_dict["Points"]["curve"]["overview_curve"]

            equity_plot = self.graph_dict["Points"]["equity_plot"]
            equity_curve = self.graph_dict["Points"]["curve"]["equity_curve"]

        range_to_set = equity_plot.viewRange()  # sent by signal
        overview_plot.update_region(
            overview_curve, range_to_set, **{"graph": active_tab_name}
        )  # update region

    def update_equity_graph(self, region):
        """
        Called when region on overview_plot (graph on bottom)
        is changed. Update x and y range on equity_plot (gaph on top)
        Maybe merge it with update_overview_graph

        :param region: pyqtgraph.LinearRegionItem
        """

        active_tab = self.widget_tab.currentIndex()
        active_tab_name = str(self.widget_tab.tabText(active_tab)).replace("&", "")

        # get plot (points, capital or growth) selected
        try:
            equity_plot = self.graph_dict[active_tab_name]["equity_plot"]
            equity_curve = self.graph_dict[active_tab_name]["curve"]["equity_curve"]

        except KeyError as KE:  # When Transactions tab is selected
            equity_plot = self.graph_dict["Points"]["equity_plot"]
            equity_curve = self.graph_dict["Points"]["curve"]["equity_curve"]

        range_to_set = region.getRegion()  # get region bounds
        equity_plot.update_range(
            equity_curve, range_to_set, **{"graph": active_tab_name}
        )

    def update_trade_details(self, *args, **kwargs):
        """
        Called when mouse is clicked and is over plot widget.
        Creates a floating dock that show trade details. This
        dock is updated with infos about trade under cursor.

        :param kw plog_widget: pyqtgraph plot widget, graph under mouse
        :param kw mouse_pos: float or QPoint depending of caller
        :param kw screenshot: boolean indicates if a screenshot
                             is being taken
        """

        config = read_config()

        """
        ordered dict with Label title as keys and values
        corresponding to keys in transactions as values
        """

        pos_details_headers = OrderedDict(
            [
                (" ", "market_name"),
                ("h_line", ""),
                ("Date", "date"),
                ("Trade", 1),
                ("Direction", "direction"),
                ("Size", "open_size"),
                ("Open", "open_level"),
                ("Close", "final_level"),
                ("Profit", "points,points_lot,pnl"),
                ("h_line_2", ""),
            ]
        )

        # get configuration
        profit_color = config["profit_color"]
        flat_color = config["flat_color"]
        loss_color = config["loss_color"]

        include = config["include"]
        all_state = config["all"]  # all markets or filter set
        currency_symbol = config["currency_symbol"]
        state_details = config["what_to_show"]["state_details"]

        plot_widget = kwargs["plot_widget"]
        mouse_pos = kwargs["mouse_pos"]
        screenshot = kwargs["screenshot"]

        # retrieve active plot and get mouse coordinates
        active_tab = self.widget_tab.currentIndex()
        active_tab_name = str(self.widget_tab.tabText(active_tab)).replace("&", "")
        mouse_x = mouse_pos.x()
        mouse_y = mouse_pos.y()
        graph_height = plot_widget.geometry().height()  # height of graph
        dict_to_search = OrderedDict()

        if state_details != 2:
            # hide line if users does not want trade overview
            for key in self.graph_dict.keys():
                pg_widget = self.graph_dict[key]["equity_plot"]
                pg_widget.hide_vline()
            return

        else:
            # show line if users want trade overview
            for key in self.graph_dict.keys():
                pg_widget = self.graph_dict[key]["equity_plot"]
                pg_widget.show_vline()

        # get correct dictionnary to search
        if all_state == 2:  # filter off
            dict_to_search = deepcopy(self.local_transactions)  # use default dict
        else:
            dict_to_search = deepcopy(self.filtered_dict)  # use filtered dict

        """
        if exclude interest or active graph is points build
        a dict without fees/interest  else delete transactions
        about account maybe there is a cleaner way to do that
        """

        if include != 2 or active_tab_name == "Points":
            for key in dict_to_search.keys():
                if (
                    dict_to_search[key]["type"] == "WITH"
                    or dict_to_search[key]["type"] == "DEPO"
                    or dict_to_search[key]["type"] == "DIVIDEND"
                    or dict_to_search[key]["type"] == "CHART"
                    or dict_to_search[key]["type"] == "CASHIN"
                    or dict_to_search[key]["type"] == "CASHOUT"
                    or dict_to_search[key]["type"] == "TRANSFER"
                ):
                    dict_to_search.pop(key, None)

                else:
                    continue

        else:
            for key in dict_to_search.keys():
                if (
                    dict_to_search[key]["type"] == "CASHIN"
                    or dict_to_search[key]["type"] == "CASHOUT"
                    or dict_to_search[key]["type"] == "TRANSFER"
                    or dict_to_search[key]["type"] == "TRANSFER"
                ):
                    dict_to_search.pop(key, None)

                else:
                    continue

        if not dict_to_search:  # no trades found
            # update vertical line pos for each plot
            for key in self.graph_dict.keys():
                # set a default vline position
                pg_widget = self.graph_dict[key]["equity_plot"]
                curve = self.graph_dict[key]["curve"]["equity_curve"]
                pg_widget.update_vline(1, curve)

            self.dock_pos_details.empty_labels(pos_details_headers)
            return

        else:
            # create a list all trade number available
            list_count_pos = [i + 1 for i in range(len(dict_to_search))]

        """
        If function is called by keyPressEvent the index of pos
        is directly send, don"t need to map the mouse click
        """

        try:
            x_value_clicked = kwargs["vline_pos"]

        except KeyError:
            # x value (trade number) under mouse click
            x_value_clicked = plot_widget.plotItem.vb.mapSceneToView(mouse_pos).x()

        if x_value_clicked < 0.5:  # no trade number equals to 0
            x_value_clicked = 1  # force trade number to be 1

        # no trade number > last trade force trade number to be = the last trade
        elif x_value_clicked > list_count_pos[-1]:
            x_value_clicked = list_count_pos[-1]

        # find closest trade number to mouse click
        closest_x = min(
            list_count_pos, key=lambda x: abs(x - round(x_value_clicked, 0))
        )

        # get mouse click coordinates in px
        x_coord = plot_widget.plotItem.vb.mapViewToScene(
            QtCore.QPointF(closest_x, 0)
        ).x()

        # update vertical line pos for each plot
        for key in self.graph_dict.keys():
            pg_widget = self.graph_dict[key]["equity_plot"]
            curve = self.graph_dict[key]["curve"]["equity_curve"]
            pg_widget.update_vline(closest_x, curve)

        """
        get deal id under mouse and send it thread
        to search a comment for this trade
        """

        # FIXME: dict .keys() order was not deterministic prior to 3.6. Reviewing is needed
        self.deal_id_clicked = list(dict_to_search.keys())[closest_x - 1]
        self.comments_queue.put(str(self.deal_id_clicked))

        # set deal_id row as active row in table
        self.widget_pos.setCurrentCell(closest_x - 1, 0)

        dock_args = {
            "pos_details_headers": pos_details_headers,
            "dict_to_search": dict_to_search,
            "deal_id_clicked": self.deal_id_clicked,
            "index_clicked": closest_x,
            "screenshot": screenshot,
        }

        try:
            self.dock_pos_details.change_content(**dock_args)  # update labels

        except Exception as e:
            msg = "An error occured, see log file"
            self.statusBar().showMessage(msg)
            self.logger_debug.log(logging.ERROR, traceback.format_exc())

    def write_comments(self, *args, **kwargs):
        """
        Called when user edit comments. Build a dict whith deal_id
        to comment as key and comment to save as value and put it
        in comments_queue. see updateCommentsThread class
        """

        dict_to_save = {}

        comment_to_write = str(self.text_edit_comment.toPlainText())
        show_on_graph = self.checkbox_showongraph.checkState()

        """
        comment_to_write is build as a list  with text
        entered at index 0 and state of checkbox at index 1
        """

        comment_to_write = [comment_to_write, show_on_graph]

        for key in self.graph_dict.keys():
            equity_plot = self.graph_dict[key]["equity_plot"]
            equity_curve = self.graph_dict[key]["curve"]["equity_curve"]
            overview_plot = self.graph_dict[key]["overview_plot"]

            if comment_to_write[0] == "":  # comment is empty
                equity_plot.remove_text_item(self.deal_id_clicked)
            else:
                equity_plot.add_text_item(
                    equity_curve, comment_to_write, self.deal_id_clicked, key
                )

            """
            as the comments are shown an equity plot only update
            the attribute of overview plot because when the range
            is modify on that plot we need to the items on the
            equity plot form the overviewplot to update the items.
            """

            comments_items = equity_plot._get_comments_items()
            overview_plot._set_comments_items(comments_items)

            dict_to_save[self.deal_id_clicked] = comment_to_write
            self.comments_queue.put(dict_to_save)

    def update_filter(self, filtered_dict):
        """
        Update results when filter is changed.
        See DialogBox.FilterWindow for more details

        :param filtered_dict: OrderedDict()
        """

        self.filtered_dict = filtered_dict

        fill_args = {
            "modified_trans": filtered_dict,
            "screenshot": False,
            "sender": "update_filter",
        }

        try:
            self.update_results({}, **fill_args)

        except Exception as e:
            msg = "An error occured, see log file"
            self.statusBar().showMessage(msg)
            self.logger_debug.log(logging.ERROR, traceback.format_exc())

    def show_options(self):
        """Show options dialog"""

        if self.dock_pos_details.isFloating() == False:
            pass

        elif self.dock_pos_details.isHidden() == False:
            self.dock_pos_details.hide()

        self.diag_options.exec_()

        config = read_config()
        state_details = config["what_to_show"]["state_details"]

        if self.dock_pos_details.isHidden() == True and state_details == 2:
            self.dock_pos_details.show()

    def show_export(self, *args, **kwargs):
        """Show a Qdialog to configure export"""

        config = read_config()

        if self.dock_pos_details.isFloating() == False:
            pass

        elif self.dock_pos_details.isHidden() == False:
            self.dock_pos_details.hide()

        if not os.path.exists("Export"):
            os.makedirs("Export")

        export_diag = ExportWindow(self)
        result = export_diag.exec()

        if result == 1:
            try:
                self.data_exporter.export(self.widget_pos)
                self.statusBar().showMessage("Data successfully exported")

            except Exception as e:
                msg = "An error occured, see log file"
                self.statusBar().showMessage(msg)
                self.logger_debug.log(logging.ERROR, traceback.format_exc())

        state_details = config["what_to_show"]["state_details"]

        if self.dock_pos_details.isHidden() == True and state_details == 2:
            self.dock_pos_details.show()

    def show_filter(self):
        """
        Show filter window. display a Qdialog
        that allow users to filter markets
        """

        if self.dock_pos_details.isFloating() == False:
            pass

        elif self.dock_pos_details.isHidden() == False:
            self.dock_pos_details.hide()

        # init window
        filter_diag = FilterWindow(self)
        filter_sig = filter_diag.filter_signal

        # connect signal that notify filter has changed
        filter_sig.connect(self.update_filter)

        # create window according to markets in transactions
        previous_filter = [
            self.filtered_dict[key]["market_name"] for key in self.filtered_dict.keys()
        ]  # list of market names

        filter_diag.build_window(self.local_transactions, previous_filter)

        config = read_config()
        state_details = config["what_to_show"]["state_details"]

        if self.dock_pos_details.isHidden() == True and state_details == 2:
            self.dock_pos_details.show()

    def show_about(self):
        """Show an "About" window."""

        if not self.dock_pos_details.isFloating():
            pass

        elif not self.dock_pos_details.isHidden():
            self.dock_pos_details.hide()

        about_window = AboutWindow(self)
        about_window.exec_()

        config = read_config()
        state_details = config["what_to_show"]["state_details"]

        if self.dock_pos_details.isHidden() and state_details == 2:
            self.dock_pos_details.show()

    def take_screenshot(self):
        """
        Take a screenshot of what user choosed in option window.
        Called when user clicks on screenshot buttons.
        """

        config = read_config()  # load config file

        what_to_print = config["what_to_print"]
        state_infos = str(config["what_to_show"]["state_infos"])
        state_size = str(config["what_to_show"]["state_size"])
        base_dir_out = config["dir_out"]
        currency_symbol = config["currency_symbol"]

        if not os.path.exists(base_dir_out):
            os.makedirs(base_dir_out)  # create dir if not exists

        dock_widget_list = self.findChildren(QtWidgets.QDockWidget)  # get all qdock
        active_tab = self.widget_tab.currentIndex()
        active_tab_name = str(self.widget_tab.tabText(active_tab)).replace("&", "")

        old_labels = OrderedDict()  # dict to save unchanged labels

        connect_dict = self.session._get_connect_dict()
        base_url = connect_dict["base_url"]

        """
        Update account dock according touser"s choice.
        Sensitive info such asID, capital...can be hidden
        """

        if state_infos == "Never":  # don"t hide infos
            pass

        else:
            for key in self.dict_account_labels.keys():
                label = self.dict_account_labels[key]
                old_text = label.text()  # get unchanged text
                old_labels[key] = old_text

                if key == "Account type: ":
                    if "demo" in base_url:
                        label.setText("Demo-xxxx")
                    else:
                        label.setText("Live-xxxx")

                elif currency_symbol in old_text:
                    label.setText(f"xxxx{currency_symbol}")

                else:
                    label.setText("xxxx")

        all_state = config["all"]  # all markets or filter set

        if all_state != 2:
            modified_transactions = self.filtered_dict

        else:
            modified_transactions = self.local_transactions

        fill_args = {
            "modified_trans": modified_transactions,
            "screenshot": True,
            "sender": "screenshot",
        }

        """
        Called update_results notifying function that a screenshot
        is being taken. Seefunction to see how it manage options
        """

        try:
            self.update_results({}, **fill_args)

        except Exception as e:
            msg = "An error occured, see log file"
            self.statusBar().showMessage(msg)
            self.logger_debug.log(logging.ERROR, traceback.format_exc())

        # dict with base file name as key and pixmap as value
        pixmap_dict = {}

        if what_to_print == "All window":
            pixmap = QtWidgets.QWidget.grab(self)  # get pix map of all window
            pixmap_dict["Summary + " + active_tab_name + " "] = pixmap

            pixmap = QtWidgets.QWidget.grab(self.widget_pos, self.widget_pos.rect())

            # the key will be used to construct file name
            pixmap_dict["Transactions "] = pixmap

            for key in self.graph_dict.keys():  # get pixmap of all graphs
                graph = self.graph_dict[key]["equity_plot"]
                pixmap_graph = QtWidgets.QWidget.grab(graph)

                # the key will be used to construct file name
                pixmap_dict[key + " EC "] = pixmap_graph

        elif what_to_print == "Transactions":  # get pixmap of transactions table
            pixmap = QtWidgets.QWidget.grab(self.widget_pos, self.widget_pos.rect())

            # the key will be used to construct file name
            pixmap_dict["Transactions "] = pixmap

        elif what_to_print == "Graph":
            for key in self.graph_dict.keys():  # take pixmap of all graph
                graph = self.graph_dict[key]["equity_plot"]
                pixmap_graph = QtWidgets.QWidget.grab(graph)

                # the key will be used to construct file name
                pixmap_dict[key + " EC "] = pixmap_graph

        elif what_to_print == "Summary":  # get pixmap of Summary dock
            # build a list with all name of qdock ans get Summary dock
            dock_widget_names = [dock.objectName() for dock in dock_widget_list]
            idx_dock_summary = dock_widget_names.index("Summary")
            dock_summary = dock_widget_list[idx_dock_summary]

            pixmap = QtWidgets.QWidget.grab(dock_summary)

            # the key will be used to construct file name
            pixmap_dict["Summary "] = pixmap

        # save the pixmap as a png file
        now_for_human = datetime.datetime.now().strftime("(%d-%m-%Y %Hh%Mh%S)")

        for key in pixmap_dict.keys():
            file_out = str((base_dir_out / f"{key}{now_for_human}.png").absolute())
            pixmap_dict[key].save(file_out, "png")

        # restore previous results
        if config["all"] == 0:
            fill_args = {"modified_trans": self.filtered_dict, "screenshot": False}

        else:
            fill_args = {"modified_trans": self.local_transactions, "screenshot": False}

        fill_args["msg"] = "Screenshot saved"
        fill_args["sender"] = "screenshot"

        try:
            self.update_results({}, **fill_args)

        except Exception as e:
            msg = "An error occured, see log file"
            self.statusBar().showMessage(msg)
            self.logger_debug.log(logging.ERROR, traceback.format_exc())

        if state_infos != "Never":  # reset account labels if they have been changed
            for key in self.dict_account_labels.keys():
                label = self.dict_account_labels[key]
                label.setText(old_labels[key])

        msg = "Screenshots saved"
        self.statusBar().showMessage(msg)

    def set_gui_enabled(self, state):
        """
        Enable/disable  all user's interactions.

        :param state: boolean
        """
        # get the dock_widgets
        dock_widget_list = self.findChildren(QtWidgets.QDockWidget)
        for dock in dock_widget_list:
            dock.setEnabled(state)

        # activate actions/buttons
        self.menu_switch.setEnabled(state)

        self.act_options.setEnabled(state)
        self.act_disconnect.setEnabled(state)

        self.btn_screenshot.setEnabled(state)
        self.btn_refresh.setEnabled(state)
        self.btn_export.setEnabled(state)

        self.widget_tab.setEnabled(state)
        self.statusBar().setEnabled(state)

    def keyPressEvent(self, event):
        """
        Reimplement keyPressEvent. Allow the user to
        naviguate throught graph using arrow keys and to
        take screenshot via a shortcut

        :param event: QtCOre.QKeyEvent
        """

        config = read_config()
        state_details = config["what_to_show"]["state_details"]
        shortcut = config["shortcut"]

        # check if the key pressed correspond to a key sequence
        if event.type() == QtCore.QEvent.KeyPress:
            key = event.key()

            if key == QtCore.Qt.Key_unknown:
                warnings.warn("Unknown key from a macro probably")
                return

            # the user have clicked just and only the special keys Ctrl, Shift, Alt, Meta.
            if (
                key == QtCore.Qt.Key_Control
                or key == QtCore.Qt.Key_Shift
                or key == QtCore.Qt.Key_Alt
                or key == QtCore.Qt.Key_Meta
            ):
                return

            # check for a combination of user clicks
            modifiers = event.modifiers()
            keyText = event.text()

            # if the keyText is empty than it's a special key like F1, F5, ...
            if modifiers & QtCore.Qt.ShiftModifier:
                key += QtCore.Qt.SHIFT
            if modifiers & QtCore.Qt.ControlModifier:
                key += QtCore.Qt.CTRL
            if modifiers & QtCore.Qt.AltModifier:
                key += QtCore.Qt.ALT
            if modifiers & QtCore.Qt.MetaModifier:
                key += QtCore.Qt.META

            # if keysequence is the one saved take screenshot
            human_shortcut = QtGui.QKeySequence(key).toString(
                QtGui.QKeySequence.NativeText
            )

            # take screenshot
            if human_shortcut == shortcut:
                self.take_screenshot()
                return

        # if key is not the shorcut naviguate on graph
        if state_details == 2:
            if event.key() == QtCore.Qt.Key_Right:  # right arrow
                # retrieve active plot widget
                active_tab = self.widget_tab.currentIndex()
                active_tab_name = str(self.widget_tab.tabText(active_tab)).replace(
                    "&", ""
                )

                # "Transactions" not a graph
                if active_tab_name == "Transactions":
                    plot_widget = self.graph_dict["Points"]["equity_plot"]

                # "Points" graph as default
                else:
                    plot_widget = self.graph_dict[active_tab_name]["equity_plot"]

                try:
                    vline_pos = plot_widget.get_vline_pos() + 1  # next pos on the right
                    point_obj = QtCore.QPointF(vline_pos, 0)

                    # simulate a mouse click near the new pos
                    vline_coord = plot_widget.plotItem.vb.mapViewToScene(
                        point_obj
                    ).toPoint()

                    trade_args = {
                        "plot_widget": plot_widget,
                        "mouse_pos": vline_coord,
                        "vline_pos": vline_pos,
                        "screenshot": False,
                    }

                except TypeError:  # update_trade_details hasn"t been called yet
                    point_obj = QtCore.QPointF(vline_pos, 0)  # FIXME

                    # simulate a mouse click (1, 0)
                    vline_coord = plot_widget.plotItem.vb.mapViewToScene(
                        point_obj
                    ).toPoint()

                    trade_args = {
                        "plot_widget": plot_widget,
                        "mouse_pos": vline_coord,
                        "vline_pos": 1,  # force new_vline to be at 1
                        "screenshot": False,
                    }

                try:
                    self.update_trade_details(**trade_args)

                except Exception as e:
                    msg = "An error occured, see log file"
                    self.statusBar().showMessage(msg)
                    self.logger_debug.log(logging.ERROR, traceback.format_exc())

                event.accept()

            elif event.key() == QtCore.Qt.Key_Left:
                # retrieve active plot widget
                active_tab = self.widget_tab.currentIndex()
                active_tab_name = str(self.widget_tab.tabText(active_tab)).replace(
                    "&", ""
                )

                # "Transactions" not a graph
                if active_tab_name == "Transactions":
                    plot_widget = self.graph_dict["Points"]["equity_plot"]

                # "Points" graph as default
                else:
                    plot_widget = self.graph_dict[active_tab_name]["equity_plot"]

                try:
                    vline_pos = plot_widget.get_vline_pos() - 1  # next pos on the right
                    point_obj = QtCore.QPointF(vline_pos, 0)

                    # simulate a mouse click near the new pos
                    vline_coord = plot_widget.plotItem.vb.mapViewToScene(
                        point_obj
                    ).toPoint()

                    trade_args = {
                        "plot_widget": plot_widget,
                        "mouse_pos": vline_coord,
                        "vline_pos": vline_pos,
                        "screenshot": False,
                    }

                except TypeError:  # update_trade_details hasn"t been called yet
                    point_obj = QtCore.QPointF(vline_pos, 0)  # FIXME

                    # simulate a mouse click (1, 0)
                    vline_coord = plot_widget.plotItem.vb.mapViewToScene(
                        point_obj
                    ).toPoint()
                    trade_args = {
                        "plot_widget": plot_widget,
                        "mouse_pos": vline_coord,
                        "vline_pos": 1,  # force new_vline to be at 1
                        "screenshot": False,
                    }

                try:
                    self.update_trade_details(**trade_args)

                except Exception as e:
                    msg = "An error occured, see log file"
                    self.statusBar().showMessage(msg)
                    self.logger_debug.log(logging.ERROR, traceback.format_exc())

                event.accept()

            else:
                QtWidgets.QMainWindow.keyPressEvent(self, event)
                event.accept()

        else:
            QtWidgets.QMainWindow.keyPressEvent(self, event)
            event.accept()

    def mousePressEvent(self, event):
        """
        Reimplement mousePressEvent. If left click and user want to see trade
        details update floating dock with infos about trade under mouse click.

        :param event: QtCore.QMouseEvent
        """

        config = read_config()
        state_details = config["what_to_show"]["state_details"]

        if event.button() == QtCore.Qt.LeftButton:
            # retrieve active plot widget
            active_tab = self.widget_tab.currentIndex()
            active_tab_name = str(self.widget_tab.tabText(active_tab)).replace("&", "")

            # "Transactions" not a graph
            if active_tab_name == "Transactions":
                plot_widget = self.graph_dict["Points"]["equity_plot"]

            # "Points" graph as default
            else:
                plot_widget = self.graph_dict[active_tab_name]["equity_plot"]

            plot_widget_rect = plot_widget.getViewBox().geometry()
            mouse_pos = plot_widget.mapFromGlobal(event.globalPos())

            # mouse not under plot widget
            if plot_widget_rect.contains(mouse_pos) == False:
                QtWidgets.QMainWindow.mousePressEvent(self, event)
                event.accept()
                return

            else:
                if self.dock_pos_details.isHidden() == True and state_details == 2:
                    self.dock_pos_details.show()

                elif self.dock_pos_details.isHidden() == False and state_details != 2:
                    self.dock_pos_details.hide()

                else:
                    pass

                # update dock_pos_details
                trade_args = {
                    "plot_widget": plot_widget,
                    "mouse_pos": mouse_pos,
                    "screenshot": False,
                }

                # update trade details
                try:
                    self.update_trade_details(**trade_args)

                except Exception as e:
                    msg = "An error occured, see log file"
                    self.statusBar().showMessage(msg)
                    self.logger_debug.log(logging.ERROR, traceback.format_exc())

                event.accept()

        else:
            QtWidgets.QMainWindow.mousePressEvent(self, event)
            event.accept()

    def resizeEvent(self, event):
        """Reimplement resizeEvent to update comment pos"""

        for key in self.graph_dict.keys():
            equity_plot = self.graph_dict[key]["equity_plot"]
            equity_curve = self.graph_dict[key]["curve"]["equity_curve"]
            equity_plot.update_text_item(equity_curve)

    def closeEvent(self, event):
        """User closes window"""

        config = read_config()

        # save state and window size
        config["gui_size"] = (self.size().width(), self.size().height())
        config["gui_state"] = QtCore.QByteArray(self.saveState())
        config["gui_pos"] = (self.pos().x(), self.pos().y())

        write_config(config)

        self.close()

    def disconnect_from_api(self):
        """
        Disconnect from API. Unsuscribe to ls
        table and clear GUI and disable interaction
        """

        self.ls_client.delete(self.balance_table)
        self.ls_client.delete(self.pos_table)

        self.ls_client.destroy()

        del (
            self.balance_table,
            self.pos_table,
            self.ls_client,
            self.pos_update_sig,
            self.acc_update_sig,
        )

        msg = "Logging out..."
        self.logger_info.log(logging.INFO, msg)

        # request a logout
        logout_reply = self.session.logout()

        # request failed
        if type(logout_reply) == APIError:
            msg = logout_reply._get_error_msg()
            self.statusBar().showMessage(msg)
            return

        else:
            # display and log a msg
            msg = "Not connected"
            self.logger_info.log(logging.INFO, msg)
            self.statusBar().showMessage(msg)

            for i in range(self.widget_pos.rowCount()):
                self.widget_pos.removeRow(0)  ## remove rows

            for key in self.dict_summary_labels.keys():
                self.dict_summary_labels[key].setText(key + ": ")  ## clear labels

            # clear all graphs
            for i, key in enumerate(self.graph_dict.keys()):
                graph = self.graph_dict[key]["equity_plot"]

                for item in self.graph_dict[key]["curve"].keys():
                    curve = self.graph_dict[key]["curve"][item]
                    curve.clear()

            self.set_gui_enabled(False)
