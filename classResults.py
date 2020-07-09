import numpy as np

from collections import OrderedDict

import funcMisc


class TradesResults(dict):

    """
       Class with method to calculates
       summary and equity plots about trades
    """

    def __init__(self):

        self.dict_results = dict

    def calculate_result(self, *args, **kwargs):

        """
        Calculate summary about trades. For infos calculated
        see summary_headers. Summary can be in points,
        points/lot, % or currency Return a dict with formatted
        string and a dict with np array to plot equity curves
        transactions and start_capital can be modified by
        user's choices so they are returned too

        :kw param transactions: OredredDict with transactions

        :kw param cash_available: string cash
                  available on current account

        :kw param start_capital: float capital initial set by user

        :kw param screenshot: boolean inform if screenshot is being
                             taken to properly format infos
        """

        transactions = kwargs["transactions"]
        cash_available = float(kwargs["cash_available"])
        start_capital = kwargs["start_capital"]
        screenshot = kwargs["screenshot"]

        config = funcMisc.read_config()  # load config file
        currency_symbol = config["currency_symbol"]
        result_in = config["result_in"]
        auto_calculate = config["auto_calculate"]
        include = config["include"]
        state_filter = config["all"]
        state_infos = config["what_to_show"]["state_infos"]

        summary_headers = [
            "Points won",
            "Trades won",
            "Points lost",
            "Trades lost",
            "Total points",
            "Trades flat",
            "Total trades",
            "Avg trade",
            "Profit Factor",
            "Avg win",
            "Capital growth",
            "Avg loss",
            "Max drawdown",
            "Avg drawdown",
            "Consec. wins",
            "Consec. losses",
            "Interests",
            "Fees",
            "Cash in/out",
            "Transfers",
        ]  # same lis as the one used to create dock

        ig_config = funcMisc.read_ig_config()

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

        summary_dict = OrderedDict()

        # -------------------------start precalculation-------------------------

        # calculate all internal funds transfer
        transfer_list = [
            float(transactions[trade]["pnl"])
            for trade in transactions.keys()
            if transactions[trade]["type"] == "TRANSFER"
        ]

        total_transfer = round(sum(transfer_list), 2)  # interaccount transfer

        cashin_list = [
            float(transactions[trade]["pnl"])
            for trade in transactions.keys()
            if transactions[trade]["type"] == "CASHIN"
        ]

        total_cashin = round(sum(cashin_list), 2)  # user"s deposit

        cashout_list = [
            float(transactions[trade]["pnl"])
            for trade in transactions.keys()
            if transactions[trade]["type"] == "CASHOUT"
        ]

        total_cashout = round(sum(cashout_list), 2)  # user"s withdrawal

        # build list with interest pnl
        interest_list = [
            float(transactions[trade]["pnl"])
            for trade in transactions.keys()
            if transactions[trade]["type"] == "WITH"
            or transactions[trade]["type"] == "DEPO"
            or transactions[trade]["type"] == "DIVIDEND"
        ]

        total_interest = round(sum(interest_list), 2)

        # build list with fees pnl
        fee_list = [
            float(transactions[trade]["pnl"])
            for trade in transactions.keys()
            if transactions[trade]["type"] == "CHART"
        ]

        total_fee = round(sum(fee_list), 2)

        # calculate total pnl to determine start capital
        if transactions:
            total_pnl = sum(
                float(transactions[deal_id]["pnl"]) for deal_id in transactions.keys()
            )

            # pnl minus funds transfert
            if include == 2:
                total_pnl = total_pnl - (total_cashin + total_cashout + total_transfer)

            # pnl minus funds transfert and fees/interest
            else:
                total_pnl = total_pnl - (
                    total_cashin
                    + total_cashout
                    + total_transfer
                    + total_fee
                    + total_interest
                )

        else:  # no data returns empy dict

            for count, header in enumerate(summary_headers):
                summary_dict[header] = ""

            curve_args = {
                "transactions": transactions,
                "start_capital": start_capital,
                "config": config,
            }

            curves_dict = self.create_curves(**curve_args)

            dict_results = {
                "summary": summary_dict,
                "start_capital": start_capital,
                "transactions": transactions,
                "curves_dict": curves_dict,
            }

            return dict_results

        # determine start capital according to user's choice
        if auto_calculate == 2:
            start_capital = cash_available - total_pnl
            capital = start_capital

        else:
            cash_available = float(start_capital) + total_pnl
            capital = start_capital

        # calculate growth according to start capital
        for count, deal_id in enumerate(transactions.keys()):

            # add nothing if trade is fund transfer
            if (
                transactions[deal_id]["type"] == "TRANSFER"
                or transactions[deal_id]["type"] == "CASHIN"
                or transactions[deal_id]["type"] == "CASHOUT"
            ):
                pnl = 0
            else:
                pnl = float(transactions[deal_id]["pnl"])
                capital += pnl  # substract every pnl to cash available

            # recalculate growth
            try:
                growth = round(
                    ((capital - start_capital) / float(start_capital)) * 100, 2
                )
            except ZeroDivisionError:
                growth = 0

            # change growth key in transactions
            transactions[deal_id]["growth"] = str(growth)

        # build list with pnl in currency
        pnl_currency_list = [
            float(transactions[trade]["pnl"])
            for trade in transactions.keys()
            if transactions[trade]["type"] in kw_order
        ]

        # build list with pnl in points
        points_list = [
            float(transactions[trade]["points"])
            for trade in transactions.keys()
            if transactions[trade]["type"] in kw_order
        ]

        # build list with pnl in points/lot
        points_lot_list = [
            float(transactions[trade]["points_lot"])
            for trade in transactions.keys()
            if transactions[trade]["type"] in kw_order
        ]

        # lists with pnl in currency
        pnl_won_list = [pnl for pnl in pnl_currency_list if pnl > 0]
        pnl_loss_list = [pnl for pnl in pnl_currency_list if pnl < 0]
        pnl_flat_list = [pnl for pnl in pnl_currency_list if pnl == 0]

        # list with pnl in points
        points_won_list = [points for points in points_list if points > 0]
        points_loss_list = [points for points in points_list if points < 0]

        # list with won in points/lot
        points_lot_won_list = [
            points_lot for points_lot in points_lot_list if points_lot > 0
        ]

        points_lot_loss_list = [
            points_lot for points_lot in points_lot_list if points_lot < 0
        ]

        money_won = sum(pnl_won_list)
        money_lost = sum(pnl_loss_list)

        """
        if users want to calculate summary with
        all profit/loss including fess/interest
        """

        if include == 2:
            total_pnl_currency = round(
                (money_won + money_lost + total_interest + total_fee), 2
            )

            if total_interest > 0:
                money_won = round(money_won + total_interest, 2)
            else:
                money_lost = round(money_lost + total_interest + total_fee, 2)

        else:

            # calculate totals in currency
            total_pnl_currency = round((money_won + money_lost), 2)
            money_won = round(money_won, 2)
            money_lost = round(money_lost, 2)

        # stats in points
        points_lost = sum(points_loss_list)
        points_won = sum(points_won_list)
        total_pnl = round((points_won + points_lost), 2)

        # stats in points/lot
        points_lot_lost = sum(points_lot_loss_list)
        points_lot_won = sum(points_lot_won_list)
        total_pnl_lot = round((points_lot_won + points_lot_lost), 2)

        # stats about nb trades
        nb_trades = float(len(pnl_currency_list))
        nb_trades_flat = float(len(pnl_flat_list))
        nb_trades_lost = float(len(pnl_loss_list))
        nb_trades_won = float(len(pnl_won_list))

        i = 0
        j = 0
        conseq_won_list = []
        conseq_loss_list = []

        # stats about consequtive win/loss
        for pnl in pnl_currency_list:
            conseq_loss = 0
            conseq_won = 0
            j = 0

            try:
                pnl = pnl_currency_list[i]  # get pnl
            except IndexError:
                break

            if pnl > 0:

                try:
                    while pnl > 0:
                        conseq_won += 1  # increment conseq wons
                        j += 1
                        pnl = pnl_currency_list[i + j]  # get next pnl
                    conseq_won_list.append(conseq_won)
                    i += j  # get pnl after last won

                except IndexError:
                    conseq_won_list.append(conseq_won)  # r eached end of list
                    i = j - 1

            elif pnl < 0:

                try:
                    while pnl < 0:
                        conseq_loss += 1  # increment conseq losses
                        j += 1
                        pnl = pnl_currency_list[i + j]  # get next pnl
                    conseq_loss_list.append(conseq_loss)
                    i += j  # get pnl after last loss

                except IndexError:
                    conseq_loss_list.append(conseq_loss)  # reached end of list
                    i = j - 1

            elif pnl == 0:
                i += 1  # trade flat get next one

        try:
            conseq_won = max(conseq_won_list)
        except ValueError:  # empty list (no won)
            conseq_won = 0

        try:
            conseq_loss = max(conseq_loss_list)  # empty list (no losses)
        except ValueError:
            conseq_loss = 0

        # manage zero division error
        try:
            profit_factor = abs(round(money_won / money_lost, 2))
        except ZeroDivisionError:
            profit_factor = "N/A"

        try:
            per_cent_trades_won = round((nb_trades_won / nb_trades) * 100, 2)
        except ZeroDivisionError:
            per_cent_trades_won = "N/A"

        try:
            per_cent_trades_lost = round((nb_trades_lost / nb_trades) * 100, 2)
        except ZeroDivisionError:
            per_cent_trades_lost = "N/A"

        try:
            per_cent_trades_flat = round((nb_trades_flat / nb_trades) * 100, 2)
        except ZeroDivisionError:
            per_cent_trades_flat = "N/A"

        try:
            growth = round(
                (cash_available - start_capital) / float(start_capital) * 100, 2
            )
        except ZeroDivisionError:
            growth = "N/A"

        # --------------------------end precalculation--------------------------

        # ------------------------start main calculation------------------------

        if result_in != "%" and result_in != "Points" and result_in != "Points/lot":
            result_in = "currency"

        if result_in == "Points":
            total_in = total_pnl
            won_in = points_won
            loss_in = points_lost

            # prepare dd calculation
            pnl_array = np.insert(np.asfarray(points_list), 0, 0)
            pnl_cumsum = np.cumsum(pnl_array)

            dd_array = np.maximum.accumulate(pnl_cumsum) - pnl_cumsum
            dd_to_list = np.ndarray.tolist(dd_array)
            dd_list = [dd for dd in dd_to_list if dd > 0]

            """
            force interest and fees to be displayed
            in currency as points are not available
            """

            interest_text = str(total_interest) + " " + currency_symbol
            fee_text = str(total_fee) + " " + currency_symbol

            result_in = "pts"  # prettier string for result_in

        elif result_in == "Points/lot":

            try:
                total_in = round(total_pnl_lot / nb_trades, 2)
            except ZeroDivisionError:
                total_in = 0

            try:
                won_in = round(points_lot_won / nb_trades_won, 2)
            except ZeroDivisionError:
                won_in = 0

            try:
                loss_in = round(points_lot_lost / nb_trades_lost, 2)
            except ZeroDivisionError:
                loss_in = 0

            # prepare dd calculation
            pnl_array = np.insert(np.asfarray(points_lot_list), 0, 0)
            pnl_cumsum = np.cumsum(pnl_array)

            dd_array = np.maximum.accumulate(pnl_cumsum) - pnl_cumsum
            dd_to_list = np.ndarray.tolist(dd_array)
            dd_list = [dd for dd in dd_to_list if dd > 0]

            """
            force interest and fees to be displayed
            in currency as points are not available
            """

            interest_text = str(total_interest) + " " + currency_symbol
            fee_text = str(total_fee) + " " + currency_symbol

            result_in = "pts/lot"  # prettier string for result_in

        elif result_in == "currency":
            total_in = total_pnl_currency
            won_in = money_won
            loss_in = money_lost

            # prepare dd calculation
            pnl_array = np.insert(np.asfarray(pnl_currency_list), 0, 0)
            pnl_cumsum = np.cumsum(pnl_array)

            dd_array = np.maximum.accumulate(pnl_cumsum) - pnl_cumsum
            dd_to_list = np.ndarray.tolist(dd_array)
            dd_list = [dd for dd in dd_to_list if dd > 0]

            interest_text = str(total_interest) + " " + currency_symbol
            fee_text = str(total_fee) + " " + currency_symbol

            result_in = currency_symbol  # prettier string for result_in

        elif result_in == "%":

            # prepare dd calculation
            pnl_array = np.insert(np.asfarray(pnl_currency_list), 0, 0)
            pnl_cumsum = np.cumsum(pnl_array)
            dd_array = np.maximum.accumulate(pnl_cumsum) - pnl_cumsum
            dd_to_list = np.ndarray.tolist(dd_array)
            dd_list = [dd for dd in dd_to_list if dd > 0]

            try:
                max_dd = np.amax(dd_array)  # first calculate max_dd in money
            except ValueError:
                max_dd = 0

            # calculate dd in %
            try:
                per_cent_avg_dd = round(
                    (float(sum(dd_list)) / len(dd_list)) / float(start_capital) * 100, 2
                )
                per_cent_max_dd = round(max_dd / float(start_capital) * 100, 2)

            except RuntimeWarning:
                per_cent_max_dd = 0
                per_cent_avg_dd = 0

            except ZeroDivisionError:
                per_cent_max_dd = 0
                per_cent_avg_dd = 0

            try:
                total_in = round(total_pnl_currency / float(start_capital) * 100, 2)
                won_in = round(money_won / float(start_capital) * 100, 2)
                loss_in = round(money_lost / float(start_capital) * 100, 2)

                total_interest = round((total_interest / start_capital) * 100, 2)
                total_fee = round((total_fee / start_capital) * 100, 2)

            except ZeroDivisionError:
                total_in = 0
                won_in = 0
                loss_in = 0
                total_interest = 0
                total_fee = 0

            interest_text = str(total_interest) + " " + "%"
            fee_text = str(total_fee) + " " + "%"

            """
            set dummy array to force TypeError. I prefer doing
            that way to avoid too much if/else statements
            """

            dd_array = ""

        # calculate avg values
        try:
            avg_trade = round((total_in / nb_trades), 2)
        except ZeroDivisionError:
            avg_trade = 0

        try:
            avg_won = round((won_in / nb_trades_won), 2)
        except ZeroDivisionError:
            avg_won = 0

        try:
            avg_loss = round((loss_in / nb_trades_lost), 2)
        except ZeroDivisionError:
            avg_loss = 0

        try:
            max_dd = np.amax(dd_array)

            try:
                avg_dd = round(float(sum(dd_list)) / len(dd_list), 2)
            except ZeroDivisionError:  # means 0 loss
                avg_dd = 0

        except TypeError:  # means result is in %
            max_dd = per_cent_max_dd
            avg_dd = per_cent_avg_dd

        except ValueError:
            max_dd = 0
            avg_dd = 0
        # -------------------------end main calculation-------------------------

        # add result_in to strings
        if max_dd != 0:
            max_dd_text = str(-max_dd) + " " + result_in
            avg_dd_text = str(-avg_dd) + " " + result_in
        else:
            max_dd_text = str(max_dd) + " " + result_in
            avg_dd_text = str(avg_dd) + " " + result_in

        avg_trade_text = str(avg_trade) + " " + result_in
        avg_won_text = str(avg_won) + " " + result_in
        avg_loss_text = str(avg_loss) + " " + result_in

        # add % values in parenthesis
        nb_trades_won_text = (
            str(nb_trades_won) + " (" + str(per_cent_trades_won) + "%" + ")"
        )

        nb_trades_loss_text = (
            str(nb_trades_lost) + " (" + str(per_cent_trades_lost) + "%" + ")"
        )

        nb_trades_flat_text = (
            str(nb_trades_flat) + " (" + str(per_cent_trades_flat) + "%" + ")"
        )

        # for important values add a color scheme
        profit_color = config["profit_color"]
        flat_color = config["flat_color"]
        loss_color = config["loss_color"]

        if total_in > 0:
            total_color = profit_color
        elif total_in == 0:
            total_color = flat_color
        elif total_in < 0:
            total_color = loss_color

        total_in_text = (
            '<span style="color:'
            + total_color
            + '">'
            + str(total_in)
            + " "
            + result_in
            + "</span>"
        )

        won_in_text = str(won_in) + " " + result_in
        loss_in_text = str(loss_in) + " " + result_in

        if str(growth) == "N/A":
            growth_text = str(growth)

        else:

            if growth > 0:
                growth_color = profit_color
            elif growth == 0:
                growth_color = flat_color
            elif growth < 0:
                growth_color = loss_color

            growth_text = (
                '<span style="color:' + growth_color + '">' + str(growth) + " %</span>"
            )

        """
        Hide infos about money if user wants. If a screenshot
        is being taken hide it according to user choice
        """

        if (
            state_infos == "Always"
            and result_in != currency_symbol
            or state_infos == "Only for screenshot"
            and screenshot == True
            and result_in != currency_symbol
        ):
            growth_text = "xx%"

            # format funds transfer strings
            total_cash_text = "xxxx" + currency_symbol + "/" + "xxxx" + currency_symbol
            total_transfer_text = "xxxx" + currency_symbol

            if "pts" in result_in:
                interest_text = "xxxx" + currency_symbol
                fee_text = "xxxx" + currency_symbol

        else:
            growth_text = growth_text
            total_cash_text = (
                str(total_cashin)
                + currency_symbol
                + "/"
                + str(total_cashout)
                + currency_symbol
            )
            total_transfer_text = str(total_transfer) + currency_symbol

        curve_args = {
            "transactions": transactions,
            "start_capital": start_capital,
            "config": config,
        }

        # creates curves for equity plot
        scatter_curves = self.create_curves(**curve_args)

        # list with all infos calculated
        summary_list = [
            won_in_text,
            nb_trades_won_text,
            loss_in_text,
            nb_trades_loss_text,
            total_in_text,
            nb_trades_flat_text,
            str(nb_trades),
            avg_trade_text,
            str(profit_factor),
            avg_won_text,
            growth_text,
            avg_loss_text,
            max_dd_text,
            avg_dd_text,
            str(conseq_won),
            str(conseq_loss),
            interest_text,
            fee_text,
            total_cash_text,
            total_transfer_text,
        ]

        summary_dict = OrderedDict()

        for count, header in enumerate(summary_headers):
            summary_dict[header] = summary_list[count]  # populate summary dict

        dict_results = {
            "summary": summary_dict,
            "start_capital": start_capital,
            "transactions": transactions,
            "curves_dict": scatter_curves,
        }

        return dict_results

    def create_curves(*args, **kwargs):

        """
           Function to build scatterplot representing
           max dd, depth and high and equity curves
           Returns a dict buil correspond to 'curve'
           subkey in graph_dict (see classIGReport)
           {nameofthegraph: {equity_curve: np.array,
                             high: np.array,
                             depth: np.array,
                             maxdd: np.array;
                            }
            }

           :kw param transactions: OrderedDict() of all trades
           :kw param start_capital: float
           :kw param config: dict with config saved
        """

        transactions = kwargs["transactions"]
        start_capital = kwargs["start_capital"]

        config = kwargs["config"]
        include = config["include"]
        result_in = config["result_in"]
        ig_config = funcMisc.read_ig_config()

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

        plot_available = ["high", "depth", "maxdd"]  # type of scatter

        states_plot = []

        # list with state of scatter to plot( show it or not)
        for plot in plot_available:
            state = config["what_to_show"][plot]
            states_plot.append(state)

        scatter_dict = {}

        """
        keys correspond to those in transactions lists are
        used to acces to correct data in transactions
        """

        if result_in == "Points/lot":
            scatter_type = ["points_lot", "pnl", "growth"]
        else:
            scatter_type = ["points", "pnl", "growth"]

        graph_name = ["Points", "Capital", "Growth"]  # tab names

        for index, scatter in enumerate(scatter_type):

            if not transactions:  # returns empty curves if no data
                scatter_data = {
                    "equity_curve": np.array([]),
                    "maxdd": (np.array([]), np.array([])),
                    "depth": (np.array([]), np.array([])),
                    "high": (np.array([]), np.array([])),
                }
                scatter_dict[graph_name[index]] = scatter_data

            else:

                # means we have to care about fees/interest
                if graph_name[index] != "Points":

                    if include == 2:
                        pnl_list = [
                            float(transactions[trade][scatter])
                            for trade in transactions.keys()
                            if transactions[trade]["type"] in kw_order
                            or transactions[trade]["type"] in kw_fees
                        ]

                    # exclude interest/fees
                    else:
                        pnl_list = [
                            float(transactions[trade][scatter])
                            for trade in transactions.keys()
                            if transactions[trade]["type"] in kw_order
                        ]

                    # pnl_list = [0,-10, 5,2,3,8,-25,54]    #dummy curves to test

                    if graph_name[index] == "Capital":

                        # insert start capital
                        if len(pnl_list) != 0:
                            pnl_list.insert(0, float(start_capital))

                        pnl_array = np.asfarray(pnl_list)
                        pnl_cumsum = np.cumsum(pnl_array)

                    else:
                        if len(pnl_list) != 0:
                            pnl_list.insert(0, 0)

                        pnl_array = np.asfarray(pnl_list)
                        pnl_cumsum = pnl_array  # don"t cumsum if growth

                else:  # we don"t care about fees/interest
                    pnl_list = [
                        float(transactions[trade][scatter])
                        for trade in transactions.keys()
                        if transactions[trade]["type"] in kw_order
                    ]

                    # pnl_list = [0,-10, 5,2,3,8,-25,54]    #dummy curves to test

                    if len(pnl_list) != 0:
                        pnl_list.insert(0, 0)

                    pnl_array = np.asfarray(pnl_list)
                    pnl_cumsum = np.cumsum(pnl_array)

                """
                find new hight in pnl_list. new higth is when
                a value isgreater than all the previous ones
                """

                dd_array = np.maximum.accumulate(pnl_cumsum) - pnl_cumsum
                idx_high = [
                    count for count, high in enumerate(dd_array) if dd_array[count] == 0
                ]

                # list of all hights on equity curves
                list_high = [pnl_cumsum[idx] for idx in idx_high]

                # del the first idx, not a trade
                if 0 in idx_high:
                    del idx_high[0]
                    del list_high[0]

                list_depth = []
                idx_depth = []
                i = 0
                j = 0

                """
                Find depth in pnl_list. depth is the
                smallest value between two hights
                """

                for dd in dd_array:

                    try:
                        dd = dd_array[j]
                    except IndexError:  # reach end of the array
                        break

                    if dd == 0.0:  # means new high an equity curve ascending
                        j += 1  # continue iteration

                    # when equity curve is descending (dd != 0) find the
                    # ext dd == 0, meaning a new high has been made
                    else:

                        try:
                            i = 1
                            while dd != 0:

                                # get next dd starting from last high
                                dd = dd_array[j + i]
                                i += 1

                            # isolate the depth in equity curve
                            current_depth = pnl_cumsum[j : j + i - 1]
                            list_depth.append(min(current_depth))

                            # get index of min
                            idx_min = np.argmin(current_depth) + j
                            idx_depth.append(idx_min)

                            # we continue iteration from the end of depth
                            j = j + i

                        except IndexError:  # reach end of the array
                            break

                try:
                    idx_max_dd = [np.argmax(dd_array)]

                    if graph_name[index] == "Capital":
                        max_dd = [pnl_cumsum[idx_max_dd[0]]]
                    else:
                        max_dd = pnl_cumsum[idx_max_dd]

                except ValueError:
                    idx_max_dd = np.array([])
                    max_dd = np.array([])

                # when growth is not revelent send empty curves
                if start_capital == 0 and graph_name[index] == "Growth":
                    scatter_data = {
                        "equity_curve": np.array([]),
                        "maxdd": (np.array([]), np.array([])),
                        "depth": (np.array([]), np.array([])),
                        "high": (np.array([]), np.array([])),
                    }

                else:
                    # order matters to keep max dd visible
                    scatter_data = OrderedDict(
                        {
                            "equity_curve": pnl_cumsum,
                            "high": (idx_high, list_high),
                            "depth": (idx_depth, list_depth),
                            "maxdd": (idx_max_dd, max_dd),
                        }
                    )

                scatter_dict[graph_name[index]] = scatter_data

        return scatter_dict
