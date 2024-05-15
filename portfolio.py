import pandas as pd
from pandas import Timestamp as tmpstemp
from pandas import Timedelta as tmpdelta
import numpy as np
import os
import json

from coinbase.rest import RESTClient
if os.environ['USERNAME'] in ['art_usr', 'Artem']:
    with open('coinbase_cloud_api_key.json') as f:
        d = json.load(f)
    os.environ['API_KEY'] =d['name']
    os.environ['API_SECRET'] = d['privateKey']
client = RESTClient(api_key = os.environ['API_KEY'], api_secret=os.environ['API_SECRET'])

class Asset_train:
    asset_dict = {}

    @staticmethod
    def make_USD():
        USD = Asset('USD')
        date_range = pd.date_range(start=tmpstemp.fromisoformat('2000-01-01'), end=tmpstemp.today())
        idx =pd.DatetimeIndex(date_range, name = 'date_time')
        USD_2000 = pd.DataFrame({'low':[1] * len(idx), 'high':[1] * len(idx),
                            'open':[1] * len(idx), 'close':[1] * len(idx),
                            'volume':[1000]* len(idx)},
                            index=idx)
        USD.update_history_from_df(USD_2000)
        return USD

    make_USD()

    def __init__(self, ticker):
        self.ticker = ticker
        self.local_path = f'{self.ticker}_history.csv'
        Asset.asset_dict.pop(ticker, None)
        Asset.asset_dict[ticker] = self
        self.history = pd.DataFrame(columns = ['high', 'low', 'open', 'close', 'volume'],
                                    index = pd.DatetimeIndex([], name = 'date_time'))
        try:
            self.read_history_from_local()
        except OSError:
            pass

        
    def latest_price(self):
        return self.price_on_date()
    
    def price_on_date(self, on_date = tmpstemp.today):
        '''
        Returns the prce on the date that is the closest to the supplied date
        '''
        matches = self.history.index.get_indexer([on_date], method='nearest')
        matched_date = self.history.index[matches[0]]
        if ((matched_date - on_date) > tmpdelta(days=1))  | ((on_date - matched_date) > tmpdelta(days=1)):
            print(f'Reported {self.ticker} price is {on_date- matched_date} old')
        return self.history['close'].loc[matched_date]
    
    def update_history_from_df(self, incoming_df:pd.DataFrame):
        '''
        incoming_df: the dataframe with the new historical records
        '''
        self.history = pd.concat([self.history, incoming_df]).groupby(level=0).last()
        self.save_history_to_local()

    def update_history_from_excahnge(self, currency: str, date_from, date_to):
        '''
        dates as pd.Datetime
        currency: the currency we pay to obtain this asset, as a ticker (USD, USDT etc)
        '''
        next_date = date_from
        while next_date < date_to:
            date_from_unix = (date_from - tmpstemp("1970-01-01")) // tmpdelta('1s')
            next_date = min((date_from + tmpdelta(days=190)), date_to)
            next_date_unix = (next_date - tmpstemp("1970-01-01")) // tmpdelta('1s')

            exchange_response = client.get_candles(f'{self.ticker}-{currency}', date_from_unix, next_date_unix, 'ONE_DAY')
            incoming_data= pd.DataFrame( data = exchange_response['candles']) 
            incoming_data.columns = [ 'date_time', 'low', 'high', 'open', 'close', 'volume' ]
            incoming_data['date_time']= incoming_data['date_time'].apply(lambda x: tmpstemp.fromtimestamp(int(x)))
            incoming_data.set_index('date_time', inplace=True)
            self.update_history_from_df(incoming_data)
            date_from = date_from + tmpdelta(days=190)
        self.save_history_to_local()

    def read_history_from_local(self):
        incoming_data= pd.read_csv(self.local_path, sep='\t', index_col=0, parse_dates=True)
        self.update_history_from_df(incoming_data)

    def save_history_to_local(self):
        try:
            os.remove(self.local_path)
        except OSError:
            print('Error occured')
            pass
        self.history.to_csv(self.local_path, sep='\t', mode = 'w')

