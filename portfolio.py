import pandas as pd
from pandas import Timestamp as tmpstemp
from pandas import Timedelta as tmpdelta
import os
import json
from asset import Asset
from math import copysign

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
        Returns the latest avalable portfolio composition, as a pandas df
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
    
    def get_hist_positions(self, on_date):
        '''
        Returns portfolio composition, as a pandas df
        Includs position size, value in USD and allocation
        If date is provide, returns composition for that date,
        If date is not provided, returns the latest avaliable on Coinbase
        '''
        if on_date: 
            return super().get_hist_positions(on_date)
        else:
            return self.get_current_postions()

    
    def execute_suggestions(self, sggst_df):
        print('-----START OF EXECUTION ---------')
        '''
        Executes transactions suggested, ASSUMES PORTFOLIO IS ONLY 1 ASSET AND USD
        Parameters:
        suggestions: dafaframe with tickers as index and suggested changes in 'delta_size' column
        exec_date: date when the transactions are executed. Can be any date

        '''
        while max(abs(sggst_df['delta_USD_value'])) >=10:

            sggst_df.sort_values(by='delta_USD_value', ascending=False, inplace=True)
            print('Suggested changes')
            print(sggst_df)
            # Figure out what pair we are traiding
            if f'{sggst_df.index[0]}-{sggst_df.index[-1]}' in Asset.tradable_pairs:
                first_ass = sggst_df.index[0]
                second_ass = sggst_df.index[-1]
            elif f'{sggst_df.index[-1]}-{sggst_df.index[0]}' in Asset.tradable_pairs:
                first_ass = sggst_df.index[-1]
                second_ass = sggst_df.index[0]
            else:
                print('Untradable pair')
                trade_pair  = None
            trade_pair = f'{first_ass}-{second_ass}'
            # Figure out if we are sellign or bying
            if sggst_df['delta_USD_value'].loc[first_ass] >=0:
                trans_type = 'buy'
            else:
                trans_type  = 'sell'

            # Figure out how much we are trading, what asset we will sell completely, what willl remain
            if abs(sggst_df['delta_USD_value'].loc[first_ass]) >= abs(sggst_df['delta_USD_value'].loc[second_ass]):
                value = abs(sggst_df['delta_USD_value'].loc[second_ass])
                to_drop = second_ass
                to_change = first_ass
            else:
                value = abs(sggst_df['delta_USD_value'].loc[first_ass])
                to_drop = first_ass
                to_change = second_ass

            # Size of the change is always in theunits of the first asset of the pair
            size = value/sggst_df['on_date_price'].loc[first_ass]

            ### START OF LAMBDA-SPECIFIC LOGIC

            if trans_type  == 'sell':
                print(f'Sell {size} of {trade_pair} for {round(value,1)} USD and drop {to_drop}')
                #client.market_order_sell()
            else:
                print(f'Buy {size} of {trade_pair} for {round(value,1)} USD and drop {to_drop}')
                #client.market_order_buy()

            ### END OF LAMBDA-SPECIFIC LOGIC

            # Drop the asset we used up from teh suggest_df
            sggst_df.drop(index = [to_drop], inplace = True)

            # Update delta for size and value of the asset that is not used up
            # Here we update the suggestion df, to make the right decision on the next iteration
            curr_val_delta = sggst_df['delta_USD_value'].loc[to_change]
            new_val_delta = curr_val_delta - copysign(value, curr_val_delta)
            sggst_df.loc[to_change, 'delta_USD_value'] = new_val_delta

            curr_size_delta = sggst_df['delta_size'].loc[to_change]
            new_size_delta = curr_size_delta - copysign(size, curr_size_delta)
            sggst_df.loc[to_change, 'delta_size'] = new_size_delta


            print('-----END OF CYCLE ---------')


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

    def get_current_postions(self):
        '''
        Returns portfolio composition on today's date
        '''
        return self.get_hist_positions()
    
    def update_value(self, up_to = tmpstemp.fromisoformat('2023-11-30')):
        #self.value.drop(self.value.index, inplace=True)
        date_to_add = up_to
        while date_to_add >= self.orig_date:
            composition_at_date = self.get_hist_positions(date_to_add).dropna()
            value_to_add = composition_at_date.position_value.sum()
            self.value.loc[date_to_add] = value_to_add
            date_to_add = date_to_add - tmpdelta(days=1)
        self.value.sort_index(inplace=True)

    def execute_suggestions(self, sggst_df: pd.DataFrame, exec_date):
        print('-----START OF EXECUTION ---------')
        '''
        Executes transactions suggested, ASSUMES PORTFOLIO IS ONLY 1 ASSET AND USD
        Parameters:
        suggestions: dafaframe with tickers as index and suggested changes in 'delta_size' column
        exec_date: date when the transactions are executed. Can be any date

        '''
        checking_time = exec_date.replace(hour=23, minute=59, second=0, microsecond=0)
        while max(abs(sggst_df['delta_USD_value'])) >=10:
            print('Suggested changes')
            sggst_df.sort_values(by='delta_USD_value', ascending=False, inplace=True)
            print(sggst_df)
            print(f'Current portfolio for {checking_time}')
            print(self.get_hist_positions(checking_time))
            # Figure out what pair we are traiding
            if f'{sggst_df.index[0]}-{sggst_df.index[-1]}' in Asset.tradable_pairs:
                first_ass = sggst_df.index[0]
                second_ass = sggst_df.index[-1]
            elif f'{sggst_df.index[-1]}-{sggst_df.index[0]}' in Asset.tradable_pairs:
                first_ass = sggst_df.index[-1]
                second_ass = sggst_df.index[0]
            else:
                print('Untradable pair')
                trade_pair  = None
            trade_pair = f'{first_ass}-{second_ass}'
            print(trade_pair)
            # Figure out if we are sellign or bying
            if sggst_df['delta_USD_value'].loc[first_ass] >=0:
                trans_type = 'buy'
            else:
                trans_type  = 'sell'

            # Figure out how much we are trading, what asset we will sell completely, what willl remain
            if abs(sggst_df['delta_USD_value'].loc[first_ass]) >= abs(sggst_df['delta_USD_value'].loc[second_ass]):
                value = abs(sggst_df['delta_USD_value'].loc[second_ass])
                to_drop = second_ass
                to_change = first_ass
            else:
                value = abs(sggst_df['delta_USD_value'].loc[first_ass])
                to_drop = first_ass
                to_change = second_ass

            # Size of the change is always in theunits of the first asset of the pair
            size = value/sggst_df['on_date_price'].loc[first_ass]

            #This is where transaction happens
            print(f'{trans_type} {size} of {trade_pair} for {value} and drop {to_drop}')
            # In local we do that in two transactions
            ### ESTART OF LOCAL_SPECIFIC LOGIC
            curr_size_delta = sggst_df['delta_size'].loc[first_ass]
            size_1 = copysign(size, curr_size_delta)
            print(f"Updating {first_ass} for {size_1}")
            self.update_transactions(ticker = first_ass,
                            qty =  size_1,
                            transaction_date = exec_date,
                            note =  sggst_df['note'].loc[first_ass])
            

            curr_size_delta = sggst_df['delta_size'].loc[second_ass]
            size_2 = value/sggst_df['on_date_price'].loc[second_ass]
            size_2 = copysign(size_2, curr_size_delta)
            print(f"Updating {second_ass} for {size_2}")
            self.update_transactions(ticker = second_ass,
                            qty =  size_2 ,
                            transaction_date = exec_date,
                            note =  sggst_df['note'].loc[second_ass])
            print(f'Updated portfolio for {checking_time}')
            print(self.get_hist_positions(checking_time))
            # Place the next transactions and a different time to avoid overlap
            exec_date = exec_date + tmpdelta(seconds=1)
            ### END OF LOCAL_SPECIFIC LOGIC

            # Drop the asset we used up
            sggst_df.drop(index = [to_drop], inplace = True)

            # Update delta for size and value of the asset that is not used up
            # Here we update the suggestion df, to make the right decision on the next iteration
            curr_val_delta = sggst_df['delta_USD_value'].loc[to_change]
            new_val_delta = curr_val_delta - copysign(value, curr_val_delta)
            sggst_df.loc[to_change, 'delta_USD_value'] = new_val_delta

            curr_size_delta = sggst_df['delta_size'].loc[to_change]
            new_size_delta = curr_size_delta - copysign(size, curr_size_delta)
            sggst_df.loc[to_change, 'delta_size'] = new_size_delta


            print('-----END OF CYCLE ---------')


    
class Portfolio(Portfolio_base):
    
    def __new__(cls, assets:dict, origination_date = tmpstemp.fromisoformat('2000-01-01')):
        key_word = os.environ['MY_ENVIRONMENT']
        if key_word == 'prod':
            return Portfolio_lambda(assets = assets)
        if key_word == 'training':
            return Portfolio_train(assets = assets, origination_date = origination_date)