import weakref

import numpy as np
import pyqtgraph as pg
from PyQt5 import QtCore, QtGui

from report_tool.qt.graphics_items import CustomLinearRegion, DateAxis


class EquityChart(pg.PlotWidget):

    """
    Class for displaying equity curves.
    Inherits from pyqtgraph plotWidget.
    """

    def __init__(self, *args, **kwargs):
        """
        Init function. Inherits from pg.PlotWidget.
        Set a title and axes label, using HTML formatting
        """

        date_axis = DateAxis({}, orientation="bottom")

        pg.PlotWidget.__init__(self, axisItems={"bottom": date_axis}, *args, **kwargs)

        self.setStyleSheet("border: 1px solid gray")
        self.plotItem.vb.sigRangeChangedManually.connect(self.update_text_item)

        # create a vertical line
        vline_pen = pg.mkPen(255, 92, 111)
        self.vline = pg.InfiniteLine(angle=90, pen=vline_pen)

        # create a linear region item
        lr_pen = pg.mkPen(95, 95, 95, width=1)
        lr_brush = pg.mkBrush(200, 200, 200, 75)
        self.linear_region = CustomLinearRegion()

        self.linear_region.setBrush(lr_brush)
        self.linear_region.set_pen(lr_pen)

        """
        create a dict with all coments items
        and a list with all deal id plotted
        """

        self._dict_comments_items = {}
        self._deal_id_plotted = []

        # self.getAxis("bottom").setLabel(text=kwargs["x_label"])
        # self.getAxis("left").setLabel(text=kwargs["y_label"])

        self.setMouseTracking(True)

    def plot_curve(self, ec_color, ec_size, ec_style, *args, **kwargs):
        """
        creates the curve

        :param ec_color: string color of plot
        :param ec_size: int the size of curve
        :param ec_style: string to select the curve style
        """

        style_dict = {
            "Solid": 1,
            "Dash": 2,
            "Dot": 3,
            "Dash Dot": 4,
            "Dash Dot Dot": 5,
        }  # dict with avalaible QtStyle

        qt_ec_style = QtCore.Qt.PenStyle(style_dict[ec_style])

        equity_pen = pg.mkPen(
            color=QtGui.QColor(ec_color),
            width=ec_size,
            style=qt_ec_style,
        )

        """
        If you set y data, don't forget to update
        it when call setData() !!! else getData()
        return None, costed me 2 days of debug !!!
        """

        curve = self.plot(x=np.array([]), y=np.array([]), pen=equity_pen)

        return curve

    def update_curve(self, curve, values, dates, *args, **kwargs):
        """
        Called when the main loops receives an activity
        update or when the user changes curve apperance

        :param curve: pg.PlotItem
        :param values: list of y values to plot
        :param dates: list with index of trades

        :kw param ec_color: string color of plot
        :kw param ec_size: int the size of curve
        :kw param ec_style: string to select the curve style
        :kw param graph: string, name of the graph, for debug
        """

        # get color, style and size
        ec_color = kwargs["ec_color"]
        ec_style = kwargs["ec_style"]
        ec_size = kwargs["ec_size"]
        graph = kwargs["graph"]  # debug purpose

        style_dict = {
            "Solid": 1,
            "Dash": 2,
            "Dot": 3,
            "Dash Dot": 4,
            "Dash Dot Dot": 5,
        }  # dict with avalaible QtStyle

        qt_ec_style = QtCore.Qt.PenStyle(style_dict[ec_style])

        equity_pen = pg.mkPen(
            color=QtGui.QColor(ec_color), width=ec_size, style=qt_ec_style
        )

        curve.clear()
        curve.setPen(equity_pen)  # update pen
        curve.setData(x=dates, y=values)

    def update_curve_style(self, curve, *args, **kwargs):
        """
        Update only style of equity curve
        Called hen user changes options

        :param curve: pg.PlotItem

        :kw param ec_color: string color of plot
        :kw param ec_size: int the size of curve
        :kw param ec_style: string to select the curve style
        :kw param graph: string, name of the graph, for debug
        """

        # get color, style and size
        ec_color = kwargs["ec_color"]
        ec_style = kwargs["ec_style"]
        ec_size = kwargs["ec_size"]
        graph = kwargs["graph"]  # debug purpose

        style_dict = {
            "Solid": 1,
            "Dash": 2,
            "Dot": 3,
            "Dash Dot": 4,
            "Dash Dot Dot": 5,
        }  # dict with avalaible QtStyle

        qt_ec_style = QtCore.Qt.PenStyle(style_dict[ec_style])

        equity_pen = pg.mkPen(
            color=QtGui.QColor(ec_color), width=ec_size, style=qt_ec_style
        )

        curve.setPen(equity_pen)  # update pen

    def plot_scatter(self, color, symbol, size, *args, **kwargs):
        """
        Creates a scatter plot item

        :param color: string color of plot
        :param symbol: string the symbol to use
        :param size: int size of the symbol
        """

        scatter_brush = pg.mkBrush(color)

        scatter_plot = pg.ScatterPlotItem(
            symbol=symbol, size=size, pen=pg.mkPen(None), brush=scatter_brush
        )  # init plot

        scatter_plot.addPoints(x=np.array([]), y=np.array([]))

        return scatter_plot

    def update_scatter(self, scatter, x_data, y_data, *args, **kwargs):
        """
        Update scatter plot

        :param scatter: pg.ScatterPlotItem
        :param x_data: list with x values to plot
        :param y_data: list with y values to plot

        :kw param color: string color of plot
        :kw param symbol: string the symbol to use
        :kw param size: int size of the symbol
        """

        try:
            kwargs["clear"]  # means user don"t want to show dd
            scatter.clear()
            return

        except KeyError:
            for arg in kwargs.keys():
                if "style" in arg:
                    dd_symbol = kwargs[arg]

                elif "color" in arg:
                    dd_color = QtGui.QColor(kwargs[arg])

                elif "size" in arg:
                    dd_size = kwargs[arg]

            dd_brush = pg.mkBrush(dd_color)  # FIXME
            scatter.setData(
                x=x_data, y=y_data, symbol=dd_symbol, size=dd_size, brush=dd_brush
            )  # update scatter
            self.autoRange()

    def update_scatter_style(self, scatter, *args, **kwargs):
        """
        Update only style of scatter plot.Called hen user changes options

        :param scatter: pg.ScatterPlotItem

        :kw param color: string color of plot
        :kw param symbol: string the symbol to use
        :kw param size: int size of the symbol
        :kw prama state: int show or not symbol
        """

        for arg in kwargs.keys():
            if "style" in arg:
                dd_symbol = kwargs[arg]

            elif "color" in arg:
                state = kwargs["state"]

                if state == 0:  # don"t show scatter
                    # set a transparant color rather than empty array
                    dd_color = QtGui.QColor(255, 255, 255, 0)

                else:
                    dd_color = QtGui.QColor(kwargs[arg])

            elif "size" in arg:
                dd_size = kwargs[arg]

        dd_brush = pg.mkBrush(dd_color)

        # update style
        scatter.setSymbol(dd_symbol)
        scatter.setSize(dd_size)
        scatter.setBrush(dd_brush)

    def show_vline(self):
        """Show vertical line"""

        items_on_graph = self.plotItem.items  # not the cleanest to get vline

        if self.vline not in items_on_graph:
            self.addItem(self.vline)  # add line if not done yet
        else:
            return

    def hide_vline(self):
        """Hide vertical line"""

        items_on_graph = self.plotItem.items  # not the cleanest to get vline

        if self.vline not in items_on_graph:
            return
        else:
            self.removeItem(self.vline)  # remove line if not done yet

    def update_vline(self, x_pos, curve):
        """
        Update vertical line position. If new position is outside
        the view, update Xrange to be sure that line will be always
        visible. Update Yrange to see all the data in the Xrange

        :param x_pos: float new pos to set
        """

        items_on_graph = self.plotItem.items  # not the cleanest to get vline

        if self.vline not in items_on_graph:
            return

        else:
            self.vline.setPos(x_pos)  # update vertical line if it is visible
            x_range = self.viewRange()[0]  # get the actual view x range
            data_plotted = curve.getData()  # get data plotted

            if data_plotted[0] is None:  # no data plotted
                return

            else:
                if x_pos <= x_range[0]:  # line pos is smaller than x min
                    x_min = x_pos - 1  # decrease x min
                    x_max = x_pos + 30  # set an arbitrary x max

                    if x_max > x_range[1]:
                        x_max = x_range[1] + 0.5

                    if x_min < 1:  # no useful values if x min < 1
                        # get y values from 1 to x_max
                        data_in_range = data_plotted[1][0 : x_max + 1]

                    else:
                        # get y values from x min to x max
                        data_in_range = data_plotted[1][x_min : x_max + 1]

                    try:
                        self.setXRange(x_min, x_max)
                        self.setYRange(min(data_in_range), max(data_in_range))

                    except ValueError:  # no data don't need to change range
                        return

                elif x_pos >= x_range[1]:  # line pos is greater than x max
                    x_min = x_pos - 30  # set an arbitrary x min
                    x_max = x_pos + 1

                    if x_min < 0:
                        x_min = -0.5

                    try:
                        # line pos is greater than the last x plotted
                        if x_max >= max(data_plotted[0]):
                            # get y values from x min to last x plotted
                            data_in_range = data_plotted[1][
                                x_min : max(data_plotted[0]) + 1
                            ]

                        else:
                            # get y values from x min to x max
                            data_in_range = data_plotted[1][x_min : x_max + 1]

                        self.setXRange(x_min, x_max)
                        self.setYRange(min(data_in_range), max(data_in_range))

                    except ValueError:  # no data don't need to change range
                        return

                else:
                    return

    def get_vline_pos(self):
        """Get the actual vline position"""

        items_on_graph = self.plotItem.items

        if self.vline not in items_on_graph:
            return
        else:
            vline_pos = self.vline.value()  # get vertical line pos if it is visible
            return vline_pos

    def update_range(self, equity_curve, range_to_set, *args, **kwargs):
        """
        Update range on equity_plot (graph on top) x_min and x_max
        are set according to the region bounds. y_min and y_max
        are set with min and max of data inside this region

        :param equity_curve: pg.PlotItem
        :param range_to_set: list of lists, range XY of plot
        """

        data_plotted = equity_curve.getData()  # get data plotted
        x_min = range_to_set[0]
        x_max = range_to_set[1]

        comments_items = self._get_comments_items()
        deal_id_plotted = self._get_deal_id_plotted()

        if data_plotted[0] is None:  # no data plotted
            return
        else:
            # means user has selected all trades
            if x_min == 0 and x_max >= len(data_plotted[0]):
                self.autoRange()
                return
            else:
                self.setXRange(x_min, x_max, padding=0)  # set x range

            """
            I'd like to update textItems here, so when the user moves the
            region (so the range), the text and the associated arrow is updated.
            I don't do it because it triggers events that i can't/don't know
            how to handle and errors. see classCustomGraphicsItems
            """

            # self.update_text_item(equity_curve, **kwargs)    #update item on graph

            """
            Following code is for set y range according tox range. not
            implemented becauce it disables thepossiblity to manually change
            y range.Moreover when there are comments they might not be visible.
            It's simpler to let the user do what he wants, than calculate
            coordinates of items in range or to implement something like ProRealTime.
            """

            ################################################################
            #   """Not fully satisfied of the following code"""
            #   data_in_range = data_plotted[1][x_min:x_max]    #get date in range
            #   while len(data_in_range) <= 3:   #ensure that the number of trade in the region will be > 3
            #       x_min -= 1    #decrease x_min
            #       x_max += 1    #increase x_max
            #       if x_min <= 0:    #if x_in <= 0 stop decreasing
            #           x_min = 0
            #       if x_max >= len(data_plotted[0]):    #if x_max >= nb of trades stop increasing
            #           x_max = len(data_plotted[0])
            #       try:
            #           data_in_range = data_plotted[1][x_min:x_max]
            #       except IndexError:
            #           break
            #           return
            #   y_min = min(data_plotted[1][x_min:x_max])    #get min value in the selected region
            #   y_max = max(data_plotted[1][x_min:x_max])    #get max value in the selected region

            # except ValueError:    #when lines are too close or problem while slicing
            #   self.autoRange()

            # ####add an offset to values for cleaner graph####
            # if y_min < 0:
            #   y_min = y_min*1.1
            # if y_min > 0:
            #   y_min = y_min*0.9
            # if y_max > 0:
            #   y_max = y_max*1.1
            # if y_max < 0:
            #   y_max = y_max*0.9
            # # return
            # self.setYRange(y_min, y_max, padding = 0)    #set y range
            ################################################################

    def update_region(self, equity_curve, range_to_set, *args, **kwargs):
        """
        Update region on overview_plot (graph on bottom) according
        to x_range selected on equity_plot (graph on top)

        :param equity_curve: pg.PlotItem
        :param range_to_set: list of lists, range XY of plot
        """

        data_plotted = equity_curve.getData()  # get data plotted
        x_min = range_to_set[0][0]
        x_max = range_to_set[0][-1]

        if data_plotted[0] is None:  # no data plotted
            return
        else:
            self.linear_region.setRegion([x_min, x_max])  # update region
            # self.update_text_item(equity_curve)

    def add_text_item(self, curve, comment, deal_id, graph):
        """
        add a new text item with an arrow pointing the clicked trade.

        :param equity_curve: pg.PlotItem
        :param comment: string comment to show
        :param deal_id: string, deal id of trade to comment
        :param graph: string name of graph for debug
        """

        data_plotted = curve.getData()  # get data plotted
        if data_plotted[0] is None or data_plotted[0].size == 0:
            return

        deal_id_plotted = self._get_deal_id_plotted()  # get all deal id plotted

        try:
            point_x = deal_id_plotted.index(deal_id)
            point_y = data_plotted[1][point_x]
        except ValueError as VE:
            return

        # get comments items (arrow and textitem) already set
        comments_items = self._get_comments_items()

        """
        comment is a list with text at index 0 and a int at
        index 1, to indicate if comment will be shown on graph
        """

        text = comment[0]
        state = comment[1]

        # create a new text item
        if deal_id not in comments_items and text != "":
            # create and configure a arrow item
            arrow = classCustomGraphicsItems.CustomCurveArrow(curve)
            head_len = 25
            tail_len = 60

            arrow.setStyle(
                tipAngle=30,
                baseAngle=20,
                headLen=head_len,
                tailLen=tail_len,
                tailWidth=3,
                pen=pg.mkPen(60, 60, 60, width=1),
                brush=pg.mkBrush(60, 60, 60),
            )  # set fixed style

            arrow.setIndex(point_x)

            angle = arrow._get_angle()  # get rotation angle
            anchor = (0, 0)

            # depending of angle set different anchor
            if 180 < angle <= 225:
                anchor = (1, 0.5)
            if 225 < angle < 270:
                anchor = (1, 1)
            if 270 < angle <= 315:
                anchor = (0, 1)
            if 315 < angle < 360:
                anchor = (0, 0.5)
            if angle == 270 or angle == 90:
                anchor = (0.5, 1)

            # create a pg.TextItem
            text_item = pg.TextItem(
                anchor=anchor,
                fill=pg.mkBrush(250, 250, 250, 200),
                border=pg.mkPen(60, 60, 60),
            )

            # populate dict of items on graph
            comments_items.setdefault(deal_id, {})
            comments_items[deal_id]["text_item"] = text_item
            comments_items[deal_id]["arrow"] = arrow

            self._set_comments_items(comments_items)
            self.addItem(arrow)
            self.addItem(text_item)

        else:
            if text == "" and deal_id in comments_items:
                self.remove_text_item(deal_id)  # remove item
                return

        text_args = {"deal_id": deal_id, "text": text, "state": state, "graph": graph}

        self.update_text_item(curve, **text_args)

    def remove_text_item(self, deal_id, all_comments=False):
        """
        Function called when text is empty or when the user chooses to hide a
        comment. remove the arrow and text_item and update dict_comments_items.

        :param deal_id: string deal_id to remove
        :kw param all_comments: boolean remove all comments if true
        """

        comments_items = self._get_comments_items()

        if all_comments == True:
            for deal_id in comments_items.keys():  # remove all items
                text_item = comments_items[deal_id]["text_item"]
                arrow = comments_items[deal_id]["arrow"]

                self.removeItem(text_item)
                self.removeItem(arrow)
            comments_items = {}  # reset dict

        else:
            try:  # remove clicked comment
                text_item = comments_items[deal_id]["text_item"]
                arrow = comments_items[deal_id]["arrow"]

                self.removeItem(text_item)
                self.removeItem(arrow)

                comments_items.pop(deal_id, None)  # delete key
                self._set_comments_items(comments_items)  # update dict_comments_items

            except KeyError:
                pass

        self._set_comments_items(comments_items)  # update dict_comments_items

    def update_text_item(self, curve, *args, **kwargs):
        """
        Update text_item and position. Called when we add a new comment
        or when the user change existing comment. In this case kwargs are used.
        Or called when the range of plot is changed. when range is updated
        programmatically the 'sender' sends the curve else, retrieves the
        curve from listDataItems() method. Update all items positions/angles

        :param curve: pg.PlotItem

        :kw param text: string, comment text
        :kw param deal_id: string, string deal_id of trade
        :kw param state: int, show or not comment
        """

        if type(curve) is list:  # means range is updated manually
            curve = self.plotItem.listDataItems()[0]  # get curve

        data_plotted = curve.getData()
        comments_items = self._get_comments_items()
        deal_id_plotted = self._get_deal_id_plotted()

        try:  # when user edits a comment
            text = kwargs["text"]
            deal_id = kwargs["deal_id"]
            state = kwargs["state"]

            html_text = text.replace("\n", "<br />")  # set carriage return html tag
            html_text = (
                '<div style="text-align: center">\
                        <span style="color: rgb(0, 0, 0);">'
                + html_text
                + "</span></div>"
            )  # set style for text

            # remove item if user don't want to show it
            if state == 0:
                self.remove_text_item(deal_id)
            else:
                comments_items[deal_id]["text_item"].setHtml(
                    html_text
                )  # TODO: check if encode/decode

            self._set_comments_items(comments_items)  # update dict_comment_items

        except KeyError:
            pass

        comments_items = self._get_comments_items()

        # iterate over all comment set
        for count, deal_id in enumerate(comments_items.keys()):
            try:
                idx = deal_id_plotted.index(deal_id)

            except ValueError as VE:  # means no comment for this deal id
                continue

            arrow = comments_items[deal_id]["arrow"]  # get arrow item
            text_item = comments_items[deal_id]["text_item"]  # get text item

            """
            udpdate arrow pos, trigger event() method and so calculate a
            new angle see classCustomGraphicsItems arrow.setIndex(idx)
            """

            arrow.curve = weakref.ref(curve)  # update curve associate to arrow
            arrow.setIndex(idx)  # udpdate arrow pos

            point_x = arrow.property("pos").toPointF().x()
            point_y = arrow.property("pos").toPointF().y()

            angle = arrow._get_angle()  # get rotation angle
            anchor = (0, 0)

            # depending of angle set different anchor
            if 180 < angle <= 225:
                anchor = (1, 0.5)
            if 225 < angle < 270:
                anchor = (1, 1)
            if 270 < angle <= 315:
                anchor = (0, 1)
            if 315 < angle < 360:
                anchor = (0, 0.5)
            if angle == 270 or angle == 90:
                anchor = (0.5, 1)

            head_len = arrow.arrow.opts["headLen"]  # get dimensions of head arrow
            tail_len = arrow.arrow.opts["tailLen"]  # get dimensions of tail arrow
            text_item.anchor = QtCore.QPointF(
                anchor[0], anchor[1]
            )  # update text anchor

            """
            calculate the width and height of the rect containing the arrow.
            a call to the boundingRect() method does  not give expected results ???
            """

            arrow_width = np.cos((angle * np.pi) / 180) * (head_len + tail_len)
            arrow_height = np.sin((angle * np.pi) / 180) * (head_len + tail_len)

            # get scene coordinates of point trade selected
            text_scene_coord = self.plotItem.vb.mapViewToScene(
                QtCore.QPointF(point_x, point_y)
            )

            # add the width of arrow to x coordinates
            text_pos_x = text_scene_coord.x() + arrow_width

            # add the height of arrow to y coordinates
            text_pos_y = text_scene_coord.y() + arrow_height

            # get view coordinates of the start point of the arrow
            text_view_coord = self.plotItem.vb.mapSceneToView(
                QtCore.QPointF(text_pos_x, text_pos_y)
            )

            # set position of text at the start point of the arrow
            text_item.setPos(text_view_coord.x(), text_view_coord.y())

        self._set_comments_items(comments_items)  # update dict_comments_items

    def _get_comments_items(self):
        """Getter method for dict_comments_items"""

        return self._dict_comments_items

    def _set_comments_items(self, dict_comments_items):
        """
        Setter method for dict_comments_items

        :param dict_comments_items: dict with arrow and tex items
        """

        self._dict_comments_items = dict_comments_items

    def _get_deal_id_plotted(self):
        """Getter method for deal_id_plotted"""

        return self._deal_id_plotted

    def _set_deal_id_plotted(self, deal_id_plotted):
        """
        Setter method for deal_id_plotted

        :param deal_id_plotted: list with all deal_id plotted
        """

        self._deal_id_plotted = deal_id_plotted
