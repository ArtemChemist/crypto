from portfolio import Portfolio, Asset
from strategies import Rebalancing_Strategy
from coinbase_advanced_trader.strategies.limit_order_strategies import fiat_limit_buy, fiat_limit_sell

def lambda_handler(event, context):
    rebal_portfolio = Portfolio()
    curr_pos = rebal_portfolio.get_current_postions()
    for pos in curr_pos.index:
        print(curr_pos['allocation'].loc[pos])