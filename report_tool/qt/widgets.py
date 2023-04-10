""" This module holds classes to custom base QtWidgets"""
import datetime
import re
import warnings
from decimal import Decimal

from PyQt5 import QtCore, QtGui, QtWidgets

from report_tool.utils.settings import read_config

RE_LABEL = re.compile(r"(.*?[A-z]): ")
RE_TAG = re.compile(r"<(.*?)>")


class CustomPushButton(QtWidgets.QPushButton):

    """
    Class to create a custom pushbutton.
    Used for plot color in OptionsWindows
    """

    def __init__(self, object_name):
        """
        :param object_name: string
        """

        QtWidgets.QPushButton.__init__(self)
        self.setObjectName(object_name)

    def set_default_style(self, color):
        """
        Set color according to user choice's

        :param color: string, describing color to set
        """

        self.setFixedWidth(80)
        self.setStyleSheet(
            "QPushButton#" + self.objectName() + "{background-color :" + color + ";\n"
            "border-radius : 4px;\n"
            "font : 12px;\n"
            "color : white;\n"
            "padding : 6px;}\n"
        )


class CustomLineEdit(QtWidgets.QLineEdit):

    """
    Class to reimplement focusOutEvent and keyPressEvent
    to send string describing object when editingFinished
    as the default event send nothing. See mainwindow class
    """

    finish_signal = QtCore.pyqtSignal(object)  # signal emited when edition is finished

    def __init__(self, *args, **kwargs):
        super(CustomLineEdit, self).__init__(*args, **kwargs)

    def focusOutEvent(self, event):
        """
        Emit a string clearly identifying widget that
        has called update_options in main window
        """

        self.finish_signal.emit("start_capital")

    def keyPressEvent(self, event):
        """
        Emit a string clearly identifying widget that has called
        update_options in main window. Send when user presses ENTER
        """

        if event.key() == QtCore.Qt.Key_Return:
            self.finish_signal.emit("start_capital")
        else:
            QtWidgets.QLineEdit.keyPressEvent(self, event)


class CustomLabel(QtWidgets.QLabel):

    """
    Class to create a custom QLabel. It's done to manage style
    when user click or hover buttons and to create a click event
    """

    clicked_signal = QtCore.pyqtSignal()  # emit when user clicks on widget

    def __init__(self, object_name):
        """
        :param object_name: string
        """

        super(CustomLabel, self).__init__()
        self.setObjectName(object_name)

    def set_default_style(self, background_color, hover_color, border_color):
        """
        Set different color for events

        :param background_color: string, describing color for background
        :param hover_color: string, describing color for hover
        :param border_color: string, describing color for border
        """

        self.setStyleSheet(
            "QLabel#"
            + self.objectName()
            + "{background-color :"
            + background_color
            + ";\n"
            "border-radius : 1px;\n"
            "padding : 1px;}\n"
            "QLabel#"
            + self.objectName()
            + ":hover\
                           {background-color:"
            + hover_color
            + ";\n"
            "border-color :" + border_color + ";\n"
            "border-style : solid ;\n"
            "border-width : 1px;}"
        )

    def mousePressEvent(self, event):
        """Override mussePressEvent to emit a click signal"""

        self.clicked_signal.emit()
        event.accept()


class CustomComboBox(QtWidgets.QComboBox):

    """
    Class to reimplement focusOutEvent and send appropriate signal.
    I couldn't find a better way to catch this event
    """

    focus_out_signal = QtCore.pyqtSignal()  # emit when focus out

    def __init__(self, object_name):
        """
        :param object_name: string
        """

        super(CustomComboBox, self).__init__()
        self.setObjectName(object_name)
        self.setFocusPolicy(QtCore.Qt.StrongFocus)

    def focusOutEvent(self, event):
        """Reimplement focus out event to emit a signal"""

        self.focus_out_signal.emit()
        event.accept()


