def initialize(context): #contest对象参数传入账户持仓信息进行初始化
	# 全局对象g存储需要被pickle.dumps()方法序列化的全局变量，pickle.dumps()为python标准库方法
	# 定义股票数量
	g.count = 20
	
	# 获取行业成分股，C39表示计算机通信行业....,其中get_industry_stocks()函数为平台集成的第三方数据库查询API接口函数
	g.stock = get_industry_stocks('C39')+get_industry_stocks('I64')\
		+get_industry_stocks('I65')+get_industry_stocks('R85')\
		+get_industry_stocks('R86')
	
	# query(valuation)为SQL数据库查询方法，valuation为一具有股票市值，市盈率等属性变量的对象，即数据库表单值
	# 进行选股，连接SQL数据库查询股票代码，相应市值，市盈率；然后过滤选取特定行业的，并且市盈率小于20的股票；再然后按照总市值排序选取后15只；
	# 最后返回最多20只股票，完成选股
	q = query(\
		valuation.code, valuation.market_cap, valuation.pe_ratio\
	).filter(\
		valuation.code.in_(g.stock),
		valuation.pe_ratio < 20\
	).order_by(\
		valuation.market_cap.asc()\
	).limit(\
		g.count\
	)

	# 获取所选取股票财务数据
	df = get_fundamentals(q)

	# 列出所选股票的股票代码，并赋值给全局股票变量g.stock，获得最终选股列表
	g.stock = list(df['code'])

	# 设置股票池，该函数已废弃
	set_universe(list(df['code']))

	# 设置资金池1000000
	g.cash = 1000000

def handle_data(context,data):
    # if context.portfolio.positions.keys() !=[]:
    #     for stock in context.portfolio.positions.keys():
    #         if stock not in g.stock:
    #             order_target_value(stock, 0)
    # 指数止损
    # 获取上证指数000001.XSHG（平安银行代码：000001.XSHE）历史数据，返回2行结果，单位时间1天，收盘价，
    # 该函数为模拟回测专用，返回值为字典dict＝｛key：value｝，key为股票代码，value为数组
    hist1 = attribute_history('000001.XSHG',2,'1d','close',df=False)
    # 计算并打印回撤指数＝（昨天收盘价－今天收盘价）／今天收盘价，大于0表示下跌，小于0表示上涨
    index_return = (hist1['close'][-1]-hist1['close'][0])/hist1['close'][0]
    print hist1,index_return
    # 1.1 如果上证指数上涨3%，则全部卖出止损，否则，对股票池中股票分别进行如下操作
    if  index_return <= -0.03:
        for stock in g.stock:
            order_target_value(stock,0) # 按照目标价值下单，即调整仓位到0元
            log.info("Sell %s for stoploss" %stock)
        return # 止损，返回并退出handle_data()函数
    for stock in g.stock: # 2. 非系统风险下，即index_return >= -0.03情况对各股票处理
    	his = history(6,'1d','close',[stock],df=False) # 获取股票池中各股票过去6天每天的平均收盘价，共返回6行数据，dict类型
    	cnt = 0
    	for i in range(len(his[stock])-1): # len()函数返回列表元素个数，i＝0～5
    		daily_returns = (his[stock][i+1] - his[stock][i])/his[stock][i] # 计算过去6天中，每天的涨跌情况
    		if daily_returns < 0:
    			cnt += 1
    	if cnt == 5:
    		return # 2.1 如果6天中全部下跌，则返回并退出handle_data()函数
    	
        # 2.2 大于5日平均或10日平均20%以上
    	current_price = data[stock].price # data对象即为SecurityUnitData对象，表示单位时间内股票数据
    	mavg5 = data[stock].mavg(5) # 获取过去5天收盘价平均值，mavg()为data对象的方法
    	print mavg5
    	mavg10 = data[stock].mavg(10) # 获取过去10天收盘价平均值
    	if current_price > 1.2*mavg5 or current_price > 1.2*mavg10:
    		return # 当前价大于5日平均或10日平均20%以上，则返回并退出handle_data()函数
    	
        # 2.3 建仓，5步法、将头寸5等分，每下跌2%加一部分
    	cash = context.portfolio.cash # portfolio表示subportfolios汇总账户信息
    	amount = int(g.cash/g.count*2/current_price/300)
    	returns = data[stock].returns # 获取股票单位时间收益，(close - preclose)/preclose，close表示当前收盘价，preclose表示之前收盘价
        # 收益率大于1%，且该股票多单仓位小于资金分配额度的50%，则投入所分配资金额度的1/5，positions表示多单或购买单
    	if returns > 0.01 and context.portfolio.positions[stock].amount < 300*amount and cash > 0:
    		order_value(stock,g.cash/g.count/5) # 按价值下单，购买相应资金的股票
    		log.info("Buying %s"%stock)
    	
        # 2.4 跌10%的严格止损, 或者整体收益大于10%（止盈）
    	cost = context.portfolio.positions[stock].avg_cost # 获取该股票所有买入价格的加权平均值
    	if cost != 0:
    	    security_returns = (current_price-cost)/cost # 计算该股票的收益率
            # 亏损大于5%，或者盈利大于15%，则空仓卖出，实现止损或者止赢
    	    if security_returns < -0.05 or security_returns > 0.15:
    	        order_target_value(stock,0) # 空仓出货
    	        log.info("Selling %s" % stock)
		#根据大盘止损
		
		#15分钟K线，连续4次收益率为正且收益率大于8%(暂不做分钟级）
#还未实现复利滚动