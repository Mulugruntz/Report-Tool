"""Module with classes to interact with IG Rest API"""
import json
import logging
import traceback
from collections import OrderedDict
from copy import deepcopy

import requests

from report_tool.utils.settings import read_config, write_config


class APIError(Exception):

    """
    Simple class to return custom error msg
    Used to clearly identify type of requests reply
    Getter and setter might be useless
    """

    def __init__(self, msg=None):
        super(APIError, self).__init__()

        self._error_msg = msg

    def _get_error_msg(self):
        """Getter method"""

        return self._error_msg

    def _set_error_msg(self, msg):
        """
        Setter method

        :param msg: string describing error
        """

        self._error_msg = msg


class IGAPI(object):

    """This class provides methods to interacts with IG Rest API"""

    def __init__(self, connect_dict):
        """
        Constructor method

        :param connect_dict: OrderedDict() with all infos for connections
                             see classDialogBox.ConnectWindow
        """

        # init loggers
        self.logger_debug = logging.getLogger("ReportTool_debug.IGAPI")
        self.logger_info = logging.getLogger("ReportTool_info.IGAPI")

        headers = connect_dict["headers"]
        proxies = connect_dict["proxies"]
        payload = connect_dict["payload"]

        self._ls_endpoint = ""
        self._connect_dict = connect_dict
        self._headers = headers

        # set up a dict with all requested argument
        self._req_args = {"headers": headers, "data": payload, "proxies": proxies}

    def send_request(self, url, req_type, base_msg, *args, **kwargs):
        """
        Generic function to send request to API. It logs any exceptions.
        Returns ig response is successull otherwise an APIError object
        with an appropriate error message.

        :param url: string, adress of request
        :param req_type: string, determine type of requests (GET, POST....)
        :param base_msg: string, describing request where an error occured
        """

        try:
            # select type of request
            if req_type == "get":
                response = requests.get(url, **kwargs)

            elif req_type == "post":
                response = requests.post(url, **kwargs)

            elif req_type == "put":
                response = requests.put(url, **kwargs)

            elif req_type == "del":
                response = requests.put(url, **kwargs)

            # raise error if status code != 200
            response.raise_for_status()
            return response

        # catch every requests exceptions
        except requests.exceptions.RequestException as e:
            # try to see if ig as send a clear error msg
            try:
                response_text = json.loads(response.text)

                error_msg = base_msg + response_text["errorCode"]
                error_obj = APIError()

                error_obj._set_error_msg(error_msg)
                self.logger_debug.log(logging.ERROR, error_msg)  # log error

                return error_obj  # return error obj

            # else, unknow error, build a generic msg
            except Exception:
                # format request error
                formatted_error = traceback.format_exception_only(
                    requests.exceptions.RequestException, e
                )[0]

                error_msg = base_msg + "see log file"
                error_obj = APIError()

                error_obj._set_error_msg(error_msg)
                self.logger_debug.log(logging.ERROR, formatted_error)  # log full error

                return error_obj  # return error obj

    def create_session(self):
        """
        Send a POST request to connect to API.
        If successfull return None else an APIError object
        """

        # set up url see online doc
        base_url = self._connect_dict["base_url"]
        session_url = base_url + "/session"

        r_connect = self.send_request(
            session_url, "post", "Unable to connect: ", **self._req_args
        )

        # request failed return error
        if type(r_connect) == APIError:
            return r_connect

        # request is successfull
        else:
            self._req_args.pop("data")
            r_text = json.loads(r_connect.text)
            token = r_connect.headers["x-security-token"]
            cst = r_connect.headers["cst"]

            # recreate headers for further requests
            self._headers["CST"] = cst
            self._headers["X-SECURITY-TOKEN"] = token

            self._req_args["headers"] = self._headers

            body = r_connect.json()
            self._ls_endpoint = body["lightstreamerEndpoint"]

            return

    def get_user_accounts(self):
        """
        Get user's account.
        Returns a nested dict with number of accounts as
        keys and strings listed in list_accounts_labels
        as subkeys with informations of account as sub values
        Else return APIError object.
        """

        config = read_config()

        # dict with ISO code of currency as keys
        # and corresponding symbol as values
        dict_currency = {
            "EUR": "€",
            "USD": "$",
            "GBP": "£",
            "CAD": "$CA",
            "AUD": "$AU",
            "SGD": "S$",
            "CHF": "CHF",
            "NOK": "krone",
            "SEK": "kronor",
            "JPY": str("\u00A5"),
        }

        """
        list is the same used to create static labels in create_dock_account
        and self.dict_account_labels in ReportToolGUI here it used to created
        the keys of dict_account.keeping the same keys for this two dict
        helps to easily acces to informations.
        currency_iso preferred string are usefull but not displayed
        """

        list_account_labels = [
            "Account ID: ",
            "Account type: ",
            "Account name: ",
            "Cash available: ",
            "Account balance: ",
            "Profit/loss: ",
            "currency_ISO",
            "preferred",
        ]

        base_url = self._connect_dict["base_url"]
        account_url = base_url + "/accounts"

        r_account = self.send_request(
            account_url, "get", "Unable to get accounts: ", **self._req_args
        )

        # request failed return error
        if type(r_account) == APIError:
            return r_account

        # request is successfull, return accounts
        else:
            r_text = json.loads(r_account.text)

            dict_account = OrderedDict()

            for count, account in enumerate(r_text["accounts"]):
                dict_account.setdefault(count, OrderedDict())

                currency_ISO = account["currency"]
                currency_symbol = dict_currency[currency_ISO]

                # write new currency symbol
                config["currency_symbol"] = currency_symbol
                write_config(config)

                """
                read new config to have the correct formatting
                for currency symbol. may have a better solution
                """

                config = read_config()
                currency_symbol = config["currency_symbol"]

                """
                following infos will be displayed
                in dock_account of main window
                """

                acc_id = account["accountId"]
                acc_type = account["accountType"]
                acc_name = account["accountName"]

                self._cash_available = str(account["balance"]["balance"])

                cash_available = self._cash_available + currency_symbol

                acc_balance = str(account["balance"]["available"]) + currency_symbol

                profit_loss = str(account["balance"]["profitLoss"]) + currency_symbol

                preferred = account["preferred"]

                list_acc_infos = [
                    acc_id,
                    acc_type,
                    acc_name,
                    cash_available,
                    acc_balance,
                    profit_loss,
                    currency_ISO,
                    preferred,
                ]

                # populate dict
                for i, label in enumerate(list_account_labels):
                    dict_account[count][label] = list_acc_infos[i]

            try:  # select currency symbol
                currency_symbol = dict_currency[currency_ISO]

            except KeyError:  # default is €
                currency_symbol = dict_currency["EUR"]

            config["currency_symbol"] = currency_symbol
            write_config(config)

            return dict_account

    def get_transactions(self, date_range):
        """
        Get transactions within the range of dates selected by user.
        Returns transactions received or an APIError object

        :param date_range: string formatted to be compliant
                           with API format /dd-MM-yyyy/"dd-MM-yyyy"
        """

        base_url = self._connect_dict["base_url"]
        req_args = self._req_args

        transaction_url = base_url + "/history/transactions/ALL" + date_range

        r_transaction = self.send_request(
            transaction_url, "get", "Unable to get transactions: ", **req_args
        )

        # request failed return error
        if type(r_transaction) == APIError:
            return r_transaction

        # request is successfull, returns transactions
        else:
            transaction_received = json.loads(r_transaction.text)  # TODO: sanitize

            return transaction_received

    def switch_account(self, acc_id, acc_name):
        """
        Switch to account selected by user.
        Returns a None or an APIError object

        :param acc_id: string, id of account to connect to
        :param acc_name: string, name of account to connect to
        """

        switch_body = json.dumps({"accountId": acc_id, "defaultAccount": ""})

        req_args = deepcopy(self._req_args)  # do not modify req args
        req_args["data"] = switch_body

        base_url = self._connect_dict["base_url"]
        switch_url = base_url + "/session"

        r_switch = self.send_request(
            switch_url, "put", "Unable to switch to %s: " % acc_name, **req_args
        )

        # request failed return error
        if type(r_switch) == APIError:
            return r_switch

        # request is successfull
        else:
            r_text = json.loads(r_switch.text)

            # when switch to another account
            # a new token is provided
            token = r_switch.headers["x-security-token"]

            # recreate headers for further requests
            self._headers["X-SECURITY-TOKEN"] = token

            self._req_args["headers"] = self._headers

            return

    def logout(self, *args, **kwargs):
        """Send a request to logout"""

        # set up url see online doc
        base_url = self._connect_dict["base_url"]
        session_url = base_url + "/session"

        r_logout = self.send_request(
            session_url, "post", "Unable to logout: ", **self._req_args
        )

        # request failed return error
        if type(r_logout) == APIError:
            return r_logout

        # request is successfull
        else:
            return

    def _get_ls_endpoint(self):
        """Getter method"""

        return self._ls_endpoint

    def _set_ls_endpoint(self, endpoint):
        """
        Setter method

        :param endpoint: string
        """

        self._ls_endpoint = endpoint

    def _get_req_args(self):
        """Getter method"""

        return self._req_args

    def _set_req_args(self, req_args):
        """
        Setter method

        :param req_args: dict
        """

        self._req_args = req_args

    def _get_connect_dict(self):
        """Getter method"""

        return self._connect_dict

    def _set_connect_dict(self, connect_dict):
        """
        Setter method

        :param connect_dict: OrderedDict()
        """

        self._connect_dict = connect_dict

    def _get_cash_available(self):
        """Getter method"""

        return self._cash_available  # TODO: change to Decimal + property

    def _set_cash_available(self, cash_available):
        """
        Setter method. Delete currency symbol
        to avoid float conversion error

        :param cash_available: str, cash on user's account
        """

        config = read_config()
        currency_symbol = config["currency_symbol"]

        self._cash_available = cash_available.replace(currency_symbol, "")
