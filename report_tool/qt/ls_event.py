from PyQt5 import QtCore


class LsEvent(QtCore.QObject):

    """
    This class create and manage objects which will send signals
    to main loop whenever an LS update is received. The items in
    my myUpdateField are determined by schema set when the user
    create a LS subscription.
    The signal emit an object, so it can emit any type (float, list..)
    """

    acc_signal = QtCore.pyqtSignal(object)  # signal for account update
    pos_signal = QtCore.pyqtSignal(object)  # signal for position update
    price_signal = QtCore.pyqtSignal(object)  # signal for price update
    status_signal = QtCore.pyqtSignal(object)  # signal to probe status

    def __init__(self):
        super(LsEvent, self).__init__()

    def on_state(self, state):
        """
        Print the LS connection state

        :param state: string, state of ls connection
        """

        self.status_signal.emit(state)

    def acc_update_event(self, item, myUpdateField):
        """
        Emit a signal when an account update is received

        :param item: string, identify table that sends update
        :param myUpdateField: tuple, see MainWindow for items
        """

        self.acc_signal.emit(myUpdateField)

    def pos_update_event(self, item, myUpdateField):
        """
        Emits a signal when a position update is received

        :param item: string, identify table that sends update
        :param myUpdateField: dict, see MainWindow for items
        """

        self.pos_signal.emit(myUpdateField)
