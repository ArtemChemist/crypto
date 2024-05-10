from portfolio import Portfolio, read_creds

def lambda_handler(event, context):
    rebal_portfolio = Portfolio()
    
    read_creds()
    curr_pos = rebal_portfolio.get_current_postions()

    for pos in curr_pos.index:
        print(curr_pos['allocation'].loc[pos])