from portfolio import Portfolio, Asset

BTC = Asset('BTC')
BTC.set_price(100)

ETH = Asset('ETH')
ETH.set_price(30)

my_portfolio = Portfolio()
my_portfolio.add_asset(BTC,1)
my_portfolio.add_asset(ETH,1)
my_value = my_portfolio.get_value()
print(my_value)