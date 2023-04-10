import logging
import re
import time
import traceback
from collections import OrderedDict, defaultdict
from decimal import Decimal, DivisionByZero
from typing import Dict, List, Text

from PyQt5 import QtCore

from report_tool.communications.ig_rest_api import APIError
from report_tool.qt.functions import (
    format_market_name,
    read_comment,
    read_ig_config,
    write_comments,
)
from report_tool.utils.settings import read_config

RE_FLOAT = re.compile(r"[+-]? *(?:\d+(?:\.|,\d*)?\.*\d+)(?:[eE][+-]?\d+)?")
RE_DATE = re.compile(r"/(.*?)$")


class TransactionThread(QtCore.QThread):

    """Create a thread for get the transaction of the given period"""

    transaction_received = QtCore.pyqtSignal(object)  # create a finish signal

    def __init__(self, session, transaction_queue, result_handler, parent=None):
        """
        :param session: :any:`IGAPI` instance
        :param transaction_queue: Queue
        :result_handler: classMainWindow.update_results
        """

        QtCore.QThread.__init__(self, parent)

        self.session = session
        self.transaction_queue = transaction_queue

        self.transaction_received.connect(result_handler)

        # init loggers
        self.logger_debug = logging.getLogger("ReportTool_debug.IGAPI")
        self.logger_info = logging.getLogger("ReportTool_info.IGAPI")

    def run(self):
        """
        Send a request for the choosen dates in transactions dict.
        If request successfull call trea_data, else emit an error msg
        """

        while not self.transaction_queue.empty():  # consumes every element in queue
            date_range = self.transaction_queue.get()  # get element in queue

            # TODO: Use datetime.datetime.strptime() instead?
            # extract start date and end date
            date = RE_DATE.findall(date_range)
            date_lst = "/".join(date).replace("/", ",").split(",")

            start = date_lst[0]
            end = date_lst[-1]

            msg = "Retrieving transactions from %s to %s..." % (start, end)
            self.logger_info.log(logging.INFO, msg)

            transactions_result = self.session.get_transactions(date_range)

            # requests failed
            if type(transactions_result) == APIError:
                self.transaction_received.emit(transactions_result)
                return

            else:
                nb_transactions = len(transactions_result["transactions"])
                msg = "Received %d transactions" % (nb_transactions)

                self.logger_info.log(logging.INFO, msg)
                self.logger_info.log(logging.INFO, "Treating data...")

                try:
                    self.treat_data(transactions_result)
                except Exception:
                    self.logger_debug.log(logging.ERROR, traceback.format_exc())
                    self.transaction_received.emit("An error occured: see log file")
        return

    def treat_data(self, transactions_result):
        """
        Treat the dict received from IG and build a more
        comprehensive nested OrderedDict(). Deal id
        for each transactions acts as main keys and string
        in dict_transactions_headers act as subkeys:
        result_dict = {"dealId": {"type": "ORDRE",
                                 "date": "19/06/2015",
                                  ...
                                 "pnl": 15},

                      "dealId": {"type": "WITH",
                                 "date": "20/06/2015",
                                 ...
                                 "pnl": 15}
                        ....
                        }

        :param transactions_result: dict returns by IG
        """

        dict_transaction_headers = [
            "type",
            "date",
            "market_name",
            "direction",
            "open_size",
            "open_level",
            "final_level",
            "points",
            "points_lot",
            "pnl",
        ]

        # load initial capital and config
        config = read_config()
        start_capital = Decimal(config["start_capital"])
        symbol = config["currency_symbol"]
        auto_calculate = config["auto_calculate"]
        aggregate = config["aggregate"]
        capital = start_capital

        ig_config = read_ig_config()

        """
        ig sends keywords to identify transactions type known
        keywords ares stored in ig_config.json
        if transaction type is unknown log it
        """

        kw_order = ig_config["keyword"]["ORDER"]
        kw_fees = ig_config["keyword"]["FEES"]
        kw_cashin = ig_config["keyword"]["CASH_IN"]
        kw_cashout = ig_config["keyword"]["CASH_OUT"]
        kw_transfer = ig_config["keyword"]["TRANSFER"]

        """
        fill a "buffer" dict with dealId as key. each key is
        a list with all transactions attached to that dealId
        """

        transactions_dict2 = defaultdict(list)
        for transaction in transactions_result["transactions"]:
            deal_ref = transaction["reference"]
            transactions_dict2[deal_ref].append(transaction)

        transactions_dict = OrderedDict()
        for transaction in transactions_result["transactions"]:
            deal_ref = transaction["reference"]

            if deal_ref not in transactions_dict:
                transactions_dict.setdefault(deal_ref, [{}])  # build dict
                transactions_dict[deal_ref][0] = transaction

            else:
                transactions_dict[deal_ref].append(transaction)

        result_dict = OrderedDict()

        # FIXME: dict .keys() order was not deterministic prior to 3.6. Reviewing is needed
        # iterate over each deal_ref from older to newer
        for deal_ref in reversed(transactions_dict.keys()):
            total_pnl = Decimal()
            total_points = Decimal()
            total_size = Decimal()

            # iterate over each event that concerns deal_ref
            for count, deal_transaction in enumerate(transactions_dict[deal_ref]):
                # get the transaction type (order, fees...)
                transaction_type = transactions_dict[deal_ref][count]["transactionType"]

                market = transactions_dict[deal_ref][count]["instrumentName"]

                market_name = format_market_name(market)

                if transaction_type in kw_order:  # transaction is a trade
                    # TODO: create sub-methods
                    open_level = Decimal(
                        transactions_dict[deal_ref][count]["openLevel"]
                    )
                    close_level = Decimal(
                        transactions_dict[deal_ref][count]["closeLevel"]
                    )
                    size = Decimal(transactions_dict[deal_ref][count]["size"])
                    str_pnl = transactions_dict[deal_ref][count]["profitAndLoss"]

                    # as the pnl is an alphanumeric value extract the float part
                    pnl = Decimal(RE_FLOAT.findall(str_pnl)[0].replace(",", ""))

                    direction = "SELL" if size < 0 else "BUY"

                    date = transactions_dict[deal_ref][count]["date"]

                    """
                    we suppose that the first close level
                    in the list is the last that occurred
                    """

                    final_level = Decimal(transactions_dict[deal_ref][0]["closeLevel"])

                    """
                    calculate points won/lost. it"s done according to
                    to lot size, because when the user partially closes
                    a trade it"s more revealing of the true profit. but
                    it can corrupt a result if the user never do it
                    """

                    points = self.calculate_pnl(
                        open_level, close_level, size, direction, market_name
                    )

                    # if aggregate cumulate size, points, pnl
                    if aggregate == 2:  # FIXME: Nani???
                        total_points += points
                        total_pnl += pnl
                        total_size += size

                    else:
                        total_points = points
                        total_pnl = pnl
                        total_size = size

                elif transaction_type in kw_fees:  # TODO: create sub-methods
                    """
                    depending of market name change
                    transaction type for a clearer one
                    """

                    if True in [kw in market_name.lower() for kw in kw_cashin]:
                        transaction_type = "CASHIN"

                    elif True in [kw in market_name.lower() for kw in kw_cashout]:
                        transaction_type = "CASHOUT"

                    elif True in [kw in market_name.lower() for kw in kw_transfer]:
                        transaction_type = "TRANSFER"

                    else:
                        transaction_type = transaction_type

                    date = transactions_dict[deal_ref][count]["date"]
                    str_pnl = transactions_dict[deal_ref][count]["profitAndLoss"]
                    re_float = r"[+-]? *(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?"
                    total_pnl = Decimal(RE_FLOAT.findall(str_pnl)[0])

                    direction = "-"
                    open_level = "-"
                    total_size = "-"
                    final_level = "-"
                    total_points = "-"

                # elif transaction_type in kw_cashin and\
                # True in [kw in market_name.lower() for kw in kw_cashin]:
                #         date      = transactions_dict[deal_ref][count]["date"]
                #         str_pnl   = transactions_dict[deal_ref][count]["profitAndLoss"]
                #         re_float  = r"[+-]? *(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?"
                #         total_pnl = float(RE_FLOAT.findall(str_pnl)[0])

                #         direction        = "-"
                #         open_level       = "-"
                #         total_size       = "-"
                #         final_level      = "-"
                #         total_points     = "-"
                #         transaction_type = "CASHIN"    # change transaction type with clearer one

                # elif transaction_type in kw_cashout and\
                # True in [kw in market_name.lower() for kw in kw_cashout]:
                #         date      = transactions_dict[deal_ref][count]["date"]
                #         str_pnl   = transactions_dict[deal_ref][count]["profitAndLoss"]
                #         re_float  = r"[+-]? *(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?"
                #         total_pnl = float(RE_FLOAT.findall(str_pnl)[0])

                #         direction        = "-"
                #         open_level       = "-"
                #         total_size       = "-"
                #         final_level      = "-"
                #         total_points     = "-"
                #         transaction_type = "CASHOUT"    # change transaction type with clearer one

                # elif transaction_type in kw_transfer and\
                # True in [kw in market_name.lower() for kw in kw_transfer]:
                #         date      = transactions_dict[deal_ref][count]["date"]
                #         str_pnl   = transactions_dict[deal_ref][count]["profitAndLoss"]
                #         re_float  = r"[+-]? *(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][+-]?\d+)?"
                #         total_pnl = float(RE_FLOAT.findall(str_pnl)[0])

                #         direction        = "-"
                #         open_level       = "-"
                #         total_size       = "-"
                #         final_level      = "-"
                #         total_points     = "-"
                #         transaction_type = "TRANSFER"    # change transaction type with clearer one

                else:  # TODO: create sub-methods
                    msg = "%s is undefined type" % transaction_type
                    self.logger_debug.log(logging.ERROR, msg)

                    date = transactions_dict[deal_ref][count]["date"]

                    str_pnl = "-"
                    re_float = "-"
                    total_pnl = "-"
                    direction = "-"
                    open_level = "-"
                    total_size = "-"
                    final_level = "-"
                    total_points = "-"

                    transaction_type = (
                        "UNDEFINED"  # change transaction type with clearer one
                    )

                try:
                    # TODO: work on types so total_size can only be Decimal or int.
                    #       Can currently be str('-').
                    points_lot = round(total_points / abs(total_size), 2)
                except DivisionByZero:
                    points_lot = "-"

                infos_list = [
                    transaction_type,
                    date,
                    market_name,
                    direction,
                    total_size,
                    open_level,
                    final_level,
                    total_points,
                    points_lot,
                    total_pnl,
                ]

                """
                if not aggregate, for each transactions add a index
                of transaction to the deal_ref this is done to simulate
                a different key. Therefore the results dict will contains
                a key for each transaction even if it concerns the same trade.
                """

                if aggregate != 2:
                    deal_ref_nb = deal_ref + "_" + str(count)
                    result_dict.setdefault(deal_ref_nb, {})

                    for count, header in enumerate(
                        dict_transaction_headers
                    ):  # fill dict
                        result_dict[deal_ref_nb][header] = infos_list[count]

                else:
                    deal_ref_nb = deal_ref + "_0"  # don"t increment deal ref
                    result_dict.setdefault(deal_ref_nb, {})

                    for count, header in enumerate(
                        dict_transaction_headers
                    ):  # fill dict
                        result_dict[deal_ref_nb][header] = infos_list[count]

        msg = "Done"
        self.logger_info.log(logging.INFO, msg)

        self.transaction_received.emit(result_dict)  # emit dict

    def calculate_pnl(
        self,
        open_level: Decimal,
        close_level: Decimal,
        size: Decimal,
        direction: str,
        market_name: str,
    ) -> Decimal:
        """
        Calculate profit loss in point and currency

        :kw param open_level: Decimal, open level of trade
        :kw param close_level: Decimal, close level of trade
        :kw param size: Decimal, size of trade
        :kw param direction: string, direction (BUY or SELL) of trade
        :kw param market_name: string, used to get type of market(FOREX, Indices)
        """

        if direction == "BUY":
            # means market is Forex
            if "/" in market_name.lower():
                # TODO: is round() still necessary with Decimal()??
                # means cross is with Yen
                if "jpy" in market_name.lower():
                    points = round((close_level - open_level) * abs(size), 5) * 100
                else:
                    points = round((close_level - open_level) * abs(size), 5) * 10000

            else:
                points = round((close_level - open_level) * abs(size), 2)

        elif direction == "SELL":
            # means market is Forex
            if "/" in market_name.lower():
                # means cross is with Yen
                if "jpy" in market_name.lower():
                    points = round((open_level - close_level) * abs(size), 5) * 100
                else:
                    points = round((open_level - close_level) * abs(size), 5) * 10000
            else:
                points = round((open_level - close_level) * abs(size), 2)

        return points


