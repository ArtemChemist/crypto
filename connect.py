import cbpro

with open('CoinBaseAPIKey.key', 'r') as f:
    contents = f.readlines()
cb_key = contents[0].split(':')[-1].strip()
cb_secret = contents[1].split(':')[-1].strip()
# print(f'key: {cb_key}\nsecret: {cb_secret}')

public_client = cbpro.PublicClient()

result = public_client.get_product_24hr_stats('BTC-USDT')

print(result)