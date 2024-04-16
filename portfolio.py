import pandas as pd
import tensorflow as tf
from datetime import date, timedelta

class Asset:
    asset_dict = {}

    def __init__(self, ticker):
        self.ticker = ticker
        Asset.asset_dict[ticker] = self
        self.history = pd.DataFrame(columns = ['date_time', 'high', 'low', 'open', 'close', 'volume'])
    
    def latest_price(self):
        return self.price_on_date()
    
    def price_on_date(self, on_date = date.today):
        condition = (self.history['date_time'] == on_date)
        return self.history[condition]['close']
    
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
        self.transactions = pd.DataFrame(columns = ['date_time', 'ticker', 'change'])
        self.value = pd.DataFrame(columns = ['date_time', 'value'])
        self.value.set_index('date_time')

    def do_transaction(self, ticker:str, qty:float, transaction_date = date.today()):
        new_transaction = pd.DataFrame({'date_time': transaction_date,
                                        'ticker': ticker,
                                        'change':qty}, index=[0])
        self.transactions = pd.concat([self.transactions, new_transaction], ignore_index=True)

    def get_value(self, on_date: date):
        self.update_value()
        mask = (self.value['date_time'] == on_date)
        return self.value[mask]['value']
    
    def update_value(self):
        self.value.drop(self.value.index, inplace=True)
        #generate a list of dates to update
        date_to_add = date.fromisoformat('2023-11-30')
        oldest_transaction = min(self.transactions['date_time'])
        while date_to_add >= oldest_transaction:
            time_mask = (self.transactions['date_time'] <= date_to_add)
            composition_at_date = self.transactions[time_mask][['ticker', 'change']].groupby(['ticker']).agg({'change':'sum'}).reset_index()
            composition_at_date.columns = ['ticker', 'position_size']
            composition_at_date['ticker'] = composition_at_date['ticker'].astype(str)
            composition_at_date['position_value'] = composition_at_date['ticker'].apply(
                                                    lambda x: Asset.asset_dict[x].price_on_date(date_to_add)
                                                    )
            composition_at_date['position_value'] = composition_at_date['position_value']*composition_at_date['position_size']
            value_to_add = composition_at_date.position_value.sum()
            df_to_add = pd.DataFrame({'value': value_to_add, 'date_time': date_to_add}, index=[0])
            self.value = pd.concat([self.value, df_to_add], ignore_index=True)
            date_to_add = date_to_add - timedelta(days=1)
class Strategy:

    def __init__(self, model):
        self.frequency = 1
        self.model = model

    def backtest(self, hist_data: pd.DataFrame, portfolio: Portfolio):
        updated_portfolio = Portfolio()
        return updated_portfolio




    
