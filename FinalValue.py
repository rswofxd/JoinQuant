'''
=================================================
总体回测前设置参数和回测
=================================================
'''
def initialize(context):
    set_params()    #1设置策参数
    set_variables() #2设置中间变量
    set_backtest()  #3设置回测条件

#1 设置参数
def set_params():
    # 设置基准收益
    set_benchmark('000300.XSHG') 
    g.lag = 20
    g.hour = 14
    g.minute = 53
    
    g.hs =  '000300.XSHG' #300指数
    g.zz =  '000905.XSHG'#500指数
        
    g.ETF300 = '510300.XSHG'#'510300.XSHG'
    g.ETF500 = '510500.XSHG'#'510500.XSHG'

    g.cash = 10,0000
    g.invest = g.cash * 2/3
    g.industry_invest = g.invest * 3%

    g,count = 20
    g.stocks = get_index_stocks('000300.XSHG')

    q = query(\
        valuation.code, valuation.market_cap, valuation.pe_ratio, valuation.pb_ratio\
    ).filter(\
        valuation.code.in_(g.stocks),
        valuation.pe_ratio < 20,
        valuation.pb_ratio < 2\
    ).order_by(\
        valuation.market_cap.asc()\
    ).limit(\
        g.count\
    )

    # 获取所选取股票财务数据
    df = get_fundamentals(q)

    # 列出所选股票的股票代码，并赋值给全局股票变量g.stocks，获得最终选股列表
    g.stocks = list(df['code'])

    # 设置股票池，该函数已废弃
    set_universe(list(df['code']))


#2 设置中间变量
def set_variables():
    return

#3 设置回测条件
def set_backtest():
    set_option('use_real_price', True) #用真实价格交易
    log.set_level('order', 'error')



'''
=================================================
每天开盘前
=================================================
'''
#每天开盘前要做的事情
def before_trading_start(context):
    set_slip_fee(context) 

#4 
# 根据不同的时间段设置滑点与手续费

def set_slip_fee(context):
    # 将滑点设置为0
    set_slippage(FixedSlippage(0)) 
    # 根据不同的时间段设置手续费
    dt=context.current_dt
    
    if dt>datetime.datetime(2013,1, 1):
        set_commission(PerTrade(buy_cost=0.0003, sell_cost=0.0013, min_cost=5)) 
        
    elif dt>datetime.datetime(2011,1, 1):
        set_commission(PerTrade(buy_cost=0.001, sell_cost=0.002, min_cost=5))
            
    elif dt>datetime.datetime(2009,1, 1):
        set_commission(PerTrade(buy_cost=0.002, sell_cost=0.003, min_cost=5))
                
    else:
        set_commission(PerTrade(buy_cost=0.003, sell_cost=0.004, min_cost=5))




'''
=================================================
每日交易时
=================================================
''' 
def handle_data(context, data):
    # 获得当前时间
    hour = context.current_dt.hour
    minute = context.current_dt.minute
    
    # 每天收盘时调整仓位
    if hour == g.hour and minute == g.minute:
        signal = get_signal(context)
        
        if signal == 'sell_the_stocks':
            sell_the_stocks(context)
        elif signal >0 :
            buy_the_stocks(context,signal)

#5
#获取信号
def get_signal(context):    
    for stock in g.stocks:
        #查询每只股票的pb，pe值
        pb = query(valuation.pb_ratio).filter(valuation.code.in_(stock))
        pe = query(valuation.pe_ratio).filter(valuation.code.in_(stock))
        #计算投资胜算概率p
        if (pb <= 1 and pe <=10):
            p = 0.95
        elif (pb >1 and pb <=1.5) and (pe >10 and pe <=15):
            p = 0.8
        elif (pb >1.5 and pb <=2) and (pe >15 and pe <=20):
            p = 0.8
        elif (pb >2 and pe >20):
            p = price_rise(stock,365)
        else:
            p = 0.5
        #计算绝对胜算概率x
        x = 2*p -1
        return x


    #沪深300与中证500的当日收盘价
    hs300,cp300 = getStockPrice(g.hs, g.lag)
    zz500,cp500  = getStockPrice(g.zz, g.lag)
        
    #计算前20日变动
    hs300increase = (cp300 - hs300) / hs300
    zz500increase = (cp500 - zz500) / zz500
        
    hold300 = context.portfolio.positions[g.ETF300].total_amount
    hold500 = context.portfolio.positions[g.ETF500].total_amount
    
    if (hs300increase<=0 and hold300>0) or (zz500increase<=0 and hold500>0):
        return 'sell_the_stocks'
    elif hs300increase>zz500increase and hs300increase>0 and (hold300==0 and hold500==0):
        return 'ETF300'
    elif zz500increase>hs300increase and zz500increase>0 and (hold300==0 and hold500==0):
        return 'ETF500'

#6
#取得股票某个区间内的所有收盘价（用于取前20日和当前收盘价）
def getStockPrice(stock, interval):
    h = attribute_history(stock, interval, unit='1d', fields=('close'), skip_paused=True)
    return (h['close'].values[0],h['close'].values[-1])


def price_rise(stock,interval):
    low_price = get_price(stock, count = interval, frequency='daily', fields=['low'])
    current_price = getStockPrice(stock, 2)
    ratio = current_price / low_price
    if (ratio >= 1.0 and ratio < 2.0):
        return 2
    elif (atio >= 2.0 and ratio < 3.0):
        return 3
    elif (atio >= 3.0 and ratio < 4.0):
        return 4
    elif (atio >= 4.0 and ratio < 5.0):
        return 5
    else:
        return 6
#7
#卖出股票
def sell_the_stocks(context):
    for stock in context.portfolio.positions.keys():
        return (log.info("Selling %s" % stock), order_target_value(stock, 0))

#8
#买入股票
def buy_the_stocks(context,signal):
    return (log.info("Buying %s"% signal ),order_value(eval('g.%s'% signal), context.portfolio.cash))
    
'''
=================================================
每日收盘后（本策略中不需要）
=================================================
'''  
def after_trading_end(context):
    return