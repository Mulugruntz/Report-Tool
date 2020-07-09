import codecs
import os
import re

from collections import OrderedDict
import numpy as np

import funcMisc


class ExportToExcel(object):

    """
    Class with method to save transactions and/or summary
    calculated to a text file. User can select what to export,
    where and file separator. File name is fixed
    """

    def __init__(self, *args, **kwargs):

        self._data_to_export = OrderedDict()


    def organize_data(self, widget_pos, *args, **kwargs):

        """
        Organize data. Build a list of list to be saved

        :param widget_pos: QtTableWidget, contains transactions. i prefer work
                           with widget instead of the OrderedDict as widget
                           contains transactions already formatted according
                           to options (include interest, agregate pos...)
        """

        config = funcMisc.read_config()

        summary      = self._data_to_export["summary"]
        summary_infos = summary.keys()

        values = [summary[key] for key in summary_infos]

        for count, value in enumerate(values):
            try:

                """
                as some values are formatted to be displayed in a QLabel
                (with html syntax) extract only interesting part of text
                """

                data = re.search(r'>(.*?)<', value).group(1)
                values[count] = data    # replace html text in list

            except Exception as e:
                continue

        # convert list to np.array to easily transpose it
        arr_summary  = np.array([list(summary_infos),values], dtype=np.str)
        self.list_summary = np.transpose(arr_summary).tolist()

        self.list_trans = []

        nb_row = widget_pos.rowCount()
        nb_col = widget_pos.columnCount()

        self.list_trans = []

        # get text of each cell in QTableWidget
        for row in range(nb_row):
            list_row = []    # list with all row cells
            for col in range(nb_col):
                item = widget_pos.item(row, col)
                list_row.append(str(item.text()))

            self.list_trans.append(list_row)


    def create_headers(self, header_type, *args, **kwargs):

        """
        Creates a header to inform about the data saved.
        Constructed according to options selected and date range

        :param header_type: string, Summary or Transactions first word of header
        """

        config = funcMisc.read_config()

        result_in = config["result_in"]
        auto_calc = config["auto_calculate"]
        include   = config["include"]
        agregate  = config["agregate"]

        what_to_export  = config["what_to_export"].lower()
        currency_symbol = config["currency_symbol"]
        start_capital   = self._data_to_export["start_capital"]

        # convert options to human readable one
        if auto_calc == 2:
            str_capital = "(auto)"
        else:
            str_capital = "(manual)"

        if agregate == 2:
            agregate = ""
        else:
            agregate = "not "

        if include == 2:
            include = ""
        else:
            include = "not "

        header = ""

        acc_name = self._data_to_export["current_acc"]["Account name: "].lower()
        acc_type = self._data_to_export["current_acc"]["Account type: "].lower()

        # constructs a header with options
        if header_type == "Summary":
            header = "#" + header_type + " calculated in " + result_in.lower() +\
                     " | interest " + str(include) + "included"\
                     " | positions " + str(agregate) +"agregated"+\
                     " | capital inital = " + str(start_capital) +\
                     str(currency_symbol) + str(str_capital)

        # constructs a header with date range
        elif header_type == "Transactions":
            transactions = self._data_to_export["transactions"]

            dates = [transactions[deal_id]["date"]
                     for deal_id in transactions.keys()]    # list of dates

            if len(dates) != 0:
                header = "#" + header_type + " from " +\
                         dates[0] + " to " + dates[-1]

                # construct fixed file name
                self.fl_name = "/report tool_%s_%s_%s_from %s to %s"\
                                %(acc_type, acc_name, what_to_export,
                                  dates[0].replace("/", "-"),
                                  dates[-1].replace("/", "-")) + ".txt"
            else:
                header = "No transactions"

        return([header])


    def save_txt(self, *args, **kwarg):

        """Save data in text file according to options"""

        trans_col = ["Date", "Market", "Direction",
                     "Open Size","Open", "Close",
                     "Points", "Points/lot", "Profit/Loss"
                     ]    # human readable columns name

        config = funcMisc.read_config()

        what_to_export = config["what_to_export"]
        separator      = config["separator"]
        dir_export     = config["dir_export"]

        summary_header = self.create_headers("Summary")
        trans_header   = self.create_headers("Transactions")

        # insert headers in list
        self.list_summary.insert(0, summary_header)
        self.list_trans.insert(0, trans_col)
        self.list_trans.insert(0, trans_header)

        # export Summary + Transactions
        if what_to_export == "All":
            self.list_summary.insert(0, "\n")
            list_to_write = self.list_trans + self.list_summary

        # export only Transactions
        elif what_to_export == "Transactions":
            list_to_write = self.list_trans

        # export only Summary
        elif what_to_export == "Summary":
            list_to_write = self.list_summary

        # save file
        with codecs.open(dir_export+self.fl_name, "w", encoding="utf-8") as f:
            for line in list_to_write:
                line = separator.join(line) + "\n"
                f.write(line)


    def _get_data_to_export(self):

        """Getter method"""

        return(self._data_to_export)


    def _set_data_to_export(self, dict_results):

        """
        Setter method, use only one for both
        transactions and summary are they are linked
        See classThread and classResults for structure

        :param dict_result: OrderedDict, contains infos to save
                            see classMainWindow.update_results
        """

        self._data_to_export = dict_results

