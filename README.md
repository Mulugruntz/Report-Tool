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

## Installation

### What you will need

* Python 3.11: https://www.python.org/downloads/
* pip (should already be installed with Python): https://pip.pypa.io/en/stable/installing/
* poetry: `curl -sSL https://install.python-poetry.org | python3 -`
  * More info: https://python-poetry.org/docs/#installing-with-the-official-installer

### Dependencies

```shell script
cd Report-Tool
poetry install
```

## Usage

* Download the archive and unzip it:
* Either run the entry point:
```shell script
cd Report-Tool
poetry run report-tool
```
* Or run the script:
```shell script
cd Report-Tool
poetry run python -m report_tool
```
* Enter your credentials, via the menu "Connect"

![Connect menu](connect.png)

* Have fun !

## Disclaimer

This tool was originally created by user **beniSo**, but he's no longer on GitHub.
