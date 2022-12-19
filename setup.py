from cx_Freeze import setup, Executable

import shutil
from pathlib import Path
import certifi

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
    "PyQt6.QtCore",
    "PyQt6.QtGui",
    "PyQt6.QtWidgets",
    "PyQt6.QtNetwork",
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
    "numpy.utils.format",
    "threading",
    "Queue",
    "time",
    "datetime",
    "collections",
    "random",
    "requests",
    "socket",
    "urllib",
    "urllib3",
    "urlparse",
]  # include needed library

# packages = ["credentials.txt", "favorite_markets.txt"]

cert_file = certifi.where()  # get SSL certificates
includesfiles = [
    cert_file,
    current_dir / "credentials.json",
    current_dir / "comments.json",
    current_dir / "config.json",
    current_dir / "ig_config.json",
    current_dir / "logging.ini",
    current_dir / "icons",
    current_dir / "georges.png",
    current_dir / "changelog.txt",
]

excludes = ["tkinter"]

bdist_msi_options = {
    "add_to_path": False,
    "initial_target_dir": rf"[ProgramFilesFolder]\\{application_title}",
}


options = {
    "build_exe": {
        "includes": includes,
        "excludes": excludes,
        "include_files": includesfiles,
        "include_msvcr": True,
        "compressed": True,
        "copy_dependent_files": True,
        "create_shared_zip": True,
        "include_in_shared_zip": True,
    }
}


setup(
    name=application_title,
    version="2.2",
    description="Report Tool",
    options={"build_exe": options, "bdist_msi": bdist_msi_options},
    executables=[
        Executable(
            main_python_file,
            base=base,
            icon=current_dir / "icons" / "main32.ico",
            shortcutDir="DesktopFolder",
        )
    ],
)
