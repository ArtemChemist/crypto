import pandas as pd
from pandas import Timestamp as tmpstemp

from asset import Asset
from portfolio import Portfolio

class BaseStrategy:

    def __init__(self, model_input_length = 15):
        self.frequency = 1
        self.input_span = model_input_length
        self.fees = 0.006

class Rebalancing_Strategy(BaseStrategy):

    def __init__(self, target_allocations):
        super().__init__()
        self.target_alloc = pd.Series(target_allocations.values(), name = 'target', index = pd.Index(target_allocations.keys(), name = 'ticker'))

    def make_suggestion(self, portfolio, on_date = None):
        suggestion  = portfolio.get_hist_positions(on_date).copy()
        total = suggestion['position_value'].sum()

        # Get on_date's price for wach asset
        on_date_price = [Asset.asset_dict[asset].price_on_date(on_date) for asset in suggestion.index]
        on_date_price = pd.Series(on_date_price, name = 'on_date_price', index = suggestion.index)

        # Bring all data on the same dataframe
        # Make use of the fact that all dfs have ticker as indeces
        suggestion = pd.concat([suggestion, self.target_alloc, on_date_price], axis = 1 )

        # Calculate the suggested change as a simple difference between current and target
        suggestion['change_in_USD_value'] = suggestion['target']*total - suggestion['position_value']
        suggestion['change_in_size'] = suggestion['change_in_USD_value']/suggestion['on_date_price']

        # Add note, in case date was None, add current date.
        try:    
            suggestion['note'] = on_date.strftime('%Y-%m-%d') + ' rebalancing'
        except AttributeError as e:
            suggestion['note'] = tmpstemp.today().strftime('%Y-%m-%d') + ' rebalancing'
        
        return suggestion
