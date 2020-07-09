from cx_Freeze import setup, Executable

import shutil
import os
import sys
import requests.certs

from glob import glob

# Remove the build folder
shutil.rmtree("build", ignore_errors=True)
shutil.rmtree("dist", ignore_errors=True)

compagny_name = "Tioneb Nadous"
application_title = "Report Tool"
main_python_file = "main.py"
current_dir = os.getcwd()
base = None

# if sys.platform == "win32":
#       base = "Win32GUI"

includes = [
    "PyQt5.QtCore",
    "PyQt5.QtGui",
    "PyQt5.QtWidgets",
    "PyQt5.QtNetwork",
    "atexit",  # TODO: QtNetwork?
    "re",
    "os",
    "sys",
    "logging",
    "glob",
    "json",
    "base64",
    "pyqtgraph",
    "numpy",
    "numpy.lib.format",
    "threading",
    "Queue",
    "time",
    "datetime",
    "collections",
    "random",
    "requests",
    "socket",
    "urllib",
    "urllib2",
    "urllib3",
    "urlparse",
]  # include needed library

# packages = ["credentials.txt", "favorite_markets.txt"]

cert_file = requests.certs.where()  # get SSL certificats
includesfiles = [
    cert_file,
    current_dir + "\\credentials.json",
    current_dir + "\\comments.json",
    current_dir + "\\config.json",
    current_dir + "\\ig_config.json",
    current_dir + "\\logging.ini",
    current_dir + "\\icons",
    current_dir + "\\georges.png",
    current_dir + "\\changelog.txt",
]

excludes = ["tkinter"]

bdist_msi_options = {
    "add_to_path": False,
    "initial_target_dir": r"[ProgramFilesFolder]\\%s" % application_title,
}

build_exe_options = {
    "includes": includes,
    "include_files": includesfiles,
    "include_msvcr": True,
    "compressed": True,
    "copy_dependent_files": True,
    "create_shared_zip": True,
    "include_in_shared_zip": True,
}

setup(
    name=application_title,
    version="2.2",
    description="Report Tool",
    options={"build_exe": build_exe_options, "bdist_msi": bdist_msi_options},
    executables=[
        Executable(
            main_python_file,
            base=base,
            icon=current_dir + "\icons\main32.ico",
            shortcutDir="DesktopFolder",
        )
    ],
)
