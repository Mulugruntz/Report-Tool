"""Main file."""

import os
import sys
from logging.config import fileConfig

from PyQt5 import QtWidgets

from report_tool.qt.main_window import ReportToolGUI
from report_tool.utils.constants import get_root_project_dir

ROOT = get_root_project_dir()

if getattr(sys, "frozen", False):
    os.environ["REQUESTS_CA_BUNDLE"] = str(ROOT / "cacert.pem")


def main() -> None:
    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName("Report Tool")

    fileConfig(ROOT / "logging.ini")

    gui = ReportToolGUI("Report Tool")
    gui.show()

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
