import pandas as pd
import tensorflow as tf
from datetime import date, timedelta

class Asset:
    asset_dict = {}

    def __init__(self, ticker):
        self.ticker = ticker
        Asset.asset_dict[ticker] = self
        self.history = pd.DataFrame(columns = ['high', 'low', 'open', 'close', 'volume'], index = pd.Index([], name = 'date_time'))
    
    def latest_price(self):
        return self.price_on_date()
    
    def price_on_date(self, on_date = date.today):
        return self.history['close'].loc[on_date]
    
    def update_history(self, incoming_df:pd.DataFrame):
        '''
        incoming_df: the dataframe with the new historical records
        '''
        self.history.update(incoming_df)
        self.history.sort_values('date_time', ascending=True)

class Portfolio:
    def __init__(self, origination_date = date.fromisoformat('2000-01-01'), initial_deposit = 0):
        idx  = pd.MultiIndex(levels=[[],[]],
                          codes=[[],[]],
                          names=[u'date_time', u'ticker'])
        my_columns = [u'change', u'note']
        self.transactions  = pd.DataFrame(index=idx, columns=my_columns)
        self.value = pd.DataFrame(columns = ['value'], index = pd.Index([], name='date_time'))
        self.orig_date = origination_date
        self.update_transactions(transaction_date = origination_date,
                                ticker = 'USD',
                                qty = initial_deposit,
                                note = 'Initial deposit')


    def update_transactions(self, ticker:str, qty:float, transaction_date = date.today(), note = ''):
        self.transactions.loc[(transaction_date,ticker),:] = [qty, note]

    def get_positions(self, on_date = date.today()):
        '''
        Returns portfolio composition on the specified date
        '''
        # First, get the mask for all records before the date
        time_mask= self.transactions.index.get_level_values('date_time')<=on_date
        # Filter the df with this mask, group by ticker
        positions = self.transactions[time_mask]['change'].groupby(level = 'ticker').sum()
        # Convert resulting Series to DataFrame
        positions = pd.DataFrame(positions, index=pd.Index(positions.index, name = 'ticker'))
        positions.columns = ['position_size']
        
        # Add the value in USD by multiplying on the asset price at this date
        positions['position_value'] = positions.index.to_series().apply(
                                                lambda x: Asset.asset_dict[str(x)].price_on_date(on_date)
                                                )
        positions['position_value'] = positions['position_value']*positions['position_size']
        return positions

    def get_value(self, on_date = date.today()):
        self.update_value()
        return self.value.loc[on_date]
    
    def update_value(self):
        #self.value.drop(self.value.index, inplace=True)
        date_to_add = date.fromisoformat('2023-11-30')
        while date_to_add >= self.orig_date:
            composition_at_date = self.get_positions(date_to_add).dropna()
            value_to_add = composition_at_date.position_value.sum()
            self.value.loc[date_to_add] = value_to_add
            date_to_add = date_to_add - timedelta(days=1)

class Strategy:

    def __init__(self, model):
        self.frequency = 1
        self.model = model
    
    def suggest_decision(self, portfolio: Portfolio):
        '''
        Returns a datframe with the suggested updates to portfolio
        '''
        delta_df = pd.DataFrame()
        return delta_df

    def backtest(self, hist_data: pd.DataFrame, portfolio: Portfolio):
        updated_portfolio = Portfolio()
        return updated_portfolio




    