class Asset ():
    if os.environ['MY_ENVIRONMENT'] == 'training':
        self = Asset_train
    def __init__(self, ticker):
        self.ticker = ticker
        self.local_path = f'{self.ticker}_history.csv'
        Asset.asset_dict.pop(ticker, None)
        Asset.asset_dict[ticker] = self
        self.history = pd.DataFrame(columns = ['high', 'low', 'open', 'close', 'volume'],
                                    index = pd.DatetimeIndex([], name = 'date_time'))
        try:
            self.read_history_from_local()
        except OSError:
            pass

class Portfolio:
    def __init__(self, origination_date = tmpstemp.fromisoformat('2000-01-01'), initial_deposit = 0):
        idx  = pd.MultiIndex(levels=[[],[]],
                          codes=[[],[]],
                          names=[u'date_time', u'ticker'])
        my_columns = [u'change', u'note']
        self.transactions  = pd.DataFrame(index=idx, columns=my_columns)
        self.value = pd.DataFrame(columns = ['value'], index = pd.DatetimeIndex([], name = 'date_time'))
        self.orig_date = origination_date
        self.update_transactions(transaction_date = origination_date,
                                ticker = 'USD',
                                qty = initial_deposit,
                                note = 'Initial deposit')


    def update_transactions(self, ticker:str, qty:float, transaction_date = tmpstemp.today(), note = ''):
        self.transactions.loc[(transaction_date,ticker),:] = [qty, note]

    def get_hist_positions(self, on_date = tmpstemp.today()):
        '''
        Returns portfolio composition on the specified date
        '''
        # First, get the mask for all records before the date
        time_mask= self.transactions.index.get_level_values('date_time')<=on_date
        # Filter the df with this mask, group by ticker
        positions = self.transactions[time_mask]['change'].groupby(level = 'ticker').sum()
        # Convert resulting Series to DataFrame
        positions = pd.DataFrame(data = positions,
                                index=pd.Index(positions.index, name = 'ticker'))
        positions.columns = ['position_size']
        
        # Add the value in USD by multiplying on the asset price at this date
        positions['position_value'] = positions.index.to_series().apply(
                                                lambda x: Asset.asset_dict[str(x)].price_on_date(on_date)
                                                )
        positions['position_value'] = positions['position_value']*positions['position_size']
        total_value = positions['position_value'].sum()
        try:
            positions['allocation'] = positions['position_value']/total_value
        except Exception:
            print('Error occured')
            pass
        
        return positions

    def get_hist_value(self, on_date = tmpstemp.today(), update = False):
        if update:
            self.update_value(up_to = on_date)
        matches = self.value.index.get_indexer([on_date], method='nearest')
        matched_date = self.value.index[matches[0]]
        if ((matched_date - on_date) > tmpdelta(days=1))  | ((on_date - matched_date) > tmpdelta(days=1)):
            print(f'Reported value is {on_date- matched_date} old')
        return self.value.loc[matched_date]
    
    def get_spot(self, coin):
        try:
            product = f'{coin}-USD'
            if product in pd.DataFrame(client.get_products()['products'])['product_id'].values:
                return float(client.get_product(product)['price'])
            elif coin in ['USD', 'USDC']:
                return 1
            else:
                pass
        except Exception as e:
            print(e)

    def get_current_postions(self, on_date = tmpstemp.today(), update = False):
        '''
        Returns portfolio composition from Coinbase account
        '''
       
        positions = {}
        for account in client.get_accounts()['accounts']:
            positions[account['name'].split(' ')[0]] = float(account['available_balance']['value'])

        positions = pd.DataFrame(columns = ['position_size'], data = positions.values(), index = pd.Index(positions.keys(), name = 'ticker'))
        positions['position_value'] = positions.index.to_series().apply(lambda x: self.get_spot(x) if positions['position_size'].loc[x]>0 else 0)  #
        positions['position_value'] = positions['position_value']*positions['position_size']
        total_value = positions['position_value'].sum()
        try:
            positions['allocation'] = positions['position_value']/total_value
        except Exception:
            print('Error occured')
            pass
        
        return positions
    
    def update_value(self, up_to = tmpstemp.fromisoformat('2023-11-30')):
        #self.value.drop(self.value.index, inplace=True)
        date_to_add = up_to
        while date_to_add >= self.orig_date:
            composition_at_date = self.get_hist_positions(date_to_add).dropna()
            value_to_add = composition_at_date.position_value.sum()
            self.value.loc[date_to_add] = value_to_add
            date_to_add = date_to_add - tmpdelta(days=1)
        self.value.sort_index(inplace=True)

    
