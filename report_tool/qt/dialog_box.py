"""Module to create custom QDialog"""

import json
from copy import deepcopy

from PyQt5 import QtCore, QtGui, QtWidgets

from report_tool import __version__
from report_tool.qt.functions import (
    create_icons,
    read_credentials,
    read_ig_config,
    write_credentials,
)
from report_tool.qt.widgets import (
    CustomComboBox,
    CustomLabel,
    CustomPushButton,
    CustomShortcutLineEdit,
)
from report_tool.utils.fs_utils import get_icon_path
from report_tool.utils.settings import read_config, write_config


class ConnectWindow(QtWidgets.QDialog):

    """Create a simple dialog to add/delete and configure user"s account"""

    def __init__(self, parent):
        super(ConnectWindow, self).__init__(parent=parent)
        self._connect_dict = {}

        # configure QDialog
        self.setModal(True)
        self.setWindowTitle("Login Informations")

        layout_login = QtWidgets.QGridLayout()

        # create input widgets
        self.combobox_usr = CustomComboBox("user_choice")
        self.combobox_type = QtWidgets.QComboBox()

        self.line_edit_proxies = QtWidgets.QLineEdit()
        self.line_edit_pwd = QtWidgets.QLineEdit()
        self.line_edit_key = QtWidgets.QLineEdit()

        self.chkbox_autoconnect = QtWidgets.QCheckBox()
        self.chkbox_remember = QtWidgets.QCheckBox()

        self.btn_trash = CustomLabel("trash")
        self.btn_connect = QtWidgets.QPushButton("Connect")

        # configure widgets
        self.combobox_type.addItems(["Live", "Demo"])
        self.chkbox_remember.setChecked(True)
        self.combobox_usr.setEditable(True)
        self.combobox_usr.setInsertPolicy(QtWidgets.QComboBox.InsertAlphabetically)

        self.line_edit_pwd.setEchoMode(QtWidgets.QLineEdit.Password)

        self.btn_trash.set_default_style("transparent", "transparent", "transparent")
        self.btn_trash.setPixmap(QtGui.QPixmap(str(get_icon_path("trash"))))

        list_widgets_login = [
            QtWidgets.QLabel("Username: "),
            self.combobox_usr,
            QtWidgets.QLabel("Password: "),
            self.line_edit_pwd,
            QtWidgets.QLabel("API key: "),
            self.line_edit_key,
            QtWidgets.QLabel("Proxies: "),
            self.line_edit_proxies,
            QtWidgets.QLabel("Account Type: "),
            self.combobox_type,
            QtWidgets.QLabel("Auto connect on start up: "),
            self.chkbox_autoconnect,
            QtWidgets.QLabel("Remember credentials: "),
            self.chkbox_remember,
        ]

        # configure signals
        self.btn_connect.clicked.connect(self.create_connection_dict)
        self.btn_trash.clicked_signal.connect(self.delete_account)

        self.combobox_usr.editTextChanged.connect(self.user_edition)
        self.combobox_usr.focus_out_signal.connect(self.add_account)

        self.line_edit_pwd.textChanged.connect(self.user_edition)
        self.line_edit_key.textChanged.connect(self.user_edition)

        # place widget on layout
        for count, widget in enumerate(list_widgets_login):
            if count % 2 == 0:
                row = count + 1
                col = 0
            else:
                row = count
                col = 1

            layout_login.addWidget(widget, row, col)

        # place trash "button" and connect button
        layout_login.addWidget(self.btn_trash, 1, 2, 1, 1)
        layout_login.addWidget(self.btn_connect, count + 1, 0, 1, 3)  # TODO: check

        # configure QDialog
        self.setLayout(layout_login)
        self.resize(300, 150)
        self.load_accounts()
        self.exec_()

    def load_accounts(self):
        """Load saved accounts in credentials.json"""

        # read config file and credentials
        saved_accounts = read_credentials()
        config = read_config()

        list_type = ["Live", "Demo"]
        acc_type = self.combobox_type.currentText()  # get account type
        saved_usr = saved_accounts.keys()  # get saved usr

        last_usr = config["last_usr"]
        auto_connect = config["auto_connect"]

        self.combobox_usr.addItems(sorted(saved_usr))  # add usr to combobox

        # set last user used if exists
        idx_last_usr = self.combobox_usr.findText(last_usr)

        if idx_last_usr != -1:
            self.combobox_usr.setCurrentIndex(idx_last_usr)
        else:
            pass

        # get infos of account selected
        current_usr = str(self.combobox_usr.currentText())
        current_account = saved_accounts[current_usr]

        current_pwd = current_account["pwd"]
        current_api_key = current_account["api_key"]
        current_type = current_account["type"]
        current_proxies = current_account["proxies"]["https"]

        # set infos into inputs widgets
        self.line_edit_pwd.setText(current_pwd)
        self.line_edit_key.setText(current_api_key)
        self.line_edit_proxies.setText(current_proxies)

        self.combobox_type.setCurrentIndex(list_type.index(current_type))
        self.chkbox_autoconnect.setCheckState(auto_connect)

        # enabled (or not) trash button
        if current_usr == "":
            self.btn_trash.setEnabled(False)
            self.btn_connect.setEnabled(False)
        else:
            self.btn_trash.setEnabled(True)
            self.btn_connect.setEnabled(True)

    def add_account(self):
        """
        Add a new account to combobox and a new key to
        credentials file. called when combobox user loses focus
        """

        saved_accounts = read_credentials()

        # get set infos
        usr = self.combobox_usr.currentText()
        idx_usr = self.combobox_usr.findText(usr)

        api_key = str(self.line_edit_key.text())
        pwd = str(self.line_edit_pwd.text())
        acc_type = str(self.combobox_type.currentText())
        proxies = str(self.line_edit_proxies.text())

        # del empty account created if no account saved
        if "" in saved_accounts.keys():
            saved_accounts.pop("", None)
            idx_empty = self.combobox_usr.findText("")

            # remove empty account from combobox
            if idx_empty != -1:
                self.combobox_usr.removeItem(idx_empty)
            else:
                pass

        # if a new user is created
        if idx_usr == -1:
            # sort alphabetically users
            saved_users = list(saved_accounts.keys())
            saved_users.append(str(usr))
            sorted_users = sorted(saved_users)
            idx_new_usr = sorted_users.index(str(usr))
            self.combobox_usr.insertItem(idx_new_usr, usr)
        else:
            pass

        # update saved accounts dict
        saved_accounts[str(usr)] = {}

        saved_accounts[str(usr)]["pwd"] = pwd
        saved_accounts[str(usr)]["api_key"] = api_key
        saved_accounts[str(usr)]["type"] = acc_type
        saved_accounts[str(usr)]["proxies"] = {"https": proxies}

        # enabled (or not) trash button
        if usr == "":
            self.btn_trash.setEnabled(False)
        else:
            self.btn_trash.setEnabled(True)

        # write new credentials
        write_credentials(saved_accounts)

    def delete_account(self):
        """When user clicks on button trash deletes selected account"""

        saved_accounts = read_credentials()

        usr_to_delete = str(self.combobox_usr.currentText())
        idx_usr_to_delete = self.combobox_usr.currentIndex()

        # delete key in dict and remove usr in combobox
        saved_accounts.pop(usr_to_delete, None)
        self.combobox_usr.removeItem(idx_usr_to_delete)

        # write new credentials
        write_credentials(saved_accounts)

    def user_edition(self):
        """User is editing account via inputs widgets."""

        saved_accounts = read_credentials()
        list_type = ["Live", "Demo"]

        # get user modifications
        usr = str(self.combobox_usr.currentText())
        api_key = str(self.line_edit_key.text())
        pwd = str(self.line_edit_pwd.text())
        acc_type = str(self.combobox_type.currentText())
        proxies = str(self.line_edit_proxies.text())

        # user editing name in combobox
        if self.sender().objectName() == "user_choice":
            # new username not saved yet
            if usr not in saved_accounts:
                # clear pwd, api key and proxies widgets
                self.line_edit_pwd.setText("")
                self.line_edit_key.setText("")
                self.line_edit_proxies.setText("")

            # username already exists, set known infos
            else:
                saved_pwd = saved_accounts[usr]["pwd"]
                saved_api_key = saved_accounts[usr]["api_key"]
                saved_acc_type = saved_accounts[usr]["type"]
                saved_proxies = saved_accounts[usr]["proxies"]["https"]

                # fill widgets with known infos
                self.line_edit_pwd.setText(saved_pwd)
                self.line_edit_key.setText(saved_api_key)
                self.line_edit_proxies.setText(saved_proxies)

                self.combobox_type.setCurrentIndex(list_type.index(saved_acc_type))
                self.btn_trash.setEnabled(True)

        else:
            # if pwd and api key and user are not
            # correctly set disable connection
            if usr == "" or pwd == "" or api_key == "":
                self.btn_connect.setEnabled(False)
            else:
                self.btn_connect.setEnabled(True)

        # write new credentials
        write_credentials(saved_accounts)

        # enabled (or not) trash button
        if usr == "":
            self.btn_trash.setEnabled(False)
        else:
            self.btn_trash.setEnabled(True)

    def create_connection_dict(self):
        """
        Set connection info, username/pwd and urls.Creates a dict
        with headers correctly setfor connection request, usr and
        pwd and urlsu sed to communicate with API
        """

        # get infos to establish connection with API
        acc_type = str(self.combobox_type.currentText())
        usr = str(self.combobox_usr.currentText())
        pwd = str(self.line_edit_pwd.text())
        api_key = str(self.line_edit_key.text())
        proxies = str(self.line_edit_proxies.text())

        checkbox_state = self.chkbox_remember.checkState()
        auto_connect = self.chkbox_autoconnect.checkState()
        saved_accounts = read_credentials()
        config = read_config()

        # set selected account in dict to saved
        saved_accounts[usr] = {}

        saved_accounts[usr]["pwd"] = pwd
        saved_accounts[usr]["api_key"] = api_key
        saved_accounts[usr]["type"] = acc_type
        saved_accounts[usr]["proxies"] = {"https": proxies}

        # update config file
        config["last_usr"] = usr
        config["auto_connect"] = auto_connect
        write_config(config)

        # delete empty key (created when file is empty)
        if "" in saved_accounts:
            saved_accounts.pop("", None)

        ig_urls = read_ig_config()

        if acc_type == "Live":
            base_url = ig_urls["base_url"]["live"]
        elif acc_type == "Demo":
            base_url = ig_urls["base_url"]["demo"]

        # credentials["usr"]     = usr
        # credentials["pwd"]     = pwd
        # credentials["api_key"] = api_key

        # save file according to user's choice(remember or not)
        if checkbox_state == 2:
            write_credentials(saved_accounts)
        elif checkbox_state == 0:
            write_credentials({})  # save empty dict

        connect_args = {
            "urls": base_url,
            "identifier": usr,
            "password": pwd,
            "X-IG-API-KEY": api_key,
            "proxies": proxies,
        }

        self._set_connect_dict(**connect_args)
        self.on_close()

    def _get_connect_dict(self):
        """Getter method"""

        return self._connect_dict

    def _set_connect_dict(self, *args, **kwargs):
        """
        Setter method. Build a connect_dict with infos
        needed for API connection see API documentation
        for structure of payload, header and get method

        :kw param identifier: string, username
        :kw param password: string,
        :kw param X-IG-API-KEY: api key of account
        :kw param proxies: dict proxy to connect through
        :kw param urls: string, base url for interacting with API
        """

        connect_dict = {}

        payload = json.dumps(
            {"identifier": kwargs["identifier"], "password": kwargs["password"]}
        )

        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "Accept": "application/json; charset=utf-8",
            "X-IG-API-KEY": kwargs["X-IG-API-KEY"],
        }

        proxies = {"https": kwargs["proxies"]}

        connect_dict["base_url"] = kwargs["urls"]
        connect_dict["payload"] = payload
        connect_dict["headers"] = headers
        connect_dict["proxies"] = proxies

        self._connect_dict = connect_dict

    def on_close(self):
        """close window"""

        self.close()


