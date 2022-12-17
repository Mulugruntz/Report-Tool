# !/usr/bin/env python3

from PyQt5 import QtWidgets

import os
import sys

import logging.config

from src.gui.classMainWindow import ReportToolGUI

if getattr(sys, "frozen", False):
    os.environ["REQUESTS_CA_BUNDLE"] = os.path.join(os.getcwd(), "cacert.pem")


def main():
    # lancement de l'app
    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName("Report Tool")

    logging.config.fileConfig(os.getcwd() + "/logging.ini")

    # app.setStyle(QtWidgets.QStyleFactory.create('Cleanlooks'))
    gui = ReportToolGUI("Report Tool")
    # gui.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()

"""
---> prob with dates in report, because of interest
---> solve delete account bug ?
---> improve thread management (quit ? del ? ) when switch account ?
---> when range changed on overview plot, it update text items but position are not good
---> solve that fucking problem with event!!! class customcurvepoint
---> hide growth colum, change version number, make msi when freezing
---> bugs raised by users:

"""
