import pandas as pd
from pandas import Timestamp as tmpstemp
from pandas import Timedelta as tmpdelta
import os
import json

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

class Asset_base:
    # Dict to keep track of all assets and call them by string ticker
    asset_dict = {}

    @classmethod
    def make_USD(cls):
        '''
        Method to create a USD as an asset with 1:1 exchange rate to USD. 
        '''
        USD = cls('USD')
        date_range = pd.date_range(start=tmpstemp.fromisoformat('2000-01-01'), end=tmpstemp.today())
        idx =pd.DatetimeIndex(date_range, name = 'date_time')
        USD_2000 = pd.DataFrame({'low':[1] * len(idx), 'high':[1] * len(idx),
                            'open':[1] * len(idx), 'close':[1] * len(idx),
                            'volume':[1000]* len(idx)},
                            index=idx)
        USD.update_history_from_df(USD_2000)
        return USD

    def __init__(self, ticker):
        self.ticker = ticker
        # Remove this asset from the class dict, if exists
        # Add reference to this asset to the class dict
        Asset_base.asset_dict.pop(ticker, None)
        Asset_base.asset_dict[ticker] = self
        self.history = pd.DataFrame(columns = ['high', 'low', 'open', 'close', 'volume'],
                            index = pd.DatetimeIndex([], name = 'date_time'))
       


    def update_history_from_df(self, incoming_df:pd.DataFrame):
        '''
        incoming_df: the dataframe with the new historical records
        '''
        self.history = pd.concat([self.history, incoming_df]).groupby(level=0).last()

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

class Asset_lambda(Asset_base):

    def __init__(self, ticker):
        super().__init__(ticker)

class Asset_train(Asset_base):

    def __init__(self, ticker):
        super().__init__(ticker)
        self.local_path = os.path.join(os.getcwd(), 'data', f'{self.ticker}_history.csv')

        try:
            self.read_history_from_local()
        except OSError:
            pass

    def update_history_from_excahnge(self, currency: str, date_from, date_to):
        super().update_history_from_excahnge(currency, date_from, date_to)
        self.save_history_to_local()
        
    def update_history_from_df(self, incoming_df: pd.DataFrame):
        super().update_history_from_df(incoming_df)
        self.save_history_to_local()

    def read_history_from_local(self):
        # Read csv, parse dates
        incoming_data= pd.read_csv(self.local_path, sep='\t', index_col=0, parse_dates=True)

        #Becasue we had dates, columns are now read as strings, so we convert data back to floats
        for col in incoming_data.columns:
            incoming_data[col] = incoming_data[col].astype(float)
        self.update_history_from_df(incoming_data)

    def save_history_to_local(self):
        try:
            os.remove(self.local_path)
        except OSError:
            print('Error occured')
            pass
        self.history.to_csv(self.local_path, sep='\t', mode = 'w')

    def price_on_date(self, on_date = tmpstemp.today):
        '''
        Returns the prce on the date that is the closest to the supplied date
        '''
        matches = self.history.index.get_indexer([on_date], method='nearest')
        matched_date = self.history.index[matches[0]]
        if ((matched_date - on_date) > tmpdelta(days=1))  | ((on_date - matched_date) > tmpdelta(days=1)):
            print(f'Reported {self.ticker} price is {on_date- matched_date} old')
        return self.history['close'].loc[matched_date]
    
    def latest_price(self):
        return self.price_on_date()
    
class Asset(Asset_base):

    def __new__(cls, ticker):
        key_word = os.environ['MY_ENVIRONMENT']
        if key_word == 'prod':
            return Asset_lambda(ticker)
        if key_word == 'training':
            return Asset_train(ticker)