class OptionsWindow(QtWidgets.QDialog):

    """
    Class to buid an options windows. Users can
    configure plot options, screenshots options
    """

    options_signal = QtCore.pyqtSignal(object)  # signal send when options changes

    def __init__(self, parent):
        super(OptionsWindow, self).__init__(parent=parent)
        self.setWindowIcon(QtGui.QIcon(str(get_icon_path("main"))))
        self.setWindowTitle("Options")
        self.setModal(True)

        ec_icons, dd_icons = create_icons()

        widget_screenshot = self.create_screenshot_options()
        widget_equity_curves = self.create_chart_options(ec_icons)
        widget_dd_options = self.create_dd_options(dd_icons)
        widget_transactions_options = self.create_transactions_options()

        btn_close = QtWidgets.QPushButton("Ok")

        # configure main widget
        layout_main = QtWidgets.QGridLayout()
        layout_main.addWidget(widget_equity_curves, 0, 0)
        layout_main.addWidget(widget_dd_options, 0, 1, 2, 1)
        layout_main.addWidget(widget_screenshot, 2, 0, 1, 2)
        layout_main.addWidget(widget_transactions_options, 1, 0)
        layout_main.addWidget(btn_close, 4, 0, 1, 2)

        btn_close.clicked.connect(self.on_close)

        self.setLayout(layout_main)
        self.update_options()
        # self.exec_()

    def create_screenshot_options(self):
        """
        Create widget for screenshot options. User can
        chose what to print, where and what to hide
        """

        config = read_config()

        # init widgets
        layout_screenshot = QtWidgets.QGridLayout()
        widget_screenshot = QtWidgets.QGroupBox("Screenshot options")

        self.combobox_what_to_print = QtWidgets.QComboBox()
        self.combobox_infos = QtWidgets.QComboBox()
        self.combobox_size = QtWidgets.QComboBox()
        self.line_edit_shortcut = CustomShortcutLineEdit("shortcut")

        self.btn_file = QtWidgets.QPushButton()

        # get standart icon for open files
        file_ico = self.style().standardIcon(QtWidgets.QStyle.SP_DirOpenIcon)

        # get config
        what_to_print = config["what_to_print"]
        state_size = config["what_to_show"]["state_size"]
        state_infos = config["what_to_show"]["state_infos"]
        shortcut = config["shortcut"]

        # configure widgets
        self.btn_file.setIcon(file_ico)
        self.combobox_what_to_print.addItems(
            ["All window", "Summary", "Transactions", "Graph"]
        )

        screenshot_options = ["Always", "Only for screenshot", "Never"]

        if shortcut == "Enter shortcut" or "Invalid shortcut":
            self.line_edit_shortcut.set_italic(True)
        else:
            self.line_edit_shortcut.set_italic(False)

        self.line_edit_shortcut.setToolTip("Configure a shortcut to take screenshot")

        # addd options to comboboxes
        for option in screenshot_options:
            self.combobox_infos.addItem(option, userData=QtCore.QVariant(option))
            self.combobox_size.addItem(option, userData=QtCore.QVariant(option))

        # get and set previous config
        index_what_to_print = self.combobox_what_to_print.findText(what_to_print)
        index_infos = self.combobox_infos.findText(state_infos)
        index_size = self.combobox_size.findText(state_size)

        self.combobox_infos.setCurrentIndex(index_infos)
        self.combobox_size.setCurrentIndex(index_size)
        self.combobox_what_to_print.setCurrentIndex(index_what_to_print)
        self.line_edit_shortcut.setText(shortcut)

        # configure size for widgets
        self.combobox_infos.setFixedWidth(200)
        self.combobox_size.setFixedWidth(200)
        self.combobox_what_to_print.setFixedWidth(200)
        self.line_edit_shortcut.setFixedWidth(200)
        self.btn_file.setFixedWidth(200)

        # set object names according to config file keys
        self.combobox_infos.setObjectName("state_infos")
        self.combobox_size.setObjectName("state_size")
        self.combobox_what_to_print.setObjectName("what_to_print")
        self.line_edit_shortcut.text_changed.connect(self.update_options)

        # connect signals
        self.combobox_what_to_print.currentIndexChanged.connect(self.update_options)
        self.combobox_infos.currentIndexChanged.connect(self.update_options)
        self.combobox_size.currentIndexChanged.connect(self.update_options)
        self.btn_file.clicked.connect(self.set_screenshot_path)

        # place widgets
        layout_screenshot.addWidget(QtWidgets.QLabel("Shortcut:"), 0, 0)
        layout_screenshot.addWidget(
            self.line_edit_shortcut, 0, 1, 1, 2, QtCore.Qt.AlignCenter
        )

        layout_screenshot.addWidget(QtWidgets.QLabel("Print:"), 1, 0)
        layout_screenshot.addWidget(
            self.combobox_what_to_print, 1, 1, 1, 2, QtCore.Qt.AlignCenter
        )

        layout_screenshot.addWidget(QtWidgets.QLabel("Hide sensitive infos: "), 2, 0)
        layout_screenshot.addWidget(
            self.combobox_infos, 2, 1, 1, 2, QtCore.Qt.AlignCenter
        )

        layout_screenshot.addWidget(QtWidgets.QLabel("Hide lot size: "), 3, 0)
        layout_screenshot.addWidget(
            self.combobox_size, 3, 1, 1, 2, QtCore.Qt.AlignCenter
        )

        layout_screenshot.addWidget(QtWidgets.QLabel("Save to :"), 5, 0)
        layout_screenshot.addWidget(self.btn_file, 5, 1, 1, 2, QtCore.Qt.AlignCenter)

        widget_screenshot.setLayout(layout_screenshot)

        return widget_screenshot

    def create_chart_options(self, ec_icons):
        """
        Create chart options widget. User can
        changes curve style, color and thickness

        :param ec_icons: dict with pixmap of curves style
        """

        config = read_config()

        # init widgets
        widget_equity_curves = QtWidgets.QGroupBox("Chart options")
        layout_equity_curves = QtWidgets.QGridLayout()

        self.btn_ec_color = CustomPushButton("ec_color")
        self.combobox_ec_style = QtWidgets.QComboBox()  # curve style
        self.spinbox_ec_size = QtWidgets.QSpinBox()  # curve thickness
        self.checkbox_details = QtWidgets.QCheckBox()
        self.checkbox_dates = QtWidgets.QCheckBox()

        # configure widgets
        self.btn_ec_color.set_default_style(config["ec_color"])
        self.btn_ec_color.clicked.connect(self.update_options)

        self.spinbox_ec_size.setObjectName("ec_size")
        self.spinbox_ec_size.setMinimum(1)
        self.spinbox_ec_size.setFixedWidth(78)
        self.spinbox_ec_size.setValue(int(config["ec_size"]))
        self.spinbox_ec_size.valueChanged.connect(self.update_options)

        self.checkbox_details.setObjectName("state_details")
        self.checkbox_details.setCheckState(config["what_to_show"]["state_details"])
        self.checkbox_details.stateChanged.connect(self.update_options)

        self.checkbox_dates.setObjectName("state_dates")
        self.checkbox_dates.setCheckState(config["what_to_show"]["state_dates"])
        self.checkbox_dates.stateChanged.connect(self.update_options)

        # add icons to combobox
        for count, key in enumerate(ec_icons.keys()):
            name = ec_icons[key]
            self.combobox_ec_style.addItem(
                ec_icons[key], "", userData=QtCore.QVariant(key)
            )

        index_ec_style = self.combobox_ec_style.findData(config["ec_style"])

        self.combobox_ec_style.setCurrentIndex(index_ec_style)
        self.combobox_ec_style.setIconSize(QtCore.QSize(100, 14))
        self.combobox_ec_style.setObjectName("ec_style")
        self.combobox_ec_style.setFixedWidth(78)
        self.combobox_ec_style.currentIndexChanged.connect(self.update_options)

        # place widgets on layout
        layout_equity_curves.addWidget(QtWidgets.QLabel("Color:"), 0, 0)
        layout_equity_curves.addWidget(self.btn_ec_color, 0, 1)

        layout_equity_curves.addWidget(QtWidgets.QLabel("Style:"), 1, 0)
        layout_equity_curves.addWidget(self.combobox_ec_style, 1, 1)

        layout_equity_curves.addWidget(QtWidgets.QLabel("Thickness:"), 2, 0)
        layout_equity_curves.addWidget(self.spinbox_ec_size, 2, 1)

        layout_equity_curves.addWidget(
            QtWidgets.QLabel("Show positions details:"), 3, 0
        )

        layout_equity_curves.addWidget(
            self.checkbox_details, 3, 1, 1, 1, QtCore.Qt.AlignRight
        )

        layout_equity_curves.addWidget(QtWidgets.QLabel("Show dates on axis:"), 4, 0)

        layout_equity_curves.addWidget(
            self.checkbox_dates, 4, 1, 1, 1, QtCore.Qt.AlignRight
        )

        widget_equity_curves.setLayout(layout_equity_curves)

        return widget_equity_curves

    def create_dd_options(self, dd_icons):
        """
        Create dd options widget. User can changes point symbol, color
        and size for each scatterplot. He can choose which scatter
        to show, to hide capital, account infos, lot size.

        :param dd_icons: dict with pixmap of scatter style
        """
        config = read_config()

        # init widgets
        widget_dd_options = QtWidgets.QGroupBox("Scatter plot options")
        layout_dd = QtWidgets.QGridLayout()

        self.checkbox_dd = QtWidgets.QCheckBox()
        self.checkbox_maxdd = QtWidgets.QCheckBox()
        self.checkbox_high = QtWidgets.QCheckBox()

        self.btn_high_color = CustomPushButton("high_color")
        self.btn_dd_color = CustomPushButton("depth_color")
        self.btn_max_dd_color = CustomPushButton("maxdd_color")

        self.combobox_dd_style = QtWidgets.QComboBox()
        self.combobox_high_style = QtWidgets.QComboBox()
        self.combobox_maxdd_style = QtWidgets.QComboBox()

        self.spinbox_symbol_size = QtWidgets.QSpinBox()

        # init lists to easily configure widgets
        combobox_name_list = ["depth_style", "high_style", "maxdd_style"]

        combobox_list = [
            self.combobox_dd_style,
            self.combobox_high_style,
            self.combobox_maxdd_style,
        ]

        color_btn_list = [self.btn_dd_color, self.btn_high_color, self.btn_max_dd_color]

        dd_color_list = [
            config["depth_color"],
            config["high_color"],
            config["maxdd_color"],
        ]  # color set previously

        symbol_list = ["x", "d", "o", "t", "+", "s"]

        # configure combobox
        for count, combobox in enumerate(combobox_list):
            color_btn = color_btn_list[count]

            combobox.setIconSize(QtCore.QSize(100, 14))
            combobox.setObjectName(combobox_name_list[count])
            combobox.setFixedWidth(78)
            color_btn.set_default_style(dd_color_list[count])

            for symbol in symbol_list:
                combobox.addItem(dd_icons[symbol], "", userData=QtCore.QVariant(symbol))

            index_dd_style = combobox.findData(config[combobox_name_list[count]])
            combobox.setCurrentIndex(index_dd_style)

        self.spinbox_symbol_size.setFixedWidth(78)

        """
        plot_available contains strings used to create scatter items in
        the main window, to place widgets and configure them in optionsWindow
        to set objectName, to detect which scatter to show   or not and are
        used in config file as keys. If you modified it be  aware that you"ll
        need to modify default_dict in read_config(),  names of plot
        in MainWindow.create_central_widget(), plot_available and order in
        scatter_data in create_curves() . If you want to modify
        the positions of widgets in optionsWindow, you"ll nedd to modify
        label_list and   buttons_list to keep the functions work correctly.
        see examples below.
        """

        #########example##########
        # plot_available = ["depth", "high", "maxdd"]
        # label_list = [
        #               QtGui.QLabel("Show drawdowns: "),
        #               QtGui.QLabel("Drawdown color: "),
        #               QtGui.QLabel("Drawdown symbol: "),
        #               QtGui.QLabel(""),
        #               QtGui.QLabel("Show new highs: "),
        #               QtGui.QLabel("New high color: "),
        #               QtGui.QLabel("New high symbol: "),
        #               QtGui.QLabel(""),
        #               QtGui.QLabel("Show max drawdown: "),
        #               QtGui.QLabel("Max drawdown color: "),
        #               QtGui.QLabel("Max drawdown symbol: "),
        #               QtGui.QLabel(""),
        #               QtGui.QLabel("Symbol size: ")
        #               ]
        # self.buttons_list = [
        #                    self.checkbox_dd, self.btn_dd_color,
        #                    self.combobox_dd_style, "",
        #                    self.checkbox_high, self.btn_high_color,
        #                    self.combobox_high_style, "",
        #                    self.checkbox_maxdd, self.btn_max_dd_color,
        #                    self.combobox_maxdd_style,"",
        #                    self.spinbox_symbol_size]
        # plot_available = ["maxdd", "depth", "high"]    # order changed
        # label_list = [
        #               QtGui.QLabel("Show max drawdown: "),
        #               QtGui.QLabel("Max drawdown color: "),
        #               QtGui.QLabel("Max drawdown symbol: "),
        #               QtGui.QLabel(""),
        #               QtGui.QLabel("Show drawdowns: "),
        #               QtGui.QLabel("Drawdown color: "),
        #               QtGui.QLabel("Drawdown symbol: "),
        #               QtGui.QLabel(""),
        #               QtGui.QLabel("Show new highs: "),
        #               QtGui.QLabel("New high color: "),
        #               QtGui.QLabel("New high symbol: "),
        #               QtGui.QLabel(""),
        #               QtGui.QLabel("Symbol size: ")]
        # self.buttons_list = [
        #                      self.checkbox_maxdd, self.btn_max_dd_color,
        #                      self.combobox_maxdd_style,"",
        #                      self.checkbox_dd, self.btn_dd_color,
        #                       self.combobox_dd_style, "",
        #                      self.checkbox_high, self.btn_high_color,
        #                      self.combobox_high_style, "",
        #                      self.spinbox_symbol_size]
        ##########end example##########

        plot_available = ["high", "depth", "maxdd"]

        label_list = [
            QtWidgets.QLabel("Symbol size: "),
            QtWidgets.QLabel(""),
            QtWidgets.QLabel("Show new highs: "),
            QtWidgets.QLabel("New high color: "),
            QtWidgets.QLabel("New high symbol: "),
            QtWidgets.QLabel(""),
            QtWidgets.QLabel("Show drawdowns: "),
            QtWidgets.QLabel("Drawdown color: "),
            QtWidgets.QLabel("Drawdown symbol: "),
            QtWidgets.QLabel(""),
            QtWidgets.QLabel("Show max drawdown: "),
            QtWidgets.QLabel("Max drawdown color: "),
            QtWidgets.QLabel("Max drawdown symbol: "),
        ]

        buttons_list = [
            self.spinbox_symbol_size,
            "",
            self.checkbox_high,
            self.btn_high_color,
            self.combobox_high_style,
            "",
            self.checkbox_dd,
            self.btn_dd_color,
            self.combobox_dd_style,
            "",
            self.checkbox_maxdd,
            self.btn_max_dd_color,
            self.combobox_maxdd_style,
        ]

        # place widgets and connect signals
        j = 0
        for i in range(len(label_list)):  # add widget to layout using loop
            label_to_set = label_list[i]
            btn_to_set = buttons_list[i]

            # add a hline to separate scatter options
            if str(label_to_set.text()) == "":
                h_line = QtWidgets.QFrame()
                h_line.setFrameShape(QtWidgets.QFrame.HLine)
                h_line.setStyleSheet("color:rgb(173,173,173);")
                layout_dd.addWidget(h_line, i, 0, 1, 2)

            else:
                layout_dd.addWidget(label_to_set, i, 0)
                layout_dd.addWidget(btn_to_set, i, 1)

            if type(btn_to_set) == CustomPushButton:
                btn_to_set.clicked.connect(self.update_options)

            elif type(btn_to_set) == QtWidgets.QComboBox:
                btn_to_set.currentIndexChanged.connect(self.update_options)

            elif type(btn_to_set) == QtWidgets.QCheckBox:
                plot = plot_available[j]
                j += 1
                btn_to_set.setObjectName(plot)
                btn_to_set.setCheckState(config["what_to_show"][plot])
                btn_to_set.stateChanged.connect(self.update_options)

            elif type(btn_to_set) == QtWidgets.QSpinBox:
                btn_to_set.setObjectName("dd_size")
                btn_to_set.setMinimum(1)
                btn_to_set.setValue(int(config["dd_size"]))
                btn_to_set.valueChanged.connect(self.update_options)

        widget_dd_options.setLayout(layout_dd)

        return widget_dd_options

    def create_transactions_options(self):
        """
        Create widget for transactions options.
        User can change flat, profit and loss colors
        """

        config = read_config()

        # init widget
        widget_transactions_options = QtWidgets.QGroupBox("Transactions options")
        layout_transactions_options = QtWidgets.QGridLayout()

        self.btn_profit_color = CustomPushButton("profit_color")
        self.btn_loss_color = CustomPushButton("loss_color")
        self.btn_flat_color = CustomPushButton("flat_color")

        # init list to easily configure and place widgets
        btn_pnl_color_list = [
            self.btn_profit_color,
            self.btn_loss_color,
            self.btn_flat_color,
        ]

        label_pnl_list = [
            QtWidgets.QLabel("Profit color:"),
            QtWidgets.QLabel("Loss color:"),
            QtWidgets.QLabel("Flat color:"),
        ]

        pnl_color_list = [
            config["profit_color"],
            config["loss_color"],
            config["flat_color"],
        ]  # color set previously

        # configure and place widgets
        for count, color in enumerate(pnl_color_list):
            label_to_set = label_pnl_list[count]
            btn_to_set = btn_pnl_color_list[count]

            btn_to_set.set_default_style(color)
            btn_to_set.clicked.connect(self.update_options)

            layout_transactions_options.addWidget(label_to_set, count, 0)
            layout_transactions_options.addWidget(btn_to_set, count, 1)

        widget_transactions_options.setLayout(layout_transactions_options)

        return widget_transactions_options

    def update_options(self):
        """
        Generic function to update options
        Options are saved each time function is called
        """

        config = read_config()

        # get config set by user and update config dict
        what_to_print = str(self.combobox_what_to_print.currentText())
        config["what_to_print"] = what_to_print

        # colors modified
        if type(self.sender()) == CustomPushButton:
            color = QtWidgets.QColorDialog.getColor()
            which_color = str(self.sender().objectName())
            config[which_color] = str(color.name())
            self.sender().set_default_style(color.name())

        # style modified
        elif type(self.sender()) == QtWidgets.QComboBox:
            idx_data = self.sender().currentIndex()
            data = self.sender().itemData(idx_data)
            which_data = str(self.sender().objectName())

            if "_style" in which_data:  # sender concerns ec style
                config[which_data] = str(data)
            else:  # else sender concerns screenshot
                config["what_to_show"][which_data] = str(data)

        # size modified
        elif type(self.sender()) == QtWidgets.QSpinBox:
            size = self.sender().value()
            which_size = str(self.sender().objectName())
            config[which_size] = size

        # what to show modified
        elif type(self.sender()) == QtWidgets.QCheckBox:
            checkbox_name = self.sender().objectName()
            state = self.sender().checkState()
            config["what_to_show"][str(checkbox_name)] = state

        # shortcut to take screenshot modified
        elif type(self.sender()) == CustomShortcutLineEdit:
            line_edit_name = self.sender().objectName()
            human_shortcut = self.sender().keysequence.toString(
                QtGui.QKeySequence.NativeText
            )

            # if shortcut is arrow key or empty, set shortcut as invalid
            if (
                human_shortcut == "Right"
                or human_shortcut == "Left"
                or human_shortcut == "Down"
                or human_shortcut == "Up"
                or human_shortcut == ""
            ):
                self.sender().setText("Invalid shortcut !")
                self.sender().set_italic(True)
                human_shortcut = "Invalid shortcut !"
            else:
                self.sender().set_italic(False)

            config[str(line_edit_name)] = str(human_shortcut)

        write_config(config)

        # notify main window what option has changed
        try:
            self.options_signal.emit(self.sender().objectName())
        except AttributeError:
            pass

    def set_screenshot_path(self):
        """
        Show a pop up window to select the
        directory where to save screenshot
        """

        config = read_config()

        screen_dir_dialbox = QtWidgets.QFileDialog()
        screen_dir_dialbox.setOption(QtWidgets.QFileDialog.ShowDirsOnly)
        screen_dir_dialbox.setFileMode(QtWidgets.QFileDialog.Directory)

        dir_out = screen_dir_dialbox.getExistingDirectory()
        config["dir_out"] = str(dir_out)

        write_config(config)

    def on_close(self):
        """Save config file and close"""

        # config_path = os.getcwd() + "/config.json"
        # with open(config_path, 'w') as f:
        #   json.dump(config, f)

        self.close()


