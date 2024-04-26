import pandas as pd
from pandas import Timestamp as tmpstemp
from pandas import Timedelta as tmpdelta
import numpy as np
import os

from sklearn.preprocessing import MinMaxScaler
from keras.models import Model

from portfolio import Asset, Portfolio

import cbpro

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
        positions['position_size'].loc['BTC']
        BTC_to_buy = ext_price/BTC_price
        suggestions.loc['BTC'] = [BTC_to_buy, ext_price, 'Buy BTC']
        suggestions.loc['USD'] = [-USD_to_spend,-USD_to_spend, 'BTC price w fees']

        USD_to_spend = BTC_allocation * positions['position_value'].loc['USD']  # In this strategy, we change position by risk_rate% on every step
        ext_price = USD_to_spend/(1 + self.fees)                    # This is how much will be paid for BTC, extended price
        fees = USD_to_spend - ext_price                            # This is plaform fees
        BTC_price = asset_to_analyze.history['close'].loc[today]                # BTC price at the time of decision



        return suggestions
    
 


    
