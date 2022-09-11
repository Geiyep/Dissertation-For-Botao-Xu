from datetime import datetime
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import linregress
import sys


# Decision making

# SPY从200天前开始，close从100天前开始，atr20从100-20=80天前开始，momentum从100-90=10天前开始，都有offset
# offset先处理好，最后都从2016-06-30输入
class strategy():
    # 整个strategy应该从2016-06-30开始
    def __init__(self,risk_factor, company, init_cash, closes, closes_with_date, SPY, SP200, SP100, filtering, momentum, atr20) -> None:
        self.company_name = company
        self.risk_factor = risk_factor
        self.i = 0
        self.cash = init_cash
        self.value = 0
        self.SPY = SPY  #大盘
        self.SP200 = SP200  #大盘200日均线
        self.close = closes_with_date #个股
        self.close_ma100 = SP100    #个股100日均线
        self.close_w_index = closes #个股，以date为index
        self.momentum = momentum    #个股momentum
        self.filtering = filtering
        self.atr20 = atr20  #个股atr20
        self.j = 0
        self.period = list(filtering.keys()) # date checking for seasons
        self.hold_stocks = {} # 持股公司：份额
    
    def get_value(self):
        return self.value

    def get_cash(self):
        return self.cash

    def next(self):
        if self.i %5 == 0: # re-portfolio every 5 working days (1 week)
            self.reportfolio()
        if self.i %10 ==0: # re-position every 10 working days (2 weeks)
            self.reposition()
        self.update_value() # 每日更新value
        self.i += 1
    
    def sell(self, name):
        # sell stocks
        self.cash = self.cash + self.hold_stocks[name]*self.close.loc[self.i][name]
        del self.hold_stocks[name]

    def buy(self, name, size):
        # buy stocks
        if self.cash - size*self.close.loc[self.i][name] > 0:
            self.hold_stocks[name] = size
            self.cash = self.cash - size*self.close.loc[self.i][name]
            return False
        else:
            size = self.cash/self.close.loc[self.i][name]
            self.hold_stocks[name] = size
            self.cash = 0
            return True

    def update_value(self):
        # update total values
        self.value = 0
        for c in list(self.hold_stocks.keys()):
            self.value += self.close.loc[self.i][c]*self.hold_stocks[c]
        self.value += self.cash

    def reportfolio(self):
        # First find filtered companies
        today = self.close.loc[self.i]['Date']
        if self.j == len(self.period)-1:
            filter_companies = self.filtering[self.period[self.j]]
        elif today < self.period[self.j + 1]:
            filter_companies = self.filtering[self.period[self.j]]
        else:
            self.j = self.j + 1
            filter_companies = self.filtering[self.period[self.j]]

        # Second, for every stocks in hold, check if to sell.
        comps = list(self.hold_stocks.keys())
        for c in comps:
            if c not in filter_companies or self.close.loc[self.i][c] < self.close_ma100.loc[self.i][c] or self.SPY.loc[self.i]['close'] < self.SP200.loc[self.i]['close']:
                self.sell(c)

        # Third, determine if to buy
        if self.SPY.loc[self.i]['close'] < self.SP200.loc[self.i]['close']:
            return

        # Forth, determine what to buy
        # Formulate rankings. Check ma100
        rankings = []
        for c in list(self.close_w_index.sort_values(today,1,ascending = False).columns):
            if c in filter_companies and self.close.loc[self.i][c]>=self.close_ma100.loc[self.i][c] and not pd.isnull(self.atr20.loc[self.i][c]) and self.atr20.loc[self.i][c]>0.0001:
                rankings += [c]
        # Buy stocks. Before buying, checking if enough money to buy
        for c in rankings:
            self.update_value()
            size = self.value*self.risk_factor/self.atr20.loc[self.i][c]
            if self.buy(c,size): # which means cash = 0
                return

    def reposition(self):
        # re-balance all stocks
        today = self.close.loc[self.i]['Date']
        if self.j == len(self.period)-1:
            filter_companies = self.filtering[self.period[self.j]]
        elif today < self.period[self.j + 1]:
            filter_companies = self.filtering[self.period[self.j]]
        else:
            self.j = self.j + 1
            filter_companies = self.filtering[self.period[self.j]]

        if self.SPY.loc[self.i]['close'] < self.SP200.loc[self.i]['close']:
            return
        
        for c in list(self.hold_stocks.keys()):
            self.sell(c)

        rankings = []
        for c in list(self.close_w_index.sort_values(today,1,ascending = False).columns):
            if c in filter_companies and self.close.loc[self.i][c]>=self.close_ma100.loc[self.i][c] and not pd.isnull(self.atr20.loc[self.i][c]) and self.atr20.loc[self.i][c]>0.0001:
                rankings += [c]
        # Buy stocks. Before buying, checking if enough money to buy
        for c in rankings:
            self.update_value()
            size = self.value*self.risk_factor/self.atr20.loc[self.i][c]
            if self.buy(c,size): # which means cash = 0
                return


if __name__ == '__main__':

    # read data for filter
    net_prof = pd.read_excel("netprofitmagin.xlsx")
    gross_prof = pd.read_excel("grossprofitmagin.xlsx")
    roe = pd.read_excel("roe4season.xlsx")
    net_prof.set_index("Date",inplace=True)
    gross_prof.set_index("Date",inplace=True)
    roe.set_index("Date",inplace=True)

    # filter
    company = [i for i in net_prof.columns]
    month_dates = [i for i in net_prof.index]
    results = {}
    for date in month_dates:
        result = []
        for c in company:
            if not pd.isnull(net_prof.loc[date][c]) and not pd.isnull(gross_prof.loc[date][c]) and not pd.isnull(roe.loc[date][c]):
                if net_prof.loc[date][c] > 10 and roe.loc[date][c]>10 and gross_prof.loc[date][c]> 20:
                    result = result + [c]
        results[date] = result
        #print(date)
        #print(len(result))
        #print(result)

    # read data for decision
    closes = pd.read_excel("closes.xlsx")
    closes.set_index("Date",inplace=True)
    closes_with_date = pd.read_excel("closes.xlsx")

    atr20 = pd.read_excel("atr20.xlsx")
    momentums = pd.read_excel("momentums.xlsx")
    sma100 = pd.read_excel("sma100.xlsx")
    sma200 = pd.read_excel("sma200.xlsx")
    spya = pd.read_excel("SPYA.xlsx")

    # decision making
    risk_factor = 0.001 # 0.1%, which is 10 basis points
    init_cash = 100000

    behavior = strategy(risk_factor, company, init_cash, closes, closes_with_date, spya, sma200, sma100, results, momentums, atr20)
    profit = spya.copy(deep=True)
    cash = spya.copy(deep=True)
    # plt.figure(figsize = (12,9))
    # plt.xlabel('Days')
    # plt.ylabel('Profits')
    # x = np.arange(len(closes))
    for i in range(len(closes)):
        behavior.next()
        profit[i,'close'] = behavior.get_value
        cash[i,'close'] = behavior.get_cash
    print("Great")
    # plt.plot(x, spya['close'], color = 'r')
    # plt.plot(x, profit['close'], color = 'g')
    # plt.plot(x, cash['close'],color = 'b')