class ExportWindow(QtWidgets.QDialog):

    """
    Class to buid an very simple export windows. Users can
    configure separator, what to export and where
    """

    def __init__(self, parent, *args, **kwargs):
        super(ExportWindow, self).__init__(parent=parent)
        self.setWindowIcon(QtGui.QIcon(str(get_icon_path("main"))))
        self.setWindowTitle("Export options")
        self.setModal(True)

        config = read_config()

        dict_sep = {
            "Comma": ",",
            "Semi-colon": ";",
            "Tabulator": "\t",
            "Space": " ",
        }  # separator available

        list_export_options = ["All", "Transactions", "Summary"]

        file_ico = self.style().standardIcon(QtWidgets.QStyle.SP_DirOpenIcon)

        # load config
        what_to_export = config["what_to_export"]
        separator = config["separator"]
        dir_export = config["dir_export"]

        # init widgets
        layout_export = QtWidgets.QGridLayout()

        combobox_what_to_export = QtWidgets.QComboBox()
        combobox_sep = QtWidgets.QComboBox()

        btn_dir_export = QtWidgets.QPushButton()
        btn_ok = QtWidgets.QPushButton("OK")

        # add separator to comboboxbox
        for count, key in enumerate(dict_sep.keys()):
            data = dict_sep[key]
            combobox_sep.addItem(key, userData=QtCore.QVariant(data))

        # add options for export
        for count, option in enumerate(list_export_options):
            data = option
            combobox_what_to_export.addItem(option, userData=QtCore.QVariant(data))

        btn_dir_export.setIcon(file_ico)
        btn_dir_export.clicked.connect(self.set_export_path)
        btn_ok.clicked.connect(self.on_ok)

        # set previous configuration and connect signals
        index_sep = combobox_sep.findData(separator)
        combobox_sep.setCurrentIndex(index_sep)
        combobox_sep.currentIndexChanged.connect(self.update_options)

        index_what_to_export = combobox_what_to_export.findText(what_to_export)
        combobox_what_to_export.setCurrentIndex(index_what_to_export)
        combobox_what_to_export.currentIndexChanged.connect(self.update_options)

        # set objectNames as same as key they modified in config.json
        combobox_what_to_export.setObjectName("what_to_export")
        combobox_sep.setObjectName("separator")
        btn_dir_export.setObjectName("dir_export")

        # place widgets
        layout_export.addWidget(QtWidgets.QLabel("Select what to export: "), 0, 0)
        layout_export.addWidget(combobox_what_to_export, 0, 1)

        layout_export.addWidget(QtWidgets.QLabel("Select separator: "), 1, 0)
        layout_export.addWidget(combobox_sep, 1, 1)

        layout_export.addWidget(QtWidgets.QLabel("Select folder: "), 2, 0)
        layout_export.addWidget(btn_dir_export, 2, 1)

        layout_export.addWidget(btn_ok, 4, 0, 1, 2)

        self.setLayout(layout_export)

    def update_options(self, *args, **kwargs):
        """Write config file with new options"""

        config = read_config()

        key = str(self.sender().objectName())  # get key to modify

        # separator or what_to_export has changed
        if type(self.sender()) == QtWidgets.QComboBox:
            idx_data = self.sender().currentIndex()
            data = str(self.sender().itemData(idx_data))

        config[key] = data  # FIXME

        write_config(config)  # write config

    def set_export_path(self, *args, **kwargs):
        """
        Show a pop up window to select the
        directory where to save exported data
        """

        config = read_config()

        export_dir_dialbox = QtWidgets.QFileDialog()
        export_dir_dialbox.setOption(QtWidgets.QFileDialog.ShowDirsOnly)
        export_dir_dialbox.setFileMode(QtWidgets.QFileDialog.Directory)

        dir_out = export_dir_dialbox.getExistingDirectory()

        config["dir_export"] = str(dir_out)

        write_config(config)

    def on_ok(self, *args, **kwargs):
        """Close window and export data (see classMainWindow)"""
        self.accept()


