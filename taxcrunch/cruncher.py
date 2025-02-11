import json
import os
import numpy as np
import pandas as pd
import taxcalc as tc

from paramtools import Parameters

CURRENT_PATH = os.path.abspath(os.path.dirname(__file__))


class CruncherParams(Parameters):

    defaults = os.path.join(CURRENT_PATH, "defaults.json")


class Cruncher:
    """
    Constructor for the Cruncher class

    Parameters
    ----------
    file: file path to input adjustment file
        The default is cruncher/adjustment_template.json.

    custom_reform: file path to optional json policy reform file
        If you choose to specify a custom reform (as opposed to the
        preset reforms in the Tax-Calculator repo), change the adjustment
        file 'reform_options' field to 'Custom' and specify the file path
        in this argument

    Returns
    -------
    class instance: Cruncher

    Notes
    -----
    The most efficient way to use the Cruncher class is to select a preset policy reform
    from the 'reform_options' field in 'defaults.json', then fill out 'adjustment_template.json'
    with your individual data and chosen reform. Create a class instance with c = Cruncher() and
    test out the following methods:

        c.basic_table()
        c.mtr_table()
        c.calc_table()
        c.calc_diff_table()

    """

    def __init__(
        self, inputs="adjustment_template.json", custom_reform=None, baseline=None
    ):
        self.inputs = inputs
        self.custom_reform = custom_reform
        self.baseline = baseline
        self.params = CruncherParams()
        self.adjustment = self.adjust_inputs()
        self.params.adjust(self.adjustment)
        self.ivar, self.mtr_options, self.reform_options = self.taxsim_inputs()
        self.data = self.translate(self.ivar)
        self.ivar2, self.mtr_wrt = self.choose_mtr()
        self.data_mtr = self.translate(self.ivar2)
        self.pol = self.choose_baseline()
        self.pol2 = self.choose_reform()
        self.calc1, self.calc_reform, self.calc_mtr = self.run_calc()
        self.df_basic_vals = self.basic_vals()
        self.df_mtr = self.mtr_table()
        self.df_calc = self.calc_table()

    def adjust_inputs(self):
        """
        Adjust inputs based on 'adjustment_template.json' or a different specified json file
        """
        CURRENT_PATH = os.path.abspath(os.path.dirname(__file__))
        if isinstance(self.inputs, str):
            self.adjustment = os.path.join(CURRENT_PATH, self.inputs)
        else:
            self.adjustment = self.inputs
        return self.adjustment

    def taxsim_inputs(self):
        """
        Iterates through params object to extract parameter values

        Returns:
            self.ivar: a Pandas dataframe with Taxsim-style variables
            self.mtr_options: a string with the user's choice of how to calculate marginal tax rates
            self.reform_options: a string with the user's choice of reform

        """
        for param in self.params.RECID:
            RECID = param["value"]
        for param in self.params.year:
            year = param["value"]
        for param in self.params.mstat:
            if param["value"] == "Single":
                mstat = 1
            elif param["value"] == "Joint":
                mstat = 2
        for param in self.params.page:
            page = param["value"]
        for param in self.params.sage:
            sage = param["value"]
        for param in self.params.depx:
            depx = param["value"]
        for param in self.params.dep13:
            dep13 = param["value"]
        for param in self.params.dep17:
            dep17 = param["value"]
        for param in self.params.dep18:
            dep18 = param["value"]
        for param in self.params.pwages:
            pwages = param["value"]
        for param in self.params.swages:
            swages = param["value"]
        for param in self.params.dividends:
            dividends = param["value"]
        for param in self.params.intrec:
            intrec = param["value"]
        for param in self.params.stcg:
            stcg = param["value"]
        for param in self.params.ltcg:
            ltcg = param["value"]
        for param in self.params.otherprop:
            otherprop = param["value"]
        for param in self.params.nonprop:
            nonprop = param["value"]
        for param in self.params.pensions:
            pensions = param["value"]
        for param in self.params.gssi:
            gssi = param["value"]
        for param in self.params.ui:
            ui = param["value"]
        for param in self.params.proptax:
            proptax = param["value"]
        for param in self.params.otheritem:
            otheritem = param["value"]
        for param in self.params.childcare:
            childcare = param["value"]
        for param in self.params.mortgage:
            mortgage = param["value"]
        for param in self.params.mtr_options:
            self.mtr_options = param["value"]
        for param in self.params.reform_options:
            self.reform_options = param["value"]

        ts_vars = [
            RECID,
            year,
            mstat,
            page,
            sage,
            depx,
            dep13,
            dep17,
            dep18,
            pwages,
            swages,
            dividends,
            intrec,
            stcg,
            ltcg,
            otherprop,
            nonprop,
            pensions,
            gssi,
            ui,
            proptax,
            otheritem,
            childcare,
            mortgage,
        ]

        ts_values = []
        for ts_var in ts_vars:
            ts_values.append(ts_var)

        array_var = np.asarray(ts_values)
        self.ivar = pd.DataFrame(array_var.reshape(1, len(array_var)))
        self.ivar = self.ivar.astype(int)
        return self.ivar, self.mtr_options, self.reform_options

    def translate(self, ivar):
        """
        Translate TAXSIM-27 input variables into Tax-Calculator input variables.

        Returns:
            self.invar: a Pandas dataframe with Tax-Calculator variables
        """
        self.invar = pd.DataFrame()
        self.invar["RECID"] = ivar.loc[:, 0]
        self.invar["FLPDYR"] = ivar.loc[:, 1]
        # no Tax-Calculator use of TAXSIM variable 3, state code
        mstat = ivar.loc[:, 2]
        self.invar["age_head"] = ivar.loc[:, 3]
        self.invar["age_spouse"] = ivar.loc[:, 4]
        num_deps = ivar.loc[:, 5]
        mars = np.where(mstat == 1, np.where(num_deps > 0, 4, 1), 2)
        assert np.all(np.logical_or(mars == 1,
                                np.logical_or(mars == 2, mars == 4)))
        self.invar["MARS"] = mars
        self.invar["f2441"] = ivar.loc[:, 6]
        self.invar["n24"] = ivar.loc[:, 7]
        num_eitc_qualified_kids = ivar.loc[:, 8]
        self.invar["EIC"] = np.minimum(num_eitc_qualified_kids, 3)
        num_taxpayers = np.where(mars == 2, 2, 1)
        self.invar["XTOT"] = num_taxpayers + num_deps
        self.invar["e00200p"] = ivar.loc[:, 9]
        self.invar["e00200s"] = ivar.loc[:, 10]
        self.invar["e00200"] = self.invar["e00200p"] + self.invar["e00200s"]
        self.invar["e00650"] = ivar.loc[:, 11]
        self.invar["e00600"] = self.invar["e00650"]
        self.invar["e00300"] = ivar.loc[:, 12]
        self.invar["p22250"] = ivar.loc[:, 13]
        self.invar["p23250"] = ivar.loc[:, 14]
        self.invar["e02000"] = ivar.loc[:, 15]
        self.invar["e00800"] = ivar.loc[:, 16]
        self.invar["e01700"] = ivar.loc[:, 17]
        self.invar["e01500"] = self.invar["e01700"]
        self.invar["e02400"] = ivar.loc[:, 18]
        self.invar["e02300"] = ivar.loc[:, 19]
        # no Tax-Calculator use of TAXSIM variable 22, non-taxable transfers
        # no Tax-Calculator use of TAXSIM variable 23, rent paid
        self.invar["e18500"] = ivar.loc[:, 20]
        self.invar["e18400"] = ivar.loc[:, 21]
        self.invar["e32800"] = ivar.loc[:, 22]
        self.invar["e19200"] = ivar.loc[:, 23]
        return self.invar

    def choose_mtr(self):
        """
        Creates data to analyze marginal tax rates by adding $1 to the type
            of income specified in 'mtr_options'

        Returns:
            self.ivar2: a Pandas dataframe with Taxsim-style variables
            self.mtr_wrt: User's choice for MTR analysis as a Tax-Calculator variable
        """
        self.ivar2 = self.ivar.copy()
        if self.mtr_options == "Taxpayer Earnings":
            self.ivar2.loc[:, 9] = self.ivar2.loc[:, 9] + 1
            self.mtr_wrt = "e00200p"
            return self.ivar2, self.mtr_wrt
        elif self.mtr_options == "Spouse Earnings":
            self.ivar2.loc[:, 10] = self.ivar2.loc[:, 10] + 1
            return self.ivar2, "e00200s"
        elif self.mtr_options == "Short Term Gains":
            self.ivar2.loc[:, 13] = self.ivar2.loc[:, 13] + 1
            return self.ivar2, "p22250"
        elif self.mtr_options == "Long Term Gains":
            self.ivar2.loc[:, 14] = self.ivar2.loc[:, 14] + 1
            return self.ivar2, "p23250"
        elif self.mtr_options == "Qualified Dividends":
            self.ivar2.loc[:, 11] = self.ivar2.loc[:, 11] + 1
            return self.ivar2, "e00650"
        elif self.mtr_options == "Interest Received":
            self.ivar2.loc[:, 12] = self.ivar2.loc[:, 12] + 1
            return self.ivar2, "e00300"
        elif self.mtr_options == "Pensions":
            self.ivar2.loc[:, 17] = self.ivar2.loc[:, 17] + 1
            return self.ivar2, "e01700"
        elif self.mtr_options == "Gross Social Security Beneifts":
            self.ivar2.loc[:, 18] = self.ivar2.loc[:, 18] + 1
            return self.ivar2, "e02400"
        elif self.mtr_options == "Real Estate Taxes Paid":
            self.ivar2.loc[:, 20] = self.ivar2.loc[:, 20] + 1
            return self.ivar2, "e18500"
        elif self.mtr_options == "Mortgage":
            self.ivar2.loc[:, 23] = self.ivar2.loc[:, 23] + 1
            return self.ivar2, "e19200"
        elif self.mtr_options == "Don't Bother":
            return self.ivar2, "None"

    def choose_baseline(self):
        """
        Creates Tax-Calculator Policy object for baseline policy

        The default baseline policy is current law.

        Returns:
            self.pol: Tax-Calculator Policy object for baseline policy
        """
        REFORMS_URL = (
            "https://raw.githubusercontent.com/"
            "PSLmodels/Tax-Calculator/master/taxcalc/reforms/"
        )
        CURRENT_PATH = os.path.abspath(os.path.dirname(__file__))

        # if no baseline policy is specified, baseline is current law
        if self.baseline is None:
            self.pol = tc.Policy()
        # if a baseline policy is specified, first see if user created json
        # policy file
        else:
            exists = os.path.isfile(os.path.join(CURRENT_PATH, self.baseline))
            if exists:
                baseline_file = os.path.join(CURRENT_PATH, self.baseline)
                self.pol = tc.Policy()
                self.pol.implement_reform(
                    tc.Policy.read_json_reform(baseline_file))
            # if the user did not create a json file, try the Tax-Calculator
            # reforms file
            else:
                try:
                    baseline_file = self.baseline
                    baseline_url = REFORMS_URL + baseline_file
                    self.pol = tc.Policy()
                    self.pol.implement_reform(tc.Policy.read_json_reform(baseline_url))
                except:
                    print("Baseline file does not exist")

        return self.pol

    def choose_reform(self):
        """
        Creates Tax-Calculator Policy object for reform analysis

        Returns:
            self.pol2: Tax-Calculator Policy object for reform analysis 
        """
        REFORMS_URL = (
            "https://raw.githubusercontent.com/"
            "PSLmodels/Tax-Calculator/master/taxcalc/reforms/"
        )
        CURRENT_PATH = os.path.abspath(os.path.dirname(__file__))

        # if user specified a preset reform in their adjustment file, pull
        # reform from Tax-Calculator reforms folder
        if self.reform_options != "None" and self.custom_reform is None:
            reform_name = self.reform_options
            reform_url = REFORMS_URL + reform_name
            self.pol2 = tc.Policy()
            self.pol2.implement_reform(tc.Policy.read_json_reform(reform_url))
        # otherwise, look for user-provided json reform file
        # first as file path
        elif self.reform_options == "None" and isinstance(self.custom_reform, str):
            try:
                reform_filename = os.path.join(
                    CURRENT_PATH, self.custom_reform)
                self.pol2 = tc.Policy()
                self.pol2.implement_reform(tc.Policy.read_json_reform(reform_filename))
            except:
                print("Reform file path does not exist")
        # then as dictionary
        elif self.reform_options == "None" and isinstance(self.custom_reform, dict):
            try:
                reform = self.custom_reform
                self.pol2 = tc.Policy()
                self.pol2.implement_reform(reform)
            except Exception as e:
                import traceback
                traceback.print_exc()
                print("Reform dictionary does not exist")
        # raise error if preset reform is chosen and custom reform is specified
        elif self.reform_options != "None" and self.custom_reform is not None:
            raise AttributeError(
                "You have specified a preset reform and a custom reform. Please choose one reform."
            )
        # if no reform file was given, set reform to current law
        else:
            self.pol2 = tc.Policy()

        return self.pol2

    def run_calc(self):
        """
        Creates baseline, reform, and + $1 Tax-Calculator objects

        Returns:
            self.calc1: Calculator object for current law
            self.calc_reform: Calculator object for reform
            self.calc_mtr: Calculator object for + $1
        """

        year = self.data.iloc[0][1]
        year = year.item()
        recs = tc.Records(data=self.data, start_year=year)

        self.calc1 = tc.Calculator(policy=self.pol, records=recs)
        self.calc1.advance_to_year(year)
        self.calc1.calc_all()

        self.calc_reform = tc.Calculator(policy=self.pol2, records=recs)
        self.calc_reform.advance_to_year(year)
        self.calc_reform.calc_all()

        recs_mtr = tc.Records(data=self.data_mtr, start_year=year)
        self.calc_mtr = tc.Calculator(policy=self.pol2, records=recs_mtr)
        self.calc_mtr.advance_to_year(year)
        self.calc_mtr.calc_all()

        return self.calc1, self.calc_reform, self.calc_mtr

    def basic_vals(self):
        """
        Creates basic output table

        Returns:
            self.basic_vals: a Pandas dataframe with basic results
        """

        basic = ["iitax", "payrolltax"]
        basic_vals1 = self.calc1.dataframe(basic)
        basic_vals1 = basic_vals1.transpose()

        basic_vals2 = self.calc_reform.dataframe(basic)
        basic_vals2 = basic_vals2.transpose()

        self.basic_vals = pd.concat([basic_vals1, basic_vals2], axis=1)
        self.basic_vals.columns = ["Base", "Reform"]
        self.basic_vals.index = ["Individual Income Tax", "Employee + Employer Payroll Tax"]

        self.basic_vals["Change"] = self.basic_vals[
            "Reform"] - self.basic_vals["Base"]

        self.basic_vals = self.basic_vals.round(2)

        return self.basic_vals

    def mtr_table(self):
        """
        Creates MTR table

        Returns:
            self.df_mtr: a Pandas dataframe MTR results with respect to 'mtr_options'
        """
        if self.mtr_options != "Don't Bother":

            mtr_calc = self.calc1.mtr(calc_all_already_called=True
                                      )
            self.mtr_df = pd.DataFrame(
                data=[mtr_calc[1], mtr_calc[0]],
                index=["Income Tax Marginal Rate", "Payroll Tax Marginal Rate"],
            )

            mtr_calc_reform = self.calc_reform.mtr(calc_all_already_called=True
                                                   )
            mtr_df_reform = pd.DataFrame(
                data=[mtr_calc_reform[1], mtr_calc_reform[0]],
                index=["Income Tax Marginal Rate", "Payroll Tax Marginal Rate"],
            )

            self.df_mtr = pd.concat([self.mtr_df, mtr_df_reform], axis=1)
            self.df_mtr.columns = ["Base", "Reform"]

            self.df_mtr["Change"] = self.df_mtr["Reform"] - self.df_mtr["Base"]

            self.df_mtr = self.df_mtr.round(3)

            return self.df_mtr

        else:
            pass

    def basic_table(self):
        """
        Combines output from basic_vals() and mtr_table() to create table with basic output

        Returns:
            self.df_mtr: a Pandas dataframe with basic output
        """
        self.df_basic = pd.concat(
            [
                self.df_basic_vals.iloc[:1],
                self.df_mtr.iloc[:1],
                self.df_basic_vals.iloc[1:],
                self.df_mtr.iloc[1:],
            ]
        )
        self.df_basic = self.df_basic.round(2)
        return self.df_basic

    def calc_table(self):
        """
        Creates detailed output table

        Returns:
            self.df_calc: a Pandas dataframe with federal tax calculations for base, reform, and + $1

        """
        calculation = [
            "c00100",
            "e02300",
            "c02500",
            "c04470",
            "c04800",
            "taxbc",
            "c07220",
            "c11070",
            "c07180",
            "eitc",
            "c62100",
            "c09600",
            "niit",
            "c05800"
        ]
        labels = [
            "Adjusted Gross Income (AGI)",
            "Unemployment Insurance in AGI",
            "Social Security in AGI",
            "Itemized Deductions",
            "Taxable Income",
            "Regular Tax",
            "Child Tax Credit (CTC)",
            "CTC Refundable",
            "Child Care Credit",
            "Earned Income Tax Credit (EITC)",
            "Alternative Minimum Tax (AMT) Taxable Income",
            "AMT Liability",
            "Net Investment Income Tax",
            "Income Tax Before Credits"
        ]

        df_calc1 = self.calc1.dataframe(calculation).transpose()

        df_calc2 = self.calc_reform.dataframe(calculation).transpose()

        df_calc_mtr = self.calc_mtr.dataframe(calculation).transpose()

        if self.mtr_options == "Don't Bother":
            self.df_calc = pd.concat([df_calc1, df_calc2], axis=1)
            self.df_calc.columns = ["Base", "Reform"]
            self.df_calc.index = labels
        else:
            self.df_calc = pd.concat([df_calc1, df_calc2, df_calc_mtr], axis=1)
            self.df_calc.columns = ["Base", "Reform", "+ $1"]
            self.df_calc.index = labels

        self.df_calc = self.df_calc.round(2)

        return self.df_calc

    def calc_diff_table(self):
        """
        Creates detailed output table. Instead of column for MTR analysis, column displays difference
            between baseline and reform amounts

        Returns:
            self.df_calc_diff: a Pandas dataframe with federal tax calculations for base, reform, and change

        """
        self.df_calc_diff = self.df_calc.copy()
        if len(self.df_calc_diff.columns) == 3:
            del self.df_calc_diff["+ $1"]
        calc_diff_vals = self.df_calc_diff[
            "Reform"] - self.df_calc_diff["Base"]
        self.df_calc_diff["Change"] = calc_diff_vals
        return self.df_calc_diff
