from portfolio import Portfolio
import os

def lambda_handler(event, context):
    rebal_portfolio = Portfolio()

    positions = rebal_portfolio.get_current_postions()
    for ticker in positions.index:
        alloc = positions['allocation'].loc[ticker]*100//1
        if alloc >0:
            print(f"{ticker}: {alloc}%")

event_test = {'key1':'one', 'key2':'two'}
context = 'QWERTY'

lambda_handler(event_test, context)