class UpdateCommentsThread(QtCore.QThread):

    """
    Thread to update comment. It runs continuously
    as soon as app is started. Read comment file and
    wait for item in queue. Comments are stored as list, e.g
    comment = ["blabla", 0], the second index (int) is used
    to show(if = 2) or not(if = 0) the comment on graph


    --If item is a string (when user click on graph) looks for a
    comment matching the deal_id. if nothing found send an empty
    string else send comment found.
    --If item is a dict means that user is editing comment,
    update or create key and save file.
    --If item is a list, means that new dta has been plotted.
    list contains all new deal id. For each deal_id search
    for a comment. send a dict with all comments found

    See update_trade_details and update_comments functions
    in classReportToolGUI to see how thread is managed.
    """

    comment_found = QtCore.pyqtSignal(object)  # signal use to send comment

    def __init__(self, queue, result_handler, parent=None):
        """
        :param transaction_queue: Queue
        :param result_handler: classMainWindow.update_comments
        """

        QtCore.QThread.__init__(self, parent)
        self.comments_queue = queue
        self.comment_found.connect(result_handler)

    def run(self):
        """
        Thread is continuously running. maybe set it as deamon
        Waiting element in queue and depending of type received
        update comments. see in line comments below
        """

        config = read_config()
        last_usr = config["last_usr"]

        while True:
            while not self.comments_queue.empty():  # run until queue is empty
                comments = read_comment()  # read saved comments

                # pop empty user key, when first start or error while loading
                try:
                    comments.pop("", None)  #
                except KeyError:
                    pass

                try:
                    usr_comments = comments[last_usr]
                    for deal_id in usr_comments.keys():  # delete empty comments
                        if usr_comments[deal_id][0] == "":
                            usr_comments.pop(deal_id, None)

                except KeyError:
                    usr_comments = {}  # no comment yet for this user

                object_in_queue = self.comments_queue.get()  # get item in queue

                if isinstance(object_in_queue, Text):  # means it a deal_id
                    """
                    when thread reveives a string it means the user
                    has clicked on graph. We know which deal_id is
                    concerned so just send the comment as list
                    """

                    # search for comment at this deal_id
                    try:
                        saved_comment = usr_comments[object_in_queue]
                        self.comment_found.emit(saved_comment)  # emit comment found

                    except KeyError:  # no comment found
                        self.comment_found.emit(["", 0])  # emit empty string

                # means new data plotted, show all comments found
                elif isinstance(object_in_queue, List):
                    """
                    When thread reveives a list it means result has
                    been updated, so for each deal id plotted try to
                    found a comment. if success sends a dict with all
                    deal_id found as keys and comment as values.
                    """

                    dict_to_send = {}

                    for deal_id in object_in_queue:
                        # dict_to_send[deal_id] = ['']z

                        # search for comment at this deal_id
                        try:
                            saved_comment = usr_comments[deal_id]
                            comment_to_send = {deal_id: saved_comment}
                            dict_to_send[deal_id] = saved_comment

                        except KeyError as KE:  # no comment found
                            # print(KE)
                            # comment_to_send = {deal_id : ['', 0]}
                            # dict_to_send[deal_id] = ['', 0]
                            continue

                    self.comment_found.emit(dict_to_send)

                # means a new comment has to be saved
                elif isinstance(object_in_queue, Dict):
                    """
                    When thread received a dict, user is
                    editing a comment or creating a new one
                    """

                    # FIXME: dict .keys() order was not deterministic prior to 3.6. Reviewing is needed
                    # get deal_id and comment
                    deal_id_to_save = str(list(object_in_queue.keys())[0])
                    comment_to_save = object_in_queue[deal_id_to_save]

                    usr_comments[
                        deal_id_to_save
                    ] = comment_to_save  # build dict to save
                    comments[last_usr] = usr_comments

                    write_comments(comments)

            time.sleep(0.05)
