import pandas as pd
from pandas import Timestamp as tmpstemp
from pandas import Timedelta as tmpdelta
import numpy as np
import os

from sklearn.preprocessing import MinMaxScaler
from keras.models import Model

import cbpro

class Asset:
    asset_dict = {}
    public_client = cbpro.PublicClient()

    @staticmethod
    def connect_to_exchange():
        with open('CoinBaseAPIKey.key', 'r') as f:
            contents = f.readlines()
        cb_key = contents[0].split(':')[-1].strip()
        cb_secret = contents[1].split(':')[-1].strip()
        #return Asset.public_client = cbpro.PublicClient()
    
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
            date_from_str = date_from.strftime('%Y-%m-%d')
            next_date = min((date_from + tmpdelta(days=190)), date_to)
            next_date_str = next_date.strftime('%Y-%m-%d')
            incoming_data= pd.DataFrame(
                Asset.public_client.get_product_historic_rates(f'{self.ticker}-{currency}',
                                                        date_from_str, next_date_str, 86400)
            )
            incoming_data.columns = [ 'date_time', 'low', 'high', 'open', 'close', 'volume' ]
            incoming_data['date_time']= incoming_data['date_time'].apply(lambda x: tmpstemp.fromtimestamp(x))
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

    def get_positions(self, on_date = tmpstemp.today()):
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
            positions['allocations'] = positions['position_value']/total_value
        except Exception:
            print('Error occured')
            pass
        
        return positions

    def get_value(self, on_date = tmpstemp.today(), update = False):
        if update:
            self.update_value(up_to = on_date)
        matches = self.value.index.get_indexer([on_date], method='nearest')
        matched_date = self.value.index[matches[0]]
        if ((matched_date - on_date) > tmpdelta(days=1))  | ((on_date - matched_date) > tmpdelta(days=1)):
            print(f'Reported {self.ticker} value is {on_date- matched_date} old')
        return self.value.loc[matched_date]
    
    def update_value(self, up_to = tmpstemp.fromisoformat('2023-11-30')):
        #self.value.drop(self.value.index, inplace=True)
        date_to_add = up_to
        while date_to_add >= self.orig_date:
            composition_at_date = self.get_positions(date_to_add).dropna()
            value_to_add = composition_at_date.position_value.sum()
            self.value.loc[date_to_add] = value_to_add
            date_to_add = date_to_add - tmpdelta(days=1)
        self.value.sort_index(inplace=True)

class BaseStrategy:

    def __init__(self, model_input_length = 15):
        self.frequency = 1
        self.model = Model()
        self.input_span = model_input_length
        self.fees = 0.006
        self.scaler = MinMaxScaler(feature_range=(0,1))
    
    def train_val_split_scale(self, df, ratio = 0.7):
        len_train = int(ratio*len(df))
        X = []
        y = []
        index = []
        scaled_data = self.scaler.fit_transform(np.array(df['close'].values).reshape(-1,1) )
        for x in range(self.input_span, len(df)):
            X.append(scaled_data[x-self.input_span:x, 0])
            y.append(scaled_data[x,0])
            index.append(df.index[(x-1)])
        X, y = (np.array(X), np.array(y))
        X = np.reshape(X, (X.shape[0], X.shape[1], 1))
        return X[0:len_train,:,:],\
                y[0:len_train],\
                index[0:len_train],\
                X[len_train:,:,:],\
                y[len_train:],\
                index[len_train:]
    
    def backtest(self, hist_data: pd.DataFrame, portfolio: Portfolio):
        updated_portfolio = Portfolio()
        return updated_portfolio