class CustomDockWidget(QtWidgets.QDockWidget):

    """
    Class to create a floating dock used
    to show a trade details when the user click
    on graph. keyPressEvent is reimplemented
    """

    def __init__(self, parent, pos_details_headers):
        """
        :param pos_details_headers: OrderedDict with same keys of result_dict
                                    as dict and a clearer description of these
                                    keys as values

        :param parent: objet parent of dock, MainWindow
        """

        self._dict_details_labels = {}  # dict label for qlabels

        self.dock_parent = parent
        super(CustomDockWidget, self).__init__(parent=parent)
        self.setObjectName("dock_details")
        self.init_dock(pos_details_headers)

        self.lot_size = "Size: "
        self.pnl_str = "Profit: "

    def init_dock(self, pos_details_headers):
        """
        Create a non-closable QDockWidget. Contains labels with
        infos about a clicked trade and a QPlainText to comments the
        clicked trade All widget are set in a QScrollArea.

        :param pos_details_headers: OrderedDict with same keys of result_dict
                                    as keys and a clearer description of these
                                    keys as values
        """

        config = read_config()

        # init widgets and layout
        splitter = QtWidgets.QSplitter()

        widget_pos = QtWidgets.QWidget()
        layout_pos = QtWidgets.QGridLayout()
        scroll_pos_infos = QtWidgets.QScrollArea()

        # widgets for checkbox and one label
        widget_comment = QtWidgets.QWidget()
        layout_comment = QtWidgets.QGridLayout()

        # widgets for text edit and one label
        widget_chkbox_graph = QtWidgets.QWidget()
        layout_chkbox_graph = QtWidgets.QHBoxLayout()

        k = 0
        dict_details_labels = {}

        # created and place labels
        for count, header in enumerate(pos_details_headers.keys()):
            if header == "h_line" or header == "h_line_2":  # add horizontal line
                h_line = QtWidgets.QFrame()
                h_line.setFrameShape(QtWidgets.QFrame.HLine)
                h_line.setStyleSheet("color:rgb(173,173,173);")
                layout_pos.addWidget(h_line, int(count), 0, 1, 2)

            elif header == " ":  # label for market name
                label = QtWidgets.QLabel(header + ": ")
                layout_pos.addWidget(label, int(count), 0, 1, 2, QtCore.Qt.AlignCenter)
                dict_details_labels[header] = label

            else:
                label = QtWidgets.QLabel(header + ": ")
                layout_pos.addWidget(label, int(count), 0, 1, 2, QtCore.Qt.AlignLeft)
                dict_details_labels[header] = label
                k += 1

        self.setFeatures(
            QtWidgets.QDockWidget.DockWidgetFloatable
            | QtWidgets.QDockWidget.DockWidgetMovable
        )

        last_row = len(pos_details_headers)

        # create one checkbox to show or not comment on graph
        self.checkbox_showongraph = CustomCheckBox(self)

        # create a QPlainTextEdit to comment pos
        self.text_edit_comment = CustomPlainTextEdit(self)

        self.checkbox_showongraph.setCheckState(0)
        layout_chkbox_graph.addWidget(self.checkbox_showongraph, 0, QtCore.Qt.AlignLeft)
        layout_chkbox_graph.addWidget(
            QtWidgets.QLabel("Show comments on graph"), 1, QtCore.Qt.AlignLeft
        )

        widget_chkbox_graph.setLayout(layout_chkbox_graph)
        widget_chkbox_graph.setFixedHeight(50)

        layout_comment.addWidget(widget_chkbox_graph, 0, 0, 1, 2)

        layout_comment.addWidget(
            QtWidgets.QLabel("Comment:"), 1, 0, QtCore.Qt.AlignTop | QtCore.Qt.AlignLeft
        )

        layout_comment.addWidget(
            self.text_edit_comment,
            1,
            1,
        )
        widget_comment.setLayout(layout_comment)

        # configure main widgets
        layout_pos.addWidget(widget_comment, last_row + 1, 0, 1, 2)
        widget_pos.setLayout(layout_pos)

        scroll_pos_infos.setWidget(widget_pos)
        scroll_pos_infos.setWidgetResizable(True)

        self.setWidget(scroll_pos_infos)
        self.topLevelChanged.connect(self.change_title)
        self.setFloating(True)
        # self.resize(310,350) unix size
        self.resize(280, 300)  # windows size

        self._set_labels(dict_details_labels)

    def change_title(self):
        """Function to manage dock title when it is floatain or not"""

        if self.isFloating() == True:
            self.setWindowTitle("")  # if dock is floating set not title
        else:
            self.setWindowTitle("Trade details")

    def empty_labels(self, pos_details_headers):
        """
        Called when no trades received. Set empty string for each labels

        :param pos_details_headers: OrderedDict with same keys of result_dict
                                    as keys and a clearer description of these
                                    keys as values.
                                    See classMainWindow.create_dock_details
        """

        dict_details_labels = self._dict_details_labels

        # del key corresponding to h_line
        pos_details_headers.pop("h_line", None)
        pos_details_headers.pop("h_line_2", None)

        for key in pos_details_headers.keys():
            label_text = dict_details_labels[key].text()  # get label text

            try:  # get label title
                static_text = RE_LABEL.search(label_text).group()
            except AttributeError as e:  # temp
                static_text = ""

            text_to_set = static_text + ""  # fill labels with empty strings
            dict_details_labels[key].setText(text_to_set)

        self.text_edit_comment.setPlainText("")

    def change_content(self, *args, **kwargs):
        """
        Set label text with info about the clicked trade

        :kw param pos_details_headers: OrderedDict with same keys of result_dict
                        as keys and a clearer description of these
                        keys as values

        :kw param dict_to_search: OrderedDict() with trqdes plotted
        :kw param deal_id_clicked: string, deal_id under mouse
        :kw param index clicked: int, index of trade under mouse
        :kw param screenchot: boolean, indicates if a screenshot is being taken
        """

        pos_details_headers = kwargs["pos_details_headers"]
        dict_to_search = kwargs["dict_to_search"]
        deal_id_clicked = kwargs["deal_id_clicked"]
        index_clicked = kwargs["index_clicked"]
        screenshot = kwargs["screenshot"]

        # get configuration
        config = read_config()
        profit_color = config["profit_color"]
        flat_color = config["flat_color"]
        loss_color = config["loss_color"]
        result_in = config["result_in"]

        currency_symbol = config["currency_symbol"]
        state_infos = config["what_to_show"]["state_infos"]
        state_size = config["what_to_show"]["state_size"]

        dict_details_labels = self._dict_details_labels

        # del key corresponding to h_line
        pos_details_headers.pop("h_line", None)
        pos_details_headers.pop("h_line_2", None)

        for key in pos_details_headers.keys():
            label_text = dict_details_labels[key].text()  # get label text

            try:  # get label title
                static_text = RE_LABEL.search(label_text).group()
            except AttributeError:  # temp function
                static_text = ""

            try:
                if key == "Date":
                    date_key = pos_details_headers[key]
                    date_str = dict_to_search[deal_id_clicked][date_key]
                    date_obj = datetime.datetime.strptime(date_str, "%d/%m/%y")

                    # set a str date with day of week
                    data = date_obj.strftime("%A %d/%m/%y")

                elif key == "Trade":
                    data = "# " + str(index_clicked)  # set number of clicked trade

                elif key == "Size":
                    size_key = pos_details_headers[key]
                    self.lot_size = dict_to_search[deal_id_clicked][
                        size_key
                    ]  # save size

                    # hide or not lot size
                    if (
                        state_size == "Always"
                        or state_size == "Only for screenshot"
                        and screenshot == True
                    ):
                        data = "--"

                    else:
                        data = str(self.lot_size)

                elif key == "Profit":
                    # create a list from string in pos_details_headers dict
                    pnl_info = pos_details_headers[key].split(",")

                    # create a list with suffix for each pnl infos
                    pnl_in = ["pts | ", "pts/lot | ", currency_symbol]
                    pnl_list = []

                    for idx, info in enumerate(pnl_info):
                        pnl = Decimal(dict_to_search[deal_id_clicked][info])

                        try:
                            pnl_color = (
                                profit_color
                                if pnl > 0
                                else flat_color
                                if pnl == 0
                                else loss_color
                            )

                            # hide or not capital little bit hardcoded
                            if (
                                state_infos == "Always"
                                and result_in != currency_symbol
                                and idx == 2
                                or state_infos == "Only for screenshot"
                                and screenshot == True
                                and idx == 2
                            ):
                                pnl = "--"

                            else:
                                pnl = str(pnl)

                            pnl_text = f"""<span style="color: {pnl_color}">{pnl}{pnl_in[idx]}</span>"""

                            pnl_list.append(pnl_text)  # construct a pnl string

                        except ValueError:  # not a float
                            continue

                    data = "".join(pnl_list)
                    self.pnl_str = data

                else:
                    key_dict_to_search = pos_details_headers[key]

                    # get data we want to show
                    data = dict_to_search[deal_id_clicked][key_dict_to_search]

            except KeyError:  # no data
                data = "N/A"

            text_to_set = static_text + data
            dict_details_labels[key].setText(text_to_set)

        self._set_labels(dict_details_labels)

    def hide_profit_loss(self, currency_symbol):
        """
        Hide profit in currency in profit string. Called when a
        screenshot is taken or if the user wants to always hide
        currency information. It's kind of dirty code but it works :-)

        :param currency_symbol: string, describing currency
        """

        dict_details_labels = self._dict_details_labels  # get labels dict

        pnl_label = dict_details_labels["Profit"]  # get label concerned

        """
        As i don't want to spend time on understanding regex, it uses a trick:
        reverse pnl string, find and replace the first text between
        html tags as the first occurrence is the one needed to be hidden
        """

        pnl_str = self.pnl_str[::-1]  # reversed string
        pnl_hidden = RE_TAG.sub(f"<{currency_symbol}-->", pnl_str, 1)[
            ::-1
        ]  # find and replace first occurence
        pnl_label.setText(pnl_hidden)  # set text

    def show_profit_loss(self):
        """
        Show profit in currency. Celled after
        screenshot or if user changes options
        """

        dict_details_labels = self._dict_details_labels  # get labels dict
        pnl_label = dict_details_labels["Profit"]  # get label concerned
        pnl_label.setText(self.pnl_str)  # set old string

    def hide_lot_size(self):
        """
        Hide lot size if user takes a screenshot or when
        "Hide lot size" is set to "Always".
        """

        dict_details_labels = self._dict_details_labels  # get labels dict
        size_label = dict_details_labels["Size"]  # get label concerned
        size_label.setText("Size: --")  # set text

    def show_lot_size(self):
        """
        Show lot size after a screenshot has been taken or
        when "Hide lot size" is changed from "Always" to
        "Never" or "Only for screenshot"
        """

        dict_details_labels = self._dict_details_labels  # get labels dict
        size_label = dict_details_labels["Size"]  # get label concerned
        size_label.setText("Size: " + str(self.lot_size))  # set old string

    def keyPressEvent(self, event):
        """
        Custom keyPressEvent. The event is passed to the main
        window so the user can keep navigate throught the trades
        without loosing focus on the dock
        """

        if (
            event.key() == QtCore.Qt.Key_Right or event.key() == QtCore.Qt.Key_Left
        ):  # right or left arrow pressed
            self.dock_parent.keyPressEvent(event)  # MainWindow keyPressEvent

        else:
            super(CustomDockWidget, self).keyPressEvent(event)  # normal behavior

    def _dict_details_labels(self):
        """Getter method maybe useless"""

        return self._dict_details_labels

    def _set_labels(self, new_dict_labels):
        """
        Setter methods maybe useless

        :param new_dict_labels: dict with labels to show
        """

        self._dict_details_labels = new_dict_labels


