def initialize(context):
    g.stockindex = '000300.XSHG' # 指数
    g.security = get_index_stocks(g.stockindex)
    set_universe(g.security)
    set_benchmark('000300.XSHG')
    # run_daily(update_benchmark, time='before_open')
    set_commission(PerTrade(buy_cost=0.0003, sell_cost=0.0013, min_cost=5))
    g.stocknum = 25 # 持股数
    ## 自动设定调仓月份（如需使用自动，注销下段）
    f = 4  # 调仓频率
    log.info(range(1,13,12/f))
    g.Transfer_date = range(1,13,12/f)
    
    ## 手动设定调仓月份（如需使用手动，注销上段）
    # g.Transfer_date = (3,9)
    
    # run_daily(dapan_stoploss) #根据大盘止损，如不想加入大盘止损，注释此句即可
    ## 按月调用程序
    run_monthly(Transfer,20)

# 每个单位时间(如果按天回测,则每天调用一次,如果按分钟,则每分钟调用一次)调用一次
def Transfer(context):
    months = context.current_dt.month
    if months in g.Transfer_date:
        ## 分配资金
        if len(context.portfolio.positions) < g.stocknum :
            Num = g.stocknum  - len(context.portfolio.positions)
            Cash = context.portfolio.cash/Num
        else: 
            Cash = context.portfolio.cash
            
        ## 获得Buylist
        Buylist = Check_Stocks(context)
        log.info(len(Buylist))
        # log.info(Buylist)
        
        ## 卖出
        if len(context.portfolio.positions) > 0:
            for stock in context.portfolio.positions.keys():
                if stock not in Buylist:
                    order_target(stock, 0)
        ## 买入
        if len(Buylist) > 0:
            for stock in Buylist:
               if stock not in context.portfolio.positions.keys():
                   order_value(stock,Cash)
    else:
        pass

def Check_Stocks(context):
    security = get_index_stocks(g.stockindex)
    Stocks = get_fundamentals(query(
            valuation.code,
            valuation.pb_ratio,
            balance.total_assets,
            balance.total_liability,
            balance.total_current_assets,
            balance.total_current_liability
        ).filter(
            valuation.code.in_(security),
            valuation.pb_ratio < 2,
            valuation.pb_ratio > 0,
            balance.total_current_assets/balance.total_current_liability > 1.2
        ))

    Stocks['Debt_Asset'] = Stocks['total_liability']/Stocks['total_assets']
    me = Stocks['Debt_Asset'].median()
    Code = Stocks[Stocks['Debt_Asset'] > me].code
    return list(Code)
def dapan_stoploss(context):
    ## 根据局大盘止损，具体用法详见dp_stoploss函数说明
    stoploss = dp_stoploss(kernel=2, n=10, zs=0.1)
    if stoploss:
        if len(context.portfolio.positions)>0:
            for stock in list(context.portfolio.positions.keys()):
                order_target(stock, 0)
        # return
        
def dp_stoploss(kernel=2, n=10, zs=0.03):
    '''
    方法1：当大盘N日均线(默认60日)与昨日收盘价构成“死叉”，则发出True信号
    方法2：当大盘N日内跌幅超过zs，则发出True信号
    '''
    # 止损方法1：根据大盘指数N日均线进行止损
    if kernel == 1:
        t = n+2
        hist = attribute_history('000300.XSHG', t, '1d', 'close', df=False)
        temp1 = sum(hist['close'][1:-1])/float(n)
        temp2 = sum(hist['close'][0:-2])/float(n)
        close1 = hist['close'][-1]
        close2 = hist['close'][-2]
        if (close2 > temp2) and (close1 < temp1):
            return True
        else:
            return False
    # 止损方法2：根据大盘指数跌幅进行止损
    elif kernel == 2:
        hist1 = attribute_history('000300.XSHG', n, '1d', 'close',df=False)
        if ((1-float(hist1['close'][-1]/hist1['close'][0])) >= zs):
            return True
        else:
            return False