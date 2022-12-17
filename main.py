# !/usr/bin/env python3

from PyQt5 import QtWidgets

import os
from pathlib import Path
import sys

import logging.config

from src.qt.main_window import ReportToolGUI

ROOT = Path(__file__).parent

if getattr(sys, "frozen", False):
    os.environ["REQUESTS_CA_BUNDLE"] = str(ROOT / "cacert.pem")


def main():
    # lancement de l'app
    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName("Report Tool")

    logging.config.fileConfig(ROOT / "logging.ini")

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
