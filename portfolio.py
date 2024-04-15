class Asset:
    def __init__(self, ticker):
        self.price = 0
        self.ticker = ticker

    def set_price(self, price):
        self.price = price
    
    def latest_price(self):
        return self.price


class Portfolio:
    def __init__(self):
        self.assets = {}
        self.value = 0

    def add_asset(self, asset: Asset, qty:float):
        self.assets[asset] = qty

    def get_value(self):
        self.value = sum([asset.latest_price() * qty for asset, qty in self.assets.items()])
        return self.value




    
