import shutil
from pathlib import Path

import certifi
from cx_Freeze import Executable, setup

# Remove the build folder
shutil.rmtree(Path("build"), ignore_errors=True)
shutil.rmtree(Path("dist"), ignore_errors=True)

compagny_name = "Tioneb Nadous"
application_title = "Report Tool"
main_python_file = "report_tool/__main__.py"
current_dir: Path = Path.cwd()
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
    "threading",
    "queue",
    "time",
    "datetime",
    "collections",
    "random",
    "requests",
    "socket",
    "urllib",
    "urllib3",
]  # include needed library

# packages = ["credentials.txt", "favorite_markets.txt"]

cert_file = certifi.where()  # get SSL certificates
includesfiles = [
    cert_file,
    current_dir / "ig_config.json",
    current_dir / "logging.ini",
    current_dir / "icons",
    current_dir / "changelog.txt",
]

excludes = ["tkinter"]

bdist_msi_options = {
    "add_to_path": False,
    "initial_target_dir": rf"[ProgramFilesFolder]\\{application_title}",
}

build_exe_options = {
    "includes": includes,
    "excludes": excludes,
    "include_files": includesfiles,
    "include_msvcr": True,
}

setup(
    name=application_title,
    version="3.0.0-alpha1",
    description="Report Tool",
    options={"build_exe": build_exe_options, "bdist_msi": bdist_msi_options},
    executables=[
        Executable(
            main_python_file,
            base=base,
            target_name=application_title,
            icon=current_dir / "icons" / "main32.ico",
            shortcut_dir="DesktopFolder",
        )
    ],
)