class AboutWindow(QtWidgets.QDialog):

    """
    Displays a typical about window
    Easter egg when attempt to close it.
    """

    def __init__(self, parent):
        super(AboutWindow, self).__init__(parent=parent)

        self.setWindowTitle("About Report Tool")
        self.setModal(True)

        self._initial_pos = None

        self.setWindowIcon(QtGui.QIcon(str(get_icon_path("main"))))

        # labels for basics infos
        github_link = "https://github.com/Mulugruntz/Report-Tool"

        label_contact = QtWidgets.QLabel(f"<a href='{github_link}'>{github_link}</a>")
        label_contact.setOpenExternalLinks(True)
        label_contact.setTextInteractionFlags(QtCore.Qt.TextBrowserInteraction)

        # place labels
        layout = QtWidgets.QGridLayout()
        lines = [
            QtWidgets.QLabel(f"<b>Report Tool {__version__}</b>"),
            QtWidgets.QLabel(),
            QtWidgets.QLabel("Developed by Benoit Soudan until 2.2."),
            self._get_label_github(),
            self._get_image_about(),
        ]

        for count, line in enumerate(lines):
            layout.addWidget(line, count, 0)

        layout.addWidget(
            self._get_close_button(),
            layout.rowCount(),
            0,
            alignment=QtCore.Qt.AlignCenter,
        )

        self.setLayout(layout)
        self._initial_pos = self.pos()

    @staticmethod
    def _get_label_github() -> QtWidgets.QLabel:
        github_link = "https://github.com/Mulugruntz/Report-Tool"

        label = QtWidgets.QLabel(f"<a href='{github_link}'>{github_link}</a>")
        label.setOpenExternalLinks(True)
        label.setTextInteractionFlags(QtCore.Qt.TextBrowserInteraction)

        return label

    @staticmethod
    def _get_image_about() -> QtWidgets.QLabel:
        label = QtWidgets.QLabel()
        label.setPixmap(QtGui.QPixmap(str(get_icon_path("georges"))))
        label.setAlignment(QtCore.Qt.AlignCenter)

        return label

    def _get_close_button(self) -> QtWidgets.QPushButton:
        button = QtWidgets.QPushButton("Close")
        button.setMaximumWidth(200)
        button.clicked.connect(self.close)

        return button

    def _get_initial_pos(self):
        """Getter method for initial position"""

        return self._initial_pos

    def _set_initial_pos(self, initial_pos):
        """
        Setter method for initial position

        :param initial_pos: QtCore.Qpoint, initial pos of window
        """

        self._initial_pos = initial_pos


