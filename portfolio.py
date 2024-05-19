import pandas as pd
from pandas import Timestamp as tmpstemp
from pandas import Timedelta as tmpdelta
import os
import json
from asset import Asset

from coinbase.rest import RESTClient
if 'API_KEY' in os.environ:
    client = RESTClient(api_key = os.environ['API_KEY'], api_secret=os.environ['API_SECRET'])
else:
    try:
        with open('coinbase_cloud_api_key.json') as f:
            d = json.load(f)
        os.environ['API_KEY'] =d['name']
        os.environ['API_SECRET'] = d['privateKey']
        client = RESTClient(api_key = os.environ['API_KEY'], api_secret=os.environ['API_SECRET'])
    except:
        print('Can not find keys')


class Portfolio_base:
    def __init__(self):
        idx  = pd.MultiIndex(levels=[[],[]],
                          codes=[[],[]],
                          names=[u'date_time', u'ticker'])
        my_columns = [u'change', u'note']
        self.transactions  = pd.DataFrame(index=idx, columns=my_columns)
        self.value = pd.DataFrame(columns = ['value'], index = pd.DatetimeIndex([], name = 'date_time'))

    def update_transactions(self, ticker:str, qty:float, transaction_date = tmpstemp.today(), note = ''):
        self.transactions.loc[(transaction_date,ticker),:] = [qty, note]

    def add_new_position(self, ticker:str, qty:float):
        note = f'Added {ticker} as a new position'
        self.update_transactions(ticker = ticker, qty = qty, note=note)
    
    def get_hist_positions(self, on_date = tmpstemp.today()):
        '''
        Returns portfolio composition on the specified date, as a pandas df
        Includs position size, value in USD and allocation
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

class Portfolio_lambda(Portfolio_base):

    def __init__(self, assets:dict):
        super().__init__()
        for account in client.get_accounts()['accounts']:
            ticker = account['name'].split(' ')[0]
            qty = float(account['available_balance']['value'])
            if ticker in assets.keys():
                self.add_new_position(ticker, qty)


    def get_current_postions(self):
        '''
        Returns portfolio composition on the specified date, as a pandas df
        Includs position size, value in USD and allocation
        '''
        # Filter the df with this mask, group by ticker
        positions = self.transactions['change'].groupby(level = 'ticker').sum()
        # Convert resulting Series to DataFrame
        positions = pd.DataFrame(data = positions,
                                index=pd.Index(positions.index, name = 'ticker'))
        positions.columns = ['position_size']

        for account in client.get_accounts()['accounts']:
            ticker = account['name'].split(' ')[0]
            qty = float(account['available_balance']['value'])
            if ticker in positions.index:
                positions.loc[ticker, 'position_size'] = qty

        # Add the value in USD by multiplying on the asset price at this date
        positions['position_value'] = positions.index.to_series().apply(
                                                lambda x: Asset.asset_dict[str(x)].price_on_date()
                                                )
        positions['position_value'] = positions['position_value']*positions['position_size']
        total_value = positions['position_value'].sum()
        try:
            positions['allocation'] = positions['position_value']/total_value
        except Exception:
            print('Error occured')
            pass
        
        return positions
    
    def execute_suggestions(suggestions):
        for ticker in suggestions.index:
            print(f"For {str(ticker)}, change of {suggestions['change_in_size'].loc[ticker]} suggested")


class Portfolio_train(Portfolio_base):

    def __init__(self, assets:dict, origination_date = tmpstemp.fromisoformat('2000-01-01') ):
        super().__init__()
        self.orig_date = origination_date
        for asset in assets.items():
            self.update_transactions(transaction_date = self.orig_date,
                                    ticker = asset[0],
                                    qty = asset[1],
                                    note = 'Initial deposit')

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

    def execute_suggestions(self, suggestions: pd.DataFrame, exec_date):
        '''
        Executes transactions suggested
        Parameters:
        suggestions: dafaframe with tickers as index and suggested changes in 'change_in_size' column
        exec_date: date when the transactions are executed. Can by any date
        '''
        for ticker in suggestions.index:
            self.update_transactions(ticker = str(ticker),
                                        qty =  suggestions['change_in_size'].loc[ticker],
                                        transaction_date = exec_date,
                                        note =  suggestions['note'].loc[ticker])
    
class Portfolio(Portfolio_base):
    
    def __new__(cls, assets:dict, origination_date = tmpstemp.fromisoformat('2000-01-01')):
        key_word = os.environ['MY_ENVIRONMENT']
        if key_word == 'prod':
            return Portfolio_lambda(assets = assets)
        if key_word == 'training':
            return Portfolio_train(assets = assets, origination_date = origination_date)