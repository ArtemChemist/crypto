from portfolio import Portfolio
from asset import Asset
import os
import pandas as pd
from strategies import Rebalancing_Strategy

rebalncer = Rebalancing_Strategy(target_allocations = {'USDT':0.39, 'BTC':0.41, 'ETH':0.20})

def lambda_handler(event, context):
    BTC = Asset('BTC')
    ETH = Asset('ETH')
    USDT = Asset('USDT')
    rebal_portfolio = Portfolio({'BTC':0, 'ETH':0, 'USDT':0})

    rebal_suggest = rebalncer.make_suggestion(rebal_portfolio)
    rebal_portfolio.execute_suggestions(rebal_suggest)

    positions = rebal_portfolio.get_current_postions()
    for ticker in positions.index:
        alloc = positions['allocation'].loc[ticker] *100
        print(f"{ticker}: {round(alloc,1)}%")

event_test = {'key1':'one', 'key2':'two'}
context = 'QWERTY'
os.environ['MY_ENVIRONMENT'] = 'prod'
lambda_handler(event_test, context)
