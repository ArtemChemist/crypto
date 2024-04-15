import pandas as pd
import tensorflow as tf

class Asset:
    def __init__(self, ticker):
        self.ticker = ticker
        self.history = pd.DataFrame(columns = ['date_time', 'high', 'low', 'open', 'close', 'volume'])
    
    def latest_price(self):
        return self.history.iloc[-1]['close']
    
    def update_history(self, incoming_df:pd.DataFrame):
        '''
        incoming_df: the dataframe with the new historical records
        '''
        df_to_use = incoming_df[['date_time', 'high', 'low', 'open', 'close', 'volume']]
        self.history.set_index('date_time', inplace=True)
        df_to_use.set_index('date_time', inplace=True)
        self.history = self.history.combine_first(df_to_use)
        self.history.reset_index(inplace=True)
        self.history.sort_values('date_time', ascending=True)


class Portfolio:
    def __init__(self):
        self.assets = {}
        self.value = 0

    def add_asset(self, asset: Asset, qty:float):
        self.assets[asset] = qty

    def get_value(self):
        self.value = sum([asset.latest_price() * qty for asset, qty in self.assets.items()])
        return self.value
    
class Strategy:

    def __init__(self, model):
        self.frequency = 1
        self.model = model

    def backtest(self, hist_data: pd.DataFrame, portfolio: Portfolio):
        updated_portfolio = Portfolio()
        return updated_portfolio




    
