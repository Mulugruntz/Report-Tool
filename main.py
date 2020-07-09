from PyQt4 import QtCore
from PyQt4 import QtGui

import os
import sys
import glob
import datetime

import logging
import logging.config

from classMainWindow import*
from classDialogBox import*


if getattr(sys, "frozen", False):
        os.environ["REQUESTS_CA_BUNDLE"] = os.path.join(os.getcwd(), "cacert.pem")

if __name__ == '__main__':

    # lancement de l'app
    app = QtGui.QApplication(sys.argv)
    app.setApplicationName('Report Tool')

    logging.config.fileConfig(os.getcwd()+"/logging.ini")

    # app.setStyle(QtGui.QStyleFactory.create('Cleanlooks'))
    gui = ReportToolGUI('Report Tool')
    # gui.show()

    sys.exit(app.exec_())

"""
---> prob with dates in report, because of interest
---> solve delete account bug ?
---> improve thread management (quit ? del ? ) when switch account ?
---> when range changed on overview plot, it update text items but position are not good
---> solve that fucking problem with event!!! class customcurvepoint
---> hide growth colum, change version number, make msi when freezing
---> bugs raised by users:

"""