class LSTM_Strategy(BaseStrategy):

    def __init__(self, model_input_length = 15):
        super().__init__(model_input_length = 15)

    def make_suggestion(self, today, portfolio, risk_rate = 0.02):
        
        asset_to_analyze = Asset.asset_dict['BTC']
        
        positions = portfolio.get_positions(today)
        suggestions = pd.DataFrame(columns = ['change_in_size', 'USD_value', 'note'], index = positions.index)
        data_to_process = asset_to_analyze.history['close'].loc[today-tmpdelta(days=self.input_span-1):today+tmpdelta(days=1)]
        prediction = self.predict_one(data_to_process)
        prediction = float(prediction['Predicted price'])

        # If BTC is predicted to go up - buy it
        if prediction > float(asset_to_analyze.price_on_date(today)):
            USD_to_spend = risk_rate * positions['position_value'].loc['USD']  # In this strategy, we change position by risk_rate% on every step
            ext_price = USD_to_spend/(1 + self.fees)                    # This is how much will be paid for BTC, extended price
            fees = USD_to_spend - ext_price                            # This is plaform fees
            BTC_price = asset_to_analyze.history['close'].loc[today]                # BTC price at the time of decision
            BTC_to_buy = ext_price/BTC_price
            suggestions.loc['BTC'] = [BTC_to_buy, ext_price, 'Buy BTC']
            suggestions.loc['USD'] = [-USD_to_spend,-USD_to_spend, 'BTC price w fees']

        # If BTC is predicted to go down - sell it
        if prediction < float(asset_to_analyze.price_on_date(today)):
            BTC_to_spend = risk_rate * positions['position_size'].loc['BTC']  # In this strategy, we change position by risk_rate% on every step
            ext_price = BTC_to_spend/(1 + self.fees)                    # This is how much BTC will be sold, extended price
            fees = BTC_to_spend - ext_price                            # This is plaform fees
            BTC_price = asset_to_analyze.history['close'].loc[today]                # BTC price at the time of decision
            USD_to_buy = ext_price*BTC_price
            suggestions.loc['BTC'] = [-BTC_to_spend, -BTC_to_spend, 'Sell BTC w fees']
            suggestions.loc['USD'] = [USD_to_buy, USD_to_buy, 'BTC sale']
            suggestions.dropna(inplace=True)
        return suggestions
    
    def predict_batch(self, data_to_process):
        '''
        Given the new data go one time point after another and make predictions
        '''
        prediction_prices = []
        pred_prices_idx = []
        for today in data_to_process.index[(self.input_span-1):]:
            try:
                tomorrow_date = today + tmpdelta(days=1)
                # range(tomorrow - 14: tomorrow) is 15 day-log timespan that end today!
                current_day_input = data_to_process.loc[today - tmpdelta(days=self.input_span-1):today]  # Data slice to be used in this step
                model_input = self.scaler.transform(np.array(current_day_input.values).reshape(-1,1) )     # Data scaled as input for the model
                model_input = np.array(model_input).reshape(-1, model_input.shape[0], model_input.shape[1])                           # Data shaped as input for the model
                tmr_BTC_price = self.model.predict(model_input,verbose = 0)                                # Predict
                tmr_BTC_price = self.scaler.inverse_transform(tmr_BTC_price)[0][0]                         # Un-scale to get predicted asset price
                prediction_prices.append(tmr_BTC_price)                                               # Save the result in the output array
                pred_prices_idx.append(tomorrow_date)

                # Format string for output
                # Get date we are predictig for 
                today_BTC_price = data_to_process.loc[today]                                             # Get current asset price 
                # print(f'Today ({today_day}):{today_BTC_price}, predicted for {tomorrow_date}: {tmr_BTC_price}')
            except Exception as e:
                print(e)
                pass
        return pd.DataFrame(data=prediction_prices, columns = ['Predicted price'], index = pd.DatetimeIndex(pred_prices_idx, name='date_time'))

    def predict_one(self, data_to_process):
        '''
        Given the data predict for the next timepoint
        '''
        tomorrow_date = data_to_process.index[-1]+tmpdelta(days=1)
        #today_day = data_to_process.index[-1]
        #today_BTC_price = data_to_process.loc[today_day] 
        try:
            model_input = self.scaler.transform(np.array(data_to_process.values).reshape(-1,1) )     # Data scaled as input for the model
            model_input = np.array(model_input).reshape(-1, model_input.shape[0], model_input.shape[1])# Data shaped as input for the model
            tmr_BTC_price = self.model.predict(model_input,verbose = 0)                                # Predict
            tmr_BTC_price = self.scaler.inverse_transform(tmr_BTC_price)[0][0]                         # Un-scale to get predicted asset price

            #print(f'Today ({today_day}):{today_BTC_price}, predicted for {tomorrow_date}: {tmr_BTC_price}')
            return pd.DataFrame(data=[tmr_BTC_price],
                    columns = ['Predicted price'],
                    index = pd.DatetimeIndex([tomorrow_date], name='date_time'))
        except Exception as e:
            print(e)
            pass

class Rebalancing_Strategy(BaseStrategy):

    def __init__(self, model_input_length = 15):
        super().__init__(model_input_length = 15)

    def make_suggestion(self, today, portfolio, BTC_allocation = 0.7):
        
        asset_to_analyze = Asset.asset_dict['BTC']
        
        positions = portfolio.get_positions(today)
        suggestions = pd.DataFrame(columns = ['change_in_size', 'USD_value', 'note'], index = positions.index)

        BTC_to_buy = ext_price/BTC_price
        suggestions.loc['BTC'] = [BTC_to_buy, ext_price, 'Buy BTC']
        suggestions.loc['USD'] = [-USD_to_spend,-USD_to_spend, 'BTC price w fees']

        USD_to_spend = BTC_allocation * positions['position_value'].loc['USD']  # In this strategy, we change position by risk_rate% on every step
        ext_price = USD_to_spend/(1 + self.fees)                    # This is how much will be paid for BTC, extended price
        fees = USD_to_spend - ext_price                            # This is plaform fees
        BTC_price = asset_to_analyze.history['close'].loc[today]                # BTC price at the time of decision



        return suggestions
    
 


    
