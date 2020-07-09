# Report Tool

Report Tool is an application coded in Python 3.8 / PyQt5 using IG Rest API to show basics statistics about past trades.

## Features

* Listing of past trades,
* Summary in points, points per lot, currency or percentage
* Equity curves,
* Export of trades in .txt format or .jpeg format
* Trades comment,
* Market filter.

![Main interface](main.png)

## Installing on Linux

### Debian

```shell script
sudo apt-get install python-pyqtgraph
sudo apt-get install python-qt5
pip install requests numpy PyQt5
```

### Fedora

```shell script
sudo dnf install python-qt5
sudo dnf install python-pyqtgraph
pip install requests numpy PyQt5
```

## Installing on MacOS

```shell script
pip install requests numpy PyQt5
```

## Installing on Windows

- Download and install Python 3.8 (https://www.python.org/downloads/)
- Download and install PyQt5 (http://www.riverbankcomputing.co.uk/software/pyqt/download),
- Download and install PyQtGraph (http://www.pyqtgraph.org/

```shell script
pip install requests numpy PyQt5
```

## Usage

* Download the archive and unzip it:
```shell script
cd /path/to/Report-Tool/folder
python main.py
```
* Enter your credentials, via the menu "Connect"

![Connect menu](connect.png)

* Have fun !
