from portfolio import Portfolio
from asset import Asset
import os
import pandas as pd
from strategies import Rebalancing_Strategy

rebalncer = Rebalancing_Strategy(target_allocations = {'USD':0.5, 'BTC':0.5})

def lambda_handler(event, context):
    BTC = Asset('BTC')
    ETH = Asset('ETH')
    USDT = Asset('USDT')
    rebal_portfolio = Portfolio({'BTC':0, 'ETH':0, 'USDT':0})

    rebal_suggest = rebalncer.make_suggestion(today , rebal_portfolio)
    rebal_portfolio.execute_suggestions(rebal_suggest, rebal_portfolio, today)

    positions = rebal_portfolio.get_current_postions()
    for ticker in positions.index:
        alloc = positions['allocation'].loc[ticker] *100
        print(f"{ticker}: {alloc}%")

event_test = {'key1':'one', 'key2':'two'}
context = 'QWERTY'
os.environ['MY_ENVIRONMENT'] = 'prod'
lambda_handler(event_test, context)