class FilterWindow(QtWidgets.QDialog):

    """
    Class to buid an filter window. This allow to
    selected which market users want to analyze
    """

    filter_signal = QtCore.pyqtSignal(object)  # signal send when filter changes

    def __init__(self, parent):
        super(FilterWindow, self).__init__(parent=parent)

        self.setWindowIcon(QtGui.QIcon(str(get_icon_path("main"))))
        self.setWindowTitle("Filter")
        self.setModal(True)

    def build_window(self, result_dict, previous_filter):
        """
        :param result_dict: OrderedDIct() with trades
        :param previous filter: list of previoulsy selected markets
        """

        config = read_config()
        self.unchanged_dict = result_dict

        # init grid layout and widgets
        layout_main = QtWidgets.QGridLayout()
        layout_filter = QtWidgets.QGridLayout()
        widget_filter = QtWidgets.QGroupBox("Select markets")
        scroll_area = QtWidgets.QScrollArea()

        LABEL_ALL = QtWidgets.QLabel("All markets")

        self.checkbox_all = QtWidgets.QCheckBox()
        self.btn_close = QtWidgets.QPushButton("OK")

        if config["all"] == 2:  # means no filter set
            self.checkbox_all.setCheckState(2)  # TODO: check
        else:
            self.checkbox_all.setCheckState(0)

        # confidure widgets and place them
        self.btn_close.clicked.connect(self.on_close)
        self.checkbox_all.stateChanged.connect(self.selection_changed)

        layout_filter.addWidget(QtWidgets.QLabel("All markets"), 0, 0)
        layout_filter.addWidget(self.checkbox_all, 0, 1, 1, 1, QtCore.Qt.AlignRight)

        # build a list with only trades
        trade_list = [
            result_dict[trade]
            for trade in list(result_dict.keys())
            if result_dict[trade]["type"] == "ORDRE"
            or result_dict[trade]["type"] == "DEAL"
        ]

        # build a list with all market names
        market_list = [trade["market_name"] for trade in trade_list]

        if market_list == []:
            LABEL_ALL.setText("No markets found")
            self.checkbox_all.setEnabled(False)
        else:
            LABEL_ALL.setText("All markets")
            self.checkbox_all.setEnabled(True)

        # init a dict to hold checkbox and associated market name
        self.dict_filter_checkbox = {}

        for count, market_name in enumerate(market_list):
            ascci_name = market_name.encode(
                "ascii", "ignore"
            )  # TODO: check encode/decode still needed?
            label_market = QtWidgets.QLabel(market_name)

            if ascci_name not in self.dict_filter_checkbox:
                # creates a checkbox and complete dict
                market_checkbox = QtWidgets.QCheckBox()
                self.dict_filter_checkbox[ascci_name] = market_checkbox

                # configure checkbox
                if config["all"] == 2:  # no filter set
                    market_checkbox.setCheckState(2)
                    market_checkbox.setEnabled(False)

                # market was previoulsy checked
                elif market_name in previous_filter:
                    market_checkbox.setCheckState(2)
                    market_checkbox.setEnabled(True)

                # market was previoulsy unchecked
                else:
                    market_checkbox.setCheckState(0)  # TODO: check all .setCheckState()
                    market_checkbox.setEnabled(True)

                market_checkbox.stateChanged.connect(self.selection_changed)
                layout_filter.addWidget(label_market, count + 1, 0)
                layout_filter.addWidget(
                    market_checkbox, count + 1, 1, 1, 1, QtCore.Qt.AlignRight
                )

            else:
                continue

        # add ok buttons at the end of layout
        nb_row = layout_filter.rowCount()
        layout_filter.addWidget(self.btn_close, nb_row + 1, 0, 1, 2)
        widget_filter.setLayout(layout_filter)

        # configure main layout and widgets
        scroll_area.setWidgetResizable(True)
        scroll_area.setWidget(widget_filter)

        layout_main.addWidget(scroll_area, 0, 0)

        self.setLayout(layout_main)
        self.exec_()

    def selection_changed(self):
        """
        Called when a checkbox is checked/unckecked It created a
        result_dict called filtered_dict without the selected markets
        """

        config = read_config()

        filtered_dict = deepcopy(self.unchanged_dict)  # deepcopy of unchanged_dict
        checkbox_all_state = self.checkbox_all.checkState()
        config["all"] = checkbox_all_state

        write_config(config)

        for key in self.dict_filter_checkbox.keys():  # loop over checkbox
            checkbox = self.dict_filter_checkbox[key]
            checkbox_state = checkbox.checkState()

            if checkbox_all_state == 2:  # means no filter can be set
                checkbox.setEnabled(False)
                checkbox.setCheckState(2)
                continue

            else:
                checkbox.setEnabled(True)

                for deal_id in self.unchanged_dict.keys():
                    # get market_name for each trade
                    market_name = self.unchanged_dict[deal_id]["market_name"].encode(
                        "ascii", "ignore"
                    )

                    # delete deal_id in filtered dict
                    if checkbox_state != 2 and market_name == key:
                        filtered_dict.pop(deal_id, None)
                    else:
                        continue

        self.filter_signal.emit(filtered_dict)  # send dict to main window

    def on_close(self):
        """Close function"""

        config = read_config()
        checkbox_all_state = self.checkbox_all.checkState()
        config["all"] = checkbox_all_state

        write_config(config)

        if checkbox_all_state == 2:  # if no filter set, send unchanged_dict
            self.filter_signal.emit(self.unchanged_dict)

        self.close()


# if __name__ == "__main__":
#     import sys
#     app = QtWidgets.QApplication(sys.argv)
#     app.setApplicationName('WuTrading')

#     a=OptionsWindow(parent=None)
# #   # a.build_window(dummy_result_dict, [])
#     a.show()
#     sys.exit(app.exec_())
