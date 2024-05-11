import pandas as pd
from portfolio import Asset, Portfolio

class BaseStrategy:

    def __init__(self, model_input_length = 15):
        self.frequency = 1
        self.input_span = model_input_length
        self.fees = 0.006


class Rebalancing_Strategy(BaseStrategy):

    def __init__(self, target_allocations):
        super().__init__()
        self.target_alloc = pd.Series(target_allocations.values(), name = 'target', index = pd.Index(target_allocations.keys(), name = 'ticker'))

    def make_suggestion(self, today, portfolio):
        suggestion  = portfolio.get_hist_positions(today).copy()
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