class CustomPlainTextEdit(QtWidgets.QPlainTextEdit):

    """
    Custom QPlainTextEdit to reimplement KeysPressEvent. If
    left/right arrow are pressed, pass event to the dock, so the
    user can navigate using arrows keys without loosing the focus on widget
    """

    def __init__(self, parent):
        """
        :param parent: obj, parent of widget, CustomDockWidget
        """

        super(CustomPlainTextEdit, self).__init__(parent=parent)
        self.plain_text_edit_parent = parent

    def keyPressEvent(self, event):
        """Custom keyPressEvent function"""

        if (
            event.key() == QtCore.Qt.Key_Right or event.key() == QtCore.Qt.Key_Left
        ):  # right or left arrow pressed
            self.plain_text_edit_parent.keyPressEvent(event)  # dock keyPressEvent
        else:
            QtWidgets.QPlainTextEdit.keyPressEvent(self, event)  # normal behavior


class CustomCheckBox(QtWidgets.QCheckBox):

    """
    Custom  Checkbox to reimplement keyPressEvent. If left/right
    arrow are pressed, pass event to the dock, so the user can
    navigate using arrows keys without loosing the focus on widget
    """

    def __init__(self, parent):
        """
        :param parent: obj, parent of widget, CustomDockWidget
        """

        super(CustomCheckBox, self).__init__(parent=parent)
        self.checkbox_parent = parent

    def keyPressEvent(self, event):
        """Custom keyPressEvent function"""

        if (
            event.key() == QtCore.Qt.Key_Right or event.key() == QtCore.Qt.Key_Left
        ):  # right or left arrow pressed
            self.checkbox_parent.keyPressEvent(event)  # dock keyPressEvent
        else:
            QtWidgets.QCheckBox.keyPressEvent(self, event)  # normal behavior


