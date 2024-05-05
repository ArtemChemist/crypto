import pandas as pd
from pandas import Timestamp as tmpstemp
from pandas import Timedelta as tmpdelta
import numpy as np

from sklearn.preprocessing import MinMaxScaler
from keras.models import Model

from portfolio import Asset, Portfolio

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

class Rebalancing_Strategy(BaseStrategy):

    def __init__(self, target_allocations):
        super().__init__()
        self.target_alloc = pd.Series(target_allocations.values(), name = 'target', index = pd.Index(target_allocations.keys(), name = 'ticker'))

    def make_suggestion(self, today, portfolio):
        suggestion  = portfolio.get_positions(today).copy()
        total = suggestion['position_value'].sum()

        # Get today's price for wach asset
        today_price = [Asset.asset_dict[asset].price_on_date(today) for asset in suggestion.index]
        today_price = pd.Series(today_price, name = 'today_price', index = suggestion.index)

        # Bring all data on the same dataframe
        suggestion = pd.concat([suggestion, self.target_alloc, today_price], axis = 1 )

        # Calculate the suggested change as a simple difference between current and target
        suggestion['USD_value'] = suggestion['target']*total - suggestion['position_value']
        suggestion['change_in_size'] = suggestion['USD_value']/suggestion['today_price']

        suggestion['note'] = today.strftime('%Y-%m-%d') + ' rebalancing'
        return suggestion
