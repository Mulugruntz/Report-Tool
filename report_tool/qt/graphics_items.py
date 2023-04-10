""" This module holds classes to custom pyqtgraph base graphics items"""

import numpy as np
import pyqtgraph as pg
from PyQt5 import QtCore, QtWidgets


class CustomLinearRegion(pg.LinearRegionItem):

    """
    Class to reimplement setPen and setHoverPen, as the base
    class does not allow to modify the inifinite lines bounding
    the linear region. see base class pg.LinearRegionItem for details
    """

    def __init__(
        self, values=[0, 1], orientation=None, brush=None, movable=True, bounds=None
    ):
        """See base base for kw arguments"""

        pg.LinearRegionItem.__init__(self)

    def set_pen(self, pen):
        """
        Set pen and hoverPen for the two
        infinite lines bounding the region
        """

        for line in self.lines:  # get the infinite lines
            line.setPen(pen)
            hover_color = pen.color()

            # keep the same color but increase width
            line.setHoverPen(color=hover_color, width=1.5)


class DateAxis(pg.AxisItem):

    """
    Class to allows displaying date stringon x axis. Found on
    internet not from me.Just added the function update_axis,
    calledwhen new data are plotted(see update_graph in main class)
    Ticks String can be either # of trades or dates
    """

    def __init__(self, xdict, *args, **kwargs):
        """
        :param xdict: dict see funcMisc.create_dates_list
        """

        pg.AxisItem.__init__(self, *args, **kwargs)

        self.x_values = np.asarray(xdict.keys())
        self.x_strings = list(xdict.values())

    def update_axis(self, xdict, *args, **kwargs):
        """
        Update x_values and x_strings. called when new data are plotted
        :param xdict: dict see funcMisc.create_dates_list
        """

        self.xdict = xdict
        self.x_values = np.asarray(self.xdict.keys())
        self.x_strings = list(self.xdict.values())

        try:
            show_dates = kwargs["show_dates"]  # means equity_plot called function

            # update x axis label
            if show_dates == 2:
                x_label = '<span style="font-size:12pt">Dates</span style>'
            else:
                x_label = '<span style="font-size:12pt"># of trades</span style>'

            self.setLabel(text=x_label)

        except KeyError:  # means overview_plot called function
            self.setLabel(text=None)  # never set label

    def tickStrings(self, values, scale, spacing):
        """Reimplement base method"""

        strings = []

        for v in values:
            # vs is the original tick value
            vs = v * scale

            # if we have vs in our values, show the string
            # otherwise show nothing
            if vs in self.x_values:
                # Find the string with x_values closest to vs
                vstr = self.x_strings[np.abs(self.x_values - vs).argmin()]

            else:
                vstr = ""

            strings.append(vstr)

        return strings


class CustomCurvePoint(pg.CurvePoint):

    """
    Reimplement class pyqtgraph.CurvePoint only to reimplement the
    event function and therefore modify and acces to the rotation
    angle. The rotation is set perpendicular to the curve's tangent.

    Base class doc string:
    A GraphicsItem that sets its location to a point on a PlotCurveItem.
    Also rotates to be tangent to the curve. The position along the curve
    is a Qt property, and thus can be easily animated.
    Note: This class does not display anything
    see CurveArrow for an applied example
    """

    def __init__(self, curve, index=0, pos=None, rotate=True):
        """See base class for arguments"""

        pg.CurvePoint.__init__(self, curve, index=0, pos=None, rotate=True)
        self._angle = 0

    def event(self, ev):
        """Reimplement base method. add 90° to angle"""

        if (
            not isinstance(ev, QtCore.QDynamicPropertyChangeEvent)
            or self.curve() is None
        ):
            return False

        # return False::::
        if ev.propertyName() == "index":
            index = self.property("index")

            if "QVariant" in repr(index):
                index = index.toInt()[0]

        elif ev.propertyName() == "position":
            index = None

        else:
            return False

        (x, y) = self.curve().getData()

        if index is None:
            # print ev.propertyName(), self.property("position").toDouble()[0], self.property("position").typeName()
            pos = self.property("position")

            if "QVariant" in repr(pos):  ## need to support 2 APIs  :(
                pos = pos.toDouble()[0]

            index = (len(x) - 1) * np.clip(pos, 0.0, 1.0)

        if index != int(index):  # interpolate floating-point values
            i1 = int(index)
            i2 = np.clip(i1 + 1, 0, len(x) - 1)
            s2 = index - i1
            s1 = 1.0 - s2
            newPos = (x[i1] * s1 + x[i2] * s2, y[i1] * s1 + y[i2] * s2)
        else:
            index = int(index)
            i1 = np.clip(index - 1, 0, len(x) - 1)
            i2 = np.clip(index + 1, 0, len(x) - 1)
            newPos = (x[index], y[index])

        p1 = self.parentItem().mapToScene(QtCore.QPointF(x[i1], y[i1]))
        p2 = self.parentItem().mapToScene(QtCore.QPointF(x[i2], y[i2]))
        ang = np.arctan2(p2.y() - p1.y(), p2.x() - p1.x())  # returns radians

        self._set_angle(ang)  # set angle
        self.resetTransform()

        if self._rotate:
            # set angle perpendicular to the curve"s tangent
            self.rotate((180 + ang * 180 / np.pi) + 90)

        QtWidgets.QGraphicsItem.setPos(self, *newPos)

        return True

    def _get_angle(self):
        """Getter method"""

        return self._angle

    def _set_angle(self, ang):
        """Setter method"""

        self._angle = (180 + ang * 180 / np.pi) + 90  # add 90 to angle


class CustomCurveArrow(CustomCurvePoint):

    """
    No change made to this class expect that it inheritates
    from the CustomCurvePoint instead of pyqtgraph.CurvePoint

    Base class docstring:
    Provides an arrow that points to any specific sample on a PlotCurveItem.
    Provides properties that can be animated
    """

    def __init__(self, curve, index=0, pos=None, **opts):
        """See base class for arguments"""

        CustomCurvePoint.__init__(self, curve, index=index, pos=pos)

        if opts.get("pxMode", True):
            opts["pxMode"] = False
            self.setFlags(self.flags() | self.ItemIgnoresTransformations)

        opts["angle"] = 0
        self.arrow = pg.ArrowItem(**opts)

        self.arrow.setParentItem(self)

    def setStyle(self, **opts):
        return self.arrow.setStyle(**opts)
