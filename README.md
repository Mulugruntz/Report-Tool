# Report Tool 3.0.0-alpha3

[![Latest GitHub release][latest-release]][latest-release-url]
![Latest GitHub pre-release][latest-prerelease]

Report Tool is an application coded in Python 3.11 / PyQt5 using IG Rest API to show basics statistics about past trades.

## Features

* Listing of past trades,
* Summary in points, points per lot, currency or percentage
* Equity curves,
* Export of trades in .txt format or .jpeg format
* Trades comment,
* Market filter.

![Main interface][gui-main-window]

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

![Connect menu][gui-connect-menu]

* Have fun !

## Building the msi installer

```shell script
cd Report-Tool
poetry run python setup.py bdist_msi
```

## Disclaimer

This tool was originally created by user **beniSo**, but he's no longer on GitHub.


[latest-prerelease]: https://img.shields.io/github/v/release/Mulugruntz/Report-Tool?include_prereleases&label=Report%20Tool
[latest-release]: https://img.shields.io/github/v/release/Mulugruntz/Report-Tool?label=Report%20Tool
[latest-release-url]: https://github.com/Mulugruntz/Report-Tool/releases/latest

[gui-main-window]: https://github.com/Mulugruntz/Report-Tool/raw/master/docs/main.png
[gui-connect-menu]: https://github.com/Mulugruntz/Report-Tool/raw/master/docs/connect.png
