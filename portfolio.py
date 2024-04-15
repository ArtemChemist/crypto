import pandas as pd

class Asset:
    def __init__(self, ticker):
        self.price = 0
        self.ticker = ticker
        self.history = pd.DataFrame(columns = ['date_time', 'high', 'low', 'open', 'close', 'volume'])

    def set_price(self, price):
        self.price = price
    
    def latest_price(self):
        return self.price
    
    def update_history(self, incoming_df:pd.DataFrame):
        '''
        incoming_df: the dataframe with the new historical records
        '''
        df_to_use = incoming_df[['date_time', 'high', 'low', 'open', 'close', 'volume']]
        self.history.set_index('date_time', inplace=True)
        df_to_use.set_index('date_time', inplace=True)
        self.history = self.history.combine_first(df_to_use)
        self.history.reset_index(inplace=True)


class Portfolio:
    def __init__(self):
        self.assets = {}
        self.value = 0

    def add_asset(self, asset: Asset, qty:float):
        self.assets[asset] = qty

    def get_value(self):
        self.value = sum([asset.latest_price() * qty for asset, qty in self.assets.items()])
        return self.value




    