class CustomShortcutLineEdit(QtWidgets.QLineEdit):

    """
    Same as CustomLineEdit excepts that keyPressEvent is also
    reimplemented to capture Qt KeySequence and creates key shortcuts
    """

    text_changed = QtCore.pyqtSignal(object, object)

    def __init__(self, object_name, *args, **kwargs):
        super(CustomShortcutLineEdit, self).__init__()
        self.setObjectName(object_name)
        self.setAlignment(QtCore.Qt.AlignCenter)

        # connect base signal to custom function
        self.textChanged.connect(self.on_text_changed)

    def set_italic(self, is_italic, *args, **kwargs):
        """
        Set or not an italic font

        :param is_italic: boolean
        """

        font = QtGui.QFont()
        font.setFamily(font.defaultFamily())
        font.setItalic(is_italic)
        self.setFont(font)

    def focusInEvent(self, event):
        """Select all text when widget get focus"""

        self.selectAll()

    def mousePressEvent(self, event):
        """Select all text when widget get click event"""

        self.selectAll()

    def on_text_changed(self, event):
        """Emit object name and text set"""

        self.text_changed.emit(self.objectName(), self.text())

    def set_keysequence(self, keysequence):
        """Set text of key sequence entered"""

        self.keysequence = keysequence
        human_keysequence = self.keysequence.toString(QtGui.QKeySequence.NativeText)
        self.setText(human_keysequence)

    def keyPressEvent(self, event):
        """Reimplement base method to capture key sequence"""

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

            self.set_keysequence(QtGui.QKeySequence(key))


# if __name__ == '__main__':
#     import sys
#     from collections import OrderedDict
#     app = QtGui.QApplication(sys.argv)
#     app.setApplicationName('WuTrading')
#     pos_details_headers = OrderedDict([(" ", "market_name"),
#                                        ("h_line", ""),
#                                        ("Date", "date"),
#                                        ("Trade", 1),
#                                        ("Direction", "direction"),
#                                        ("Size", "open_size"),
#                                        ("Open", "open_level"),
#                                        ("Close", "final_level"),
#                                        ("Profit", "points,points_lot,pnl"),
#                                        ("h_line_2", "")])
#     a=CustomDockWidget(None, pos_details_headers)
# #     # a.build_window(dummy_result_dict, [])
#     a.show()
#     sys.exit(app.exec_())
