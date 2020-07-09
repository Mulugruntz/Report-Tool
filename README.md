# Report Tool
Report Tool is an application coded in python/PyQt4 using IG Rest API to show basics statistics about past trades.


# Features
- Listing of past trades,
- Summary in points, points per lot, currency or percentage
- Equity curves,
- Export of trades in .txt format or .jpeg format
- Trades comment,
- Market filter.

![alt tag](https://github.com/beniSo/Report-Tool/blob/master/main.png)


# Installation under Linux
- for Debian
```bash
$ sudo apt-get install python-pyqtgraph
$ sudo apt-get install python-qt4
$ pip install requests
$ pip install numpy
$ pip install urllib3
```

- for Fedora
```bash
$ sudo dnf install python-qt4
$ sudo dnf install python-pyqtgraph
$ pip install requests
$ pip install numpy
$ pip install urllib3
```

# Installation under Windows

- Download and install python 2.7 (https://www.python.org/downloads/)
- Download and install PyQt4 (http://www.riverbankcomputing.co.uk/software/pyqt/download),
- Download and install PyQtGraph (http://www.pyqtgraph.org/

```bash
$ pip install requests
$ pip install numpy
$ pip install urllib3
```

# Usage
- Download the archive and unzip it:
```bash
$ cd /path/to/Report-Tool/folder
$ python main.py
```
- Enter your credentials, via the menu "Connect"

![alt tag](https://github.com/beniSo/Report-Tool/blob/master/connect.png)

- Have fun !
