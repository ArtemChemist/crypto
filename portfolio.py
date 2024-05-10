import pandas as pd
from pandas import Timestamp as tmpstemp
from pandas import Timedelta as tmpdelta

import coinbase_advanced_trader.coinbase_client as cb
from coinbase_advanced_trader.config import set_api_credentials

import os

def read_creds():
    # Try reading credentials from environment, if none, read from file
    try:
        cb_key = os.environ['cb_key']
        cb_secret = os.environ['cb_secret']
        set_api_credentials(cb_key, cb_secret)
    except:
        print('Keys are not in the env vars')
    

class Portfolio:
    def __init__(self, origination_date = tmpstemp.fromisoformat('2000-01-01'), initial_deposit = 0):
        idx  = pd.MultiIndex(levels=[[],[]],
                          codes=[[],[]],
                          names=[u'date_time', u'ticker'])
        my_columns = [u'change', u'note']
        self.transactions  = pd.DataFrame(index=idx, columns=my_columns)
        self.value = pd.DataFrame(columns = ['value'], index = pd.DatetimeIndex([], name = 'date_time'))
        self.orig_date = origination_date

                                
    def get_spot(self, x):
        try:
            return float(cb.getProduct(f'{x}-USD')['price'])
        except:
            if x[:3] == 'USD':
                return 1
            else:
                return 0
                
    def get_current_postions(self, on_date = tmpstemp.today(), update = False):
        '''
        Returns portfolio composition from Coinbase account
        '''
       
        positions = {}
        for account in cb.listAccounts()['accounts']:
            positions[account['name'].split(' ')[0]] = float(account['available_balance']['value'])

        positions = pd.DataFrame(columns = ['position_size'], data = positions.values(), index = pd.Index(positions.keys(), name = 'ticker'))
        positions['position_value'] = positions.index.to_series().apply(lambda x: self.get_spot(x))
        positions['position_value'] = positions['position_value']*positions['position_size']
        total_value = positions['position_value'].sum()
        try:
            positions['allocation'] = positions['position_value']/total_value
        except Exception:
            print('Error occured')
            pass
        
        return positions